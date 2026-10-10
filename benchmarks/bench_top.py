"""Top-model benchmark for RTX 3080 10 GB + 32 GB RAM (run after the RAM upgrade and WSL memory change).
Models that fit run fully on GPU (-ngl 99); larger dense/MoE models use `--fit on`, which places layers and MoE
experts so the chosen context fits free VRAM (no sysmem spill). A guard kills the server if host RAM runs low.
usage: python bench_top.py [--only A,B] [--skip-done]   -> results_top.jsonl, raw/<model>/"""
import argparse, ctypes, json, os, subprocess, threading, time, urllib.request
import bench_all as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_all.jsonl")
MIN_HOST_FREE_GB = 2.0

# name, file, quant, mmproj, mode (plain|hybrid|reasoning), placement (gpu|fit)
NO_CTX = False
TOP = [  # name, file in volume, quant, mmproj, mode (plain|hybrid|reasoning), placement, runtime (up|prism)
    ("Qwen3.5-9B-MTP", "Qwen3/Qwen3.5-9B-UD-Q4_K_XL.gguf", "UD-Q4_K_XL", "Qwen3/mmproj-F16.gguf", "hybrid", "gpu", "up"),
    ("Qwen3.5-9B", "Qwen3/Qwen3.5-9B-Q5_K_S-4.60bpw.gguf", "Q5_K_S", None, "hybrid", "gpu", "up"),
    ("MiniCPM5-2B-Q8", "MiniCPM5/MiniCPM5-2B-Q8_0.gguf", "Q8_0", None, "hybrid", "gpu", "up"),
    ("MiniCPM5-2B-Q4", "MiniCPM5/MiniCPM5-2B-Q4_K_M.gguf", "Q4_K_M", None, "hybrid", "gpu", "up"),
    ("Spark-X2.5-4B-Q8", "Spark/Spark-X2.5-4B-Q8_0.gguf", "Q8_0", None, "hybrid", "gpu", "up"),
    ("Spark-X2.5-4B-Q4", "Spark/Spark-X2.5-4B-Q4_K_M.gguf", "Q4_K_M", None, "hybrid", "gpu", "up"),
    ("Bonsai-2-27B", "Ternary-Bonsai-2-27B-PTQ1_0.gguf", "PTQ1_0", None, "hybrid", "gpu", "prism"),
    ("Qwen3-VL-8B", "Qwen-Image-2.1/text_encoder/Qwen3VL-8B-Instruct-Q4_K_M.gguf", "Q4_K_M",
     "Qwen-Image-2.1/text_encoder/mmproj-Qwen3VL-8B-Instruct-F16.gguf", "plain", "gpu", "up"),
    ("Qwen3-8B", "cand/Qwen3-8B/Qwen3-8B-Q4_K_M.gguf", "Q4_K_M", None, "hybrid", "gpu", "up"),
    ("Gemma-3-12B", "cand/Gemma-3-12B-it/gemma-3-12b-it-Q4_K_M.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("R1-Distill-Llama-8B", "cand/DeepSeek-R1-Distill-Llama-8B/DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf", "Q4_K_M", None, "reasoning", "gpu", "up"),
    ("Qwen2.5-Coder-7B", "cand/Qwen2.5-Coder-7B-Instruct/qwen2.5-coder-7b-instruct-q4_k_m.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("Qwen2.5-VL-7B", "cand/Qwen2.5-VL-7B-Instruct/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf", "Q4_K_M",
     "cand/Qwen2.5-VL-7B-Instruct/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf", "plain", "gpu", "up"),
    ("Llama-3.1-8B", "cand/Llama-3.1-8B-Instruct/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("Mistral-Nemo-12B", "cand/Mistral-Nemo-12B-Instruct/Mistral-Nemo-Instruct-2407-Q4_K_M.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("Gemma-4-12B", "top/Gemma-4-12B-it/gemma-4-12b-it-Q4_K_M.gguf", "Q4_K_M", "top/Gemma-4-12B-it/mmproj-F16.gguf", "plain", "gpu", "up"),
    ("Gemma-4-12B-QAT", "top/Gemma-4-12B-it-QAT/gemma-4-12b-it-qat-q4_0.gguf", "QAT Q4_0",
     "top/Gemma-4-12B-it-QAT/mmproj-gemma-4-12b-it-qat-q4_0.gguf", "plain", "gpu", "up"),
    ("Gemma-4-E4B", "top/Gemma-4-E4B-it/gemma-4-E4B-it-Q4_K_M.gguf", "Q4_K_M", "top/Gemma-4-E4B-it/mmproj-F16.gguf", "plain", "gpu", "up"),
    ("LFM2.5-2.6B", "top/LFM2.5-2.6B/LFM2.5-2.6B-Q4_K_M.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("LFM2.5-8B-A1B", "top/LFM2.5-8B-A1B/LFM2.5-8B-A1B-Q4_K_M.gguf", "Q4_K_M", None, "plain", "gpu", "up"),
    ("MiMo-9B", "top/MiMo-V2.6-Distill-Qwen-9B/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M.gguf", "Q4_K_M", None, "hybrid", "gpu", "up"),
    ("MiMo-9B-MTP", "top/MiMo-V2.6-Distill-Qwen-9B-MTP/MiMo-V2.6-Distill-Qwen-9B-Q4_K_M-MTP.gguf", "Q4_K_M+MTP", None, "hybrid", "gpu", "up"),
    ("Ornith-1.5-9B", "top/Ornith-1.5-9B/Ornith-1.5-9B-Q4_K_M.gguf", "Q4_K_M", None, "hybrid", "gpu", "up"),
]
# not chat models, tested separately: top/Qwen3-Embedding-4B, top/Qwen3-Embedding-0.6B (RAG over drawings);
# MTP drafts for speculative decoding: top/Qwen3.8-27B/MTP/*, top/Gemma-4-26B-A4B-it/MTP/*


class MEM(ctypes.Structure):
    _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong)] + \
               [(f"x{i}", ctypes.c_ulonglong) for i in range(5)]


def host_free_gb():
    if not hasattr(ctypes, "windll"):      # runs inside the bench-runner container: WSL VM MemAvailable (caches are dropped by cache-dropper)
        for l in open("/proc/meminfo"):
            if l.startswith("MemAvailable:"): return int(l.split()[1]) / 2**20
    m = MEM(); m.l = ctypes.sizeof(MEM); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ap / 2**30


class Guard:
    def __init__(self): self.min_free, self.killed, self.run = host_free_gb(), False, True
    def __enter__(self):
        def loop():
            while self.run:
                f = host_free_gb(); self.min_free = min(self.min_free, f)
                if f < MIN_HOST_FREE_GB and not self.killed:
                    self.killed = True; subprocess.run(["docker", "rm", "-f", "bench-srv"], capture_output=True)
                time.sleep(0.5)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a): self.run = False; self.t.join()


