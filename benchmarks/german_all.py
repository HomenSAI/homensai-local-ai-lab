"""German passive test (30 items, every form of the Passiv) on all models, same task set and grader as before.
One server per model (same flags as the benchmark), temperature 0, system prompt GERMAN_INSTR.
Reasoning-only models (mode 'reasoning') get a larger token budget and their <think> block is stripped.
Writes results_german.jsonl and german_table.md."""
import json, os, re, sys, time, urllib.request
import bench_top as T
import bench_all as B
from qa_tasks import GERMAN, GERMAN_INSTR
from qa_bench import correct, answer_of

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_german.jsonl")


def ask(t, q):
    body = {"messages": [{"role": "system", "content": GERMAN_INSTR}, {"role": "user", "content": q}],
            "temperature": 0, "seed": 42, "max_tokens": 5000 if t[4] == "reasoning" else 400}
    if t[4] == "hybrid": body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r: d = json.load(r)
    return d["choices"][0]["message"].get("content") or "", d["usage"]["completion_tokens"]


def run(t):
    t = (t[0], t[1], t[2], None, t[4], t[5], t[6])                       # text only: no vision projector
    ok, load_s = T.start(t, 8192)
    if not ok:
        B.stop_server(); return {"model": t[0], "error": "не запустилась"}
    items = []; tok = 0
    for iid, cat, q, acc in GERMAN:
        try:
            raw, n = ask(t, q); tok += n
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
            got = answer_of("german", raw); good = correct("german", got, acc)
        except Exception as e:
            got, good = "ошибка: " + str(e)[:80], False
        items.append({"id": iid, "cat": cat, "ok": bool(good), "got": got[:160]})
    B.stop_server()
    return {"model": t[0], "mode": t[4], "score": sum(i["ok"] for i in items), "n": len(items), "tokens": tok, "items": items}


if __name__ == "__main__":
    done = {json.loads(l)["model"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) and "--skip-done" in sys.argv else set()
    for t in T.TOP:
        if t[0] in done: continue
        t0 = time.time(); r = run(t); r["minutes"] = round((time.time() - t0) / 60, 1)
        open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"GERMAN {t[0]}: {r.get('score')}/{r.get('n')} ({r['minutes']} min) {r.get('error', '')}", flush=True)
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    rows = [r for r in rows if "score" in r]; rows.sort(key=lambda r: -r["score"])
    cats = [g[1] for g in GERMAN]
    md = ["| # | Модель | Верно из 30 | % |", "|---|---|---|---|"] + [f"| {i} | {r['model']} | {r['score']}/{r['n']} | {round(100 * r['score'] / r['n'])} |" for i, r in enumerate(rows, 1)]
    md += ["", "### Какие формы дают ошибки у большинства моделей", "| Форма | Моделей верно |", "|---|---|"]
    hard = sorted(((sum(r["items"][k]["ok"] for r in rows), cats[k]) for k in range(len(cats))))
    md += [f"| {c} | {n}/{len(rows)} |" for n, c in hard]
    open(os.path.join(HERE, "german_table.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("GERMAN-FINISHED", flush=True)
