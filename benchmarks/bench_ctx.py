"""Step 2: maximum STABLE context per model using VRAM + system RAM together (RTX 3080 10 GB + 32 GB RAM).
For every model the KV-cache placement is searched from fast to slow:
  gpu-f16  -> KV in VRAM, full precision
  gpu-q8   -> KV in VRAM, q8_0
  gpu-q4   -> KV in VRAM, q4_0
  ram-q8   -> KV cache in system RAM (--no-kv-offload), q8_0  (huge contexts, slower)
Context ladder 8K..native max (powers of two, then one midpoint refinement). A step counts as STABLE when the server starts,
the host RAM guard is not tripped, all 3 hidden facts are recalled at ~80% fill, and speed does not collapse.
usage: python bench_ctx.py [--only A,B] [--skip-done] [--cap 262144]"""
import argparse, json, os, re, sys, time, urllib.request
import bench_top as T
import bench_all as B
import mneedle as N

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_ctx.jsonl")
TRIALS = os.path.join(HERE, "results_ctx_trials.jsonl")      # every finished probe, so a stopped run resumes without repeating work
CACHE = {}
if os.path.exists(TRIALS):
    for _l in open(TRIALS, encoding="utf-8"):
        _r = json.loads(_l); CACHE[(_r["model"], _r["cfg"], _r["ctx"])] = _r

CFGS = [("gpu-f16", "f16", False), ("gpu-q8", "q8_0", False), ("gpu-q4", "q4_0", False)]   # ram-q8 removed 2026-10-02: user rule, only GPU runs count (it also hung LFM2.5)
LADDER = [65536, 131072, 262144]      # user requirement: context must be at least 64K, so smaller steps are not probed
YARN = None                            # (scale, original ctx) while a model with native context < 64K is probed with YaRN scaling
BASE = N.corpus()
MAX_PREFILL_GPU = 480     # a healthy GPU layout prefills 200K tokens in ~1-3 min; slower means VRAM spilled into RAM
MAX_PREFILL_RAM = 1500    # KV cache in system RAM is slower by design
VRAM_LIMIT_MIB = 9990


def start(t, ctx, kv, nkvo):
    name, f, q, mm, mode, place, rt = t
    B.sh(["docker", "rm", "-f", "bench-srv"])
    args = ["-m", "/models/" + f, "-c", str(ctx), "-fa", "on", "--parallel", "1", "--jinja", "--host", "0.0.0.0", "--port", "8080",
            "--cache-ram", "0", "-ngl", "99", "-ctk", kv, "-ctv", kv]
    if rt == "up": args += ["--fit", "off"]
    if nkvo: args += ["--no-kv-offload"]
    if YARN: args += ["--rope-scaling", "yarn", "--rope-scale", str(YARN[0]), "--yarn-orig-ctx", str(YARN[1])]
    B.sh(["docker", "run", "-d", "--name", "bench-srv", "--gpus", "all", "-p", f"127.0.0.1:{B.PORT}:8080",
          "-v", "llm-models-fast:/models:ro", "--entrypoint", B.binary(rt, "llama-server")[0], B.IMAGE] + B.binary(rt, "llama-server")[1:] + args)
    t0 = time.time()
    while time.time() - t0 < 900:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{B.PORT}/health", timeout=3) as r:
                if r.status == 200: return True, round(time.time() - t0, 1)
        except Exception: pass
        if B.sh(["docker", "inspect", "-f", "{{.State.Running}}", "bench-srv"])[1].strip() != "true": return False, round(time.time() - t0, 1)
        time.sleep(1)
    return False, 900


