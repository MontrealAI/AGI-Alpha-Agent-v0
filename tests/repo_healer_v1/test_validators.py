# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import validators


def test_parse_first_pytest_command_multiline() -> None:
    block = """
    pytest -m smoke \\
      tests/test_one.py \\
      tests/test_two.py -q
    echo done
    """
    cmd = validators._parse_first_pytest_command(block)
    assert cmd[0:3] == [validators.PYTHON, "-m", "pytest"]
    assert "tests/test_one.py" in cmd
    assert "tests/test_two.py" in cmd


def test_parse_first_pytest_command_returns_empty_when_absent() -> None:
    cmd = validators._parse_first_pytest_command("python -m pip install -U pip")
    assert cmd == []
