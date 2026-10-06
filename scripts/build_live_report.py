#!/usr/bin/env python3
"""Aggregate the newest benchmark output of bench_results/ into report/live-data.json.

Runs once, or with --watch as a sidecar that rebuilds whenever a result file changes:
  results*.jsonl       one row per model (bench_all.py / bench_top.py)
  code_eval*.jsonl     pass/fail of generated code
  fallback_test*.jsonl RAM-guard / fallback probes
  report.md            human status line ("Дата: … Статус: …")
live-data.json is rewritten only when its content changes; live-status.json is a tiny
heartbeat rewritten every cycle so the page can show "checked N seconds ago".
"""
import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone

BENCH = os.environ.get("BENCH_DIR", "/data")
OUT = os.environ.get("OUT_DIR", "/out")
DB_PATH = os.environ.get("RESULTS_DB", "/db/llm-results.sqlite")
CATS = ["Русский", "Логика", "Код", "Инструкции", "Зрение"]
CODE_TASKS = {"cd_lru": "lru", "cd_calc": "calc", "cd_csv": "csv_line"}
SKIP = re.compile(r"\.(before|bak|old)[.-]|before-|invalid|\.run\d", re.I)


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def files(pattern):
    found = [p for p in glob.glob(os.path.join(BENCH, pattern)) if not SKIP.search(os.path.basename(p))]
    return sorted(found, key=os.path.getmtime)


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass  # a line still being written
    return rows


def current_model(updated):
    """Model the benchmark is working on right now: last '=== name (...)' line of the newest log.
    Hidden once that model has a result newer than the log's last activity (or the log is stale)."""
    logs = sorted(glob.glob(os.path.join(BENCH, "*.log")), key=os.path.getmtime)
    if not logs or time.time() - os.path.getmtime(logs[-1]) > 20 * 60:
        return None
    log_mtime = os.path.getmtime(logs[-1])
    with open(logs[-1], encoding="utf-8", errors="replace") as source:
        lines = source.read().splitlines()[-300:]
    marks = [i for i, line in enumerate(lines) if line.startswith("=== ")]
    if not marks:
        return None
    name = re.split(r"\s+\(", lines[marks[-1]][4:].strip())[0].strip()
    if not name:
        return None
    if name in updated:
        done_at = datetime.fromisoformat(updated[name].replace("Z", "+00:00")).timestamp()
        if log_mtime - done_at < 120 or time.time() - log_mtime > 180:
            return None
    tail = [line.strip()[:160] for line in lines[marks[-1] + 1:] if line.strip()][-4:]
    return {"model": name, "header": lines[marks[-1]][4:].strip()[:120], "log": tail,
            "updated_utc": iso(log_mtime), "log_file": os.path.basename(logs[-1])}


def model_row(r, code, source, tested):
    base = {"model": r.get("model"), "file": r.get("file"), "quant": r.get("quant"), "size_gb": r.get("size_gb"),
            "origin": r.get("origin"), "mode": r.get("mode"), "source": source, "tested_utc": tested}
    if not r.get("load_ok"):
        return {**base, "failed": True, "error": str(r.get("error") or "не загрузилась")[:240]}
    got = collections.defaultdict(lambda: [0, 0])
    for q in r.get("quality") or []:
        task = q.get("task", "")
        if task.startswith("cd_"):
            score, top = int(bool(code.get(r["model"], {}).get(CODE_TASKS.get(task, task[3:]), False))), 1
        else:
            score, top = q.get("score") or 0, q.get("max") or 1
        got[q.get("cat", "?")][0] += score
        got[q.get("cat", "?")][1] += top
    pct = {c: round(100 * v[0] / v[1]) for c, v in got.items() if v[1]}
    text = [pct[c] for c in CATS[:4] if c in pct]
    ctx = r.get("ctx") or {}
    return {**base, "failed": False, "ngl": r.get("ngl"), "fits": r.get("fits_gpu"),
            "placement": r.get("placement"), "vram_mib": max(r.get("vram_peak_8k") or 0, r.get("vram_bench") or 0) or None,
            "pp": r.get("pp"), "tg": r.get("tg"), "load_s": r.get("load_s"), "max_ctx": r.get("max_ctx"),
            "ctx": {k: bool(v.get("ok")) for k, v in ctx.items()}, "pct": pct,
            "raw": {c: got[c] for c in got}, "total": round(sum(text) / len(text)) if text else None,
            "guard_killed": r.get("guard_killed"), "host_free_min_gb": r.get("host_free_min_gb")}