def needle_test(t, ctx, limit=1500):
    """~80% fill, 3 hidden facts at 10/50/90% depth; returns (hits, prompt_tokens, pp, tg, wall)."""
    sample = BASE[:24000]
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/tokenize", json.dumps({"content": sample}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: cpt = len(sample) / max(1, len(json.load(r)["tokens"]))
    text = BASE[: int((ctx * 0.8 - 700) * cpt)]
    for depth, sent, _, _ in reversed(N.NEEDLES):
        pos = text.rfind("\n", 0, int(len(text) * depth)); text = text[:pos] + "\n" + sent + "\n" + text[pos:]
    q = "\n".join(f"{i+1}. {n[2]}" for i, n in enumerate(N.NEEDLES))
    prompt = ("Below is a long document with three NOTE-* sentences hidden in it.\n\n" + text +
              "\n\n=== END ===\nAnswer using only the hidden NOTE sentences, one short line each, format '1. answer':\n" + q)
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 120, "temperature": 0, "seed": 42}
    if t[4] == "hybrid": body["chat_template_kwargs"] = {"enable_thinking": False}
    t0 = time.time()
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=limit + 60) as r: d = json.load(r)
    ans = d["choices"][0]["message"].get("content") or ""
    tm = d.get("timings", {})
    return sum(n[3] in ans for n in N.NEEDLES), d["usage"]["prompt_tokens"], round(tm.get("prompt_per_second", 0), 1), \
        round(tm.get("predicted_per_second", 0), 1), round(time.time() - t0, 1)


def trial(t, ctx, cfg, ref_tg):
    label, kv, nkvo = cfg
    hit = CACHE.get((t[0], label, ctx))
    if hit:
        print(f"   {label} ctx {ctx}: {'OK ' if hit['stable'] else 'FAIL'} (из сохранённого) hits={hit.get('hits')} tok={hit.get('prompt_tokens')} tg={hit.get('tg')}", flush=True)
        return hit
    with T.Guard() as g, B.Peak() as pk:
        ok, load_s = start(t, ctx, kv, nkvo)
        row = {"ctx": ctx, "cfg": label, "started": ok, "load_s": load_s}
        if ok and not g.killed:
            try:
                hits, pt, pp, tg, wall = needle_test(t, ctx, MAX_PREFILL_RAM if nkvo else MAX_PREFILL_GPU)
                row.update(hits=hits, prompt_tokens=pt, pp=pp, tg=tg, wall_s=wall)
            except Exception as e:
                row["error"] = str(e)[:120]
    row.update(vram_peak=pk.v, gpu_util_peak=pk.util, host_free_min_gb=round(g.min_free, 2), guard_killed=g.killed)
    B.stop_server()
    min_tg = 3.0 if nkvo else 0.4 * ref_tg
    vram_ok = nkvo or row["vram_peak"] <= VRAM_LIMIT_MIB          # keep >= 250 MiB of VRAM free for the desktop and spikes
    row["spill"] = bool(not nkvo and (row["vram_peak"] > VRAM_LIMIT_MIB or (row.get("started") and row.get("hits") is None and row["vram_peak"] >= 9700)
                        or (row.get("tg", 99) < 10 and row["vram_peak"] >= 9700)))   # VRAM overflow into system RAM (Windows sysmem fallback)
    row["stable"] = bool(row.get("started") and not g.killed and row.get("hits") == 3 and row.get("tg", 0) >= min_tg and (nkvo or row.get("gpu_util_peak", 100) >= 20)
                         and row.get("wall_s", 1e9) <= (MAX_PREFILL_RAM if nkvo else MAX_PREFILL_GPU) and vram_ok)
    if not row["stable"]:
        row["why"] = ("RAM-сторож" if g.killed else "не запустилась" if not row.get("started") else row.get("error") or ("GPU почти не загружена (пик %d%%)" % row["gpu_util_peak"] if row.get("hits") == 3 and row.get("gpu_util_peak", 100) < 20 else None) or
                      ("мало видеопамяти: пик %d МиБ" % row["vram_peak"] if not vram_ok and row.get("hits") == 3 else None) or
                      (f"факты {row.get('hits')}/3" if row.get("hits") != 3 else f"медленно: tg {row.get('tg')}, {row.get('wall_s')} с"))
    print(f"   {label} ctx {ctx}: {'OK ' if row['stable'] else 'FAIL'} hits={row.get('hits')} tok={row.get('prompt_tokens')} pp={row.get('pp')} "
          f"tg={row.get('tg')} wall={row.get('wall_s')}s vram={row['vram_peak']} ramfree={row['host_free_min_gb']} {row.get('why', '')}", flush=True)
    row["model"] = t[0]
    with open(TRIALS, "a", encoding="utf-8") as f: f.write(json.dumps(row, ensure_ascii=False) + chr(10))
    CACHE[(t[0], label, ctx)] = row
    return row


