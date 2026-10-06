"""Benchmark results for the main page: report/live-data.json joined with the numbered model library."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

LIVE_FILE = Path(os.environ.get("TESTS_LIVE_FILE", "/report-data/live-data.json"))
MODEL_ROOT = Path(os.environ.get("MODEL_DIR", "/models"))


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _library() -> list[tuple[str, str, str]]:
    """[(normalized name, '016', '016_Qwen3.5-9B')], longest names first so the most specific folder wins."""
    found = []
    try:
        for path in MODEL_ROOT.iterdir():
            match = re.match(r"^(\d{3})_(.+)$", path.name)
            if match and path.is_dir():
                found.append((_norm(match.group(2)), match.group(1), path.name))
    except OSError:
        pass
    return sorted(found, key=lambda item: -len(item[0]))


def _number(name: str, library: list[tuple[str, str, str]]) -> tuple[str | None, str | None]:
    normalized = _norm(name)
    return next(((number, folder) for norm, number, folder in library if normalized.startswith(norm)), (None, None))


def payload() -> dict:
    try:
        data = json.loads(LIVE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"error": f"Данные испытаний недоступны: {exc}", "entries": [], "total": 0}
    library = _library()
    entries = data.get("entries") or []
    for entry in entries:
        entry["library_no"], entry["library_folder"] = _number(str(entry.get("model")), library)
    current = data.get("current")
    if current:
        current["library_no"] = _number(str(current.get("model")), library)[0]
    return {"updated_utc": data.get("built_utc"), "latest_result_utc": data.get("latest_result_utc"), "current": current,
            "suites": data.get("suites") or [], "plan": data.get("plan"), "entries": entries,
            "total": sum(1 for e in entries if e.get("in_plan", True)), "total_all": len(entries)}
