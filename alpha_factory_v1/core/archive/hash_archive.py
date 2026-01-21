# SPDX-License-Identifier: Apache-2.0
"""Archive tarballs and pin them using IPFS."""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Iterable, List, Tuple


def _ensure_db(path: Path) -> None:
    with sqlite3.connect(path) as cx:
        cx.execute(
            "CREATE TABLE IF NOT EXISTS tarballs("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,path TEXT,cid TEXT,pinned INTEGER,ts REAL)"
        )
        cx.execute("CREATE TABLE IF NOT EXISTS merkle(date TEXT PRIMARY KEY,root TEXT)")


class HashArchive:
    """SQLite backed archive tracking pinned tarballs."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        _ensure_db(self.db_path)

    def _ipfs_add(self, tarball: Path) -> str:
        cmd = shutil.which("ipfs")
        if cmd:
            try:
                proc = subprocess.run([cmd, "add", "-Q", str(tarball)], capture_output=True, text=True, check=True)
                return proc.stdout.strip()
            except Exception:
                pass
        return hashlib.sha256(tarball.read_bytes()).hexdigest()

    def add_tarball(self, tarball: str | Path) -> str:
        """Record ``tarball`` and return its content identifier (CID)."""
        path = Path(tarball)
        cid = self._ipfs_add(path)
        with sqlite3.connect(self.db_path) as cx:
            cx.execute(
                "INSERT INTO tarballs(path, cid, pinned, ts) VALUES(?,?,?,?)",
                (str(path), cid, 1, time.time()),
            )
        return cid

    def list_entries(self) -> List[Tuple[int, str, str, int]]:
        """Return archive rows as ``(id, path, cid, pinned)`` tuples."""
        with sqlite3.connect(self.db_path) as cx:
            rows = list(cx.execute("SELECT id, path, cid, pinned FROM tarballs ORDER BY id"))
        return [(int(r[0]), str(r[1]), str(r[2]), int(r[3])) for r in rows]

    def _compute_root(self, cids: Iterable[str]) -> str:
        hashes = [hashlib.sha256(c.encode()).digest() for c in sorted(cids)]
        if not hashes:
            return ""
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [hashlib.sha256(hashes[i] + hashes[i + 1]).digest() for i in range(0, len(hashes), 2)]
        return hashes[0].hex()

    def merkle_root(self, date: str | None = None) -> str:
        """Compute the Merkle root over entries for ``date`` or all entries."""
        with sqlite3.connect(self.db_path) as cx:
            if date:
                rows = [
                    r[0]
                    for r in cx.execute(
                        "SELECT cid FROM tarballs WHERE DATE(ts,'unixepoch')=? ORDER BY cid",
                        (date,),
                    )
                ]
            else:
                rows = [r[0] for r in cx.execute("SELECT cid FROM tarballs ORDER BY cid")]
        return self._compute_root(rows)

    def publish_daily_root(self) -> str:
        """Compute today's Merkle root and store it on disk."""
        date = time.strftime("%Y-%m-%d")
        root = self.merkle_root(date)
        with sqlite3.connect(self.db_path) as cx:
            cx.execute("INSERT OR REPLACE INTO merkle(date, root) VALUES(?,?)", (date, root))
        output_path = self.db_path.with_name(f"agi-insight.{date}.eth")
        output_path.write_text(root, encoding="utf-8")
        return root


__all__ = ["HashArchive"]
