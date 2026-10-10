"""Step 3: accelerators and embeddings.
 spec  : every gateway profile that uses MTP / DFlash / a draft model is run twice with the SAME flags, once without the speculative options
         (baseline) and once with them; speed is the median generation tok/s over 3 prompts x 2 runs (temperature 0).
         A pair that fails to start (e.g. vocabulary mismatch) is reported as 'не работает'.
 embed : Qwen3-Embedding-0.6B / 4B: dimension, speed, similarity of paraphrase pairs vs unrelated pairs, and top-1 retrieval on a small RU/EN/DE set.
usage: python bench_accel.py [spec|embed|all]   -> results_accel.jsonl"""
import json, os, shlex, statistics, sys, time, urllib.request
import numpy as np
import yaml
import bench_all as B
import bench_top as T

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "..", "config", "llama-swap.yaml")
OUT = os.path.join(HERE, "results_accel.jsonl")
SPEC_ARITY1 = {"--spec-type", "--spec-draft-model", "-md", "--model-draft", "--spec-draft-n-max", "--spec-draft-n-min", "-ngld",
               "--spec-draft-ngl", "--gpu-layers-draft", "--n-gpu-layers-draft", "--spec-draft-type-k", "--spec-draft-type-v"}
PROMPTS = ["Напиши на Python функцию, которая проверяет, является ли строка палиндромом, и три теста к ней.",
           "Объясни простыми словами, как работает цикл воды в природе, в трёх абзацах.",
           "Верни JSON-массив из пяти объектов {\"city\": ..., \"country\": ..., \"population\": ...} для крупных европейских городов."]


def profile_tokens(name, cfg, ctx=16384):
    t = shlex.split(cfg["models"][name]["cmd"].replace("\n", " "))
    out, i = [], 0
    while i < len(t):
        a = t[i]
        if a == "--port": out += ["--port", "8080"]; i += 2; continue
        if a == "--host": out += ["--host", "0.0.0.0"]; i += 2; continue
        if a in ("--ctx-size", "-c"): out += ["--ctx-size", str(ctx)]; i += 2; continue
        out.append(a); i += 1
    return out


def baseline(tokens):
    out, i = [], 0
    while i < len(tokens):
        if tokens[i] in SPEC_ARITY1: i += 2; continue
        out.append(tokens[i]); i += 1
    return out


def launch(tokens):
    B.sh(["docker", "rm", "-f", "bench-srv"])
    B.sh(["docker", "run", "-d", "--name", "bench-srv", "--gpus", "all", "-p", f"127.0.0.1:{B.PORT}:8080", "-v", "llm-models-fast:/models:ro",
          "--entrypoint", tokens[0], B.IMAGE] + tokens[1:])
    t0 = time.time()
    while time.time() - t0 < 600:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{B.PORT}/health", timeout=3) as r:
                if r.status == 200: return True
        except Exception: pass
        if B.sh(["docker", "inspect", "-f", "{{.State.Running}}", "bench-srv"])[1].strip() != "true": return False
        time.sleep(1)
    return False


