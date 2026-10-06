import subprocess
import sys
import unittest

from helpers import ROOT

SCRIPT = ROOT / "scripts" / "install.py"


class InstallerTest(unittest.TestCase):
    def test_compose_arguments(self):
        import install
        self.assertEqual(install.compose_args(False), ["docker", "compose"])
        self.assertIn("docker-compose.nogpu.yml", install.compose_args(True))

    def test_unknown_flag_prints_usage(self):
        done = subprocess.run([sys.executable, str(SCRIPT), "doctor", "--bogus"], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("--no-gpu", done.stderr)

    def test_usage_documents_the_flags(self):
        done = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertIn("--pull", done.stderr)
        self.assertIn("--no-gpu", done.stderr)

    def test_gpu_override_file_is_valid_yaml_for_compose(self):
        text = (ROOT / "docker-compose.nogpu.yml").read_text(encoding="utf-8")
        self.assertIn("ai-console", text)
        self.assertIn("!reset", text)


if __name__ == "__main__":
    unittest.main()
