import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT


def write_rows(folder: Path, name: str, rows: list) -> None:
    (folder / name).write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n", encoding="utf-8")


class BuilderTest(unittest.TestCase):
    def build(self, files: dict) -> dict:
        tmp = Path(tempfile.mkdtemp())
        bench, out = tmp / "bench", tmp / "out"
        bench.mkdir()
        out.mkdir()
        for name, rows in files.items():
            write_rows(bench, name, rows)
        env = {**os.environ, "BENCH_DIR": str(bench), "OUT_DIR": str(out), "RESULTS_DB": str(tmp / "db" / "r.sqlite")}
        done = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "build_live_report.py")], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.db = tmp / "db" / "r.sqlite"
        return json.loads((out / "live-data.json").read_text(encoding="utf-8"))

    def test_model_that_failed_to_load_is_listed_even_without_quality(self):
        data = self.build({"results_all.jsonl": [{"model": "Broken", "load_ok": False, "error": "out of memory"}]})
        broken = [m for m in data["models"] if m["model"] == "Broken"]
        self.assertEqual(len(broken), 1)
        self.assertTrue(broken[0]["failed"])
        self.assertEqual(broken[0]["error"], "out of memory")

    def test_scores_are_computed_per_category(self):
        row = {"model": "A", "load_ok": True, "quality": [{"task": "t1", "cat": "Русский", "score": 3, "max": 4},
                                                            {"task": "t2", "cat": "Логика", "score": 2, "max": 2}]}
        model = self.build({"results_all.jsonl": [row]})["models"][0]
        self.assertEqual(model["pct"], {"Русский": 75, "Логика": 100})
        self.assertEqual(model["total"], 88)

    def test_invalid_scores_never_give_more_than_100_percent(self):
        row = {"model": "A", "load_ok": True, "quality": [
            {"task": "t1", "cat": "Код", "score": 5, "max": 0},      # a broken checker
            {"task": "t2", "cat": "Код", "score": "x", "max": 2},    # not a number
            {"task": "t3", "cat": "Код", "score": 9, "max": 3},      # above the maximum: clamped
            {"task": "t4", "cat": "Код", "score": -1, "max": 3}]}    # negative
        model = self.build({"results_all.jsonl": [row]})["models"][0]
        self.assertEqual(model["pct"], {"Код": 100})
        self.assertEqual(model["invalid_items"], 3)

    def test_half_written_line_is_ignored_and_old_rows_stay_in_the_archive(self):
        good = {"model": "A", "load_ok": True, "quality": [{"task": "t", "cat": "Код", "score": 1, "max": 2}]}
        data = self.build({"results_all.jsonl": [good, "{broken json"]})
        self.assertEqual([m["model"] for m in data["models"]], ["A"])
        count = sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM raw_rows").fetchone()[0]
        self.assertEqual(count, 1)

    def test_deleted_output_file_is_written_again_without_new_results(self):
        import build_live_report as builder
        tmp = Path(tempfile.mkdtemp())
        (tmp / "bench").mkdir()
        write_rows(tmp / "bench", "results_all.jsonl", [{"model": "A", "load_ok": True, "quality": [{"task": "t", "cat": "Код", "score": 1, "max": 1}]}])
        saved = builder.BENCH, builder.OUT, builder.DB_PATH
        builder.BENCH, builder.OUT, builder.DB_PATH = str(tmp / "bench"), str(tmp / "out"), str(tmp / "db" / "r.sqlite")
        try:
            version, _, changed = builder.cycle(None)
            self.assertTrue(changed)
            self.assertFalse(builder.cycle(version)[2])  # nothing new: not rewritten
            (tmp / "out" / "live-data.json").unlink()
            self.assertTrue(builder.cycle(version)[2])
            self.assertTrue((tmp / "out" / "live-data.json").is_file())
        finally:
            builder.BENCH, builder.OUT, builder.DB_PATH = saved


if __name__ == "__main__":
    unittest.main()
