import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT

SCRIPT = ROOT / "scripts" / "make_public_results.py"


class PublicResultsTest(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=tempfile.mkdtemp())

    def test_help_does_not_create_a_folder(self):
        cwd = Path(tempfile.mkdtemp())
        done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, cwd=cwd)
        self.assertEqual(done.returncode, 0)
        self.assertEqual(list(cwd.iterdir()), [])

    def test_missing_data_file_is_a_clear_error(self):
        done = self.run_script("--live", "/nonexistent/live-data.json", str(Path(tempfile.mkdtemp()) / "out"))
        self.assertEqual(done.returncode, 1)
        self.assertIn("cannot read", done.stderr)
        self.assertNotIn("Traceback", done.stderr)

    def test_failed_model_is_not_marked_admitted(self):
        tmp = Path(tempfile.mkdtemp())
        live = tmp / "live.json"
        live.write_text(json.dumps({"built_utc": "2026-01-01T00:00:00Z", "plan": {"stages": []}, "entries": [
            {"model": "Good", "general": {"total": 90, "failed": False}},
            {"model": "Bad", "general": {"failed": True, "error": "/home/someone/secret path"}}]}), encoding="utf-8")
        done = self.run_script("--live", str(live), str(tmp / "out"))
        self.assertEqual(done.returncode, 0, done.stderr)
        summary = json.loads((tmp / "out" / "results-summary.json").read_text(encoding="utf-8"))
        status = {m["model"]: m["status"] for m in summary["models"]}
        self.assertEqual(status, {"Good": "admitted", "Bad": "failed to load"})
        self.assertEqual(summary["provenance"]["models_admitted"], 1)
        self.assertNotIn("secret", (tmp / "out" / "RESULTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
