#!/usr/bin/env python3
"""Turns the live report data into a publishable results snapshot (no raw prompts or answers).

  python scripts/make_public_results.py [OUT_DIR]      # default: ./results-public

Reads report/live-data.json (written by the report builder) and writes
  RESULTS.md              tables for people (overall table and one leaderboard per test)
  results-summary.csv     one row per model, for spreadsheets
  results-summary.json    the same with the provenance block, for programs and for an AI supervisor

Provenance (who did what) is explained in docs/METHODOLOGY.*.md; the numbers come only from bench_results/results*.jsonl.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "report" / "live-data.json"
HARDWARE = os.environ.get("HARDWARE_NOTE", "NVIDIA GeForce RTX 3080 (10 GB video memory), Windows 10 + Docker Desktop (WSL2)")
COLUMNS = [("model", "Model"), ("quant", "Quant"), ("size_gb", "Size, GB"), ("vram_mib", "VRAM peak, MiB"), ("pp", "Prompt tok/s"), ("tg", "Gen tok/s"),
           ("general", "General %"), ("german", "German %"), ("ctx_k", "Stable context, K"), ("stem", "Math+Physics %"), ("chem", "Chemistry %"),
           ("code20", "Code, of 20"), ("status", "Status")]


def value(entry: dict, suite: str, key: str):
    return (entry.get(suite) or {}).get(key)


def status(name: str, general: dict, excluded: dict) -> str:
    if general.get("failed"):
        return "failed to load"
    return "removed from later tests: " + excluded[name] if name in excluded else "admitted"


def row(entry: dict, excluded: dict) -> dict:
    general = entry.get("general") or {}
    ctx = value(entry, "context", "stable_ctx") or value(entry, "context", "best_ctx")
    name = entry["model"]
    return {"model": name, "quant": general.get("quant"), "size_gb": general.get("size_gb"), "vram_mib": general.get("vram_mib"),
            "pp": general.get("pp"), "tg": general.get("tg"), "general": general.get("total"), "german": value(entry, "german", "pct"),
            "ctx_k": round(ctx / 1024) if ctx else None, "stem": value(entry, "stem", "pct"), "chem": value(entry, "chem", "pct"),
            "code20": value(entry, "code20", "passed"), "status": status(name, general, excluded)}


def fmt(v) -> str:
    return "-" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


def table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(title for _, title in columns) + " |\n|" + "|".join("---" for _ in columns) + "|\n"
    return head + "\n".join("| " + " | ".join(fmt(r.get(key)) for key, _ in columns) + " |" for r in rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the publishable results snapshot (no prompts, no answers).")
    parser.add_argument("out", nargs="?", type=Path, default=ROOT / "results-public", help="output folder (default: results-public)")
    parser.add_argument("--live", type=Path, default=LIVE, help="report data file written by the report builder (default: report/live-data.json)")
    args = parser.parse_args()
    out = args.out
    try:
        data = json.loads(args.live.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"cannot read {args.live}: {exc}. Start the report builder (python scripts/install.py up) and wait for the first results.")
    out.mkdir(parents=True, exist_ok=True)
    excluded = {}
    for stage in (data.get("plan") or {}).get("stages", []):
        for item in stage.get("excluded") or []:
            excluded[item["model"]] = "no stable GPU context of 64K or more"
    entries = [e for e in data["entries"] if e.get("in_plan", True)]
    rows = sorted((row(e, excluded) for e in entries), key=lambda r: (-(r["general"] if r["general"] is not None else -1), r["model"]))
    version = ""
    try:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    provenance = {"server_version": version, "snapshot_built_utc": data.get("built_utc"), "hardware": HARDWARE, "models_tested": len(rows),
                  "models_admitted": sum(1 for r in rows if r["status"] == "admitted"),
                  "chain": "server core (gateway + console + report builder) -> Claude as supervisor (prepared, ran and checked the tests) -> results -> this repository",
                  "license": "CC BY 4.0, credit: homensai.com (https://homensai.com)"}
    (out / "results-summary.json").write_text(json.dumps({"provenance": provenance, "models": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "results-summary.csv").open("w", encoding="utf-8", newline="") as sink:
        writer = csv.writer(sink)
        writer.writerow([title for _, title in COLUMNS])
        for r in rows:
            writer.writerow([r.get(key) for key, _ in COLUMNS])
    lines = ["# Test results / Результаты тестов / Testergebnisse", "",
             f"Server version {version or '?'} · snapshot {data.get('built_utc', '?')} · {HARDWARE}", "",
             f"{provenance['models_tested']} models tested, {provenance['models_admitted']} admitted to the later stages (stable GPU context of at least 64K). "
             "How the numbers were produced (server core -> Claude as supervisor -> results): [METHODOLOGY](../docs/METHODOLOGY.en.md) · "
             "[RU](../docs/METHODOLOGY.ru.md) · [DE](../docs/METHODOLOGY.de.md).", "",
             "Data: homensai.com (https://homensai.com), CC BY 4.0. Results are from one machine and from small task sets: use them as a guide, not as a ranking of model quality.", "",
             "## All models", "", table(rows, COLUMNS)]
    boards = [("general", "General test, %"), ("german", "German, %"), ("ctx_k", "Stable context, K"), ("stem", "Math + Physics, %"), ("chem", "Chemistry, %"), ("code20", "Code, of 20"), ("tg", "Generation speed, tok/s")]
    for key, title in boards:
        ranked = sorted((r for r in rows if r.get(key) is not None), key=lambda r: -r[key])
        if ranked:
            lines += [f"## {title}", "", table(ranked, [("model", "Model"), (key, title)]), ""]
    (out / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"{len(rows)} models -> {out}")


if __name__ == "__main__":
    main()