def start(t, ctx, kv=None):
    name, f, q, mm, mode, place, rt = t
    B.sh(["docker", "rm", "-f", "bench-srv"])
    args = ["-m", "/models/" + f, "-c", str(ctx), "-fa", "on", "--parallel", "1", "--jinja", "--host", "0.0.0.0",
            "--port", "8080", "--cache-ram", "0"]
    args += (["-ngl", "99"] + (["--fit", "off"] if rt == "up" else [])) if place == "gpu" else ["--fit", "on", "-fitt", "512"]
    if kv: args += ["-ctk", kv, "-ctv", kv]
    if mm: args += ["--mmproj", "/models/" + mm]
    B.sh(["docker", "run", "-d", "--name", "bench-srv", "--gpus", "all", "-p", f"127.0.0.1:{B.PORT}:8080",
          "-v", "llm-models-fast:/models:ro", "--entrypoint", B.binary(rt, "llama-server")[0], B.IMAGE] + B.binary(rt, "llama-server")[1:] + args)
    t0 = time.time()
    while time.time() - t0 < 1200:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{B.PORT}/health", timeout=3) as r:
                if r.status == 200:
                    return True, round(time.time() - t0, 1)
        except Exception:
            pass
        if B.sh(["docker", "inspect", "-f", "{{.State.Running}}", "bench-srv"])[1].strip() != "true":
            return False, round(time.time() - t0, 1)
        time.sleep(1)
    return False, 1200


def chat(t, text, max_tokens):
    body = {"messages": [{"role": "user", "content": text}], "max_tokens": max_tokens, "temperature": 0, "seed": 42}
    if t[4] == "hybrid":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


FILL = "Библиотека открыла новый цифровой зал, и читатели записываются в студию звукозаписи заранее. "


def speed(t):
    """llama-bench equivalent through the server: ~512-token prompt, 128 generated tokens, 3 runs."""
    pps, tgs = [], []
    for i in range(3):
        d = chat(t, f"[{i}] " + FILL * 23 + "\nНапиши подробный рассказ об этой библиотеке.", 128)
        pps.append(d["timings"]["prompt_per_second"]); tgs.append(d["timings"]["predicted_per_second"])
    return round(sum(pps) / 3, 1), round(sum(tgs) / 3, 1)


def fill_probe(t, ctx):
    d = chat(t, FILL * int(ctx * 0.8 / 22) + "\nСколько раз встречается слово «студию»? Ответь одним числом.", 48)
    return d["usage"]["prompt_tokens"], round(d["timings"]["prompt_per_second"], 1), round(d["timings"]["predicted_per_second"], 1)


def as_bench_tuple(t):
    return (t[0], t[1], t[2], t[3], t[6], t[4], "прогон")


