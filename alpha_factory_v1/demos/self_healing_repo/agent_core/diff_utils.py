# SPDX-License-Identifier: Apache-2.0
# diff_utils.py
import logging
import re
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Paths relative to the cloned repository that patches may touch.  ``None``
# means the entire repository is allowed.
ALLOWED_PATHS: list[str] | None = None

# Reject diffs that exceed these limits to avoid unbounded file modifications.
MAX_DIFF_LINES = 1000
MAX_DIFF_BYTES = 100_000


def _find_subsequence(lines: list[str], needle: list[str]) -> int | None:
    for idx in range(len(lines) - len(needle) + 1):
        if lines[idx : idx + len(needle)] == needle:
            return idx
    return None


def _apply_minimal_diff(diff_text: str, repo_dir: str) -> tuple[bool, str]:
    file_path: str | None = None
    hunks: list[list[str]] = []
    current: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            m = re.match(r"^[+]{3} [ab]/(.+)$", line)
            if m:
                file_path = m.group(1)
        elif line.startswith("--- "):
            continue
        elif line.startswith("@@"):
            if current:
                hunks.append(current)
                current = []
        elif line.startswith(("+", "-", " ")):
            current.append(line)

    if current:
        hunks.append(current)

    if not file_path or not hunks:
        return False, "unsupported diff format"

    target = Path(repo_dir) / file_path
    if not target.exists():
        return False, f"file not found: {file_path}"

    original = target.read_text()
    lines = original.splitlines()
    for hunk in hunks:
        removed = [line[1:] for line in hunk if line.startswith("-")]
        added = [line[1:] for line in hunk if line.startswith("+")]
        if removed:
            if removed == [""] and not lines:
                lines = added
                continue
            idx = _find_subsequence(lines, removed)
            if idx is None:
                return False, f"patch failed for {file_path}"
            lines = lines[:idx] + added + lines[idx + len(removed) :]
        else:
            lines.extend(added)

    new_text = "\n".join(lines)
    if original.endswith("\n") or new_text:
        new_text += "\n"
    target.write_text(new_text)
    return True, f"patching file {file_path}"


def parse_and_validate_diff(
    diff_text: str,
    repo_dir: str,
    allowed_paths: list[str] | None = None,
) -> str | None:
    """Verify the LLM's output is a valid unified diff and meets safety criteria.

    Diffs that exceed ``MAX_DIFF_LINES`` or ``MAX_DIFF_BYTES`` are rejected to
    avoid accidentally applying huge patches.
    """
    if not diff_text:
        return None

    lines = diff_text.splitlines()
    if len(lines) > MAX_DIFF_LINES or len(diff_text.encode("utf-8")) > MAX_DIFF_BYTES:
        logger.warning(
            "Diff too large: %s lines, %s bytes",
            len(lines),
            len(diff_text.encode("utf-8")),
        )
        return None

    # Basic unified diff check: should contain lines starting with '+++ ' and '--- '
    if "+++" not in diff_text or "---" not in diff_text:
        return None  # Not a diff format
    repo_root = Path(repo_dir).resolve()
    allowed = allowed_paths if allowed_paths is not None else ALLOWED_PATHS
    allowed_dirs = [repo_root.joinpath(p).resolve() for p in allowed] if allowed else [repo_root]

    for line in diff_text.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            m = re.match(r"^[+-]{3} [ab]/(.+)$", line)
            if m:
                file_path = m.group(1)
                target = (repo_root / file_path).resolve()
                if not target.is_relative_to(repo_root):
                    logger.warning("Diff outside repository: %s", file_path)
                    return None
                if not any(target.is_relative_to(d) for d in allowed_dirs):
                    logger.warning("Diff touches disallowed path: %s", file_path)
                    return None
    # (Additional checks: e.g., diff length, certain forbidden content can be added here.)
    return diff_text


def apply_diff(diff_text: str, repo_dir: str) -> tuple[bool, str]:
    """Apply the unified diff to repo_dir. Returns (success, output)."""
    if shutil.which("patch") is None:
        return False, "patch command not found"
    try:
        process = subprocess.run(
            ["patch", "-p1"],
            input=diff_text,
            text=True,
            cwd=repo_dir,
            timeout=60,
            capture_output=True,
        )
        output = (process.stdout or "") + (process.stderr or "")
        if process.returncode != 0:
            logger.error(
                "Patch command failed with code %s: %s",
                process.returncode,
                output,
            )
            if "Only garbage was found in the patch input" in output:
                success, minimal_output = _apply_minimal_diff(diff_text, repo_dir)
                if success:
                    return True, minimal_output
                return False, output or minimal_output
            return False, output
        return True, output
    except Exception as e:
        logger.exception("Exception while applying patch: %s", e)
        return False, str(e)
