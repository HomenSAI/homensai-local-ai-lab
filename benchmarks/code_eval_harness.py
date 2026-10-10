"""Runs inside the sandbox container (no network). For every /work/gen/<model>/<task>.py appends the task's
tests and executes it in a subprocess with a timeout. Prints one JSON line per file."""
import json, os, subprocess, sys
sys.path.insert(0, "/work")
from coding_tasks import TASKS

tests = {t[0]: t[3] for t in TASKS}
root = "/work/gen"
for model in sorted(os.listdir(root)):
    for fn in sorted(os.listdir(os.path.join(root, model))):
        tid = fn[:-3]
        code = open(os.path.join(root, model, fn), encoding="utf-8").read()
        prog = code + "\n\n# ---- hidden tests ----\n" + tests[tid] + "\nprint('ALL_TESTS_PASSED')\n"
        path = f"/tmp/{model}_{tid}.py"
        open(path, "w", encoding="utf-8").write(prog)
        try:
            p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=10)
            ok = "ALL_TESTS_PASSED" in p.stdout
            err = "" if ok else (p.stderr.strip().splitlines() or ["no output"])[-1][:200]
        except subprocess.TimeoutExpired:
            ok, err = False, "timeout 10s"
        print(json.dumps({"model": model, "task": tid, "pass": ok, "error": err}, ensure_ascii=False), flush=True)