def probe_native(t):
    ok, _ = start(t, 8192, "f16", False)
    if not ok: B.stop_server(); return None
    native = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{B.PORT}/v1/models", timeout=20) as r:
            native = int(json.load(r)["data"][0]["meta"]["n_ctx_train"])
    except Exception:
        m = re.findall(r"n_ctx_train\s*=\s*(\d+)", B.logs()); native = int(m[-1]) if m else None
    B.stop_server()
    return native


def run(t, cap, ref):
    name = t[0]
    print(f"=== {name}", flush=True)
    global YARN
    native = probe_native(t)
    YARN = None
    if native and native < LADDER[0]:                                    # native window below 64K: extend it with YaRN and let the recall test judge
        scale = 4 if native * 4 >= 131072 else 8
        YARN = (scale, native)
        print(f"   native context {native} < 64K: probing with YaRN scale {scale}", flush=True)
    top = min((native * YARN[0]) if YARN else (native or 131072), cap)
    ladder = [c for c in LADDER if c <= top] + ([top] if top not in LADDER and top > LADDER[0] else [])
    res = {"model": name, "native_ctx": native, "cap": top, "ref_tg_8k": ref, "cfgs": {}, "trials": [], "yarn": YARN[0] if YARN else None}
    start_from = 0
    for cfg in CFGS:
        best = None; bad = None
        for c in [x for x in ladder if x >= start_from]:                 # a slower layout can only help: resume at the last good size
            r = trial(t, c, cfg, ref); res["trials"].append(r)
            if r["stable"]: best = r
            else: bad = c; break
        if best and bad and bad > best["ctx"] * 1:                      # one midpoint refinement between last OK and first FAIL
            mid = (best["ctx"] + bad) // 2 // 4096 * 4096
            if mid > best["ctx"] + 4096:
                r = trial(t, mid, cfg, ref); res["trials"].append(r)
                if r["stable"]: best = r
        if best: start_from = max(start_from, best["ctx"])
        res["cfgs"][cfg[0]] = {"best_ctx": best["ctx"] if best else 0, "tg": best and best["tg"], "pp": best and best["pp"],
                               "vram": best and best["vram_peak"], "wall_s": best and best["wall_s"]}
        if best and best["ctx"] >= top: break                            # already at the native maximum with this (faster) layout
    ok = [(v["best_ctx"], -i, k) for i, (k, v) in enumerate(res["cfgs"].items()) if v["best_ctx"]]
    if ok:
        mc, _, k = max(ok); res["best_ctx"], res["best_cfg"] = mc, k
        res["recommended_cfg"] = next(k2 for k2, v in res["cfgs"].items() if v["best_ctx"] >= min(mc, 65536)) if mc else k
    res["meets_64k"] = bool(res.get("best_ctx", 0) >= LADDER[0])
    YARN = None
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--skip-done", action="store_true"); ap.add_argument("--cap", type=int, default=262144)
    a = ap.parse_args()
    speed = {}
    for l in open(os.path.join(HERE, "results_all.jsonl"), encoding="utf-8"):
        r = json.loads(l); speed[r["model"]] = r.get("tg") or 30.0
    done = {json.loads(l)["model"] for l in open(OUT, encoding="utf-8")} if a.skip_done and os.path.exists(OUT) else set()
    for t in T.TOP:
        if (a.only and t[0] not in a.only.split(",")) or t[0] in done or t[0] not in speed: continue
        t0 = time.time()
        try: r = run(t, a.cap, speed[t[0]])
        except Exception as e:
            B.stop_server(); r = {"model": t[0], "error": "crash: " + str(e)[:200]}; print("   MODEL ERROR", str(e)[:150], flush=True)
        r["minutes"] = round((time.time() - t0) / 60, 1)
        open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"DONE {t[0]} best {r.get('best_ctx')} via {r.get('best_cfg')} in {r['minutes']} min", flush=True)
    print("CTX-FINISHED", flush=True)
