# SPDX-License-Identifier: Apache-2.0
"""Transactional mission journal with an Ed25519 identity and verified recovery."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any, Iterator
import uuid
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from .models import Mission, RuntimeConfig


def canonical(value: Any) -> bytes:
    """Encode finite JSON consistently for hashes and signatures."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    """Return a canonical JSON SHA-256 digest."""
    return hashlib.sha256(canonical(value)).hexdigest()


def private_write(path: Path, data: bytes) -> None:
    """Create a private file exclusively, without following an existing link."""
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class Conflict(ValueError):
    """The reviewed state changed, or a transition is not allowed."""


def public_error(exc: Exception) -> str:
    """Keep useful operator errors while withholding provider response contents."""
    from pydantic import ValidationError
    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
            for item in exc.errors(include_input=False, include_context=False, include_url=False)
        )
    if type(exc) in {ValueError, Conflict, FileNotFoundError, FileExistsError, TimeoutError, SandboxUnavailable}:
        return str(exc)
    return f"{type(exc).__name__}: provider or dependency failed; inspect configuration and retained mission state"


class Journal:
    """Use a signed append-only journal as the authoritative mission state.

    Signatures expose corruption and bind evidence to a local key. They do not
    prove ENS ownership or protect against an attacker who steals that key.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.path = self.root / "journal.sqlite3"
        self.config = RuntimeConfig.model_validate_json((self.root / "config.json").read_bytes())
        key = (self.root / "identity.key").read_bytes()
        self.key = Ed25519PrivateKey.from_private_bytes(key)
        self.public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        self.identity = f"urn:agialpha:ed25519:{self.public}"
        if not self.path.is_file():
            raise ValueError("journal is missing; restore a verified backup")

    @classmethod
    def initialize(cls, root: str | Path, config: RuntimeConfig | None = None, *, allow_empty: bool = False) -> Journal:
        """Initialize a new directory or explicitly allowed empty mount; never overwrite identity."""
        path = Path(root).resolve()
        try:
            path.mkdir(mode=0o700, parents=True, exist_ok=False)
        except FileExistsError:
            if not allow_empty or not path.is_dir() or any(path.iterdir()):
                raise
            path.chmod(0o700)
        cfg = config or RuntimeConfig()
        private_write(path / "config.json", canonical(cfg.model_dump()))
        key = Ed25519PrivateKey.generate()
        private_write(path / "identity.key", key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        private_write(path / "api.token", secrets.token_urlsafe(32).encode())
        private_write(path / "journal.sqlite3", b"")
        with sqlite3.connect(path / "journal.sqlite3") as cx:
            cx.execute("PRAGMA journal_mode=WAL")
            cx.execute(
                "CREATE TABLE events(seq INTEGER PRIMARY KEY, mission TEXT NOT NULL, "
                "body TEXT NOT NULL, hash TEXT NOT NULL UNIQUE, signature TEXT NOT NULL)"
            )
            cx.execute("CREATE INDEX events_mission ON events(mission,seq)")
        journal = cls(path)
        with journal.transaction() as cx:
            journal.append(cx, "@control", {"state": "ready", "config_hash": digest(cfg.model_dump())})
        return journal

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Serialize state changes and roll back on every exception."""
        with sqlite3.connect(self.path, timeout=30) as cx:
            cx.execute("PRAGMA synchronous=FULL")
            cx.execute("BEGIN IMMEDIATE")
            yield cx

    def append(self, cx: sqlite3.Connection, mission: str, document: dict[str, Any]) -> dict[str, Any]:
        """Append a complete state document under the caller's transaction."""
        row = cx.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        sequence, previous = (row[0] + 1, row[1]) if row else (1, "0" * 64)
        body = {
            "schema": 1,
            "sequence": sequence,
            "previous": previous,
            "identity": self.identity,
            "mission": mission,
            "time_ns": time.time_ns(),
            "document": document,
        }
        hashed = digest(body)
        signature = base64.b64encode(self.key.sign(bytes.fromhex(hashed))).decode()
        cx.execute(
            "INSERT INTO events VALUES(?,?,?,?,?)", (sequence, mission, canonical(body).decode(), hashed, signature)
        )
        return {**document, "id": mission, "revision": sequence, "digest": hashed}

    def latest(self, mission: str, cx: sqlite3.Connection | None = None) -> dict[str, Any]:
        """Read a signed state; verify the full chain with ``verify`` at startup."""
        if cx is None:
            with sqlite3.connect(self.path) as connection:
                return self.latest(mission, connection)
        row = cx.execute(
            "SELECT seq,body,hash,signature FROM events WHERE mission=? ORDER BY seq DESC LIMIT 1", (mission,)
        ).fetchone()
        if row is None:
            raise KeyError(mission)
        body = json.loads(row[1])
        if digest(body) != row[2] or body["mission"] != mission or body["sequence"] != row[0]:
            raise ValueError("journal content is corrupt")
        self.key.public_key().verify(base64.b64decode(row[3], validate=True), bytes.fromhex(row[2]))
        return {**body["document"], "id": mission, "revision": row[0], "digest": row[2]}

    @staticmethod
    def document(record: dict[str, Any]) -> dict[str, Any]:
        """Strip read-side metadata before appending the next revision."""
        return {k: v for k, v in record.items() if k not in {"id", "revision", "digest"}}

    def submit(self, mission: Mission, request_id: str | None = None) -> dict[str, Any]:
        """Idempotently enqueue a request without executing it."""
        ident = str(uuid.UUID(request_id)) if request_id is not None else str(uuid.uuid4())
        payload = mission.model_dump()
        with self.transaction() as cx:
            try:
                existing = self.latest(ident, cx)
            except KeyError:
                return self.append(cx, ident, {"state": "queued", "request": payload, "request_hash": digest(payload)})
            if existing["request_hash"] != digest(payload):
                raise Conflict("request ID already belongs to different input")
            return existing

    def transition(
        self,
        ident: str,
        revision: int,
        allowed: set[str],
        state: str,
        *,
        fields: dict[str, Any] | None = None,
        require_ready: bool = True,
        expected_config_hash: str | None = None,
    ) -> dict[str, Any]:
        """Apply a compare-and-swap state transition and an optional result."""
        with self.transaction() as cx:
            if require_ready:
                control = self.latest("@control", cx)
                if control["state"] != "ready":
                    raise Conflict("agent is paused")
                config_hash = expected_config_hash or digest(self.config.model_dump())
                if control["config_hash"] != config_hash:
                    raise Conflict("configuration changed; restart and retry")
            old = self.latest(ident, cx)
            if old["revision"] != revision or old["state"] not in allowed:
                raise Conflict("mission state changed; review its current revision")
            return self.append(cx, ident, {**self.document(old), **(fields or {}), "state": state})

    def control(self, paused: bool) -> dict[str, Any]:
        """Persist the operator stop switch across process restarts."""
        with self.transaction() as cx:
            old = self.latest("@control", cx)
            return self.append(cx, "@control", {**self.document(old), "state": "paused" if paused else "ready"})

    def missions(self) -> list[dict[str, Any]]:
        """Return the latest state of each submitted mission."""
        with sqlite3.connect(self.path) as cx:
            ids = [
                row[0]
                for row in cx.execute(
                    "SELECT DISTINCT mission FROM events WHERE mission NOT LIKE '@%' ORDER BY mission"
                )
            ]
            return [self.latest(ident, cx) for ident in ids]

    def verify(self) -> dict[str, Any]:
        """Verify integrity, every signature, chain order and active configuration."""
        previous, count = "0" * 64, 0
        with sqlite3.connect(self.path) as cx:
            if cx.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("SQLite integrity check failed")
            for seq, mission, raw, hashed, signature in cx.execute("SELECT * FROM events ORDER BY seq"):
                body = json.loads(raw)
                count += 1
                if seq != count or body["sequence"] != seq or body["previous"] != previous:
                    raise ValueError("journal sequence or hash chain is broken")
                if body["identity"] != self.identity or body["mission"] != mission or digest(body) != hashed:
                    raise ValueError("journal identity or content mismatch")
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public)).verify(
                    base64.b64decode(signature, validate=True), bytes.fromhex(hashed)
                )
                previous = hashed
            raw_config = (self.root / "config.json").read_bytes()
            if self.latest("@control", cx)["config_hash"] != digest(json.loads(raw_config)):
                raise ValueError("configuration changed outside the journal")
            if RuntimeConfig.model_validate_json(raw_config).model_dump() != self.config.model_dump():
                raise ValueError("configuration changed; restart the running process")
        return {"valid": True, "events": count, "head": previous, "identity": self.identity}

    def configure(self, config: RuntimeConfig) -> None:
        """Change provider policy only while paused, recording its full hash.

        Write-before-commit may leave a detectable mismatch after a crash. A
        verified backup provides recovery; no mismatched config is executed.
        """
        self.verify()
        with self.transaction() as cx:
            old = self.latest("@control", cx)
            if old["state"] != "paused":
                raise Conflict("pause the agent before changing configuration")
            temporary = self.root / f"config-{uuid.uuid4()}.tmp"
            private_write(temporary, canonical(config.model_dump()))
            os.replace(temporary, self.root / "config.json")
            self.append(cx, "@control", {**self.document(old), "config_hash": digest(config.model_dump())})
        self.config = config

    def backup(self, destination: str | Path) -> dict[str, Any]:
        """Create an owner-readable recovery archive including the private key."""
        self.verify()
        target = Path(destination).resolve()
        temporary = self.root / f"backup-{uuid.uuid4()}.sqlite3"
        try:
            # Hold the writer lock while another connection snapshots committed
            # rows. configure() uses the same lock, so files and rows agree.
            with self.transaction():
                self.verify()
                with sqlite3.connect(self.path) as source, sqlite3.connect(temporary) as dest:
                    source.backup(dest)
                files = {name: (self.root / name).read_bytes() for name in ("config.json", "identity.key", "api.token")}
                files["journal.sqlite3"] = temporary.read_bytes()
            manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
            private_write(target, b"")
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in files.items():
                    archive.writestr(name, data)
                archive.writestr("manifest.json", canonical(manifest))
            return {
                "path": str(target),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "contains_private_key": True,
            }
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def restore(cls, backup: str | Path, destination: str | Path) -> Journal:
        """Restore into a new directory only, then verify signatures and identity."""
        target = Path(destination).resolve()
        expected = {"config.json", "identity.key", "api.token", "journal.sqlite3", "manifest.json"}
        with zipfile.ZipFile(backup) as archive:
            if set(archive.namelist()) != expected or len(archive.infolist()) != len(expected):
                raise ValueError("unexpected or duplicate recovery archive members")
            if sum(info.file_size for info in archive.infolist()) > 256 * 1024**2:
                raise ValueError("recovery archive exceeds 256 MiB limit")
            files = {name: archive.read(name) for name in expected}
        manifest = json.loads(files.pop("manifest.json"))
        if manifest != {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}:
            raise ValueError("recovery archive checksum mismatch")
        target.mkdir(parents=True, exist_ok=False, mode=0o700)
        for name, data in files.items():
            private_write(target / name, data)
        journal = cls(target)
        journal.verify()
        return journal
