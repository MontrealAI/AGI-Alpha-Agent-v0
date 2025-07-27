# SPDX-License-Identifier: Apache-2.0
"""File manipulation helpers for self-editing agents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# Optional OpenAI Agents SDK ---------------------------------------------------
try:  # pragma: no cover - optional dependency
    from agents import function_tool, RunContextWrapper  # type: ignore

    _HAVE_AGENTS = True
except ModuleNotFoundError:  # pragma: no cover - stub fallbacks

    def function_tool(*_dargs, **_dkwargs):
        def _wrap(func):
            return func

        return _wrap

    RunContextWrapper = dict  # type: ignore
    _HAVE_AGENTS = False

# Optional Google ADK ----------------------------------------------------------
try:  # pragma: no cover - optional dependency
    import google_adk as adk  # type: ignore
    if not hasattr(adk, "task"):
        raise ModuleNotFoundError
    _HAVE_ADK = True
except ModuleNotFoundError:  # pragma: no cover - stub fallbacks

    class _StubAgent:  # type: ignore
        def __init__(self, name: str) -> None:
            self.name = name

    class _StubDecor:  # type: ignore
        def __call__(self, func):
            return func

    class adk:  # type: ignore
        Agent = _StubAgent

        @staticmethod
        def task(**_kw):
            return _StubDecor()

        JsonSchema = dict

    _HAVE_ADK = False

REPO_ROOT = Path(__file__).resolve().parents[2]

_EDIT_HISTORY: list[tuple[Path, str]] = []

__all__ = [
    "view",
    "edit",
    "replace",
    "view_lines",
    "replace_str",
    "insert_after",
    "undo_last_edit",
    "view_tool",
    "edit_tool",
    "replace_tool",
    "view_lines_tool",
    "replace_str_tool",
    "insert_after_tool",
    "undo_tool",
    "FileToolsADK",
]


def _safe_path(path: str | Path) -> Path:
    """Return the resolved repository path.

    Args:
        path: File path relative to the repository.

    Returns:
        Absolute path inside the repository.
    """
    p = Path(path).expanduser().resolve()
    if REPO_ROOT not in p.parents and p != REPO_ROOT:
        raise PermissionError(f"path '{p}' outside repository root")
    return p


def _record_history(p: Path) -> None:
    """Record the current file contents for undo.

    Args:
        p: File path to snapshot.

    Returns:
        None.
    """
    _EDIT_HISTORY.append((p, p.read_text(encoding="utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def view(path: str | Path, start: int = 0, end: Optional[int] = None) -> str:
    """Return a slice of lines from ``path``.

    Args:
        path: File to read.
        start: Starting line index (0-based).
        end: Exclusive end line index.

    Returns:
        The selected lines joined by newlines.
    """
    p = _safe_path(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    sliced = lines[start:end] if end is not None else lines[start:]
    return "\n".join(sliced)


def edit(path: str | Path, start: int, end: Optional[int], new_code: str) -> None:
    """Replace a region of a file with new code.

    Args:
        path: File to modify.
        start: First line index to replace.
        end: Last line index to replace or ``None``.
        new_code: Replacement text.

    Returns:
        None.
    """
    p = _safe_path(path)
    _record_history(p)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines = new_code.splitlines()
    if end is None:
        end = start
    lines[start:end] = new_lines
    p.write_text("\n".join(lines), encoding="utf-8")


def replace(path: str | Path, pattern: str, repl: str) -> int:
    """Regex replace ``pattern`` with ``repl`` in ``path``.

    Args:
        path: File to update.
        pattern: Regular expression to search for.
        repl: Replacement string.

    Returns:
        Number of substitutions made.
    """
    p = _safe_path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    new_text, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if n:
        _record_history(p)
        p.write_text(new_text, encoding="utf-8")
    return n


def view_lines(path: str | Path, start: int, end: Optional[int]) -> str:
    """Return an inclusive line range from ``path``.

    Args:
        path: File to read.
        start: 1-based starting line number.
        end: Inclusive end line or ``None``.

    Returns:
        Requested lines joined by newlines.
    """
    s = max(0, start - 1)
    return view(path, s, end)


def replace_str(path: str | Path, old: str, new: str) -> int:
    """Replace occurrences of ``old`` with ``new`` in ``path``.

    Args:
        path: File to modify.
        old: Text to search for.
        new: Replacement text.

    Returns:
        Number of replacements made.
    """
    p = _safe_path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    count = text.count(old)
    if count:
        _record_history(p)
        p.write_text(text.replace(old, new), encoding="utf-8")
    return count


def insert_after(path: str | Path, anchor: str, code: str) -> None:
    """Insert ``code`` after the first line containing ``anchor``.

    Args:
        path: File to modify.
        anchor: Text marking the insertion point.
        code: Code to insert.

    Returns:
        None.
    """
    p = _safe_path(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for idx, line in enumerate(lines):
        if anchor in line:
            _record_history(p)
            insert_lines = code.splitlines()
            lines[idx + 1 : idx + 1] = insert_lines  # noqa: E203
            p.write_text("\n".join(lines), encoding="utf-8")
            return
    raise ValueError(f"anchor '{anchor}' not found in {p}")


def undo_last_edit() -> bool:
    """Revert the last edit operation if possible.

    Returns:
        ``True`` if a previous edit was undone.
    """
    if not _EDIT_HISTORY:
        return False
    p, text = _EDIT_HISTORY.pop()
    p.write_text(text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# OpenAI Agents wrappers
# ---------------------------------------------------------------------------


def _view_tool(ctx: RunContextWrapper | dict, path: str, start: int = 0, end: Optional[int] = None) -> str:
    return view(path, start, end)


def _edit_tool(ctx: RunContextWrapper | dict, path: str, start: int, end: Optional[int], new_code: str) -> str:
    edit(path, start, end, new_code)
    return "ok"


def _replace_tool(ctx: RunContextWrapper | dict, path: str, pattern: str, repl: str) -> int:
    return replace(path, pattern, repl)


def _view_lines_tool(ctx: RunContextWrapper | dict, path: str, start: int, end: Optional[int]) -> str:
    return view_lines(path, start, end)


def _replace_str_tool(ctx: RunContextWrapper | dict, path: str, old: str, new: str) -> int:
    return replace_str(path, old, new)


def _insert_after_tool(ctx: RunContextWrapper | dict, path: str, anchor: str, code: str) -> str:
    insert_after(path, anchor, code)
    return "ok"


def _undo_tool(ctx: RunContextWrapper | dict) -> bool:
    return undo_last_edit()


if _HAVE_AGENTS:  # pragma: no cover - thin wrapper
    view_tool = function_tool(
        name_override="view_file",
        description_override="Return selected lines from a repository file",
        strict_mode=False,
    )(_view_tool)

    edit_tool = function_tool(
        name_override="edit_file",
        description_override="Replace a line range inside a repository file",
        strict_mode=False,
    )(_edit_tool)

    replace_tool = function_tool(
        name_override="replace_text",
        description_override="Regex search/replace inside a repository file",
        strict_mode=False,
    )(_replace_tool)
    view_lines_tool = function_tool(
        name_override="view_lines",
        description_override="Return inclusive line range from a file",
        strict_mode=False,
    )(_view_lines_tool)
    replace_str_tool = function_tool(
        name_override="replace_string",
        description_override="Simple text replacement inside a repository file",
        strict_mode=False,
    )(_replace_str_tool)
    insert_after_tool = function_tool(
        name_override="insert_after",
        description_override="Insert text after an anchor line in a repository file",
        strict_mode=False,
    )(_insert_after_tool)
    undo_tool = function_tool(
        name_override="undo_last_edit",
        description_override="Undo the last file edit operation",
        strict_mode=False,
    )(_undo_tool)
else:  # pragma: no cover - simple alias
    view_tool = _view_tool
    edit_tool = _edit_tool
    replace_tool = _replace_tool
    view_lines_tool = _view_lines_tool
    replace_str_tool = _replace_str_tool
    insert_after_tool = _insert_after_tool
    undo_tool = _undo_tool


# ---------------------------------------------------------------------------
# Google ADK adapter
# ---------------------------------------------------------------------------
class FileToolsADK(adk.Agent):
    """Expose file utilities via Google ADK."""

    def __init__(self) -> None:
        super().__init__(name="file_tools")

    @adk.task(
        name="view",
        description="Return selected lines from a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer", "default": 0},
                    "end": {"type": ["integer", "null"], "default": None},
                },
                "required": ["path"],
            }
        ),
        output_schema=adk.JsonSchema(
            {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
        ),
    )
    def view_task(self, *, path: str, start: int = 0, end: Optional[int] = None) -> dict[str, str]:
        """Return file contents between ``start`` and ``end``."""
        return {"text": view(path, start, end)}

    @adk.task(
        name="edit",
        description="Replace a line range inside a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": ["integer", "null"]},
                    "new_code": {"type": "string"},
                },
                "required": ["path", "start", "new_code"],
            }
        ),
        output_schema=adk.JsonSchema({"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}),
    )
    def edit_task(self, *, path: str, start: int, end: Optional[int] = None, new_code: str) -> dict[str, bool]:
        """Replace a range of lines in ``path`` with ``new_code``."""
        edit(path, start, end, new_code)
        return {"ok": True}

    @adk.task(
        name="replace",
        description="Regex search/replace inside a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"},
                    "repl": {"type": "string"},
                },
                "required": ["path", "pattern", "repl"],
            }
        ),
        output_schema=adk.JsonSchema(
            {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}
        ),
    )
    def replace_task(self, *, path: str, pattern: str, repl: str) -> dict[str, int]:
        """Perform a regex replacement in ``path``."""
        return {"count": replace(path, pattern, repl)}

    @adk.task(
        name="view_lines",
        description="Return inclusive line range from a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": ["integer", "null"]},
                },
                "required": ["path", "start"],
            }
        ),
        output_schema=adk.JsonSchema(
            {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
        ),
    )
    def view_lines_task(self, *, path: str, start: int, end: Optional[int] = None) -> dict[str, str]:
        """Return inclusive line range from ``path``."""
        return {"text": view_lines(path, start, end)}

    @adk.task(
        name="replace_str",
        description="Simple text replacement inside a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            }
        ),
        output_schema=adk.JsonSchema(
            {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}
        ),
    )
    def replace_str_task(self, *, path: str, old: str, new: str) -> dict[str, int]:
        """Replace occurrences of ``old`` with ``new`` in ``path``."""
        return {"count": replace_str(path, old, new)}

    @adk.task(
        name="insert_after",
        description="Insert text after an anchor line in a repository file",
        input_schema=adk.JsonSchema(
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "anchor": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["path", "anchor", "code"],
            }
        ),
        output_schema=adk.JsonSchema({"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}),
    )
    def insert_after_task(self, *, path: str, anchor: str, code: str) -> dict[str, bool]:
        """Insert ``code`` after ``anchor`` in ``path``."""
        insert_after(path, anchor, code)
        return {"ok": True}

    @adk.task(
        name="undo_last_edit",
        description="Undo the last file edit operation",
        input_schema=adk.JsonSchema({"type": "object", "properties": {}}),
        output_schema=adk.JsonSchema({"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}),
    )
    def undo_task(self) -> dict[str, bool]:
        """Undo the last edit applied via this tool."""
        return {"ok": undo_last_edit()}
