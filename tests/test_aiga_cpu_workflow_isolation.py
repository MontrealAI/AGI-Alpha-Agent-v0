# SPDX-License-Identifier: Apache-2.0
"""CPU workflow invocation regression; this does not qualify neural execution."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def test_cpu_invocation_blocks_explicit_legacy_package_plugin(tmp_path: Path) -> None:
    """Exercise the actual workflow flags with coverage intentionally absent."""
    workflow = (ROOT / ".github/workflows/aiga-reproducibility.yml").read_text()
    command = next(line.strip() for line in workflow.splitlines() if "pytest -q" in line and "--junitxml=" in line)
    tokens = shlex.split(command)
    args = tokens[tokens.index("pytest") + 1 :]
    # Preserve the workflow's exact invocation options while substituting a tiny
    # unittest package, independent of optional Torch/Gym/coverage installations.
    options = [arg for arg in args if not arg.endswith(".py") and not arg.startswith("--junitxml=")]
    assert "--noconftest" in options and "no:tests.conftest" in options
    assert "assert len(cases) == 36" in workflow  # Keep the real CPU gate separate.
    package = tmp_path / "legacy_cases"
    package.mkdir()
    (package / "__init__.py").write_text((ROOT / "alpha_factory_v1/tests/__init__.py").read_text())
    (package / "test_case.py").write_text(
        "import unittest\n\n"
        "class LegacyCase(unittest.TestCase):\n"
        "    def test_without_shared_fixtures(self):\n"
        "        self.assertEqual(1 + 1, 2)\n"
    )
    (tmp_path / "sitecustomize.py").write_text(
        "import importlib.abc\nimport sys\n\n"
        "class MissingCoverage(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'coverage' or fullname.startswith('coverage.'):\n"
        "            raise ModuleNotFoundError('coverage intentionally unavailable', name='coverage')\n"
        "sys.meta_path.insert(0, MissingCoverage())\n"
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(tmp_path), str(ROOT)]),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_ADDOPTS": "",
    }
    control_options = options.copy()
    block_index = control_options.index("no:tests.conftest")
    assert control_options[block_index - 1] == "-p"
    del control_options[block_index - 1 : block_index + 1]
    control = subprocess.run(
        [sys.executable, "-m", "pytest", *control_options, str(package)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert control.returncode == 1, control.stdout + control.stderr
    assert "coverage intentionally unavailable" in control.stdout + control.stderr
    report = tmp_path / "isolated.xml"
    isolated = subprocess.run(
        [sys.executable, "-m", "pytest", *options, str(package), f"--junitxml={report}"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert isolated.returncode == 0, isolated.stdout + isolated.stderr
    cases = list(ET.parse(report).getroot().iter("testcase"))
    assert len(cases) == 1
    assert all(cases[0].find(tag) is None for tag in ("skipped", "failure", "error"))
