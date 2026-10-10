#!/usr/bin/env python3
"""Keeps every version of the model-test reports in a Git repository (the local Gitea service).

Every INTERVAL seconds the current results are copied into a work clone as stable text files; when something changed a commit is
made and pushed. Each commit gets a running tag v0001, v0002 ...; a finished stage adds stage-<id>-done, the end of all tests
adds final-<date>. Nothing is ever force-pushed or rewritten, so any earlier report can be restored with `git checkout <tag>`.

Environment: BENCH_DIR (/data), REPORT_DIR (/report), DB_FILE (/db/llm-results.sqlite), GIT_URL, GIT_TOKEN_FILE, WORK_DIR (/work).
"""
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time

BENCH = os.environ.get("BENCH_DIR", "/data")
REPORT = os.environ.get("REPORT_DIR", "/report")
DB_FILE = os.environ.get("DB_FILE", "/db/llm-results.sqlite")
URL = os.environ["GIT_URL"]
TOKEN_FILE = os.environ.get("GIT_TOKEN_FILE", "/run/secrets/gitea_token")
WORK = os.environ.get("WORK_DIR", "/work")
INTERVAL = int(os.environ.get("INTERVAL", "60"))
VOLATILE_KEYS = {"built_utc", "version", "checked_utc", "log_updated_utc", "updated_utc_checked"}


def log(text):
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), text, flush=True)


def git(*args, check=True):
    with open(TOKEN_FILE, encoding="utf-8") as source:
        token = source.read().strip()
    command = ["git", "-c", f"http.extraHeader=Authorization: token {token}", "-C", WORK, *args]
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and done.returncode:
        message = done.stderr.strip()[:300]
        raise RuntimeError(f"git {args[0]} failed: {message.replace(token, '***') if token else message}")  # an empty token would mask every character
    return done.stdout.strip()


def setup():
    if not os.path.isdir(os.path.join(WORK, ".git")):
        os.makedirs(WORK, exist_ok=True)
        git("init", "-b", "main")
        git("remote", "add", "origin", URL)
        git("config", "user.name", "model-test-versioner")
        git("config", "user.email", "versioner@local.invalid")
        git("config", "gc.auto", "0")
    if git("remote", "get-url", "origin", check=False) != URL:
        git("remote", "set-url", "origin", URL)
    git("fetch", "origin", check=False)
    if git("rev-parse", "--verify", "origin/main", check=False):
        git("checkout", "-B", "main", "origin/main", check=False)
        git("fetch", "--tags", "origin", check=False)


def strip(value):
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def write(path, data):
    target = os.path.join(WORK, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as sink:
        sink.write(data)


def copy_files(pattern, folder):
    for name in sorted(glob.glob(os.path.join(BENCH, pattern))):
        if os.path.isfile(name):
            target = os.path.join(WORK, folder, os.path.basename(name))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(name, target)


def snapshot():
    """Copy the reports into the work clone; returns the live-data dict (or None)."""
    for folder in ("results", "tables", "report", "database"):
        shutil.rmtree(os.path.join(WORK, folder), ignore_errors=True)
    for pattern in ("results*.jsonl", "fallback_test*.jsonl", "code_eval*.jsonl"):
        copy_files(pattern, "results")
    for pattern in ("*.md", "summary*.json", "benchmark_plan.json", "ctx_recheck.txt"):
        copy_files(pattern, "tables")
    legal = os.environ.get("LEGAL_DIR", "/legal")
    if os.path.isdir(legal):
        for name in os.listdir(legal):
            shutil.copyfile(os.path.join(legal, name), os.path.join(WORK, name))
    live = None
    path = os.path.join(REPORT, "live-data.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as source:
            live = json.load(source)
        write("report/live-data.json", json.dumps(strip(live), ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        write("report/plan.json", json.dumps(strip(live.get("plan")), ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    if os.path.isfile(DB_FILE):
        con = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        try:
            dump = {}
            for table in ("results", "history", "model_scores"):
                try:
                    cursor = con.execute(f"SELECT * FROM {table}")
                except sqlite3.Error:
                    continue
                names = [c[0] for c in cursor.description]
                dump[table] = sorted((dict(zip(names, row)) for row in cursor), key=lambda r: json.dumps(r, sort_keys=True, default=str))
            write("database/results.json", json.dumps(dump, ensure_ascii=False, indent=1, sort_keys=True, default=str) + "\n")
        finally:
            con.close()
    return live


def next_tag():
    tags = [t for t in git("tag", "-l", "v[0-9]*").split() if t[1:].isdigit()]
    return "v%04d" % (max((int(t[1:]) for t in tags), default=0) + 1)


def message(live):
    if not live:
        return "Снимок результатов"
    plan = live.get("plan") or {}
    running = next((s for s in plan.get("stages", []) if s.get("state") == "running"), None)
    done = sum(1 for s in plan.get("stages", []) if s.get("state") == "done")
    overall = plan.get("overall") or {}
    return (f"Результаты: {sum(1 for e in (live.get('entries') or []) if e.get('in_plan', True)) or len(live.get('models') or [])} моделей, этапов готово {done}/{len(plan.get('stages', []))}"
            + (f", идёт «{running['title']}»" if running else "") + (f", {overall['percent']}%" if overall.get("percent") is not None else ""))


def commit_if_changed(live, state):
    git("add", "-A")
    if not git("status", "--porcelain"):
        return False
    tag = next_tag()
    git("commit", "-m", f"{tag}: {message(live)}")
    git("tag", tag)
    stages = {s["id"]: s["state"] for s in ((live or {}).get("plan") or {}).get("stages", [])}
    for stage_id, status in stages.items():
        if status == "done" and state.get(stage_id) not in (None, "done"):
            git("tag", "-f", f"stage-{stage_id}-done")
    state.update(stages)
    overall = ((live or {}).get("plan") or {}).get("overall") or {}
    if overall.get("finished"):
        git("tag", "-f", "final-" + time.strftime("%Y%m%d"))
    git("push", "origin", "main", check=True)
    git("push", "--force", "origin", "--tags", check=False)  # moving stage/final tags only; commit history is never rewritten
    log(f"committed {tag}: {message(live)}")
    return True


def main():
    state = {}
    while True:
        try:
            setup()
            live = snapshot()
            if live and not state:
                state.update({s["id"]: s["state"] for s in (live.get("plan") or {}).get("stages", [])})
            commit_if_changed(live, state)
        except Exception as exc:  # keep running: Gitea may be starting or briefly unavailable
            log(f"error: {exc}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
