"""Re-run the German passive test for models that returned empty answers (thinking ate the token budget).
Two variants per model: thinking OFF (enable_thinking=false, 1500 tokens) and thinking ON with a big budget (6000 tokens).
The better variant is stored in results_german_fix.jsonl (the original run stays untouched)."""
import json, os, re, sys, time, urllib.request
import bench_top as T
import bench_all as B
from qa_tasks import GERMAN, GERMAN_INSTR
from qa_bench import correct, answer_of

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_german_fix.jsonl")
MODELS = ["Gemma-4-12B", "Gemma-4-12B-QAT", "LFM2.5-2.6B", "LFM2.5-8B-A1B", "R1-Distill-Llama-8B"]
VARIANTS = [("thinking-off", False, 1500), ("thinking-on", True, 6000)]


def ask(q, think, max_tokens):
    body = {"messages": [{"role": "system", "content": GERMAN_INSTR}, {"role": "user", "content": q}], "temperature": 0, "seed": 42,
            "max_tokens": max_tokens, "chat_template_kwargs": {"enable_thinking": think}}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r: d = json.load(r)
    m = d["choices"][0]["message"]
    return (m.get("content") or ""), d["usage"]["completion_tokens"], d["choices"][0].get("finish_reason")


if __name__ == "__main__":
    _r = [json.loads(l) for l in open(OUT, encoding="utf-8")] if os.path.exists(OUT) else []
    DONE_M = {m for m in MODELS if {r["variant"] for r in _r if r["model"] == m} >= {v[0] for v in VARIANTS}}
    for t in T.eligible(T.TOP):
        if t[0] not in MODELS: continue
        if t[0] in DONE_M: continue   # resume: both variants already stored
        t = (t[0], t[1], t[2], None, t[4], t[5], t[6])
        ok, _ = T.start(t, 16384)
        if not ok: B.stop_server(); print(f"GERMAN-FIX {t[0]}: не запустилась", flush=True); continue
        best = None
        for label, think, mt in VARIANTS:
            items = []; t0 = time.time(); trunc = 0
            for iid, cat, q, acc in GERMAN:
                try:
                    raw, n, fin = ask(q, think, mt); trunc += fin == "length"
                    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S); got = answer_of("german", raw); good = correct("german", got, acc)
                except Exception as e:
                    got, good = "ошибка: " + str(e)[:80], False
                items.append({"id": iid, "cat": cat, "ok": bool(good), "got": got[:160]})
            r = {"model": t[0], "variant": label, "score": sum(i["ok"] for i in items), "n": 30, "empty": sum(1 for i in items if not i["got"].strip()),
                 "truncated": trunc, "minutes": round((time.time() - t0) / 60, 1), "items": items}
            open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"GERMAN-FIX {t[0]} {label}: {r['score']}/30 empty={r['empty']} truncated={trunc} ({r['minutes']} min)", flush=True)
        B.stop_server()
    print("GERMAN-FIX-FINISHED", flush=True)