def status_text():
    path = os.path.join(BENCH, "report.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as source:
        head = [line.strip() for line in source.read().splitlines()[:8] if line.strip() and not line.startswith("#")]
    return re.sub(r"\*\*|`", "", " ".join(head[:2]))[:400] or None


def recent_files(limit=14):
    entries = []
    for root, dirs, names in os.walk(BENCH):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        depth = os.path.relpath(root, BENCH).count(os.sep) + (0 if root == BENCH else 1)
        if depth > 2:
            dirs[:] = []
        for name in names:
            if name.endswith((".pyc", ".tmp", ".part")):
                continue
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            entries.append({"path": os.path.relpath(path, BENCH).replace(os.sep, "/"),
                            "size": stat.st_size, "mtime": stat.st_mtime})
    entries.sort(key=lambda e: -e["mtime"])
    return [{"path": e["path"], "size": e["size"], "modified_utc": iso(e["mtime"])} for e in entries[:limit]]


SUITES = {"general": "Общий тест", "german": "Немецкий язык", "context": "Длинный контекст",
          "stem": "Математика и физика", "chem": "Химия", "code20": "Код: 20 задач"}
VOLATILE = ("tested_utc", "source", "archived")


def row_hash(row):
    stable = {k: v for k, v in row.items() if k not in VOLATILE}
    return hashlib.sha1(json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:10]


def german_row(r):
    items = r.get("items") or []
    n = r.get("n") or len(items)
    score = r.get("score") or 0
    cats = collections.defaultdict(lambda: [0, 0])
    for item in items:
        cats[item.get("cat", "?")][1] += 1
        cats[item.get("cat", "?")][0] += 1 if item.get("ok") else 0
    weak = sorted(([k, v[0], v[1]] for k, v in cats.items() if v[1] and v[0] < v[1]), key=lambda x: x[1] / x[2])[:4]
    return {"score": score, "n": n, "pct": round(100 * score / n) if n else None, "tokens": r.get("tokens"),
            "minutes": r.get("minutes"), "mode": r.get("mode"), "weak": weak}


def context_row(r):
    cfgs = r.get("cfgs") or {}
    return {"native_ctx": r.get("native_ctx"), "cap": r.get("cap"), "ref_tg_8k": r.get("ref_tg_8k"), "best_ctx": r.get("best_ctx"),
            "best_cfg": r.get("best_cfg"), "recommended_cfg": r.get("recommended_cfg"), "minutes": r.get("minutes"),
            "cfgs": {k: {"best_ctx": v.get("best_ctx"), "tg": v.get("tg"), "vram": v.get("vram")}
                     for k, v in cfgs.items() if isinstance(v, dict)}}


def collect():
    """Rows of every kind of test, kept apart: suite -> model -> (row, file mtime, file name)."""
    code = collections.defaultdict(dict)
    raw = []  # (kind, file, model, original row) of every result line, for the database
    for path in files("code_eval*.jsonl"):
        for r in read_jsonl(path):
            code[r.get("model")][r.get("task")] = r.get("pass")
            raw.append(("code_eval", os.path.basename(path), r.get("model"), r))
    for path in files("fallback_test*.jsonl"):
        raw += [("fallback", os.path.basename(path), r.get("model"), r) for r in read_jsonl(path)]
    out = {suite: {} for suite in SUITES}
    trials, stem_think, chem_think = {}, {}, {}
    for path in files("results*.jsonl"):  # oldest first, so a newer file of the same test overrides an older row
        name, mtime = os.path.basename(path), os.path.getmtime(path)
        for r in read_jsonl(path):
            model = r.get("model")
            if not model:
                continue
            raw.append(("results", name, model, r))
            if "quality" in r:
                out["general"][model] = (model_row(r, code, name, iso(mtime)), mtime, name)
            elif name.startswith("results_code20"):
                row = {k: r.get(k) for k in ("passed", "n", "by_level", "tokens", "minutes", "failed", "request_errors")}
                row["pct"] = round(100 * r["passed"] / r["n"]) if r.get("n") and r.get("passed") is not None else None
                out["code20"][model] = (row, mtime, name)
            elif name.startswith("results_chem"):
                row = {"think": r.get("think"), "score": r.get("score"), "n": 10, "truncated": r.get("truncated"), "minutes": r.get("minutes"),
                       "pct": round(10 * r["score"]) if isinstance(r.get("score"), (int, float)) else None}
                if r.get("think"):
                    chem_think[model] = (row, mtime, name)
                else:
                    out["chem"][model] = (row, mtime, name)
            elif "math" in r and "phys" in r:
                row = {k: r.get(k) for k in ("think", "math", "phys", "total", "n", "tokens", "truncated", "minutes")}
                row["pct"] = round(100 * (r.get("total") or 0) / r["n"]) if r.get("n") else None
                if r.get("think"):
                    stem_think[model] = (row, mtime, name)
                else:
                    out["stem"][model] = (row, mtime, name)
            elif "items" in r and "score" in r:
                out["german"][model] = (german_row(r), mtime, name)
            elif "best_ctx" in r or "cfgs" in r:
                out["context"][model] = (context_row(r), mtime, name)
            elif "ctx" in r and "stable" in r:
                trials[model] = max(trials.get(model, 0), r["ctx"] if r.get("stable") else 0)
    for model, (row, mtime, name) in stem_think.items():  # thinking run: attached to the plain row, or alone if there is none
        base = out["stem"].get(model)
        if base:
            out["stem"][model] = ({**base[0], "think_run": row}, base[1], base[2])
        else:
            out["stem"][model] = (row, mtime, name)
    for model, (row, mtime, name) in chem_think.items():
        base = out["chem"].get(model)
        out["chem"][model] = ({**base[0], "think_run": row}, base[1], base[2]) if base else (row, mtime, name)
    for model, stable in trials.items():
        row, mtime, name = out["context"].get(model, ({}, time.time(), "results_ctx_trials.jsonl"))
        out["context"][model] = ({**row, "stable_ctx": stable or None}, mtime, name)
    return out, raw


SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_rows (
  hash TEXT PRIMARY KEY, kind TEXT NOT NULL, source_file TEXT, model TEXT, raw_json TEXT NOT NULL, first_seen_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results (
  suite TEXT NOT NULL, model TEXT NOT NULL, row_json TEXT NOT NULL, hash TEXT NOT NULL, source_file TEXT,
  first_seen_utc TEXT NOT NULL, updated_utc TEXT NOT NULL, PRIMARY KEY (suite, model));
CREATE TABLE IF NOT EXISTS history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, suite TEXT NOT NULL, model TEXT NOT NULL, hash TEXT NOT NULL,
  row_json TEXT NOT NULL, source_file TEXT, recorded_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_scores (
  model TEXT PRIMARY KEY, quant TEXT, size_gb REAL, total_pct INTEGER, ru_pct INTEGER, logic_pct INTEGER, code_pct INTEGER,
  instruction_pct INTEGER, vision_pct INTEGER, tg_tokens_s REAL, pp_tokens_s REAL, vram_peak_mib INTEGER, max_ctx_tested INTEGER,
  german_score INTEGER, german_n INTEGER, german_pct INTEGER, ctx_best INTEGER, ctx_stable INTEGER, ctx_recommended_cfg TEXT,
  updated_utc TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS idx_history_model ON history (model, recorded_utc);
CREATE INDEX IF NOT EXISTS idx_raw_model ON raw_rows (model);
"""


def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def merge_archive(current, raw):
    """Write every result into the SQLite database (nothing is ever dropped) and return all stored results."""
    now = iso(time.time())
    con = db()
    try:
        with con:
            for kind, name, model, row in raw:
                text = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
                con.execute("INSERT OR IGNORE INTO raw_rows (hash, kind, source_file, model, raw_json, first_seen_utc) VALUES (?,?,?,?,?,?)",
                            (hashlib.sha1((kind + text).encode("utf-8")).hexdigest(), kind, name, model, text, now))
            for suite in SUITES:
                first_import = con.execute("SELECT COUNT(*) FROM results WHERE suite=?", (suite,)).fetchone()[0] == 0
                for model, (row, mtime, name) in current[suite].items():
                    digest = row_hash(row)
                    old = con.execute("SELECT hash FROM results WHERE suite=? AND model=?", (suite, model)).fetchone()
                    if old and old[0] == digest:
                        continue
                    stamp = iso(mtime) if first_import and not old else now
                    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
                    con.execute("INSERT INTO results (suite, model, row_json, hash, source_file, first_seen_utc, updated_utc) VALUES (?,?,?,?,?,?,?) "
                                "ON CONFLICT(suite, model) DO UPDATE SET row_json=excluded.row_json, hash=excluded.hash, "
                                "source_file=excluded.source_file, updated_utc=excluded.updated_utc",
                                (suite, model, payload, digest, name, stamp, stamp))
                    con.execute("INSERT INTO history (suite, model, hash, row_json, source_file, recorded_utc) VALUES (?,?,?,?,?,?)",
                                (suite, model, digest, payload, name, stamp))
        archive = {"suites": {suite: {} for suite in SUITES}}
        for suite, model, payload, source, updated in con.execute("SELECT suite, model, row_json, source_file, updated_utc FROM results"):
            archive["suites"].setdefault(suite, {})[model] = {"row": json.loads(payload), "updated": updated, "source": source}
        return archive
    finally:
        con.close()


def write_scores(entries):
    """Flat per-model table for SQL queries / spreadsheets; rewritten only when something changed."""
    rows = []
    for e in entries:
        g, de, c = e.get("general") or {}, e.get("german") or {}, e.get("context") or {}
        pct = g.get("pct") or {}
        rows.append((e["model"], g.get("quant"), g.get("size_gb"), g.get("total"), pct.get("Русский"), pct.get("Логика"), pct.get("Код"),
                     pct.get("Инструкции"), pct.get("Зрение"), g.get("tg"), g.get("pp"), g.get("vram_mib"), g.get("max_ctx"),
                     de.get("score"), de.get("n"), de.get("pct"), c.get("best_ctx"), c.get("stable_ctx"), c.get("recommended_cfg"),
                     e["updated_utc"]))
    digest = hashlib.sha1(json.dumps(rows, default=str).encode()).hexdigest()
    con = db()
    try:
        old = con.execute("SELECT value FROM meta WHERE key='scores_hash'").fetchone()
        if old and old[0] == digest:
            return
        with con:
            con.execute("DELETE FROM model_scores")
            con.executemany("INSERT INTO model_scores VALUES (" + ",".join("?" * 20) + ")", rows)
            con.execute("INSERT INTO meta (key, value) VALUES ('scores_hash', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (digest,))
            con.execute("INSERT INTO meta (key, value) VALUES ('scores_updated_utc', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (iso(time.time()),))
    finally:
        con.close()


def assemble(archive, current):
    entries = {}
    for suite in SUITES:
        for model, record in archive["suites"].get(suite, {}).items():
            entry = entries.setdefault(model, {"model": model})
            entry[suite] = {**record["row"], "tested_utc": record["updated"], "source": record.get("source"),
                            "archived": model not in current[suite]}
    for entry in entries.values():
        entry["updated_utc"] = max(entry[s]["tested_utc"] for s in SUITES if s in entry)
    ordered = sorted(entries.values(), key=lambda e: e["updated_utc"])
    for seq, entry in enumerate(ordered, 1):
        entry["seq"] = seq
    flat = [{**e["general"], "model": e["model"], "seq": e["seq"]} for e in ordered if "general" in e]
    flat.sort(key=lambda m: (m.get("failed", False), -(m.get("total") or -1)))
    return list(reversed(ordered)), flat


DEFAULT_PLAN = [
    {"id": "general", "title": "Общий тест", "per_model": True, "results": ["results_all.jsonl"], "log": "bench_full.log",
     "what": "Качество и скорость на контексте 8K: русский язык, логика, код, следование инструкциям, зрение; скорость генерации и чтения, пик видеопамяти."},
    {"id": "german", "title": "Немецкий язык: пассив", "per_model": True, "results": ["results_german.jsonl"], "log": "german_all.log",
     "what": "30 форм немецкого пассива (Vorgangspassiv, Modalverb + Passiv и др.), проверка точного ответа.",
     "note": "У части моделей много пустых ответов, их перемер идёт отдельным шагом после контекста."},
    {"id": "context", "title": "Максимальный стабильный контекст", "per_model": True, "results": ["results_ctx.jsonl"], "log": "bench_ctx.log",
     "finish_marker": "CTX-FINISHED",
     "what": "Для каждой модели ищется самое большое окно, при котором сервер стартует, находит 3 из 3 спрятанных фактов на 80% окна и не теряет скорость. Кэш пробуется только в видеопамяти (f16, q8, q4); пики загрузки GPU и перелив в оперативную память фиксируются в результате."},
    {"id": "german_fix", "title": "Перемер немецкого", "scope": "eligible", "est_total_minutes": 10, "results": ["results_german_fix.jsonl"], "log": "german_fix.log",
     "finish_marker": "GERMAN-FIX-FINISHED", "after": "context",
     "what": "Повтор немецкого теста для моделей с пустыми ответами; участвуют только модели с устойчивым GPU-контекстом 64K и более."},
    {"id": "accel", "title": "Ускорители и эмбеддинги", "scope": "eligible", "est_total_minutes": 120, "results": ["results_accel.jsonl"], "log": "bench_accel.log",
     "finish_marker": "ACCEL-FINISHED", "after": "german_fix",
     "what": "Скорость каждой пары с MTP, DFlash или черновой моделью с ускорителем и без (медиана ток/с), плюс проверка Qwen3-Embedding 0.6B и 4B: размерность, скорость, поиск на RU/EN/DE."},
    {"id": "stem", "title": "Математика и физика, 11 класс", "scope": "eligible", "est_minutes_per_model": 6, "results": ["results_stem.jsonl"], "log": "bench_stem.log",
     "finish_marker": "STEM-FINISHED", "after": "accel",
     "what": "40 сгенерированных задач с вычисленным ответом: сначала все модели без «размышлений», затем 8 лучших гибридных с размышлениями."},
    {"id": "soak", "title": "Финальная проверка надёжности (soak)", "fixed_total": 16, "est_total_minutes": 90, "results": ["results_soak.jsonl"], "log": "soak.log",
     "finish_marker": "SOAK-FINISHED", "after": "stem",
     "what": "Каждый из 16 профилей шлюза проходит серию шагов подряд: запуск, ответы на разном контексте, пик видеопамяти и свободная память хоста; отмечаются проблемы."},
    {"id": "code20", "title": "Код: 20 задач", "fixed_total": 15, "est_total_minutes": 120, "results": ["results_code20.jsonl"], "log": "bench_code20.log",
     "finish_marker": "CODE20-FINISHED", "after": "soak",
     "what": "Каждая из 15 моделей решает 20 задач на программирование; код запускается и проверяется тестами."},
    {"id": "chem", "title": "Химия, 11 класс", "scope": "eligible", "est_minutes_per_model": 3, "results": ["results_chem.jsonl"], "log": "bench_chem.log",
     "finish_marker": "CHEM-FINISHED", "after": "code20",
     "what": "10 задач с вычисляемым ответом: сначала без «размышлений», затем с размышлениями у подходящих моделей."},
    {"id": "finish", "title": "Профили шлюза и итоговый отчёт", "results": [], "log": "final.log", "finish_marker": "FINAL-FINISHED", "est_total_minutes": 15, "after": "chem",
     "what": "Найденные окна контекста переносятся в профили llama-swap и проверяются; итоговый отчёт: лидеры, дубли, список на удаление."},
]


def _log_info(name, marker):
    """(mtime, finished, current model, last result line) of a stage log."""
    if not name:
        return None
    path = os.path.join(BENCH, name)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as source:
        source.seek(max(0, os.path.getsize(path) - 120_000))
        lines = source.read().splitlines()
    current = None
    for line in reversed(lines):
        if line.startswith("=== "):
            current = re.split(r"\s+\(", line[4:].strip())[0].strip()
            break
    last = next((l.strip()[:170] for l in reversed(lines)
                 if re.match(r"^(DONE|ACCEL|STEM|GERMAN-FIX|EMBED|CTX)", l.strip())), None)
    progress = None
    for line in reversed(lines):
        found = re.match(r"^PROGRESS\s+(\d+)\s*/\s*(\d+)", line.strip())
        if found:
            progress = (int(found.group(1)), int(found.group(2)))
            break
        if re.match(r"^(DONE|ACCEL|STEM|GERMAN-FIX|EMBED|CTX)", line.strip()):
            break  # the previous model finished after the last progress line
    return {"mtime": os.path.getmtime(path), "finished": bool(marker and any(marker in l for l in lines)),
            "current": current, "last": last, "progress": progress}


def plan_models():
    """The models of the current benchmark list (TOP in bench_top.py); results of older runs of other models are not counted."""
    path = os.path.join(BENCH, "bench_top.py")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as source:
        text = source.read()
    block = text.split("TOP = [", 1)[-1].split(chr(10) + "]", 1)[0]
    return re.findall(r'^\s*\("([^"]+)",', block, re.M)


def excluded_models():
    """Models dropped from the later stages by the user rule: no stable GPU context >= 64K (best_ctx < 65536 in results_ctx.jsonl).
    ctx_recheck.txt lists models kept for a re-check; reasons come from the table in exclude_not_gpu.md."""
    path = os.path.join(BENCH, "results_ctx.jsonl")
    if not os.path.isfile(path):
        return {}
    keep = set()
    recheck = os.path.join(BENCH, "ctx_recheck.txt")
    if os.path.isfile(recheck):
        with open(recheck, encoding="utf-8") as source:
            keep = set(source.read().split())
    reasons = {}
    notes = os.path.join(BENCH, "exclude_not_gpu.md")
    if os.path.isfile(notes):
        with open(notes, encoding="utf-8") as source:
            for line in source:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == 2 and not set(cells[0]) <= set("-: ") and cells[0] != "Модель":
                    for name in cells[0].split(","):
                        reasons[name.strip()] = cells[1]
    out = {}
    for r in read_jsonl(path):
        model = r.get("model")
        if model and (r.get("best_ctx") or 0) < 65536 and model not in keep:
            out[model] = reasons.get(model) or "нет устойчивого GPU-контекста 64K и более"
    return out


def build_plan():
    """Benchmark pipeline: what is measured at every stage, what is done, what is running and what comes next."""
    plan = DEFAULT_PLAN
    override = os.path.join(BENCH, "benchmark_plan.json")
    if os.path.isfile(override):
        try:
            with open(override, encoding="utf-8") as source:
                plan = json.load(source).get("stages") or plan
        except (OSError, ValueError):
            pass
    order = plan_models()
    first = None if order else next((s for s in plan if s.get("per_model") and s.get("results")), None)
    if first:
        for r in read_jsonl(os.path.join(BENCH, first["results"][0])) if os.path.isfile(os.path.join(BENCH, first["results"][0])) else []:
            if r.get("model") and r["model"] not in order:
                order.append(r["model"])
    dropped = excluded_models()
    now, stages, states = time.time(), [], {}
    for stage in plan:
        eligible = stage.get("scope") == "eligible"
        stage_order = [m for m in order if m not in dropped] if eligible else order
        done, minutes, rows = [], [], []
        for name in stage.get("results") or []:
            path = os.path.join(BENCH, name)
            if os.path.isfile(path):
                for r in read_jsonl(path):
                    rows.append(r)
                    if r.get("model") and r["model"] not in done and not (eligible and r["model"] in dropped):
                        done.append(r["model"])
                    if isinstance(r.get("minutes"), (int, float)):
                        minutes.append(r["minutes"])
        log = _log_info(stage.get("log"), stage.get("finish_marker"))
        total = stage.get("fixed_total") or (len(stage_order) if (stage.get("per_model") or eligible) else None)
        recent = bool(log and now - log["mtime"] < 25 * 60)
        if stage.get("manual"):
            state = "waiting"
        elif log and log["finished"] or (total and len(done) >= total):
            state = "done"
        elif recent:
            state = "running"
        elif done or log:
            state = "paused"
        else:
            state = "waiting"
        states[stage["id"]] = state
        fact = None
        if state == "done" and eligible and stage["id"] == "accel":
            specs = len({r.get("profile") for r in rows if r.get("kind") == "spec"})
            embeds = len({r.get("profile") for r in rows if r.get("kind") == "embed"})
            if specs or embeds:
                fact = f"Готово: {specs} профилей ускорителей и {embeds} эмбеддингов."
        elif state == "done" and eligible and not rows:
            fact = "Не требовался: все модели списка сняты по правилу 64K."
        pending = [m for m in stage_order if m not in done] if total and not stage.get("fixed_total") else []
        current = log["current"] if state == "running" and log else None
        if current and current in pending:
            pending.remove(current)
        avg = sum(minutes) / len(minutes) if minutes else None
        pct, pct_exact = None, False
        if state == "running" and log:
            if log.get("progress") and log["progress"][1]:
                pct, pct_exact = min(99, round(100 * log["progress"][0] / log["progress"][1])), True
            elif avg:
                stamps = [os.path.getmtime(os.path.join(BENCH, n)) for n in stage.get("results") or [] if os.path.isfile(os.path.join(BENCH, n))]
                if stamps:
                    pct = max(1, min(95, round(100 * (now - max(stamps)) / 60 / avg)))
        remaining = len(pending) + (1 if current else 0)
        waiting_est = None
        if state in ("waiting", "paused") and not done:
            waiting_est = stage.get("est_total_minutes") or (stage.get("est_minutes_per_model", 0) * len(stage_order) or None)
        elapsed = sum(minutes) + ((pct / 100 * avg) if avg and pct is not None else 0)
        model_eta = round(avg * (1 - pct / 100), 1) if avg and pct is not None else None
        stages.append({"id": stage["id"], "title": stage["title"], "what": stage.get("what"), "note": stage.get("note"),
                       "state": state, "current_pct": pct, "pct_exact": pct_exact, "done": len(done), "total": None if fact else total, "fact": fact, "current": current, "next_models": pending[:6],
                       "pending_count": len(pending), "avg_minutes": round(avg, 1) if avg else None,
                       "eta_minutes": (round(avg * len(pending) + (model_eta if model_eta is not None else avg if current else 0)) if avg and state in ("running", "paused") and remaining else None),
                       "model_eta_minutes": model_eta, "queue_count": len(pending), "waiting_est_minutes": waiting_est, "elapsed_minutes": round(elapsed, 1),
                       "last": log["last"] if log else None, "log_updated_utc": iso(log["mtime"]) if log else None,
                       "after": stage.get("after"),
                       "excluded": [{"model": m, "reason": dropped[m]} for m in order if m in dropped] if eligible else []})
    running = next((s for s in stages if s["state"] == "running"), None)
    upcoming = [s for s in stages if s["state"] in ("waiting", "paused") and s is not running]
    spent = sum(x["elapsed_minutes"] for x in stages)
    left = sum((x["eta_minutes"] or 0) if x["state"] in ("running", "paused") and x["eta_minutes"] is not None else (x["waiting_est_minutes"] or 0)
               for x in stages if x["state"] != "done")
    overall = {"elapsed_minutes": round(spent), "remaining_minutes": round(left),
               "percent": min(100, round(100 * spent / (spent + left))) if spent + left else 0,
               "finished": all(x["state"] == "done" for x in stages)}
    return {"overall": overall, "stages": stages, "running": running["id"] if running else None,
            "next": upcoming[0]["id"] if upcoming else None, "models_total": len(order)}


def build():
    current, raw = collect()
    archive = merge_archive(current, raw)
    entries, models = assemble(archive, current)
    write_scores(entries)
    sources = [{"file": os.path.basename(p), "rows": len(read_jsonl(p)), "modified_utc": iso(os.path.getmtime(p))}
               for p in files("results*.jsonl")]
    fallback = []
    for path in files("fallback_test*.jsonl"):
        fallback += [{k: r.get(k) for k in ("model", "ctx", "kv", "started", "guard_killed", "host_free_min_gb", "error")}
                     for r in read_jsonl(path)]
    plan = set(plan_models())
    for entry in entries:
        entry["in_plan"] = not plan or entry["model"] in plan
    latest = max([e["updated_utc"] for e in entries] or [""])
    updated = {e["model"]: e["updated_utc"] for e in entries}
    return {"status": status_text(), "latest_result_utc": latest or None, "sources": sources, "models": models,
            "entries": entries, "suites": [{"id": k, "label": v, "count": len([m for m in archive["suites"].get(k, {}) if not plan or m in plan])} for k, v in SUITES.items()],
            "fallback": fallback, "activity": recent_files(), "current": current_model(updated), "plan": build_plan()}


def cycle(last_version):
    data = build()
    version = hashlib.sha1(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    os.makedirs(OUT, exist_ok=True)
    if version != last_version:
        payload = {"version": version, "built_utc": iso(time.time()), **data}
        target = os.path.join(OUT, "live-data.json")
        with open(target + ".tmp", "w", encoding="utf-8") as sink:
            json.dump(payload, sink, ensure_ascii=False, separators=(",", ":"))
        os.replace(target + ".tmp", target)
    beat = os.path.join(OUT, "live-status.json")
    with open(beat + ".tmp", "w", encoding="utf-8") as sink:
        json.dump({"version": version, "checked_utc": iso(time.time()), "models": len(data["models"])}, sink)
    os.replace(beat + ".tmp", beat)
    return version, len(data["models"]), version != last_version


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=15)
    args = parser.parse_args()
    version = None
    while True:
        try:
            version, count, changed = cycle(version)
            if changed:
                print(f"{iso(time.time())} live-data.json updated: {count} models, version {version}", flush=True)
        except Exception as exc:  # keep the sidecar alive through half-written files
            print(f"{iso(time.time())} build failed: {type(exc).__name__}: {exc}", flush=True)
        if not args.watch:
            break
        time.sleep(max(3, args.interval))


if __name__ == "__main__":
    main()
