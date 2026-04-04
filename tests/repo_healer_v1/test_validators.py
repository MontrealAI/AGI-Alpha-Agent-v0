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


def test_extract_smoke_pytest_command_returns_empty_on_invalid_yaml(monkeypatch) -> None:
    def _boom(_text: str) -> list[str]:
        raise validators.yaml.YAMLError("bad yaml")

    monkeypatch.setattr(validators.yaml, "safe_load", _boom)
    assert validators._extract_smoke_pytest_command() == []


def test_extract_smoke_pytest_command_returns_empty_on_non_mapping_yaml(monkeypatch) -> None:
    monkeypatch.setattr(validators.yaml, "safe_load", lambda _text: ["not-a-mapping"])
    assert validators._extract_smoke_pytest_command() == []


def test_smoke_broader_validation_runs_full_pytest_suite() -> None:
    plan = validators.get_plan(validators.ValidatorClass.SMOKE)
    assert plan.broader == [validators.PYTHON, "-m", "pytest", "-q"]
