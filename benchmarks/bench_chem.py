"""Grade-11 chemistry (10 problems) on every eligible model (context >= 64K). Pass 1: thinking OFF; pass 2: thinking ON for the 5 best hybrid models.
Resumable. usage: python bench_chem.py  -> results_chem.jsonl"""
import json, os, re, sys, time
import bench_top as T
import bench_all as B
import bench_stem as S
from chem_tasks import TASKS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_chem.jsonl")


def run(t, think):
    t = (t[0], t[1], t[2], None, t[4], t[5], t[6])
    ok, _ = T.start(t, 16384 if not think and t[4] != "reasoning" else 24576)
    if not ok:
        B.stop_server()
        return {"model": t[0], "think": think, "error": "не запустилась"}
    mt = 8000 if (think or t[4] == "reasoning") else 2500
    items = []; t0 = time.time()
    for tid, subj, topic, q, ans, tol in TASKS:
        print(f"PROGRESS {len(items)}/{len(TASKS)}", flush=True)
        try:
            raw, n, fin = S.ask(t, q, think, mt)
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
            got = S.parse_number(raw)
        except Exception:
            got, fin, n = None, "error", 0
        items.append({"id": tid, "topic": topic, "ok": S.close(got, ans, tol), "got": got, "want": ans, "finish": fin, "tokens": n})
    B.stop_server()
    return {"model": t[0], "think": think, "score": sum(i["ok"] for i in items), "n": len(items), "truncated": sum(1 for i in items if i["finish"] == "length"),
            "minutes": round((time.time() - t0) / 60, 1), "items": items}


def done():
    return {(json.loads(l)["model"], json.loads(l)["think"]) for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()


if __name__ == "__main__":
    models = T.eligible(T.TOP)
    for t in models:
        if (t[0], t[4] == "reasoning") in done():
            continue
        r = run(t, t[4] == "reasoning")
        open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"CHEM {t[0]} (think={r['think']}): {r.get('score')}/10 trunc {r.get('truncated')} ({r.get('minutes')} min) {r.get('error', '')}", flush=True)
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    hyb = {t[0] for t in models if t[4] == "hybrid"}
    best = [r["model"] for r in sorted((r for r in rows if not r["think"] and "score" in r and r["model"] in hyb), key=lambda r: -r["score"])][:5]
    for m in best:
        if (m, True) in done():
            continue
        r = run(next(x for x in models if x[0] == m), True)
        open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"CHEM {m} (think=True): {r.get('score')}/10 trunc {r.get('truncated')} ({r.get('minutes')} min)", flush=True)
    print("CHEM-FINISHED", flush=True)
