# SPDX-License-Identifier: Apache-2.0
"""Structured logging and Merkle root broadcasting.

The :class:`Ledger` class appends envelopes to a local database (SQLite by
default) and can periodically broadcast the Merkle root to Solana.
``setup`` configures console logging, optionally emitting JSON lines.
"""

from __future__ import annotations

__all__ = ["Ledger", "setup", "logging"]

import asyncio
import contextlib
import json
import logging
import sqlite3
import os
from datetime import datetime
import dataclasses
from pathlib import Path
from typing import Iterable, List, cast

try:  # optional dependency for colorized output
    import coloredlogs
except Exception:  # pragma: no cover - optional
    coloredlogs = None

from . import messaging
from google.protobuf import json_format
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from alpha_factory_v1.core.utils.tracing import span
    from alpha_factory_v1.core.utils import a2a_pb2 as pb

try:  # optional dependency
    from blake3 import blake3
except Exception:  # pragma: no cover - fallback
    from hashlib import sha256 as blake3

try:  # optional dependency
    from solana.rpc.async_api import AsyncClient
    from solana.transaction import Transaction
    from solana.publickey import PublicKey
    from solana.transaction import TransactionInstruction
except Exception:  # pragma: no cover - offline fallback
    AsyncClient = None

try:  # optional dependency
    import duckdb
except Exception:  # pragma: no cover - optional
    duckdb = None

with contextlib.suppress(ModuleNotFoundError):
    import psycopg2

