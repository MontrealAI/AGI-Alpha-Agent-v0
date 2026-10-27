# SPDX-License-Identifier: Apache-2.0
"""One-use local query grants using unchanged native trust and journal code.

This is a public research fixture, not live ENS or organizational authorization.
Keep each Journal directory private and temporary; publish only public_receipt().
The controller has only the existing controller role. No validator role is added.
"""

from __future__ import annotations

import hashlib
import importlib
import itertools
import json
import sqlite3
import sys
import time
import uuid
from contextlib import closing
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HERE = Path(__file__).resolve().parent
NATIVE_ROOT = HERE / "native_vendor"
NATIVE_MANIFEST_SHA256 = "84642a9c3a0c5f7602b9cd77f4615ec5a47cff4eeb304db49de1e163a2a73973"
DOMAIN = "reserve-query-grant-v1"
PRINCIPAL = "reserve-query-controller"
MODE = "LOCAL_EPHEMERAL_RESEARCH_FIXTURE_NOT_LIVE_ENS"


def canonical(value: Any) -> bytes:
    """Encode finite public JSON without changing monetary strings or numbers."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    """Hash public canonical JSON."""
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> tuple[dict[str, Any], str]:
    """Read an ordinary public JSON file without duplicate keys."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected an ordinary public input file")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate public input key")
            result[key] = value
        return result

    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=unique)
    canonical(value)
    if not isinstance(value, dict):
        raise ValueError("Expected a public JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def native_modules() -> tuple[ModuleType, ModuleType]:
    """Verify the unchanged ten-file closure before loading its Journal and trust."""
    raw = (HERE / "native_source_manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != NATIVE_MANIFEST_SHA256:
        raise ValueError("Native source manifest changed")
    for record in json.loads(raw)["files"]:
        path = HERE / record["local_path"]
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Pinned native source changed: " + record["local_path"])
    if str(NATIVE_ROOT) not in sys.path:
        sys.path.insert(0, str(NATIVE_ROOT))
    for name, module in tuple(sys.modules.items()):
        module_path = getattr(module, "__file__", None)
        if name.startswith("alpha_factory_v1") and isinstance(module_path, str):
            if not Path(module_path).resolve().is_relative_to(NATIVE_ROOT):
                raise ValueError("Run query authority in a process without another Alpha runtime import")
    trust = importlib.import_module("alpha_factory_v1.core.runtime.successor.trust")
    store = importlib.import_module("alpha_factory_v1.core.runtime.store")
    return trust, store


def bind_query(manifest_path: Path, worker_path: Path) -> dict[str, Any]:
    """Recheck the public function, complete scenario family, inputs and executable."""
    manifest, manifest_hash = read_json(Path(manifest_path))
    fields = {
        "schema",
        "parties",
        "assets_per_party",
        "demands",
        "max_claims",
        "scope_id",
        "scenario_epoch",
        "world_count",
        "scenarios",
        "input_commitments",
    }
    if set(manifest) != fields or manifest["schema"] != "reserve-mpc-v1":
        raise ValueError("Unsupported reserve query manifest")
    for key, expected in (("parties", 3), ("assets_per_party", 2), ("demands", 6)):
        if type(manifest[key]) is not int or manifest[key] != expected:
            raise ValueError("Public padded dimensions changed")
    claims = manifest["max_claims"]
    if type(claims) is not int or claims not in (2, 3):
        raise ValueError("Only the original or separately authorized successor scenario family is supported")
    for key in ("scope_id", "scenario_epoch"):
        if not isinstance(manifest[key], str) or not 1 <= len(manifest[key]) <= 128:
            raise ValueError("Missing fixed query scope or input epoch")
    if type(manifest["world_count"]) is not int or not 1 <= manifest["world_count"] <= 1000:
        raise ValueError("Invalid fixed output count")
    expected_groups = {group for size in range(1, claims + 1) for group in itertools.combinations(range(6), size)}
    groups: list[tuple[int, ...]] = []
    identifiers: list[str] = []
    if not isinstance(manifest["scenarios"], list):
        raise ValueError("Missing public scenario list")
    for scenario in manifest["scenarios"]:
        if not isinstance(scenario, dict) or set(scenario) != {"id", "demand_clients"}:
            raise ValueError("Unsupported scenario fields")
        clients = scenario["demand_clients"]
        if not isinstance(clients, list) or any(type(item) is not int for item in clients):
            raise ValueError("Demand identifiers must be exact integers")
        if clients != sorted(set(clients)) or not isinstance(scenario["id"], str):
            raise ValueError("Invalid scenario identity")
        groups.append(tuple(clients))
        identifiers.append(scenario["id"])
    if set(groups) != expected_groups or len(groups) != len(expected_groups) or len(set(identifiers)) != len(groups):
        raise ValueError("A declared scenario was changed, duplicated or omitted")
    commitments = manifest["input_commitments"]
    if not isinstance(commitments, list) or len(commitments) != 3:
        raise ValueError("Exactly three private owner-file commitments are required")
    if any(
        not isinstance(item, str) or len(item) != 64 or any(c not in "0123456789abcdef" for c in item)
        for item in commitments
    ):
        raise ValueError("Invalid owner-file commitment")
    worker_path = Path(worker_path)
    if worker_path.is_symlink() or not worker_path.is_file():
        raise ValueError("Expected an ordinary pinned MPC worker file")
    return {
        "schema": "agialpha.reserve-query.binding.v1",
        "mode": MODE,
        "right": "run-one-fixed-local-reserve-feasibility-query",
        "function": "For every declared scenario there exists an eligible injective allocation respecting availability and withholding.",
        "manifest_sha256": manifest_hash,
        "worker_sha256": hashlib.sha256(worker_path.read_bytes()).hexdigest(),
        "scope_id": manifest["scope_id"],
        "scenario_epoch": manifest["scenario_epoch"],
        "parties": 3,
        "assets_per_party": 2,
        "demands": 6,
        "max_claims": claims,
        "scenario_count": len(groups),
        "scenario_family_sha256": digest(manifest["scenarios"]),
        "input_commitments": commitments,
        "world_count": manifest["world_count"],
        "output": {
            "bits_per_independent_world": 1,
            "recipients": ["party_0", "party_1", "party_2"],
            "per_scenario_results": False,
        },
    }


def verify_grant(signed: dict[str, Any], context: dict[str, Any], binding: dict[str, Any], now: int) -> dict[str, Any]:
    """Verify current fixture authority independently of the incoming signed payload."""
    trust, _ = native_modules()
    if context.get("mode") != MODE or context.get("principal") != PRINCIPAL:
        raise ValueError("Unsupported local query-authority context")
    registry = trust.TrustRegistry({PRINCIPAL: trust.TrustAnchor(context["public_key"], frozenset({"controller"}))})
    for principal in context.get("revoked", []):
        registry.revoke(principal)
    payload = registry.verify(trust.SignedEnvelope.model_validate(signed), DOMAIN, "controller")
    fields = {"binding", "nonce", "not_before", "expires", "journal_identity"}
    if set(payload) != fields or payload["binding"] != binding:
        raise ValueError("Grant does not authorize this exact current scope, epoch, function, inputs and worker")
    if payload["journal_identity"] != context.get("journal_identity"):
        raise ValueError("Grant belongs to a different retained journal identity")
    if type(payload["not_before"]) is not int or type(payload["expires"]) is not int:
        raise ValueError("Query grant validity times must be integers")
    if not payload["not_before"] <= now < payload["expires"]:
        raise ValueError("Query grant is expired or not yet valid")
    if not isinstance(payload["nonce"], str) or not 1 <= len(payload["nonce"]) <= 128:
        raise ValueError("A bounded one-use nonce is required")
    return cast(dict[str, Any], payload)


def consume_grant(
    signed: dict[str, Any],
    context: dict[str, Any],
    manifest_path: Path,
    worker_path: Path,
    journal_path: Path,
    *,
    now: int | None = None,
) -> dict[str, Any]:
    """Atomically reserve one nonce and one scope/epoch slot before MPC execution."""
    _, store = native_modules()
    binding = bind_query(manifest_path, worker_path)
    payload = verify_grant(signed, context, binding, int(time.time()) if now is None else now)
    journal = store.Journal(journal_path)
    journal.verify()
    if journal.identity != context["journal_identity"]:
        raise ValueError("Retained query journal identity changed")
    nonce_key = "@reserve-query-nonce:" + digest({"nonce": payload["nonce"]})
    epoch_key = "@reserve-query-epoch:" + digest({key: binding[key] for key in ("scope_id", "scenario_epoch")})
    with journal.transaction() as connection:
        for name, label in ((nonce_key, "Query nonce"), (epoch_key, "Query scope and epoch")):
            try:
                journal.latest(name, connection)
            except KeyError:
                pass
            else:
                raise ValueError(label + " already consumed; no automatic retry or adaptive query")
        document = {"state": "consumed-before-mpc", "binding_sha256": digest(binding), "signed_grant": signed}
        journal.append(connection, nonce_key, document)
        journal.append(connection, epoch_key, document)
    if binding != bind_query(manifest_path, worker_path):
        raise ValueError("Public inputs or MPC worker changed during authority consumption")
    checkpoint = journal.verify()
    return {
        "schema": "agialpha.reserve-query.consumption.v1",
        "mode": MODE,
        "binding": binding,
        "binding_sha256": digest(binding),
        "journal_checkpoint": checkpoint,
        "nonce_consumed": True,
        "scope_epoch_consumed": True,
        "consumed_before_mpc": True,
        "authority": "Explicit local controller fixture only; no live ENS or independent organizational consent.",
    }


class FixtureQueryAuthority:
    """A small local controller fixture; never publish its private Journal directory."""

    def __init__(self, journal_dir: Path) -> None:
        trust, store = native_modules()
        self.trust = trust
        self.key = Ed25519PrivateKey.generate()
        self.journal_dir = Path(journal_dir)
        self.journal = store.Journal.initialize(self.journal_dir)
        self.context = {
            "mode": MODE,
            "principal": PRINCIPAL,
            "public_key": self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
            "journal_identity": self.journal.identity,
            "revoked": [],
        }

    def issue(
        self, binding: dict[str, Any], *, nonce: str | None = None, now: int | None = None, ttl: int = 300
    ) -> dict[str, Any]:
        """Explicitly issue a new fixture grant; prior acceptance confers no authority."""
        instant = int(time.time()) if now is None else now
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise ValueError("Fixture grant lifetime must be one second to one hour")
        payload = {
            "binding": json.loads(canonical(binding)),
            "nonce": nonce or str(uuid.uuid4()),
            "not_before": instant - 1,
            "expires": instant + ttl,
            "journal_identity": self.journal.identity,
        }
        return cast(
            dict[str, Any], self.trust.sign_record(self.key, PRINCIPAL, DOMAIN, payload).model_dump(mode="json")
        )

    def consume(self, grant: dict[str, Any], manifest: Path, worker: Path, *, now: int | None = None) -> dict[str, Any]:
        """Consume current authority immediately before the parent starts MPC workers."""
        return consume_grant(grant, self.context, manifest, worker, self.journal_dir, now=now)

    def public_receipt(self) -> dict[str, Any]:
        """Export signed public events and an exact checkpoint, never keys or API tokens."""
        checkpoint = self.journal.verify()
        with closing(sqlite3.connect(self.journal.path)) as connection:
            events = [
                {"body": json.loads(raw), "sha256": hashed, "signature": signature}
                for raw, hashed, signature in connection.execute("SELECT body,hash,signature FROM events ORDER BY seq")
            ]
        return {
            "schema": "agialpha.reserve-query.authority-receipt.v1",
            "mode": MODE,
            "context": self.context,
            "checkpoint": checkpoint,
            "events": events,
            "native_source_manifest_sha256": NATIVE_MANIFEST_SHA256,
            "scope": "One-use enforcement in this retained local journal; no malicious-host rollback resistance or independent consent claim.",
            "private_material_exported": False,
            "provider_calls": 0,
            "live_ens_checks": 0,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Consume one existing public local-fixture query grant")
    for field in ("grant", "context", "manifest", "worker", "journal"):
        parser.add_argument("--" + field, required=True, type=Path)
    arguments = parser.parse_args()
    try:
        receipt = consume_grant(
            read_json(arguments.grant)[0],
            read_json(arguments.context)[0],
            arguments.manifest,
            arguments.worker,
            arguments.journal,
        )
        print(json.dumps({"accepted": True, "binding_sha256": receipt["binding_sha256"]}))
    except Exception as error:
        print(json.dumps({"accepted": False, "error": str(error)}))
        raise SystemExit(1) from error
