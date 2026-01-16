# SPDX-License-Identifier: Apache-2.0
"""Scheduler for publishing archive Merkle roots."""
from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from rocketry import Rocketry
    from rocketry.conds import daily
except Exception:  # pragma: no cover - optional dependency
    Rocketry = None  # type: ignore
    daily = None  # type: ignore

from .hash_archive import HashArchive


def publish_root(*, db_path: str | Path | None = None, out_file: str | Path = "archive_root.json") -> str:
    """Publish today's Merkle root and store it in ``out_file``."""
    path = Path(db_path or os.getenv("ARCHIVE_PATH", "archive.db"))
    arch = HashArchive(path)
    cid = arch.publish_daily_root()
    Path(out_file).write_text(json.dumps({"cid": cid}), encoding="utf-8")
    return cid


def create_scheduler(
    *, db_path: str | Path | None = None, out_file: str | Path = "archive_root.json"
) -> Rocketry | None:
    """Return a ``Rocketry`` app publishing the archive root daily."""
    if Rocketry is None or daily is None:
        return None

    try:
        app = Rocketry(execution="async")
    except TypeError:
        app = Rocketry()

    @app.task(daily)
    def _job() -> None:  # pragma: no cover - Rocketry callback
        publish_root(db_path=db_path, out_file=out_file)

    return app


__all__ = ["publish_root", "create_scheduler"]