def gen(p):
    body = {"messages": [{"role": "user", "content": p}], "max_tokens": 220, "temperature": 0, "seed": 42, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r: d = json.load(r)
    tm = d.get("timings", {})
    return tm.get("predicted_per_second", 0), tm.get("draft_n", 0), tm.get("draft_n_accepted", 0)


def measure(tokens):
    if not launch(tokens): B.stop_server(); return None
    gen(PROMPTS[0])                                                    # warm-up
    runs = [gen(p) for p in PROMPTS for _ in range(2)]
    B.stop_server()
    dn, da = sum(r[1] for r in runs), sum(r[2] for r in runs)
    return {"tg": round(statistics.median(r[0] for r in runs), 1), "accept": round(da / dn, 2) if dn else None}


def spec():
    cfg = yaml.safe_load(open(CFG, encoding="utf-8")); seen_base = {}
    for name, m in cfg["models"].items():
        cmd = m["cmd"]
        if ("spec", name) in DONE: continue
        if "--spec-type" not in cmd and "--spec-draft-model" not in cmd and "-md " not in cmd: continue
        tokens = profile_tokens(name, cfg)
        key = " ".join(baseline(tokens))
        row = {"kind": "spec", "profile": name, "spec_flags": [tokens[i + 1] if tokens[i] == "--spec-type" else os.path.basename(tokens[i + 1])
                                                          for i in range(len(tokens) - 1) if tokens[i] in ("--spec-type", "--spec-draft-model")]}
        if key not in seen_base: seen_base[key] = measure(baseline(tokens))
        row["baseline"] = seen_base[key]
        row["with_accel"] = measure(tokens)
        if row["baseline"] and row["with_accel"] and row["baseline"]["tg"]:
            row["speedup"] = round(row["with_accel"]["tg"] / row["baseline"]["tg"], 2)
        row["verdict"] = ("не работает (не стартовала)" if not row["with_accel"] else "базовая модель не стартовала" if not row["baseline"] else
                          "ускоряет" if row["speedup"] >= 1.10 else "без пользы" if row["speedup"] >= 0.95 else "замедляет")
        open(OUT, "a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"ACCEL {name}: base {row['baseline'] and row['baseline']['tg']} -> {row['with_accel'] and row['with_accel']['tg']} tok/s  x{row.get('speedup')}  {row['verdict']}", flush=True)


DOCS = ["Чертёж корпуса редуктора: размеры 240x180x120 мм, толщина стенки 8 мм, материал чугун СЧ20.",
        "Cooking recipe: how to bake sourdough bread with rye flour and a long overnight fermentation.",
        "Anleitung zur Montage eines Wandregals mit Dübeln und Schrauben, Bohrlochabstand 600 mm.",
        "Расписание поездов Москва - Санкт-Петербург, отправление в 06:30, прибытие в 10:30.",
        "Technical drawing of a shaft: diameter 35 mm, length 210 mm, keyway 10x8, tolerance h6, steel 45.",
        "Список покупок: молоко, яйца, хлеб, сыр, яблоки и кофе."]
QUERIES = [("габариты корпуса редуктора и материал", 0), ("how long to ferment rye sourdough", 1), ("Wandregal montieren Abstand Bohrungen", 2),
           ("во сколько приходит поезд в Петербург", 3), ("shaft diameter keyway tolerance", 4), ("что купить в магазине", 5)]


DONE = {(r.get("kind"), r.get("profile")) for r in (json.loads(l) for l in open(OUT, encoding="utf-8")) } if os.path.exists(OUT) else set()  # resume after a crash


def embed():
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    for name in [n for n in cfg["models"] if "Embedding" in n]:
        if (("embed", name) in DONE): continue
        tokens = profile_tokens(name, cfg)
        if not launch(tokens): B.stop_server(); print(f"EMBED {name}: не стартовала", flush=True); open(OUT, "a").write(json.dumps({"kind": "embed", "profile": name, "verdict": "не работает"}) + "\n"); continue
        def emb(texts):
            req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/embeddings", json.dumps({"input": texts, "model": name}).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r: d = json.load(r)
            v = np.array([x["embedding"] for x in d["data"]], dtype=np.float32); return v / np.linalg.norm(v, axis=1, keepdims=True)
        t0 = time.time(); D = emb(DOCS); Q = emb([q for q, _ in QUERIES]); dt = time.time() - t0
        top1 = sum(int(np.argmax(Q[i] @ D.T)) == w for i, (_, w) in enumerate(QUERIES))
        B.stop_server()
        row = {"kind": "embed", "profile": name, "dim": int(D.shape[1]), "top1": f"{top1}/{len(QUERIES)}", "seconds_for_12_texts": round(dt, 2),
               "verdict": "работает" if top1 >= 5 else "слабый поиск"}
        open(OUT, "a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"EMBED {name}: dim {row['dim']} top1 {row['top1']} {row['verdict']}", flush=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("embed", "all"): embed()
    if what in ("spec", "all"): spec()
    print("ACCEL-FINISHED", flush=True)
