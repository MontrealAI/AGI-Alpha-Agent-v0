# SPDX-License-Identifier: Apache-2.0
"""Explicit high-water custody outside portable runtime backups; fail closed on rollback."""

from __future__ import annotations
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from typing import Any
from ..store import Conflict, Journal, private_write
from .trust import JournalCheckpoint


class DurableCheckpoint:
    """Use a separately provisioned durable mount; a local file is not remote custody."""

    def __init__(self, path: Path, journal: Journal) -> None:
        if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("checkpoint requires an existing regular provisioned file")
        self.path = path.resolve()
        if self.path.is_relative_to(journal.root):
            raise ValueError("checkpoint must remain outside portable runtime recovery state")
        if self.path.stat().st_mode & 0o077:
            raise ValueError("checkpoint file must be private to the service account")
        self.identity = journal.identity
        with journal.transaction() as cx:
            self.verify(journal, cx)

    @classmethod
    def initialize(cls, path: Path, journal: Journal) -> DurableCheckpoint:
        """Explicit provisioning operation; no constructor silently resets lost custody."""
        if path.resolve().is_relative_to(journal.root):
            raise ValueError("checkpoint belongs on a separate durable custody mount")
        checkpoint = JournalCheckpoint.capture(journal)
        private_write(path, b"")
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                "CREATE TABLE highwater(identity TEXT PRIMARY KEY, sequence INTEGER NOT NULL, head TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO highwater VALUES(?,?,?)", (checkpoint.identity, checkpoint.sequence, checkpoint.head)
            )
        return cls(path, journal)

    def verify(self, journal: Journal, cx: Any) -> tuple[int, str]:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT sequence,head FROM highwater WHERE identity=?", (journal.identity,)
            ).fetchone()
        if row is None or journal.identity != self.identity:
            raise ValueError("checkpoint identity is missing or changed")
        local = cx.execute("SELECT hash FROM events WHERE seq=?", (row[0],)).fetchone()
        if local is None or local[0] != row[1]:
            raise Conflict("journal is older than or diverges from separately retained high-water custody")
        return int(row[0]), str(row[1])

    def advance(self, journal: Journal, cx: Any) -> None:
        """Advance before local commit; a split-commit crash refuses rather than rolling back."""
        previous = self.verify(journal, cx)
        row = cx.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        if row is None:
            raise ValueError("cannot checkpoint an empty journal")
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE highwater SET sequence=?,head=? WHERE identity=? AND sequence=? AND head=?",
                (*row, journal.identity, *previous),
            )
            if changed.rowcount != 1:
                raise Conflict("checkpoint custody changed concurrently")
