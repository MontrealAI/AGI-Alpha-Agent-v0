import unittest
import subprocess
import sys
from pathlib import Path


class EdgeRunnerWrapperTest(unittest.TestCase):
    def test_edge_runner_help(self):
        script = Path(__file__).resolve().parents[1] / "edge_runner.py"
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Alpha-Factory Edge Runner", result.stdout)


if __name__ == "__main__":
    unittest.main()
