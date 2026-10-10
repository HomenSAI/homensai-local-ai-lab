"""Final stability soak THROUGH THE GATEWAY (llama-swap, port 8080), GPU profiles only (image/video models are not part of it).
Per profile: load (swap), 3 fills of 95% of the profile context with 3 hidden facts (different text offsets, no prefix cache reuse),
a long generation at ~full context, image check for vision profiles, embeddings check. Watches VRAM / GPU load / host RAM / gateway health.
Resumable: profiles already in results_soak.jsonl are skipped.  usage: python soak.py [--only A,B]"""
import base64, json, os, re, struct, sys, threading, time, urllib.request, zlib, subprocess
import yaml
import mneedle as N
import bench_top as T

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "results_soak.jsonl")
PORT = 8080; BASE = N.corpus(); CFG = yaml.safe_load(open(os.path.join(HERE, "..", "config", "llama-swap.yaml"), encoding="utf-8"))["models"]
VRAM_LIMIT = 9990; FILL = 0.95


def call(path, body, timeout):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)


def gpu():
    o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,power.draw", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.split(",")
    return int(o[0]), int(o[1]), float(o[2])


class Watch:
    def __enter__(self):
        self.v = self.u = self.p = 0; self.free = 99.0; self.run = True
        def loop():
            while self.run:
                try: v, u, p = gpu(); self.v, self.u, self.p = max(self.v, v), max(self.u, u), max(self.p, p)
                except Exception: pass
                self.free = min(self.free, T.host_free_gb()); time.sleep(1)
        self.t = threading.Thread(target=loop, daemon=True); self.t.start(); return self
    def __exit__(self, *a): self.run = False; self.t.join()


def png(r, g, b, n=64):
    raw = b"".join(b"\x00" + bytes([r, g, b]) * n for _ in range(n))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b"")


def doc(model, ctx, offset):
    sample = BASE[:24000]; cpt = len(sample) / max(1, len(call(f"/upstream/{model}/tokenize", {"content": sample}, 120)["tokens"]))
    base = BASE[offset:] + BASE[:offset]
    text = base[: int((ctx * FILL - 1400) * cpt)]
    for depth, sent, _, _ in reversed(N.NEEDLES):
        pos = text.rfind("\n", 0, int(len(text) * depth)); text = text[:pos] + "\n" + sent + "\n" + text[pos:]
    return text


def ask(model, content, max_tokens, timeout):
    t0 = time.time()
    r = call("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens, "temperature": 0,
                                       "chat_template_kwargs": {"enable_thinking": False}}, timeout)
    tm = r.get("timings", {}); return r, {"pt": r["usage"]["prompt_tokens"], "ct": r["usage"]["completion_tokens"], "pp": round(tm.get("prompt_per_second", 0), 1),
                                          "tg": round(tm.get("predicted_per_second", 0), 1), "wall": round(time.time() - t0, 1)}


def soak(model):
    m = CFG[model]; ctx = int(re.search(r"--ctx-size (\d+)", m["cmd"]).group(1)); row = {"model": model, "ctx": ctx, "steps": [], "problems": []}
    with Watch() as w:
        try:
            t0 = time.time(); call("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8}, 1200)
            row["load_s"] = round(time.time() - t0, 1)
            for i, off in enumerate([0, 400000], 1):
                text = doc(model, ctx, off)
                q = "\n".join(f"{k+1}. {n[2]}" for k, n in enumerate(N.NEEDLES))
                r, s = ask(model, "Below is a long document with three NOTE-* sentences hidden in it.\n\n" + text + "\n\n=== END ===\nAnswer using only the hidden NOTE sentences, one short line each, format '1. answer':\n" + q, 200, 900)
                ans = r["choices"][0]["message"].get("content") or ""; s.update(step=f"fill{i}", hits=sum(n[3] in ans for n in N.NEEDLES), fill=round(s["pt"] / ctx, 3)); row["steps"].append(s)
                if s["hits"] < 3: row["problems"].append(f"fill{i}: facts {s['hits']}/3")
                if s["tg"] < 8: row["problems"].append(f"fill{i}: slow tg {s['tg']}")
            r, s = ask(model, "Below is a long document.\n\n" + text + "\n\n=== END ===\nWrite a detailed 1000-word overview of what kind of code this document contains.", 1500, 1500)
            s.update(step="long_generation", hits=None); row["steps"].append(s)
            if s["ct"] < 300: row["problems"].append(f"long generation only {s['ct']} tokens")
            if "Vision" in model or "VL" in model:
                body = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png(220, 20, 20)).decode()}}, {"type": "text", "text": "What is the main color of this image? One word."}]
                r, s = ask(model, body, 20, 300); ans = (r["choices"][0]["message"].get("content") or "").lower()
                s.update(step="image", ok=("red" in ans or "красн" in ans), answer=ans[:40]); row["steps"].append(s)
                if not s["ok"]: row["problems"].append("image not recognised: " + ans[:40])
        except Exception as e:
            msg = str(e)[:200]
            if "timed out" in msg or isinstance(e, TimeoutError):
                row["problems"].append("ЗАВИС: нет ответа в отведённое время — снят с теста"); row["removed"] = True
            else: row["problems"].append("error: " + msg)
            try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/unload", timeout=60).read()      # free the GPU for the next profile
            except Exception: pass
        row.update(vram_peak=w.v, gpu_util_peak=w.u, power_peak=w.p, host_free_min_gb=round(w.free, 2))
    if row["vram_peak"] > VRAM_LIMIT: row["problems"].append(f"VRAM peak {row['vram_peak']} > {VRAM_LIMIT} (spill risk)")
    if row["host_free_min_gb"] < 3: row["problems"].append(f"host RAM free min {row['host_free_min_gb']} GB")
    row["ok"] = not row["problems"]
    return row


def embed(model):
    t0 = time.time(); r = call("/v1/embeddings", {"model": model, "input": ["тест", "test", "Test"]}, 600)
    return {"model": model, "ctx": 8192, "ok": len(r["data"]) == 3, "dim": len(r["data"][0]["embedding"]), "seconds": round(time.time() - t0, 1), "problems": []}


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    done = {json.loads(l)["model"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) and "--redo" not in sys.argv else set()
    for model in CFG:
        if model in done or (only and model not in only): continue
        row = embed(model) if "Embedding" in model else soak(model)
        open(OUT, "a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
        if row.get("removed"):
            open(os.path.join(HERE, "exclude_not_gpu.md"), "a", encoding="utf-8").write(chr(10) + "- %s soak: %s — ЗАВИС при ctx %s, снят с теста (проверить перед возвратом)." % (time.strftime("%Y-%m-%d %H:%M"), model, row["ctx"]) + chr(10))
        print(f"SOAK {model}: {'OK' if row['ok'] else 'PROBLEMS ' + '; '.join(row['problems'])} vram={row.get('vram_peak')} free={row.get('host_free_min_gb')}", flush=True)
    print("SOAK-FINISHED", flush=True)
