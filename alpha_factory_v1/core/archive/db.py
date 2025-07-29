# SPDX-License-Identifier: Apache-2.0
"""SQLAlchemy-backed archive database."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
import dataclasses
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import Boolean, Column, Float, String, create_engine
from sqlalchemy.orm import Session, DeclarativeBase


class Base(DeclarativeBase):
    pass


@dataclass(slots=True)
class ArchiveEntry:
    """Archive row representation."""

    hash: str
    parent: Optional[str]
    score: float
    novelty: float
    is_live: bool
    ts: float


class _ArchiveRow(Base):
    __tablename__ = "archive"

    hash = Column(String, primary_key=True)
    parent = Column(String, nullable=True)
    score = Column(Float, default=0.0)
    novelty = Column(Float, default=0.0)
    is_live = Column(Boolean, default=True)
    ts = Column(Float)


class _StateRow(Base):
    """Key/value storage for miscellaneous state."""

    __tablename__ = "state"

    key = Column(String, primary_key=True)
    value = Column(String)


class ArchiveDB:
    """Simple wrapper around ``sqlalchemy`` for archive access."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.engine = create_engine(f"sqlite:///{self.path}")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            exists = session.query(_ArchiveRow).first() is not None
        if not exists:
            self._migrate_legacy()

    def _migrate_legacy(self) -> None:
        json_path = self.path.with_name("archive.json")
        if not json_path.exists():
            return
        try:
            records = json.loads(json_path.read_text())
        except Exception:
            return
        with Session(self.engine) as session:
            for rec in records:
                row = _ArchiveRow(
                    hash=rec["hash"],
                    parent=rec.get("parent"),
                    score=rec.get("score", 0.0),
                    novelty=rec.get("novelty", 0.0),
                    is_live=rec.get("is_live", True),
                    ts=rec.get("ts", time.time()),
                )
                session.merge(row)
            session.commit()

    def add(self, entry: ArchiveEntry) -> None:
        """Insert or update ``entry`` in the database."""
        with Session(self.engine) as session:
            session.merge(_ArchiveRow(**dataclasses.asdict(entry)))
            session.commit()

    def get(self, h: str) -> ArchiveEntry | None:
        """Return the entry matching ``h`` or ``None`` if missing."""
        with Session(self.engine) as session:
            row = session.get(_ArchiveRow, h)
            if row is None:
                return None
            return ArchiveEntry(
                hash=row.hash,
                parent=row.parent,
                score=row.score,
                novelty=row.novelty,
                is_live=row.is_live,
                ts=row.ts,
            )

    def history(self, start_hash: str) -> Iterator[ArchiveEntry]:
        """Yield ancestral lineage starting from ``start_hash``."""
        current = self.get(start_hash)
        while current is not None:
            yield current
            if not current.parent:
                break
            current = self.get(current.parent)

    # state helpers -----------------------------------------------------

    def get_state(self, key: str, default: str | None = None) -> str | None:
        """Return the stored value for ``key`` from the ``state`` table."""
        with Session(self.engine) as session:
            row = session.get(_StateRow, key)
            return row.value if row is not None else default

    def set_state(self, key: str, value: str) -> None:
        """Store ``key`` as ``value`` in the ``state`` table."""
        with Session(self.engine) as session:
            session.merge(_StateRow(key=key, value=value))
            session.commit()

    # snark helpers -----------------------------------------------------

    def set_proof_cid(self, agent_hash: str, cid: str) -> None:
        """Store the IPFS CID of the SNARK proof for ``agent_hash``."""
        self.set_state(f"snark:{agent_hash}", cid)

    def get_proof_cid(self, agent_hash: str) -> str | None:
        """Return the stored proof CID for ``agent_hash`` if present."""
        return self.get_state(f"snark:{agent_hash}")
