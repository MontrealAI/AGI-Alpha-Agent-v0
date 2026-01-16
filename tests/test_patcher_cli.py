# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
import unittest


class TestPatcherCLI(unittest.TestCase):
    def test_cli_patches_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "tests").mkdir(parents=True)
            # buggy source file
            (repo / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            # failing test
            (repo / "tests" / "test_calc.py").write_text(
                "from calc import add\n\n" "def test_add():\n    assert add(1, 2) == 3\n",
                encoding="utf-8",
            )

            patch_file = Path(tmp) / "patch.diff"
            patch_contents = textwrap.dedent(
                    """\
                    --- a/calc.py
                    +++ b/calc.py
                    @@ -1,2 +1,2 @@
                    -def add(a, b):
                    -    return a - b
                    +def add(a, b):
                    +    return a + b
                    \\ No newline at end of file
                    """
            )
            if not patch_contents.endswith("\n"):
                patch_contents += "\n"
            patch_file.write_text(patch_contents, encoding="utf-8")

            stub_dir = Path(tmp) / "stubs"
            stub_pkg = stub_dir / "openai_agents"
            stub_pkg.mkdir(parents=True)
            (stub_pkg / "__init__.py").write_text(
                """import os
from pathlib import Path

class OpenAIAgent:
    def __init__(self, *a, **k):
        self.patch_file = os.environ.get('PATCH_FILE')

    def __call__(self, _prompt):
        return Path(self.patch_file).read_text() if self.patch_file else ''
""",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PATCH_FILE"] = str(patch_file)
            env["PYTHONPATH"] = f"{stub_dir}:{env.get('PYTHONPATH', '')}"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.demos.self_healing_repo.patcher_core",
                    "--repo",
                    str(repo),
                ],
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            combined = result.stdout + result.stderr
            self.assertIn("Patch fixed the tests", combined)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