def run(t):
    name = t[0]
    rawdir = os.path.join(HERE, "raw", name); os.makedirs(rawdir, exist_ok=True)
    res = {"model": name, "file": t[1], "quant": t[2], "mmproj": t[3], "mode": t[4], "placement": t[5], "runtime": t[6], "origin": "прогон-32гб"}
    sz = B.sh(["docker", "run", "--rm", "-v", "llm-models-fast:/models:ro", "alpine", "stat", "-c", "%s", "/models/" + t[1]]
              + (["/models/" + t[3]] if t[3] else []))[1].split()
    res["size_gb"] = round(sum(int(x) for x in sz if x.isdigit()) / 1e9, 2)
    print(f"=== {name} ({res['size_gb']} GB, {t[5]})", flush=True)
    B.drop_cache()
    with Guard() as g, B.Peak() as pk:
        ok, load_s = start(t, 8192)
        res.update(load_ok=ok, load_s=load_s, vram_loaded_8k=B.vram())
        if ok:
            res["pp"], res["tg"] = speed(t)
            res["quality"] = B.quality(as_bench_tuple(t), rawdir)
    res.update(vram_peak_8k=pk.v, host_free_min_gb=round(g.min_free, 2), guard_killed=g.killed)
    B.stop_server()
    if not ok or g.killed:
        res["error"] = "сторож RAM" if g.killed else B.logs()[-400:]
        print(f"   FAILED: {res['error'][:200]}", flush=True)
        return res
    print(f"   8K: load {load_s}s pp {res['pp']} tg {res['tg']} VRAM {res['vram_peak_8k']} RAM free min {res['host_free_min_gb']}", flush=True)
    if NO_CTX:   # context limits are measured by bench_ctx.py (VRAM + RAM search with needle recall)
        res["ctx"] = {}; res["max_ctx"] = None
        return res
    ctx = {"8192": {"ok": True, "pp": res["pp"], "tg": res["tg"]}}
    for c in (16384, 32768, 65536):
        with Guard() as g2, B.Peak() as pk2:
            ok2, _ = start(t, c)
            pt, pp, tg = fill_probe(t, c) if ok2 and not g2.killed else (0, 0, 0)
        B.stop_server()
        good = ok2 and not g2.killed and pt > 0 and tg >= 0.5 * res["tg"]
        ctx[str(c)] = {"ok": good, "prompt_tokens": pt, "pp": pp, "tg": tg, "vram": pk2.v, "host_free_min_gb": round(g2.min_free, 2),
                       **({} if good else {"why": "сторож RAM" if g2.killed else f"tg {tg} < 50% от 8K" if ok2 else "не запустилась"})}
        print(f"   ctx {c}: {ctx[str(c)]}", flush=True)
        if not good:
            break
    res["ctx"] = ctx
    res["max_ctx"] = max(int(k) for k, v in ctx.items() if v["ok"])
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--skip-done", action="store_true"); ap.add_argument("--no-ctx", action="store_true")
    a = ap.parse_args()
    NO_CTX = a.no_ctx
    done = {json.loads(l)["model"] for l in open(OUT, encoding="utf-8")} if a.skip_done and os.path.exists(OUT) else set()
    for t in TOP:
        if (a.only and t[0] not in a.only.split(",")) or t[0] in done:
            continue
        if B.sh(["docker", "run", "--rm", "-v", "llm-models-fast:/models:ro", "alpine", "test", "-f", "/models/" + t[1]])[0] != 0:
            print(f"=== {t[0]}: not downloaded yet", flush=True); continue
        t0 = time.time()
        try:
            r = run(t)
        except Exception as e:      # one broken model must not stop the whole run
            B.stop_server()
            r = {"model": t[0], "file": t[1], "quant": t[2], "mmproj": t[3], "mode": t[4], "load_ok": False, "size_gb": 0,
                 "error": "crash: " + str(e)[:200]}
            print(f"   MODEL ERROR {t[0]}: {str(e)[:160]}", flush=True)
        r["minutes"] = round((time.time() - t0) / 60, 1)
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"DONE {t[0]} in {r['minutes']} min", flush=True)
    print("ALL-FINISHED", flush=True)


def eligible(models):
    """User rule 2026-10-02: only models with a stable GPU context >= 64K take part in the later phases (German fix, STEM, CAD).
    Models without a finished context result are kept (not yet decided); an extra allow-list in ctx_recheck.txt keeps models under re-examination."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_ctx.jsonl")
    res = {}
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            r = json.loads(l); res[r["model"]] = (r.get("best_ctx") or 0) >= 65536
    rc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ctx_recheck.txt")
    keep = set(open(rc, encoding="utf-8").read().split()) if os.path.exists(rc) else set()
    return [t for t in models if res.get(t[0], True) or t[0] in keep]
