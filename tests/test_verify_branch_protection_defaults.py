from __future__ import annotations

import ast

import pytest
from pathlib import Path
from scripts import verify_branch_protection


EXPECTED_REQUIRED_CHECKS = [
    "Lint (ruff)",
    "Smoke tests",
]


def test_default_required_checks_match_expectations() -> None:
    assert verify_branch_protection.DEFAULT_REQUIRED_CHECKS == EXPECTED_REQUIRED_CHECKS


def test_verify_branch_protection_has_no_requests_dependency() -> None:
    source = Path(verify_branch_protection.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "requests" not in imported_roots


def test_verify_branch_protection_warns_and_exits_cleanly_without_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    rc = verify_branch_protection.main(["--branch", "main"])
    output = capsys.readouterr().err

    assert rc == 0
    assert "No GitHub token available; skipping branch protection verification." in output
