"""Multi-needle long-context benchmark against a llama-swap gateway.
usage: mneedle.py --port 8080 --label A-live --plan "Model:ctx,Model:ctx" [--fill 0.85] [--timeout 1500]
Each run appends one JSON line to results.jsonl (label, model, ctx, tokens, needles hit, pp/tg speed, VRAM).
"""
import argparse, glob, json, os, random, subprocess, sys, time, urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")
import sysconfig
LIB = sysconfig.get_paths()['stdlib']   # filler text = Python stdlib sources (PSF licence), rebuilt locally


def corpus():
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus_cache.txt")   # frozen copy: identical text on host and in the bench-runner container
    if os.path.exists(cache): return open(cache, encoding="utf-8").read()
    files = sorted(glob.glob(os.path.join(LIB, "*.py")) + glob.glob(os.path.join(LIB, "*", "*.py")))
    random.Random(7).shuffle(files)
    parts, size = [], 0
    for f in files:
        try:
            t = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        parts.append(f"# ---- {os.path.basename(f)} ----\n{t[:6000]}")
        size += len(parts[-1])
        if size > 1_600_000:
            break
    return "\n".join(parts)


NEEDLES = [  # (depth, sentence, question, answer)
    (0.10, "NOTE-A: The access code of the Orion vault is 48213-KLM.", "What is the access code of the Orion vault?", "48213-KLM"),
    (0.50, "NOTE-B: The maintenance window for cluster Helios starts every Tuesday at 03:47 UTC.", "When does the maintenance window for cluster Helios start?", "03:47"),
    (0.90, "NOTE-C: Engineer Marta Vollmer owns the Zephyr migration and her ticket number is QX-90417.", "What is the ticket number of the owner of the Zephyr migration?", "QX-90417"),
]


def call(port, path, body, timeout):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def chat(port, model, content, timeout, max_tokens=300):
    return call(port, "/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": content}],
                "max_tokens": max_tokens, "temperature": 0, "stream": False,
                "chat_template_kwargs": {"enable_thinking": False}}, timeout)


def chars_per_token(port, model, text):
    sample = text[:24000]
    try:
        r = call(port, f"/upstream/{model}/tokenize", {"content": sample}, 120)
        return len(sample) / max(1, len(r["tokens"]))
    except Exception:
        return 3.0


def vram():
    o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True, capture_output=True).stdout
    return int(o.strip().splitlines()[0])


def run(port, label, model, ctx, fill, timeout, base):
    row = {"label": label, "model": model, "ctx": ctx, "fill": fill, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    t0 = time.time()
    try:
        warm = chat(port, model, "Reply with the single word OK.", 900, 8)  # loads model
        row["load_s"] = round(time.time() - t0, 1)
        row["vram_idle_mib"] = vram()
        cpt = chars_per_token(port, model, base)
        budget_tokens = int(ctx * fill) - 900
        text = base[: int(budget_tokens * cpt)]
        for depth, sent, _, _ in reversed(NEEDLES):
            pos = text.rfind("\n", 0, int(len(text) * depth))
            text = text[:pos] + "\n" + sent + "\n" + text[pos:]
        q = "\n".join(f"{i+1}. {n[2]}" for i, n in enumerate(NEEDLES))
        prompt = ("Below is a long document (Python source files) with three NOTE-* sentences hidden in it.\n\n" + text +
                  "\n\n=== END ===\nAnswer these questions using only the hidden NOTE sentences, one short line each, format '1. answer':\n" + q)
        t1 = time.time()
        r = chat(port, model, prompt, timeout, 200)
        row["wall_s"] = round(time.time() - t1, 1)
        ans = (r["choices"][0]["message"].get("content") or "").strip()
        tm = r.get("timings", {})
        row.update(prompt_tokens=r["usage"]["prompt_tokens"], completion_tokens=r["usage"]["completion_tokens"],
                   pp_tps=round(tm.get("prompt_per_second", 0), 1), tg_tps=round(tm.get("predicted_per_second", 0), 1),
                   hits=[n[3] in ans for n in NEEDLES], answer=ans[:400], vram_peak_mib=vram(), status="ok")
        row["score"] = sum(row["hits"])
    except Exception as e:
        row.update(status="error", error=str(e)[:300], score=0, wall_s=round(time.time() - t0, 1))
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[{label}] {model} ctx={ctx} -> {row['status']} tok={row.get('prompt_tokens')} score={row.get('score')}/3 "
          f"pp={row.get('pp_tps')} tg={row.get('tg_tps')} vram={row.get('vram_peak_mib')} wall={row.get('wall_s')}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--label", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--fill", type=float, default=0.85)
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()
    base = corpus()
    print("corpus chars:", len(base), flush=True)
    for item in a.plan.split(","):
        m, c = item.rsplit(":", 1)
        run(a.port, a.label, m, int(c), a.fill, a.timeout, base)
