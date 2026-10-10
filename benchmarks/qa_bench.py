"""Run a short-answer suite (german | iq) and grade it.
usage: qa_bench.py --suite german --runs "Model:nothink,Model:think" [--port 8086]
Appends one line per item to qa_results.jsonl and prints a per-run summary."""
import argparse, json, os, re, time, urllib.request
from qa_tasks import GERMAN, GERMAN_INSTR, IQ, IQ_INSTR

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = {"german": (GERMAN, GERMAN_INSTR), "iq": (IQ, IQ_INSTR)}


def norm(s):
    s = s.strip().lower()
    s = re.sub(r"^(antwort|ответ)\s*:\s*", "", s)
    s = re.sub(r"[„“”\"«»*`]", "", s)
    s = re.sub(r"\s*/\s*", " / ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".!。 ").strip()


def answer_of(suite, text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if suite == "iq":
        m = re.findall(r"ОТВЕТ\s*:\s*(.+)", text, flags=re.I)
        return m[-1] if m else (text.splitlines() or [""])[-1]
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[0] if lines else ""


def correct(suite, got, accepted):
    g = norm(got)
    if suite == "iq":
        g = g.replace(",", ".")
        for a in accepted:
            a = norm(a)
            if re.fullmatch(r"[\d.]+", a):
                nums = re.findall(r"-?\d+(?:\.\d+)?", g)
                if nums and float(nums[0]) == float(a):
                    return True
            elif g == a or g.startswith(a):
                return True
        return False
    return any(g == norm(a) for a in accepted)


def chat(port, model, system, q, think, timeout):
    body = {"model": model, "temperature": 0, "stream": False, "max_tokens": 8000 if think else 400,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": q}],
            "chat_template_kwargs": {"enable_thinking": think}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True, choices=SUITES)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--port", type=int, default=8086)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    items, system = SUITES[a.suite]
    for run in a.runs.split(","):
        model, mode = run.rsplit(":", 1)
        think = mode == "think"
        t0 = time.time(); ok = 0; tok = 0
        for iid, cat, q, acc in items:
            row = {"suite": a.suite, "tag": f"{model}__{mode}", "id": iid, "cat": cat}
            try:
                r = chat(a.port, model, system, q, think, a.timeout)
                raw = r["choices"][0]["message"].get("content") or ""
                got = answer_of(a.suite, raw)
                row.update(got=got[:200], ok=correct(a.suite, got, acc), tokens=r["usage"]["completion_tokens"])
                tok += row["tokens"]
            except Exception as e:
                row.update(got="", ok=False, error=str(e)[:200])
            ok += row["ok"]
            with open(os.path.join(HERE, "qa_results.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"QA {a.suite} {model}__{mode}: {ok}/{len(items)} correct, {tok} tokens, {time.time() - t0:.0f}s", flush=True)
