# SPDX-License-Identifier: Apache-2.0
"""Patch admission controller for the archive."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from alpha_factory_v1.core.eval.preflight import run_preflight
from alpha_factory_v1.core.self_edit.tools import REPO_ROOT, edit, undo_last_edit
from alpha_factory_v1.core.monitoring import metrics

from .db import ArchiveDB, ArchiveEntry


def patch_identity(diff: str, parent: str) -> str:
    """Bind new patch identities to exact content and lineage without rewriting legacy IDs."""
    body = json.dumps(["alpha-archive-patch/v2", parent, diff], ensure_ascii=False, separators=(",", ":"))
    return "archive-patch-v2:sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _tool_roundtrip() -> bool:
    """Return ``True`` if edit/undo leaves no changes."""
    path = REPO_ROOT / "_roundtrip.txt"
    path.write_text("a\nb\n", encoding="utf-8")
    baseline = path.read_text(encoding="utf-8")
    edit(path, 1, 2, "x")
    undo_last_edit()
    ok = path.read_text(encoding="utf-8") == baseline
    path.unlink(missing_ok=True)  # type: ignore[call-arg]
    return ok


class PatchManager:
    """Control patch acceptance and persist history."""

    def __init__(self, db_path: str | Path) -> None:
        self.db = ArchiveDB(db_path)

    def admit(self, diff: str, parent: str, repo_dir: str | Path | None = None) -> bool:
        """Validate and store ``diff`` with its parent hash."""

        repo = Path(repo_dir) if repo_dir else REPO_ROOT
        try:
            run_preflight(repo)
        except Exception:
            return False
        if not _tool_roundtrip():
            return False

        h = patch_identity(diff, parent)
        entry = json.dumps({"diff": diff, "parent": parent})
        try:
            inserted = self.db.add_patch_once(
                ArchiveEntry(hash=h, parent=parent, score=0.0, novelty=0.0, is_live=True, ts=time.time()), entry
            )
        except ValueError:
            return False
        if inserted:
            metrics.dgm_children_admitted_total.inc()
        return True
