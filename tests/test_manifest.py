import subprocess
import sys
import unittest

from helpers import ROOT


class ManifestTest(unittest.TestCase):
    def test_manifest_matches_tracked_files(self):
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_manifest.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
