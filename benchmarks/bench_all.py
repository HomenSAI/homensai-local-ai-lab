"""Benchmark every model one at a time on the RTX 3080 (gateway must be stopped).
usage: python bench_all.py [--only name1,name2] [--skip-done]
Per model: drop OS cache -> llama-server -c 8192 (cold load time, VRAM, quality tasks) -> llama-bench -> ctx probes 16K/32K.
Writes results.jsonl (one line per model) and raw/<model>/<task>.json."""
import argparse, base64, json, os, re, subprocess, threading, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = "local/ai-server-llama-swap:260"
PORT = 8090
PRISM = "/opt/prism/"
from qtasks import TASKS
from coding_tasks import TASKS as CODE_TASKS

CODE = {t[0]: t for t in CODE_TASKS}
CODE_SYS = ("You are an expert Python developer. Reply with exactly one ```python code block that contains the complete "
            "implementation with all needed imports. Do not include tests, examples or explanations.")

# name, files (relative to /models), quant, mmproj, runtime, mode (plain|hybrid|reasoning), origin
MODELS = [
    ("Qwen3.5-9B-MTP", "Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf", "UD-Q4_K_XL", "Qwen3/mmproj-F16.gguf", "up", "hybrid", "было"),
    ("Qwen3.5-9B", "Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf", "Q5_K_S", None, "up", "hybrid", "было"),
    ("MiniCPM5-2B-Q8", "MiniCPM5/MiniCPM5-2B-Q8_0.gguf", "Q8_0", None, "up", "hybrid", "было"),
    ("MiniCPM5-2B-Q4", "MiniCPM5/MiniCPM5-2B-Q4_K_M.gguf", "Q4_K_M", None, "up", "hybrid", "было"),
    ("Spark-X2.5-4B-Q8", "Spark/Spark-X2.5-4B-Q8_0.gguf", "Q8_0", None, "up", "hybrid", "было"),
    ("Spark-X2.5-4B-Q4", "Spark/Spark-X2.5-4B-Q4_K_M.gguf", "Q4_K_M", None, "up", "hybrid", "было"),
    ("Bonsai-2-27B", "Ternary-Bonsai-2-27B-PTQ1_0.gguf", "PTQ1_0", None, "prism", "hybrid", "было"),
    ("Qwen3-VL-8B", "Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf", "Q4_K_M",
     "Qwen-Image-2.1/text_encoder/mmproj-Qwen3VL-8B-Instruct-F16.gguf", "up", "plain", "было"),
    ("Qwen3-14B", "cand/Qwen3-14B/Qwen3-14B-Q4_K_M.gguf", "Q4_K_M", None, "up", "hybrid", "новая"),
    ("Qwen3-8B", "cand/Qwen3-8B/Qwen3-8B-Q4_K_M.gguf", "Q4_K_M", None, "up", "hybrid", "новая"),
    ("Gemma-3-12B", "cand/Gemma-3-12B-it/gemma-3-12b-it-Q4_K_M.gguf", "Q4_K_M", None, "up", "plain", "новая"),
    ("Phi-4-14B", "cand/Phi-4-14B/phi-4-Q4_K_M.gguf", "Q4_K_M", None, "up", "plain", "новая"),
    ("R1-Distill-Llama-8B", "cand/DeepSeek-R1-Distill-Llama-8B/DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf", "Q4_K_M", None, "up", "reasoning", "новая"),
    ("R1-Distill-Qwen-14B", "cand/DeepSeek-R1-Distill-Qwen-14B/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf", "Q4_K_M", None, "up", "reasoning", "новая"),
    ("Qwen2.5-Coder-7B", "cand/Qwen2.5-Coder-7B-Instruct/qwen2.5-coder-7b-instruct-q4_k_m.gguf", "Q4_K_M", None, "up", "plain", "новая"),
    ("Qwen2.5-Coder-14B", "cand/Qwen2.5-Coder-14B-Instruct/qwen2.5-coder-14b-instruct-q4_k_m.gguf", "Q4_K_M", None, "up", "plain", "новая"),
    ("Qwen2.5-VL-7B", "cand/Qwen2.5-VL-7B-Instruct/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf", "Q4_K_M",
     "cand/Qwen2.5-VL-7B-Instruct/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf", "up", "plain", "новая"),
    ("Llama-3.1-8B", "cand/Llama-3.1-8B-Instruct/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", "Q4_K_M", None, "up", "plain", "новая"),
    ("Mistral-Nemo-12B", "cand/Mistral-Nemo-12B-Instruct/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf", "Q4_K_M", None, "up", "plain", "новая"),
]