_log = logging.getLogger(__name__)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - short
        data = {
            "ts": datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "lvl": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        return json.dumps(data)


def setup(level: str = "INFO", json_logs: bool = False) -> None:
    """Initialise the root logger if not configured."""

    if not logging.getLogger().handlers:
        if json_logs:
            handler = logging.StreamHandler()
            handler.setFormatter(_JsonFormatter())
            logging.basicConfig(level=level, handlers=[handler])
        else:
            fmt = "%(asctime)s %(levelname)s %(name)s | %(message)s"
            if coloredlogs is not None:
                coloredlogs.install(level=level, fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
            else:
                logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")


def _merkle_root(hashes: Iterable[str]) -> str:
    nodes: List[bytes] = [bytes.fromhex(h) for h in hashes]
    if not nodes:
        return cast(str, blake3(b"\x00").hexdigest())

    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        next_lvl: List[bytes] = []
        for i in range(0, len(nodes), 2):
            next_lvl.append(blake3(nodes[i] + nodes[i + 1]).digest())
        nodes = next_lvl
    return nodes[0].hex()


class Ledger:
    """Append-only ledger with optional Merkle root broadcasting."""

    def __init__(
        self,
        path: str,
        rpc_url: str | None = None,
        wallet: str | None = None,
        broadcast: bool = True,
        db: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db_type = db or os.getenv("AGI_INSIGHT_DB", "sqlite")
        self.db_type = db_type
        if db_type == "duckdb" and duckdb is not None:
            self.conn = duckdb.connect(str(self.path))
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                    ts DOUBLE,
                    sender TEXT,
                    recipient TEXT,
                    payload TEXT,
                    hash TEXT
                )
                """
            )
        elif db_type == "postgres":
            if "psycopg2" not in globals():
                _log.warning("AGI_INSIGHT_DB=postgres but psycopg2 not installed – falling back to sqlite")
                self.conn = sqlite3.connect(str(self.path))
                self.conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts REAL,
                        sender TEXT,
                        recipient TEXT,
                        payload TEXT,
                        hash TEXT
                    )
                    """
                )
            else:
                params = {
                    "host": os.getenv("PGHOST"),
                    "port": os.getenv("PGPORT", "5432"),
                    "user": os.getenv("PGUSER"),
                    "password": os.getenv("PGPASSWORD"),
                    "dbname": os.getenv("PGDATABASE", "insight"),
                }
                self.conn = psycopg2.connect(**{k: v for k, v in params.items() if v is not None})
                with self.conn, self.conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS messages (
                            id BIGSERIAL PRIMARY KEY,
                            ts DOUBLE PRECISION,
                            sender TEXT,
                            recipient TEXT,
                            payload TEXT,
                            hash TEXT
                        )
                        """
                    )
        else:
            if db_type == "duckdb" and duckdb is None:
                _log.warning("AGI_INSIGHT_DB=duckdb but duckdb not installed – falling back to sqlite")
            self.conn = sqlite3.connect(str(self.path))
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL,
                    sender TEXT,
                    recipient TEXT,
                    payload TEXT,
                    hash TEXT
                )
                """
            )
        self.conn.commit()
        self._task: asyncio.Task[None] | None = None
        self.rpc_url = rpc_url
        self.wallet = wallet
        self.broadcast = broadcast

    def log(self, env: messaging.Envelope) -> None:
        """Hash ``env`` and append to the ledger."""
        from alpha_factory_v1.core.utils.tracing import span
        from alpha_factory_v1.core.utils import a2a_pb2 as pb

        with span("ledger.log"):
            assert self.conn is not None
            if dataclasses.is_dataclass(env) and not isinstance(env, type):
                record = dataclasses.asdict(env)
            elif isinstance(env, pb.Envelope):
                record = json_format.MessageToDict(env, preserving_proto_field_name=True)
            else:
                record = env.__dict__
            data = json.dumps(record, sort_keys=True).encode()
            digest = blake3(data).hexdigest()
            payload_json = json.dumps(record.get("payload", {}))
            if self.db_type == "postgres":
                with self.conn, self.conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO messages (ts, sender, recipient, payload, hash) VALUES (%s, %s, %s, %s, %s)",
                        (env.ts, env.sender, env.recipient, payload_json, digest),
                    )
            else:
                with self.conn:
                    self.conn.execute(
                        "INSERT INTO messages (ts, sender, recipient, payload, hash) VALUES (?, ?, ?, ?, ?)",
                        (env.ts, env.sender, env.recipient, payload_json, digest),
                    )

    def compute_merkle_root(self) -> str:
        assert self.conn is not None
        if self.db_type == "postgres":
            with self.conn.cursor() as cur:
                cur.execute("SELECT hash FROM messages ORDER BY id")
                raw_hashes = [row[0] for row in cur.fetchall()]
        else:
            cur = self.conn.execute("SELECT hash FROM messages ORDER BY id")
            raw_hashes = [row[0] for row in cur.fetchall()]

        hashes: List[str] = []
        for h in raw_hashes:
            if not isinstance(h, str) or not h:
                continue
            try:
                bytes.fromhex(h)
            except Exception:
                continue
            hashes.append(h)

        return _merkle_root(hashes)

    def tail(self, count: int = 10) -> List[dict[str, object]]:
        """Return the last ``count`` ledger entries."""

        assert self.conn is not None
        if self.db_type == "postgres":
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT ts, sender, recipient, payload FROM messages ORDER BY id DESC LIMIT %s",
                    (count,),
                )
                rows = cur.fetchall()
        else:
            cur = self.conn.execute(
                "SELECT ts, sender, recipient, payload FROM messages ORDER BY id DESC LIMIT ?",
                (count,),
            )
            rows = cur.fetchall()
        result: List[dict[str, object]] = []
        for ts, sender, recipient, payload in reversed(rows):
            try:
                data = json.loads(payload)
            except Exception:
                data = payload
            result.append({"ts": ts, "sender": sender, "recipient": recipient, "payload": data})
        return result

    async def broadcast_merkle_root(self) -> None:
        try:
            root = self.compute_merkle_root()
        except Exception as exc:  # pragma: no cover - corruption
            _log.warning("Failed to compute Merkle root: %s", exc)
            return
        if AsyncClient is None or not self.broadcast:
            _log.info("Merkle root %s", root)
            return
        try:
            client = AsyncClient(self.rpc_url or "https://api.testnet.solana.com")
            memo_prog = PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
            tx = Transaction().add(TransactionInstruction(program_id=memo_prog, data=root.encode(), keys=[]))
            signer = None
            if self.wallet:
                try:  # pragma: no cover - optional dependency
                    from solana.keypair import Keypair

                    signer = Keypair.from_secret_key(bytes.fromhex(self.wallet))
                except Exception as exc:  # noqa: BLE001 - invalid key
                    _log.warning("Invalid wallet key: %s", exc)
            if signer:
                await client.send_transaction(tx, signer)
            else:
                await client.send_transaction(tx)
            _log.info("Broadcasted Merkle root %s", root)
        except Exception as exc:  # pragma: no cover - network errors
            _log.warning("Failed to broadcast Merkle root: %s", exc)
        finally:
            try:
                await client.close()
            except Exception:  # pragma: no cover - ignore close errors
                pass

    async def _loop(self, interval: int) -> None:
        while True:
            await asyncio.sleep(interval)
            await self.broadcast_merkle_root()

    def start_merkle_task(self, interval: int = 3600) -> None:
        if self._task is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # pragma: no cover - no loop in sync context
                _log.warning("Merkle task requires a running event loop")
                return
            self._task = loop.create_task(self._loop(interval))

    async def stop_merkle_task(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - expected
                pass
            self._task = None

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "Ledger":
        """Return ``self`` for context manager support."""
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Ensure the database connection is closed."""
        self.close()

    async def __aenter__(self) -> "Ledger":
        """Start the Merkle broadcast task and return ``self``."""
        self.start_merkle_task()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Stop the Merkle task and close the database."""
        await self.stop_merkle_task()
        self.close()
