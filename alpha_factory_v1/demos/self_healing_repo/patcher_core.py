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

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
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


# ────────────────────────── patch logic ─────────────────────────────────────
def generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str:
    """Ask the LLM to suggest a unified diff patch fixing the failure."""
    override = os.getenv("PATCH_FILE")
    if override:
        override_path = pathlib.Path(override)
        if override_path.is_file():
            patch = override_path.read_text()
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
    if hasattr(response, "__await__"):
        import asyncio

        response = asyncio.run(response)
    patch = str(response).strip()
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


@dataclass
class _Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]


_HUNK_RE = re.compile(r"^@@ -(?P<o>\d+)(?:,(?P<ol>\d+))? \\+(?P<n>\d+)(?:,(?P<nl>\d+))? @@")


def _parse_diff(patch: str) -> list[tuple[str, list[_Hunk]]]:
    files: list[tuple[str, list[_Hunk]]] = []
    current_file: str | None = None
    hunks: list[_Hunk] = []
    current_hunk: _Hunk | None = None

    def _flush() -> None:
        nonlocal current_file, hunks
        if current_file is not None:
            files.append((current_file, hunks))
        current_file = None
        hunks = []

    for line in patch.splitlines():
        if line.startswith("--- "):
            continue
        if line.startswith("+++ "):
            _flush()
            path = re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
            current_file = path
            continue
        if line.startswith("@@"):
            if current_file is None:
                raise RuntimeError("patch command failed: missing file header")
            match = _HUNK_RE.match(line)
            if match:
                current_hunk = _Hunk(
                    old_start=int(match.group("o")),
                    old_count=int(match.group("ol") or "1"),
                    new_start=int(match.group("n")),
                    new_count=int(match.group("nl") or "1"),
                    lines=[],
                )
            else:
                current_hunk = _Hunk(old_start=1, old_count=0, new_start=1, new_count=0, lines=[])
            hunks.append(current_hunk)
            continue
        if line.startswith("\\ No newline"):
            continue
        if current_hunk is not None:
            current_hunk.lines.append(line)

    if current_file is not None:
        files.append((current_file, hunks))
    return files


def _apply_hunks(original: list[str], hunks: Iterable[_Hunk]) -> list[str]:
    new_lines: list[str] = []
    idx = 0
    for hunk in hunks:
        start = max(hunk.old_start - 1, 0)
        if start > len(original):
            raise RuntimeError("patch command failed: hunk start out of range")
        new_lines.extend(original[idx:start])
        idx = start
        for hline in hunk.lines:
            if hline.startswith(" "):
                expected = hline[1:]
                if idx >= len(original) or original[idx] != expected:
                    raise RuntimeError("patch command failed: context mismatch")
                new_lines.append(original[idx])
                idx += 1
            elif hline.startswith("-"):
                expected = hline[1:]
                if idx >= len(original) or original[idx] != expected:
                    raise RuntimeError("patch command failed: removal mismatch")
                idx += 1
            elif hline.startswith("+"):
                new_lines.append(hline[1:])
            else:
                raise RuntimeError("patch command failed: unknown diff line")
    new_lines.extend(original[idx:])
    return new_lines


def _apply_patch_fallback(patch: str, repo: pathlib.Path) -> None:
    files = _parse_diff(patch)
    if not files:
        raise RuntimeError("patch command failed: missing file headers")
    for rel_path, hunks in files:
        file_path = repo / rel_path
        if not file_path.exists():
            raise RuntimeError("patch command failed: target file missing")
        text = file_path.read_text(encoding="utf-8")
        ends_newline = text.endswith("\n")
        lines = text.splitlines()
        patched = _apply_hunks(lines, hunks)
        output = "\n".join(patched)
        if ends_newline:
            output += "\n"
        file_path.write_text(output, encoding="utf-8")


def apply_patch(patch: str, repo_path: str) -> None:
    """Apply patch atomically with rollback on failure."""
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
        use_patch_cmd = shutil.which("patch") is not None
        has_unversioned_hunks = any(
            line.startswith("@@") and not _HUNK_RE.match(line) for line in patch.splitlines()
        )
        if not use_patch_cmd or has_unversioned_hunks:
            _apply_patch_fallback(patch, repo)
        else:
            code, out = _run(["patch", "-p1", "-i", patch_file], cwd=repo_path)
            if code != 0:
                _apply_patch_fallback(patch, repo)
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