def sh(cmd, timeout=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    return p.returncode, p.stdout + p.stderr


def vram():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True).stdout.split()[0])
    except Exception:
        return 0


def gpu_util():
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split()[0])
    except Exception:
        return 0


class Peak:
    def __init__(self): self.v, self.run, self.util = 0, True, 0
    def __enter__(self):
        def loop():
            while self.run:
                self.v = max(self.v, vram()); self.util = max(self.util, gpu_util()); time.sleep(0.5)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a): self.run = False; self.t.join()


def drop_cache():
    sh(["docker", "run", "--rm", "--privileged", "alpine", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"], 120)


def binary(rt, tool):
    return (["env", "LD_LIBRARY_PATH=/opt/prism:/usr/local/cuda/lib64", PRISM + tool] if rt == "prism" else ["/app/" + tool])


def start_server(m, ctx, ngl, kv=None):
    name, f, q, mm, rt, mode, _ = m
    sh(["docker", "rm", "-f", "bench-srv"])
    args = ["-m", "/models/" + f, "-ngl", str(ngl), "-c", str(ctx), "-fa", "on", "--parallel", "1", "--jinja",
            "--host", "0.0.0.0", "--port", "8080", "--cache-ram", "0"]
    if rt == "up": args += ["--fit", "off"]
    if kv: args += ["-ctk", kv, "-ctv", kv]
    if mm: args += ["--mmproj", "/models/" + mm]
    rc, out = sh(["docker", "run", "-d", "--name", "bench-srv", "--gpus", "all", "-p", f"127.0.0.1:{PORT}:8080",
                  "-v", "llm-models-fast:/models:ro", "--entrypoint", binary(rt, "llama-server")[0], IMAGE]
                 + binary(rt, "llama-server")[1:] + args)
    t0 = time.time()
    while time.time() - t0 < 900:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
                if r.status == 200:
                    return True, round(time.time() - t0, 1), logs()
        except Exception:
            pass
        st = sh(["docker", "inspect", "-f", "{{.State.Running}}", "bench-srv"])[1].strip()
        if st != "true":
            return False, round(time.time() - t0, 1), logs()
        time.sleep(1)
    return False, 900, logs()


def logs():
    return sh(["docker", "logs", "bench-srv"])[1]


def offload(log):
    m = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log)
    return f"{m[-1][0]}/{m[-1][1]}" if m else "?"


def stop_server():
    sh(["docker", "rm", "-f", "bench-srv"])
    time.sleep(2)


def chat(m, messages, max_tokens, timeout=900):
    mode = m[5]
    body = {"messages": messages, "max_tokens": max_tokens, "seed": 42, "stream": False,
            "temperature": 0.6 if mode == "reasoning" else 0.2}
    if mode == "hybrid":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def probe_tg(m):
    try:
        body = {"messages": [{"role": "user", "content": "Count from 1 to 60 separated by commas."}], "max_tokens": 128,
                "temperature": 0, "seed": 42}
        if m[5] == "hybrid": body["chat_template_kwargs"] = {"enable_thinking": False}
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            return round(json.load(r).get("timings", {}).get("predicted_per_second", 0), 1)
    except Exception:
        return 0


def split_reasoning(msg):
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    m = re.search(r"<think>(.*?)</think>", content, flags=re.S)
    if m:
        reasoning += m.group(1); content = content.replace(m.group(0), "")
    return content.strip(), reasoning


def extract_code(text):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return (max(blocks, key=len) if blocks else text).strip()


def quality(m, rawdir):
    rows = []
    maxtok = 6000 if m[5] == "reasoning" else 1500
    for tid, cat, prompt, grader, kind in TASKS:
        if kind.startswith("image:") and (not m[3] or not os.path.isfile(os.path.join(HERE, "images", kind[6:]))):
            continue
        if kind.startswith("code:"):
            ct = CODE[kind[5:]]
            messages = [{"role": "system", "content": CODE_SYS}, {"role": "user", "content": ct[2]}]
        elif kind.startswith("image:"):
            b64 = base64.b64encode(open(os.path.join(HERE, "images", kind[6:]), "rb").read()).decode()
            messages = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
                                                     {"type": "text", "text": prompt}]}]
        else:
            messages = [{"role": "user", "content": prompt}]
        row = {"task": tid, "cat": cat}
        try:
            r = chat(m, messages, maxtok)
            ans, reasoning = split_reasoning(r["choices"][0]["message"])
            tm = r.get("timings", {})
            row.update(tokens=r["usage"]["completion_tokens"], prompt_tokens=r["usage"]["prompt_tokens"],
                       reasoning_chars=len(reasoning), finish=r["choices"][0].get("finish_reason"),
                       tg=round(tm.get("predicted_per_second", 0), 1), pp=round(tm.get("prompt_per_second", 0), 1))
            if kind.startswith("code:"):
                os.makedirs(os.path.join(HERE, "gen", m[0]), exist_ok=True)
                open(os.path.join(HERE, "gen", m[0], kind[5:] + ".py"), "w", encoding="utf-8").write(extract_code(ans))
                row.update(score=None, max=1, reason="проверяется тестами")
            else:
                s, mx, why = grader(ans)
                row.update(score=s, max=mx, reason=why)
            json.dump({"messages": messages if not kind.startswith("image:") else "image:" + kind[6:], "answer": ans,
                       "reasoning": reasoning, "raw_usage": r.get("usage"), "timings": tm},
                      open(os.path.join(rawdir, tid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception as e:
            row.update(score=0, max=5 if tid in ("ru_sum", "ru_tr", "vi_desc") else 1, reason="ошибка: " + str(e)[:120])
        rows.append(row)
        print(f"   {tid}: {row.get('score')}/{row.get('max')} tok={row.get('tokens')} {row.get('reason', '')[:70]}", flush=True)
    return rows


def bench(m, ngl):
    rt = m[4]
    cmd = ["docker", "run", "--rm", "--gpus", "all", "-v", "llm-models-fast:/models:ro", "--entrypoint",
           binary(rt, "llama-bench")[0], IMAGE] + binary(rt, "llama-bench")[1:] + \
          ["-m", "/models/" + m[1], "-ngl", str(ngl), "-fa", "1", "-p", "512", "-n", "128", "-r", "3", "-o", "json"]
    with Peak() as pk:
        rc, out = sh(cmd, 1800)
    try:
        data = json.loads(out[out.index("["):out.rindex("]") + 1])
        pp = next(x["avg_ts"] for x in data if x.get("n_prompt") == 512 and x.get("n_gen") == 0)
        tg = next(x["avg_ts"] for x in data if x.get("n_gen") == 128 and x.get("n_prompt") == 0)
        return round(pp, 1), round(tg, 1), pk.v
    except Exception:
        print("   bench parse failed:", out[-300:], flush=True)
        return None, None, pk.v


def run_model(m):
    name = m[0]
    rawdir = os.path.join(HERE, "raw", name); os.makedirs(rawdir, exist_ok=True)
    res = {"model": name, "file": m[1], "quant": m[2], "mmproj": m[3], "runtime": m[4], "mode": m[5], "origin": m[6]}
    sz = sh(["docker", "run", "--rm", "-v", "llm-models-fast:/models:ro", "alpine", "stat", "-c", "%s",
             "/models/" + m[1]] + (["/models/" + m[3]] if m[3] else []))[1].split()
    res["size_gb"] = round(sum(int(x) for x in sz if x.isdigit()) / 1e9, 2)
    print(f"=== {name} ({res['size_gb']} GB, {m[2]})", flush=True)
    drop_cache()
    base = vram()
    ngl = 99
    for ngl in (99, 40, 32, 24, 16):
        with Peak() as pk:
            ok, load_s, log = start_server(m, 8192, ngl)
        if ok:
            break
        stop_server()
    res.update(vram_base=base, ngl=ngl, fits_gpu=(ngl == 99), load_s=load_s if ok else None,
               offload=offload(log), load_ok=ok)
    if not ok:
        res["error"] = log[-400:]
        print("   LOAD FAILED", log[-200:], flush=True)
        return res
    res["vram_loaded_8k"] = vram()
    with Peak() as pk:
        res["quality"] = quality(m, rawdir)
    res["vram_peak_8k"] = pk.v
    stop_server()
    res["pp"], res["tg"], res["vram_bench"] = bench(m, ngl)
    print(f"   bench pp={res['pp']} tg={res['tg']} vram={res['vram_bench']} load={load_s}s offload={res['offload']}", flush=True)
    ctx = {"8192": {"ok": True, "kv": "f16", "vram": res["vram_loaded_8k"]}}
    for c in (16384, 32768):
        got = None
        for kv in ("f16", "q8_0"):
            ok2, _, log2 = start_server(m, c, ngl, None if kv == "f16" else kv)
            v, tgp = vram(), probe_tg(m) if ok2 else 0
            spill = bool(res.get("tg")) and tgp < 0.6 * res["tg"]
            stop_server()
            if ok2 and v < 10240 - 100 and not spill:
                got = {"ok": True, "kv": kv, "vram": v, "tg": tgp}; break
            if ok2:
                got = got or {"ok": False, "why": f"перелив в системную память (VRAM {v}, tg {tgp})"}
        ctx[str(c)] = got or {"ok": False}
        print(f"   ctx {c}: {ctx[str(c)]}", flush=True)
    tgs = sorted(q["tg"] for q in res.get("quality", []) if q.get("tg"))
    tg8 = tgs[len(tgs) // 2] if tgs else 0
    ctx["8192"]["tg"] = tg8
    if res.get("tg") and tg8 < 0.6 * res["tg"]:
        ctx["8192"] = {"ok": False, "why": f"перелив при 8K (tg {tg8} против {res['tg']} в llama-bench)", "tg": tg8}
    res["ctx"] = ctx
    res["max_ctx"] = max([int(k) for k, v in ctx.items() if v.get("ok")] or [0])
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--skip-done", action="store_true")
    ap.add_argument("--ctx-redo", action="store_true")
    a = ap.parse_args()
    if a.ctx_redo:
        rows = [json.loads(l) for l in open(os.path.join(HERE, "results.jsonl"), encoding="utf-8")]
        byname = {mm[0]: mm for mm in MODELS}
        for r in rows:
            if r.get("ctx", {}).get("32768", {}).get("tg") is not None or not r.get("load_ok"):
                continue
            m = byname[r["model"]]; ngl = r["ngl"]
            tgs = sorted(q["tg"] for q in r.get("quality", []) if q.get("tg")); tg8 = tgs[len(tgs) // 2] if tgs else 0
            ctx = {"8192": {"ok": tg8 >= 0.6 * (r.get("tg") or 0), "kv": "f16", "vram": r.get("vram_loaded_8k"), "tg": tg8}}
            if not ctx["8192"]["ok"]: ctx["8192"]["why"] = f"перелив при 8K (tg {tg8} против {r.get('tg')})"
            for c in (16384, 32768):
                got = None
                for kv in ("f16", "q8_0"):
                    ok2, _, _ = start_server(m, c, ngl, None if kv == "f16" else kv)
                    v, tgp = vram(), probe_tg(m) if ok2 else 0
                    stop_server()
                    if ok2 and v < 10140 and tgp >= 0.6 * (r.get("tg") or 0):
                        got = {"ok": True, "kv": kv, "vram": v, "tg": tgp}; break
                    if ok2: got = got or {"ok": False, "why": f"перелив (VRAM {v}, tg {tgp})"}
                ctx[str(c)] = got or {"ok": False}
            r["ctx"] = ctx; r["max_ctx"] = max([int(k) for k, v in ctx.items() if v.get("ok")] or [0])
            print(f"CTX-REDO {r['model']}: {r['max_ctx']} {ctx}", flush=True)
        open(os.path.join(HERE, "results.jsonl"), "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in rows))
        raise SystemExit
    done = set()
    out = os.path.join(HERE, "results.jsonl")
    if a.skip_done and os.path.exists(out):
        done = {json.loads(l)["model"] for l in open(out, encoding="utf-8")}
    for m in MODELS:
        if a.only and m[0] not in a.only.split(","):
            continue
        if m[0] in done:
            continue
        if m[6] == "новая":
            code, o = sh(["docker", "run", "--rm", "-v", "llm-models-fast:/models:ro", "alpine", "test", "-f", "/models/" + m[1]])
            if code != 0:
                print(f"=== {m[0]}: file not downloaded yet, skipped", flush=True)
                continue
        t = time.time()
        r = run_model(m)
        r["minutes"] = round((time.time() - t) / 60, 1)
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"DONE {m[0]} in {r['minutes']} min", flush=True)
    print("ALL-FINISHED", flush=True)
