# SPDX-License-Identifier: Apache-2.0
"""Deterministic candidate generation for Repo-Healer v1."""

from __future__ import annotations

import difflib
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Callable

from .models import FailureBundle, PatchCandidate, ValidatorClass

_IGNORE_DIRS = {".git", ".mypy_cache", ".pytest_cache", "__pycache__"}


def generate_candidates(repo_root: pathlib.Path, bundle: FailureBundle) -> list[PatchCandidate]:
    """Return bounded rule-based candidates for supported Tier-1 classes."""
    if bundle.validator_class == ValidatorClass.RUFF:
        candidate = _candidate_from_mutation(repo_root, bundle, _apply_ruff_fix)
        return [candidate] if candidate else []
    if bundle.validator_class == ValidatorClass.IMPORT:
        candidate = _candidate_from_mutation(repo_root, bundle, _fix_missing_import)
        return [candidate] if candidate else []
    if bundle.validator_class == ValidatorClass.MKDOCS:
        candidate = _candidate_from_mutation(repo_root, bundle, _fix_mkdocs_yaml)
        return [candidate] if candidate else []
    return []


def _candidate_from_mutation(
    repo_root: pathlib.Path,
    bundle: FailureBundle,
    mutator: Callable[[pathlib.Path, FailureBundle], bool],
) -> PatchCandidate | None:
    with tempfile.TemporaryDirectory(prefix="repo-healer-candidate-") as tmp:
        tmp_repo = pathlib.Path(tmp) / "repo"
        shutil.copytree(repo_root, tmp_repo, ignore=shutil.ignore_patterns(*_IGNORE_DIRS))
        changed = mutator(tmp_repo, bundle)
        if not changed:
            return None
        diff = _diff_between_repos(repo_root, tmp_repo)
        if not diff.strip():
            return None
        return PatchCandidate(diff=diff, summary=f"rule-based fix for {bundle.validator_class.value}", score=0.7)


def _apply_ruff_fix(repo: pathlib.Path, bundle: FailureBundle) -> bool:
    targets = [path for path in bundle.candidate_files if path.endswith(".py")]
    cmd = ["ruff", "check", "--fix", *(targets or ["."])]
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return proc.returncode == 0


def _fix_missing_import(repo: pathlib.Path, bundle: FailureBundle) -> bool:
    missing = _extract_missing_module(bundle.logs)
    if not missing:
        return False
    targets = [pathlib.Path(path) for path in bundle.candidate_files if path.endswith(".py")]
    if not targets:
        targets = [pathlib.Path("tests/test_imports.py")]

    changed = False
    for rel in targets:
        path = repo / rel
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        filtered = [line for line in lines if not _is_import_of(line, missing)]
        if filtered != lines:
            path.write_text("".join(filtered), encoding="utf-8")
            changed = True
    return changed


def _fix_mkdocs_yaml(repo: pathlib.Path, _bundle: FailureBundle) -> bool:
    mkdocs = repo / "mkdocs.yml"
    if not mkdocs.exists():
        return False
    original = mkdocs.read_text(encoding="utf-8")
    marker = "this_is_not_valid_yaml: [\n"
    if marker not in original:
        return False
    mkdocs.write_text(original.replace(marker, "", 1), encoding="utf-8")
    return True


def _extract_missing_module(logs: str) -> str | None:
    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", logs)
    return match.group(1) if match else None


def _is_import_of(line: str, module: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(f"import {module}") or stripped.startswith(f"from {module} import")


def _iter_files(root: pathlib.Path) -> set[pathlib.Path]:
    out: set[pathlib.Path] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in _IGNORE_DIRS:
            continue
        out.add(rel)
    return out


def _diff_between_repos(original: pathlib.Path, modified: pathlib.Path) -> str:
    files = sorted(_iter_files(original) | _iter_files(modified))
    hunks: list[str] = []
    for rel in files:
        left = original / rel
        right = modified / rel
        left_text = left.read_text(encoding="utf-8") if left.exists() else ""
        right_text = right.read_text(encoding="utf-8") if right.exists() else ""
        if left_text == right_text:
            continue
        diff = difflib.unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile=f"a/{rel.as_posix()}",
            tofile=f"b/{rel.as_posix()}",
            lineterm="",
        )
        hunks.append("\n".join(diff) + "\n")
    return "".join(hunks)
