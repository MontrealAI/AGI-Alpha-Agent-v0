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
    • Applies the diff atomically (uses GNU patch).
    • Creates a `.bak` backup per touched file and rolls back on failure.

validate_repo(repo_path: str, cmd: Optional[list[str]] = None) -> tuple[int,str]
    • Runs the given command, returning (returncode, combined stdout+stderr).

The trio forms a minimal, production‑ready healing loop while remaining
agnostic to any higher‑level agent orchestration.

All file‑system mutations stay **inside `repo_path`** for container safety.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import textwrap
from typing import List, Optional, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid hard dependency unless actually used
    from openai_agents import OpenAIAgent


# ─────────────────────────── helpers ─────────────────────────────────────────
def _run(cmd: List[str], cwd: str) -> Tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def validate_repo(repo_path: str, cmd: Optional[List[str]] = None) -> Tuple[int, str]:
    """Return (exit_code, full_output)."""
    cmd = cmd or ["pytest", "-q"]
    return _run(cmd, cwd=repo_path)


def _existing_files(repo: pathlib.Path) -> set[str]:
    return {str(p.relative_to(repo)) for p in repo.rglob("*") if p.is_file()}


def _normalize_line(line: str) -> str:
    return line if line.endswith("\n") else f"{line}\n"


def _apply_hunk(lines: list[str], hunk_lines: list[str]) -> list[str]:
    """Apply a single unified-diff hunk by search/replace."""
    old = [_normalize_line(l[1:]) for l in hunk_lines if l.startswith(("-", " "))]
    new = [_normalize_line(l[1:]) for l in hunk_lines if l.startswith(("+", " "))]
    for idx in range(len(lines) - len(old) + 1):
        if lines[idx : idx + len(old)] == old:
            return lines[:idx] + new + lines[idx + len(old) :]
    raise RuntimeError("hunk context not found for patch application")


def _apply_patch_fallback(patch: str, repo_path: str) -> None:
    """Apply a unified diff without external patch tooling."""
    repo = pathlib.Path(repo_path)
    lines = patch.splitlines()
    i = 0
    applied = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            path_line = lines[i + 1] if i + 1 < len(lines) else ""
            if not path_line.startswith("+++ "):
                raise RuntimeError("patch missing '+++' header")
            rel_path = re.sub(r"^[ab]/", "", path_line[4:].split("\t")[0])
            file_path = repo / rel_path
            file_lines = file_path.read_text().splitlines(keepends=True)
            i += 2
            while i < len(lines) and not lines[i].startswith("--- "):
                if lines[i].startswith("@@"):
                    hunk: list[str] = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith(("@@", "--- ")):
                        if lines[i].startswith("\\"):
                            i += 1
                            continue
                        hunk.append(lines[i])
                        i += 1
                    if hunk:
                        file_lines = _apply_hunk(file_lines, hunk)
                        applied = True
                else:
                    i += 1
            file_path.write_text("".join(file_lines))
        else:
            i += 1
    if not applied:
        raise RuntimeError("patch command failed:\nNo applicable hunks")


# ────────────────────────── patch logic ─────────────────────────────────────
def generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str:
    """Ask the LLM to suggest a unified diff patch fixing the failure."""
    patch_file = os.getenv("PATCH_FILE")
    if patch_file:
        patch = textwrap.dedent(pathlib.Path(patch_file).read_text()).strip()
        _sanity_check_patch(patch, pathlib.Path(repo_path))
        return patch
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
    patch = textwrap.dedent(str(response)).strip()
    _sanity_check_patch(patch, pathlib.Path(repo_path))
    return patch


def _sanity_check_patch(patch: str, repo_root: pathlib.Path) -> None:
    """Ensure the diff only touches existing files to avoid LLM wildness."""
    touched = set()
    for line in patch.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
            touched.add(path)
    non_existing = touched - _existing_files(repo_root)
    if non_existing:
        raise ValueError(f"Patch refers to unknown files: {', '.join(non_existing)}")


def apply_patch(patch: str, repo_path: str) -> None:
    """Apply patch atomically with rollback on failure."""
    patch = textwrap.dedent(patch).strip()
    repo = pathlib.Path(repo_path)
    _sanity_check_patch(patch, repo)
    backups = {}

    # write patch to temp file
    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(patch)
        patch_file = tf.name

    try:
        # back up touched files
        for line in patch.splitlines():
            if line.startswith(("--- ", "+++ ")):
                rel = re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
                file_path = repo / rel
                if file_path.exists():
                    backup = file_path.with_suffix(".bak")
                    shutil.copy2(file_path, backup)
                    backups[file_path] = backup
        # apply
        if shutil.which("patch") is None:
            _apply_patch_fallback(patch, repo_path)
        else:
            code, out = _run(["patch", "-p1", "-i", patch_file], cwd=repo_path)
            if code != 0:
                try:
                    _apply_patch_fallback(patch, repo_path)
                except Exception as exc:
                    raise RuntimeError(f"patch command failed:\n{out}") from exc
    except Exception as e:
        # rollback
        for orig, bak in backups.items():
            shutil.move(bak, orig)
        raise e
    finally:
        os.unlink(patch_file)
        # clean backups if success
        for bak in backups.values():
            if bak.exists():
                os.unlink(bak)


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
            return llm_client.call_local_model([{"role": "user", "content": prompt}])

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
