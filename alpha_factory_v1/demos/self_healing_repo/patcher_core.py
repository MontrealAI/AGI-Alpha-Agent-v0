# alpha_factory_v1/demos/self_healing_repo/patcher_core.py
# © 2025 MONTREAL.AI   MIT License
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

validate_repo(repo_path: str, cmd: list[str] = ["pytest", "-q"]) -> tuple[int,str]
    • Runs the given command, returning (returncode, combined stdout+stderr).

The trio forms a minimal, production‑ready healing loop while remaining
agnostic to any higher‑level agent orchestration.

All file‑system mutations stay **inside `repo_path`** for container safety.
"""

from __future__ import annotations
import subprocess, tempfile, pathlib, shutil, os, textwrap
from typing import List, Tuple
from openai_agents import OpenAIAgent

# ─────────────────────────── helpers ─────────────────────────────────────────
def _run(cmd: List[str], cwd: str) -> Tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr

def validate_repo(repo_path: str, cmd: List[str] = ["pytest", "-q"]) -> Tuple[int, str]:
    """Return (exit_code, full_output)."""
    return _run(cmd, cwd=repo_path)

def _existing_files(repo: pathlib.Path) -> set[str]:
    return {str(p.relative_to(repo)) for p in repo.rglob("*") if p.is_file()}

# ────────────────────────── patch logic ─────────────────────────────────────
def generate_patch(test_log: str, llm: OpenAIAgent, repo_path: str) -> str:
    """Ask the LLM to suggest a unified diff patch fixing the failure."""
    prompt = textwrap.dedent(f"""
    You are an expert software engineer. A test suite failed as follows:

    ```text
    {test_log}
    ```

    Produce a **unified diff** that fixes the bug. Constraints:
    1. Modify only existing files inside the repository.
    2. Do not add or delete entire files.
    3. Keep the patch minimal and idiomatic.
    """)
    patch = llm(prompt).strip()
    _sanity_check_patch(patch, pathlib.Path(repo_path))
    return patch

def _sanity_check_patch(patch: str, repo_root: pathlib.Path):
    """Ensure the diff only touches existing files to avoid LLM wildness."""
    touched = set()
    for line in patch.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = line[4:].split("\t")[0].lstrip("ab/")  # strip diff prefixes
            touched.add(path)
    non_existing = touched - _existing_files(repo_root)
    if non_existing:
        raise ValueError(f"Patch refers to unknown files: {', '.join(non_existing)}")

def apply_patch(patch: str, repo_path: str):
    """Apply patch atomically with rollback on failure."""
    repo = pathlib.Path(repo_path)
    backups = {}

    # write patch to temp file
    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(patch)
        patch_file = tf.name

    try:
        # back up touched files
        for line in patch.splitlines():
            if line.startswith(("--- ", "+++ ")):
                rel = line[4:].split("\t")[0].lstrip("ab/")
                file_path = repo / rel
                if file_path.exists():
                    backup = file_path.with_suffix(".bak")
                    shutil.copy2(file_path, backup)
                    backups[file_path] = backup
        # apply
        code, out = _run(["patch", "-p1", "-i", patch_file], cwd=repo_path)
        if code != 0:
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
