# SPDX-License-Identifier: Apache-2.0
"""Browserless smoke must retain mandatory browser coverage in its qualified job."""
from pathlib import Path
import shlex
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_native_browser_acceptance_is_one_command_with_both_suites() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/mark-wallet.yml").read_text())
    steps = workflow["jobs"]["wallet"]["steps"]
    run = next(
        step["run"] for step in steps if step.get("name") == "Bounded native bridge, authority and operator checks"
    )
    assert len(run.splitlines()) == 1, "Folded YAML must not split the pytest shell command"
    args = shlex.split(run)
    assert args[:3] == ["python", "-m", "pytest"]
    for name in ["test_budget_browser.py", "test_ecosystem_browser.py", "test_supplier_browser_browser.py"]:
        assert "tests/runtime/" + name in args
    assert any("playwright install --with-deps chromium" in step.get("run", "") for step in steps)
