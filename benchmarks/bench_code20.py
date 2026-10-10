"""20 Python coding tasks with hidden asserts on every eligible model (context >= 64K).
Model writes code (thinking off for hybrid models), tests run in the sandbox (docker --network none).
Resumable: models already in results_code20.jsonl are skipped.  usage: python bench_code20.py [--only A,B]"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
import bench_top as T
import bench_all as B
from coding_tasks import TASKS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_code20.jsonl")
GEN = os.path.join(HERE, "code20")
SANDBOX_IMAGE = os.environ.get("SANDBOX_IMAGE", "python:3.12-slim")   # tests need the standard library only


def ask(t, prompt):
    body = {"messages": [{"role": "user", "content": prompt + "\n\nReturn only the complete Python code in one ```python block, no explanations."}],
            "temperature": 0, "seed": 42, "max_tokens": 2500}
    if t[4] in ("hybrid", "plain"):
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{B.PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        d = json.load(r)
    return d["choices"][0]["message"].get("content") or "", d["usage"]["completion_tokens"]


def sandbox(model_dir):
    """Runs the hidden tests in a throw-away container without network. The files go in with `docker cp` instead of
    bind mounts, so this works from the host and from the bench-runner container alike."""
    name = "bench-sandbox"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "work")
        shutil.copytree(os.path.join(GEN, model_dir), os.path.join(work, "gen", model_dir))
        shutil.copy(os.path.join(HERE, "coding_tasks.py"), os.path.join(work, "coding_tasks.py"))
        shutil.copy(os.path.join(HERE, "code_eval_harness.py"), os.path.join(work, "h.py"))
        subprocess.run(["docker", "create", "--name", name, "--network", "none", "--memory", "2g", "--cpus", "2",
                        SANDBOX_IMAGE, "python", "/work/h.py"], capture_output=True, check=True)
        try:
            subprocess.run(["docker", "cp", work, f"{name}:/"], capture_output=True, check=True)
            p = subprocess.run(["docker", "start", "-a", name], capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    return [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]


def run(t):
    t = (t[0], t[1], t[2], None, t[4], t[5], t[6])
    ok, _ = T.start(t, 16384)
    if not ok:
        B.stop_server()
        return {"model": t[0], "error": "не запустилась"}
    d = os.path.join(GEN, t[0]); os.makedirs(d, exist_ok=True)
    tok = 0; t0 = time.time(); errs = 0
    for tid, level, prompt, tests, ref in TASKS:
        try:
            raw, n = ask(t, prompt); tok += n
        except Exception:
            raw = ""; errs += 1
        open(os.path.join(d, tid + ".py"), "w", encoding="utf-8").write(B.extract_code(raw))
    B.stop_server()
    res = sandbox(t[0])
    lv = {x[0]: x[1] for x in TASKS}
    by = {1: [0, 0], 2: [0, 0], 3: [0, 0]}
    for r in res:
        by[lv[r["task"]]][1] += 1; by[lv[r["task"]]][0] += bool(r["pass"])
    return {"model": t[0], "passed": sum(1 for r in res if r["pass"]), "n": len(TASKS), "by_level": {str(k): v for k, v in by.items()}, "tokens": tok,
            "request_errors": errs, "minutes": round((time.time() - t0) / 60, 1), "failed": [r["task"] for r in res if not r["pass"]]}


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    done = {json.loads(l)["model"] for l in open(OUT, encoding="utf-8")} if os.path.exists(OUT) else set()
    for t in [x for x in T.eligible(T.TOP) if not only or x[0] in only]:
        if t[0] in done:
            continue
        r = run(t)
        open(OUT, "a", encoding="utf-8").write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"CODE20 {t[0]}: {r.get('passed')}/{r.get('n')} levels {r.get('by_level')} ({r.get('minutes')} min) {r.get('error', '')}", flush=True)
    print("CODE20-FINISHED", flush=True)
