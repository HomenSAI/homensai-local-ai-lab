"""Phase: grade-11 math + physics (40 generated problems with computed answers).
Pass 1: every model, thinking OFF (short written solution allowed, 2500 tokens).
Pass 2: the 8 best hybrid models again with thinking ON (8000 tokens); reasoning-only models (R1) always run with 8000 tokens.
usage: python bench_stem.py [--only A,B]   -> results_stem.jsonl, stem_table.md"""
import json, math, os, re, sys, time, urllib.request
import bench_top as T
import bench_all as B
from stem_tasks import TASKS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_stem.jsonl")
SUP = {"⁻": "-", "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "−": "-", "–": "-"}


def parse_number(text):
    """Number from the last 'ОТВЕТ:' line: 12, -3.5, 1,5, 1.5e-3, 1.5·10^-3, 1.5×10⁻³, 5/36, 70 %."""
    m = re.findall(r"ОТВЕТ\s*[:：]\s*(.+)", text, flags=re.I)
    if not m: return None
    s = m[-1].strip()
    for k, v in SUP.items(): s = s.replace(k, v)
    s = s.replace(" ", " ").replace("\\cdot", "·").replace("\\times", "×").replace("$", "").replace("{", "").replace("}", "")
    mm = re.search(r"(-?\d+(?:[.,]\d+)?)\s*[·×x*]\s*10\s*\^?\s*(-?\d+)", s)
    if mm: return float(mm.group(1).replace(",", ".")) * 10 ** int(mm.group(2))
    mm = re.search(r"(-?\d+(?:[.,]\d+)?)\s*/\s*(-?\d+(?:[.,]\d+)?)", s)
    if mm and float(mm.group(2).replace(",", ".")) != 0: return float(mm.group(1).replace(",", ".")) / float(mm.group(2).replace(",", "."))
    mm = re.search(r"-?\d+(?:[.,]\d+)?(?:[eE]-?\d+)?", s.replace(" ", "") if re.search(r"\d \d{3}\b", s) else s)
    return float(mm.group(0).replace(",", ".")) if mm else None


def close(got, want, tol):
    return got is not None and (abs(got - want) <= tol * abs(want) + 1e-9 if want else abs(got) < 1e-6)


def ask(t, q, think, max_tokens):
    body = {"messages": [{"role": "user", "content": q}], "temperature": 0, "seed": 42, "max_tokens": max_tokens}
    if t[4] in ("hybrid", "plain"): body["chat_template_kwargs"] = {"enable_thinking": think}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r: d = json.load(r)
    return d["choices"][0]["message"].get("content") or "", d["usage"]["completion_tokens"], d["choices"][0].get("finish_reason")


def run(t, think):
    t = (t[0], t[1], t[2], None, t[4], t[5], t[6])
    ok, _ = T.start(t, 16384 if not think and t[4] != "reasoning" else 24576)
    if not ok: B.stop_server(); return {"model": t[0], "think": think, "error": "не запустилась"}
    mt = 8000 if (think or t[4] == "reasoning") else 2500
    items = []; t0 = time.time(); tok = 0
    for tid, subj, topic, q, ans, tol in TASKS:
        print(f"PROGRESS {len(items)}/{len(TASKS)}", flush=True)
        try:
            raw, n, fin = ask(t, q, think, mt); tok += n
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S); got = parse_number(raw)
        except Exception as e:
            got, fin, n = None, "error", 0
        items.append({"id": tid, "subj": subj, "topic": topic, "ok": close(got, ans, tol), "got": got, "want": ans, "finish": fin, "tokens": n})
    B.stop_server()
    sc = lambda s: sum(i["ok"] for i in items if i["subj"] == s)
    return {"model": t[0], "think": think, "math": sc("math"), "phys": sc("phys"), "total": sc("math") + sc("phys"), "n": len(items), "tokens": tok,
            "truncated": sum(1 for i in items if i["finish"] == "length"), "minutes": round((time.time() - t0) / 60, 1), "items": items}


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    done = {(json.loads(l)["model"], json.loads(l)["think"]) for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()
    models = [t for t in T.eligible(T.TOP) if not only or t[0] in only]
    for t in models:
        if (t[0], t[4] == "reasoning") in done: continue
        r = run(t, t[4] == "reasoning"); open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"STEM {t[0]} (think={r['think']}): math {r.get('math')}/20 phys {r.get('phys')}/20 trunc {r.get('truncated')} ({r.get('minutes')} min) {r.get('error', '')}", flush=True)
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    best = [r["model"] for r in sorted((r for r in rows if not r["think"] and "total" in r), key=lambda r: -r["total"])]
    hyb = {t[0] for t in T.TOP if t[4] == "hybrid"}
    for m in [b for b in best if b in hyb][:8]:
        t = next(x for x in T.TOP if x[0] == m)
        if (m, True) in {(json.loads(l)["model"], json.loads(l)["think"]) for l in open(OUT, encoding="utf-8")}: continue
        r = run(t, True); open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"STEM {m} (think=True): math {r.get('math')}/20 phys {r.get('phys')}/20 trunc {r.get('truncated')} ({r.get('minutes')} min)", flush=True)
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]; rows = [r for r in rows if "total" in r]; rows.sort(key=lambda r: -r["total"])
    md = ["| # | Модель | Рассуждение | Математика | Физика | Итого из 40 | Обрезано |", "|---|---|---|---|---|---|---|"]
    md += [f"| {i} | {r['model']} | {'да' if r['think'] else 'нет'} | {r['math']}/20 | {r['phys']}/20 | **{r['total']}** | {r['truncated']} |" for i, r in enumerate(rows, 1)]
    open(os.path.join(HERE, "stem_table.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("STEM-FINISHED", flush=True)
