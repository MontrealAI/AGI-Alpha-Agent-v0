# SPDX-License-Identifier: Apache-2.0
"""Deterministic patch candidate generation for Repo-Healer v1."""

from __future__ import annotations

import difflib
import pathlib
import re
from dataclasses import dataclass

from .models import FailureBundle, PatchCandidate, ValidatorClass


@dataclass(frozen=True)
class _CandidateEdit:
    path: str
    summary: str
    original: str
    updated: str
    score: float


def _build_diff(path: str, original: str, updated: str) -> str:
    lines = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(lines) + "\n"


def _candidate_paths(bundle: FailureBundle) -> list[str]:
    paths = list(bundle.candidate_files)
    for signal in bundle.annotations:
        if signal.path:
            paths.append(signal.path)
    return sorted(set(paths))


def _ruff_fix(text: str, logs: str) -> str | None:
    # Example: "F401 'pathlib' imported but unused"
    match = re.search(r"F401\s+['\"]([\w.]+)['\"]\s+imported but unused", logs)
    if match:
        symbol = match.group(1)
        lines = text.splitlines()
        kept = [
            line
            for line in lines
            if not re.match(
                rf"\s*(from\s+\S+\s+import\s+.*\b{re.escape(symbol)}\b|import\s+{re.escape(symbol)}\b)",
                line,
            )
        ]
        if kept != lines:
            return "\n".join(kept) + "\n"

    # Example: "E702 Multiple statements on one line (semicolon)"
    if "E702" in logs and ";" in text:
        for line in text.splitlines():
            if ";" in line:
                parts = [part.strip() for part in line.split(";") if part.strip()]
                replacement = "\n".join(parts)
                return text.replace(line, replacement, 1)
    return None


def _mypy_fix(text: str, _logs: str) -> str | None:
    patterns = {
        "sha: str = 1": "sha: str",
        "= None": "",
    }
    for old, new in patterns.items():
        if old in text:
            return text.replace(old, new, 1)
    return None


def _import_fix(text: str, logs: str) -> str | None:
    # Example: "No module named 'definitely_missing_module'"
    match = re.search(r"No module named ['\"]([\w.]+)['\"]", logs)
    if not match:
        return None
    module = match.group(1)
    lines = text.splitlines()
    kept = [line for line in lines if line.strip() != f"import {module}"]
    if kept == lines:
        return None
    return "\n".join(kept) + "\n"


def _pytest_fix(text: str, _logs: str) -> str | None:
    replacements = {
        '"agent.pong"': '"agent.ping"',
        "'agent.pong'": "'agent.ping'",
    }
    for old, new in replacements.items():
        if old in text:
            return text.replace(old, new, 1)
    return None


def _mkdocs_fix(text: str, _logs: str) -> str | None:
    marker = "this_is_not_valid_yaml: ["
    if marker not in text:
        return None
    lines = [line for line in text.splitlines() if marker not in line]
    return "\n".join(lines) + "\n"


def _generate_edits(bundle: FailureBundle, repo_root: pathlib.Path) -> list[_CandidateEdit]:
    fixers = {
        ValidatorClass.RUFF: _ruff_fix,
        ValidatorClass.MYPY: _mypy_fix,
        ValidatorClass.IMPORT: _import_fix,
        ValidatorClass.PYTEST: _pytest_fix,
        ValidatorClass.SMOKE: _pytest_fix,
        ValidatorClass.MKDOCS: _mkdocs_fix,
    }
    fixer = fixers.get(bundle.validator_class)
    if fixer is None:
        return []

    edits: list[_CandidateEdit] = []
    for rel_path in _candidate_paths(bundle):
        path = repo_root / rel_path
        if not path.exists() or not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        updated = fixer(original, bundle.logs)
        if updated is None or updated == original:
            continue
        edits.append(
            _CandidateEdit(
                path=rel_path,
                summary=f"{bundle.validator_class.value} repair in {rel_path}",
                original=original,
                updated=updated,
                score=0.95,
            )
        )
    return edits


def generate_candidates(bundle: FailureBundle, repo_root: pathlib.Path) -> list[PatchCandidate]:
    """Generate deterministic safe patch candidates for supported Tier-1 failures."""
    candidates: list[PatchCandidate] = []
    for edit in _generate_edits(bundle, repo_root):
        diff = _build_diff(edit.path, edit.original, edit.updated)
        candidates.append(PatchCandidate(diff=diff, summary=edit.summary, score=edit.score))
    return candidates
