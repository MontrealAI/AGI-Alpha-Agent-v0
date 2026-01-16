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

from .agent_core import diff_utils

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
async def _llm_to_text(llm: OpenAIAgent, prompt: str) -> str:
    result = llm(prompt)
    if asyncio.iscoroutine(result):
        return str(await result)
    return str(result)


async def generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str:
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
    patch = (await _llm_to_text(llm, prompt)).strip()
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
        ok, out = diff_utils.apply_diff(patch, repo_path)
        if not ok:
            raise RuntimeError(f"patch command failed:\n{out}")
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
        patch = asyncio.run(generate_patch(out, llm=llm, repo_path=args.repo))
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
