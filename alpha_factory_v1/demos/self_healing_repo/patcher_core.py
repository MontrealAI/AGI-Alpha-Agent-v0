# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/demos/self_healing_repo/patcher_core.py
# © 2025 MONTREAL.AI   Apache-2.0 License
"""
patcher_core.py
───────────────
A self‑contained utility for the **Self‑Healing Repo** demo.

Functions
---------
generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str
    • Crafts a prompt from the pytest log and asks the LLM for a unified diff.
    • Verifies that the diff only touches files that already exist.

apply_patch(patch: str, repo_path: str) -> None
    • Applies the diff using GNU patch, with rollback on patch failure.
    • Keeps distinct backups in a temporary directory, preserving user backups.

validate_repo(repo_path: str, cmd: Optional[list[str]] = None) -> tuple[int,str]
    • Runs the given command, returning (returncode, combined stdout+stderr).

The trio forms a minimal healing loop for trusted, exclusively owned workspaces.
Validation commands execute with the caller's permissions; this is not a sandbox.

Patch targets must be ordinary repository files. Untrusted validators require
separate operating-system isolation.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from typing import List, Optional, Tuple
from typing import TYPE_CHECKING

from .repo_healer_v1.workspace import project_path, workspace_files

if TYPE_CHECKING:  # avoid hard dependency unless actually used
    from openai_agents import OpenAIAgent


# ─────────────────────────── helpers ─────────────────────────────────────────
def _run(cmd: List[str], cwd: str) -> Tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def validate_repo(repo_path: str, cmd: Optional[List[str]] = None) -> Tuple[int, str]:
    """Return (exit_code, full_output)."""
    cmd = cmd or [sys.executable, "-m", "pytest", "-q"]
    return _run(cmd, cwd=repo_path)


def _existing_files(repo: pathlib.Path) -> set[str]:
    return {path.as_posix() for path in workspace_files(repo)}


# ────────────────────────── patch logic ─────────────────────────────────────
def generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str:
    """Ask the LLM to suggest a unified diff patch fixing the failure."""
    prompt = textwrap.dedent(
        f"""
    You are an expert software engineer. A test suite failed as follows:

    ```text
    {test_log}
    ```

    Produce a **unified diff** that fixes the bug. Constraints:
    1. Modify only existing files inside the repository.
    2. Do not add or delete entire files.
    3. Keep the patch minimal and idiomatic.
    """
    )
    response = llm(prompt)
    if asyncio.iscoroutine(response):
        response = asyncio.run(response)
    patch = _normalize_patch(str(response))
    if not _looks_like_diff(patch):
        patch_override = os.getenv("PATCH_FILE")
        if patch_override:
            patch = _normalize_patch(pathlib.Path(patch_override).read_text(encoding="utf-8"))
    _sanity_check_patch(patch, pathlib.Path(repo_path))
    return patch


def _ensure_hunk_ranges(patch: str) -> str:
    lines = patch.splitlines()
    normalized: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("@@") and not re.search(r"@@\s*-\d", line):
            removed = 0
            added = 0
            scan = idx + 1
            while scan < len(lines) and not lines[scan].startswith(("@@", "--- ", "+++ ")):
                hunk_line = lines[scan]
                if hunk_line.startswith("+") and not hunk_line.startswith("+++"):
                    added += 1
                elif hunk_line.startswith("-") and not hunk_line.startswith("---"):
                    removed += 1
                else:
                    added += 1
                    removed += 1
                scan += 1
            normalized.append(f"@@ -1,{removed} +1,{added} @@")
            idx += 1
            continue
        normalized.append(line)
        idx += 1
    return "\n".join(normalized) + "\n"


def _normalize_patch(patch: str) -> str:
    patch = textwrap.dedent(patch).lstrip()
    patch = _ensure_hunk_ranges(patch)
    if not patch.endswith("\n"):
        patch += "\n"
    return patch


def _looks_like_diff(patch: str) -> bool:
    has_before = False
    has_after = False
    for line in patch.splitlines():
        if line.startswith("--- "):
            has_before = True
        elif line.startswith("+++ "):
            has_after = True
        if has_before and has_after:
            return True
    return False


def _sanity_check_patch(patch: str, repo_root: pathlib.Path) -> None:
    """Ensure the diff only touches existing files to avoid LLM wildness."""
    touched = set()
    for line in patch.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
            project_path(repo_root, path)
            touched.add(path)
    if not touched or not _looks_like_diff(patch):
        raise ValueError("Patch must contain unified diff file headers")
    non_existing = touched - _existing_files(repo_root)
    if non_existing:
        raise ValueError(f"Patch refers to unknown files: {', '.join(non_existing)}")


def apply_patch(patch: str, repo_path: str) -> None:
    """Apply a patch to ordinary project files, restoring backups on failure."""
    repo = pathlib.Path(repo_path).resolve(strict=True)
    patch = _normalize_patch(patch)
    _sanity_check_patch(patch, repo)
    if shutil.which("patch") is None:
        raise RuntimeError(
            '`patch` command not found. Install the utility, e.g., "sudo apt-get update && sudo apt-get install -y patch"'
        )
    touched = sorted(
        {
            re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
            for line in patch.splitlines()
            if line.startswith(("--- ", "+++ "))
        }
    )
    with tempfile.TemporaryDirectory(prefix="repo-healer-patch-") as temp:
        storage = pathlib.Path(temp)
        patch_file = storage / "change.diff"
        patch_file.write_text(patch, encoding="utf-8")
        backups: dict[pathlib.Path, pathlib.Path] = {}
        for index, rel in enumerate(touched):
            file_path = project_path(repo, rel)
            backup = storage / f"original-{index}"
            shutil.copy2(file_path, backup)
            backups[file_path] = backup
        try:
            code, out = _run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--no-backup-if-mismatch",
                    "--reject-file=-",
                    "-p1",
                    "-i",
                    str(patch_file),
                ],
                cwd=str(repo),
            )
            if code != 0:
                raise RuntimeError(f"patch command failed:\n{out}")
        except Exception:
            for original, backup in backups.items():
                shutil.copy2(backup, original)
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Minimal self-healing CLI")
    parser.add_argument("--repo", default=".", help="Repository path")
    args = parser.parse_args()

    _temp_env = os.getenv("TEMPERATURE")
    try:
        from openai_agents import OpenAIAgent
    except ModuleNotFoundError:
        from .agent_core import llm_client

        def llm(prompt: str) -> str:
            """Offline fallback using the local LLM."""
            return str(llm_client.call_local_model([{"role": "user", "content": prompt}]))

    else:
        llm = OpenAIAgent(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=("http://ollama:11434/v1" if not os.getenv("OPENAI_API_KEY") else None),
            temperature=float(_temp_env) if _temp_env is not None else None,
        )
    rc, out = validate_repo(args.repo)
    print(out)
    if rc != 0:
        patch = generate_patch(out, llm=llm, repo_path=args.repo)
        print(patch)
        apply_patch(patch, repo_path=args.repo)
        rc, out = validate_repo(args.repo)
        print(out)
        if rc == 0:
            print("\n\u2728 Patch fixed the tests")
        else:
            print("\n\u26a0\ufe0f Patch did not fix the tests")
    else:
        print("Tests already pass")
