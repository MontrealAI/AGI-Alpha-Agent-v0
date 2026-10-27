# SPDX-License-Identifier: Apache-2.0
"""Finite-run custody and separate CPU accounts; this module is not a scheduler."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    """Encode exact finite JSON data for local integrity, not authentication."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def micros(value: float) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("CPU_AMOUNT_INVALID")
    return math.ceil(value * 1000)


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError("IDENTIFIER_INVALID")
    return value


def hash_value(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("HASH_INVALID")
    return value


class CustodyError(RuntimeError):
    """A bounded operation cannot proceed under its retained context."""


class Custody:
    """Retain exact request results and segregate externally endowed CPU allowances."""

    def __init__(
        self, path: str | Path, source_hash: str, service_ms: float, improvement_ms: float,
        earned_cap_ms: float = 250, *, dependencies: dict[str, str] | None = None,
        expires_at: float | None = None, deadline_at: float | None = None,
    ):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise CustodyError("SYMLINK_CUSTODY_PATH")
        self.source_hash = hash_value(source_hash)
        self.dependencies = dict(dependencies or {})
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in self.dependencies.items()):
            raise CustodyError("DEPENDENCY_MAP_INVALID")
        canonical(self.dependencies)
        self.lock = None
        for name in ("writer.lock", "journal.jsonl", "anchor.jsonl"):
            if (self.path / name).is_symlink():
                raise CustodyError("SYMLINK_CUSTODY_FILE")
        self.lock = (self.path / "writer.lock").open("a+b")
        try:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.lock.close()
            self.lock = None
            raise CustodyError("ACTIVE_WRITER") from error
        try:
            expected = {"source_hash": self.source_hash, "dependency_digest": digest(self.dependencies),
                "service_us": micros(service_ms), "improvement_us": micros(improvement_ms),
                "earned_cap_us": micros(earned_cap_ms), "scope": "LOCAL_BOUNDED_NUMERICAL_RESEARCH"}
            self.events: list[dict[str, Any]] = []
            self.head = "0" * 64
            self.state: dict[str, Any] = {}
            if not (self.path / "journal.jsonl").exists():
                if (self.path / "anchor.jsonl").exists():
                    raise CustodyError("JOURNAL_MISSING_WITH_ANCHOR")
                now = time.time()
                config = {**expected, "dependencies": self.dependencies,
                    "expires_at": expires_at if expires_at is not None else now + 3600,
                    "deadline_at": deadline_at if deadline_at is not None else now + 3600}
                if not all(isinstance(config[k], (int, float)) and math.isfinite(config[k]) for k in ("expires_at", "deadline_at")):
                    raise CustodyError("TIME_BOUND_INVALID")
                self._append("init", config)
            else:
                self._load()
                config = self.state["config"]
                if config["source_hash"] != expected["source_hash"]:
                    raise CustodyError("SOURCE_CHANGED")
                if config["dependency_digest"] != expected["dependency_digest"]:
                    raise CustodyError("DEPENDENCY_CHANGED")
                for key in ("service_us", "improvement_us", "earned_cap_us", "scope"):
                    if config[key] != expected[key]:
                        raise CustodyError("BUDGET_OR_SCOPE_CHANGED")
                if expires_at is not None and config["expires_at"] != expires_at:
                    raise CustodyError("AUTHORITY_EXPIRY_CHANGED")
                if deadline_at is not None and config["deadline_at"] != deadline_at:
                    raise CustodyError("DEADLINE_CHANGED")
                pending = [key for key, value in self.state["requests"].items() if value["status"] == "PENDING"]
                for key in pending:
                    self._append("quarantine", {"id": key, "reason": "UNCLEAN_OR_UNACKNOWLEDGED_PENDING_WORK",
                        "charged_us": self.state["requests"][key]["ceiling_us"], "actual_cpu_us": None})
        except Exception:
            self.close()
            raise

    def _load(self) -> None:
        path = self.path / "journal.jsonl"
        if path.stat().st_size > 50_000_000:
            raise CustodyError("JOURNAL_SIZE_LIMIT")
        raw = path.read_bytes()
        if not raw or not raw.endswith(b"\n"):
            raise CustodyError("JOURNAL_TRUNCATED")
        rows = raw.splitlines()
        if len(rows) > 10000:
            raise CustodyError("JOURNAL_EVENT_LIMIT")
        self.events, self.state, self.head = [], {}, "0" * 64
        for line in rows:
            try:
                event = json.loads(line)
                body = {key: value for key, value in event.items() if key != "hash"}
                if set(event) != {"sequence", "previous", "kind", "at_ns", "payload", "hash"}:
                    raise ValueError("event fields")
                if event["sequence"] != len(self.events) or event["previous"] != self.head or digest(body) != event["hash"]:
                    raise ValueError("event chain")
                self._apply(event["kind"], event["payload"])
            except Exception as error:
                raise CustodyError("JOURNAL_INTEGRITY") from error
            self.events.append(event)
            self.head = event["hash"]
        anchor_path = self.path / "anchor.jsonl"
        if not anchor_path.exists():
            raise CustodyError("ANCHOR_MISSING")
        anchor_bytes = anchor_path.read_bytes()
        if anchor_bytes and not anchor_bytes.endswith(b"\n"):
            raise CustodyError("ANCHOR_TRUNCATED")
        try:
            anchors = [json.loads(line) for line in anchor_bytes.splitlines()]
            for index, anchor in enumerate(anchors):
                if anchor != {"sequence": index, "head": self.events[index]["hash"]}:
                    raise ValueError("anchor chain")
        except Exception as error:
            raise CustodyError("STALE_OR_CORRUPT_CHECKPOINT") from error
        if len(anchors) == len(self.events) - 1:
            self._write_line(anchor_path, {"sequence": len(self.events) - 1, "head": self.head})
        elif len(anchors) != len(self.events):
            raise CustodyError("STALE_OR_CORRUPT_CHECKPOINT")

    def _apply(self, kind: str, payload: dict[str, Any]) -> None:
        if kind == "init":
            if self.state:
                raise CustodyError("DUPLICATE_INIT")
            self.state = {"config": payload, "accounts": {
                "service": {"external_us": payload["service_us"], "available_us": payload["service_us"], "spent_us": 0, "reserved_us": 0},
                "improvement": {"external_us": payload["improvement_us"], "available_us": payload["improvement_us"], "spent_us": 0, "reserved_us": 0},
                "earned": {"external_us": 0, "available_us": 0, "spent_us": 0, "reserved_us": 0}},
                "requests": {}, "earned_released_us": 0, "stopped": False, "stop_generation": 0,
                "terminal_hold": False, "assets": {}, "rejected": [], "selected_asset": None}
        elif kind == "reserve":
            account = self.state["accounts"][payload["account"]]
            account["available_us"] -= payload["ceiling_us"]
            account["reserved_us"] += payload["ceiling_us"]
            self.state["requests"][payload["id"]] = {**payload, "status": "PENDING", "released_us": 0}
        elif kind in {"commit", "quarantine"}:
            request = self.state["requests"][payload["id"]]
            account = self.state["accounts"][request["account"]]
            charged = payload["charged_us"]
            account["reserved_us"] -= request["ceiling_us"]
            account["available_us"] += request["ceiling_us"] - charged
            account["spent_us"] += charged
            request.update(payload)
            if kind == "quarantine":
                request["status"] = "QUARANTINED"
                request["accepted"] = False
            else:
                if digest(payload["receipt"]) != payload["receipt_digest"]:
                    raise CustodyError("RECEIPT_INTEGRITY")
                request["status"] = "OVERRUN" if charged > request["ceiling_us"] else "COMPLETED"
                request["accepted"] = (request["status"] == "COMPLETED" and not payload.get("acceptance_blocker")
                    and payload["receipt"]["valid"] and payload["receipt"]["qualified"])
                if request["status"] == "OVERRUN":
                    self.state["stopped"] = True
                    self.state["terminal_hold"] = True
        elif kind == "release-capacity":
            amount = payload["amount_us"]
            self.state["accounts"]["service"]["available_us"] -= amount
            self.state["accounts"]["earned"]["available_us"] += amount
            self.state["requests"][payload["id"]]["released_us"] += amount
            self.state["earned_released_us"] += amount
        elif kind == "stop":
            self.state["stopped"] = True
            self.state["stop_generation"] += 1
        elif kind == "resume":
            self.state["stopped"] = False
        elif kind == "retain-asset":
            self.state["assets"][payload["digest"]] = payload
        elif kind == "reject-asset":
            self.state["rejected"].append(payload["digest"])
            ancestor = self.state["selected_asset"]
            while ancestor is not None:
                if ancestor == payload["digest"]:
                    self.state["selected_asset"] = None
                    break
                ancestor = self.state["assets"].get(ancestor, {}).get("parent_digest")
        elif kind in {"select-asset", "rollback-asset"}:
            self.state["selected_asset"] = payload["digest"]
        else:
            raise CustodyError("UNKNOWN_EVENT")

    def _write_line(self, path: Path, value: dict[str, Any]) -> None:
        data = canonical(value) + b"\n"
        if len(data) > 2_000_000:
            raise CustodyError("EVENT_SIZE_LIMIT")
        with path.open("ab") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())

    def _append(self, kind: str, payload: dict[str, Any]) -> None:
        if self.lock is None:
            raise CustodyError("CUSTODY_CLOSED")
        payload = json.loads(canonical(payload))
        body = {"sequence": len(self.events), "previous": self.head, "kind": kind,
            "at_ns": time.time_ns(), "payload": payload}
        event = {**body, "hash": digest(body)}
        self._write_line(self.path / "journal.jsonl", event)
        self._write_line(self.path / "anchor.jsonl", {"sequence": len(self.events), "head": event["hash"]})
        self._apply(kind, payload)
        self.events.append(event)
        self.head = event["hash"]

    def assert_context(self, source_hash: str | None = None, dependencies: dict[str, str] | None = None) -> None:
        """Reject an observed source or dependency change, without refreshing authority."""
        if source_hash is not None and source_hash != self.state["config"]["source_hash"]:
            raise CustodyError("SOURCE_CHANGED")
        if dependencies is not None and digest(dependencies) != self.state["config"]["dependency_digest"]:
            raise CustodyError("DEPENDENCY_CHANGED")

    def _guard(self, *, permit_stopped: bool = False) -> None:
        if self.lock is None:
            raise CustodyError("CUSTODY_CLOSED")
        self.assert_context(self.source_hash, self.dependencies)
        config = self.state["config"]
        now = time.time()
        if now >= config["expires_at"]:
            raise CustodyError("EXPIRED_AUTHORITY")
        if now >= config["deadline_at"]:
            raise CustodyError("EXHAUSTED_DEADLINE")
        if self.state["terminal_hold"]:
            raise CustodyError("TERMINAL_ACCOUNTING_HOLD")
        if self.state["stopped"] and not permit_stopped:
            raise CustodyError("STOPPED")

    def _result(self, request: dict[str, Any], execute: bool = False) -> dict[str, Any]:
        return json.loads(canonical({**request, "execute": execute}))

    def reserve(self, request_id: str, account: str, ceiling_ms: float, request_digest: str) -> dict[str, Any]:
        """Reserve only one named account; a completed duplicate returns its exact receipt."""
        request_id, request_digest = identifier(request_id), hash_value(request_digest)
        ceiling = micros(ceiling_ms)
        if account not in {"service", "improvement", "earned"}:
            raise CustodyError("ACCOUNT_NOT_ALLOWED")
        if request_id in self.state["requests"]:
            request = self.state["requests"][request_id]
            if (request["account"], request["ceiling_us"], request["request_digest"]) != (account, ceiling, request_digest):
                raise CustodyError("REQUEST_BINDING_CHANGED")
            return self._result(request)
        self._guard()
        if ceiling > self.state["accounts"][account]["available_us"]:
            raise CustodyError("ACCOUNT_EXHAUSTED")
        self._append("reserve", {"id": request_id, "account": account, "ceiling_us": ceiling,
            "request_digest": request_digest, "source_hash": self.source_hash,
            "dependency_digest": self.state["config"]["dependency_digest"]})
        return self._result(self.state["requests"][request_id], True)

    def commit(self, request_id: str, actual_cpu_ms: float, receipt: dict[str, Any]) -> dict[str, Any]:
        """Charge observed CPU even on overrun, without borrowing from another account."""
        if request_id not in self.state["requests"]:
            raise CustodyError("UNRESERVED_REQUEST")
        if not isinstance(receipt, dict) or type(receipt.get("valid")) is not bool or type(receipt.get("qualified")) is not bool:
            raise CustodyError("INVALID_RECEIPT")
        if receipt["qualified"] and not receipt["valid"]:
            raise CustodyError("INVALID_RECEIPT")
        if "source_hash" in receipt and receipt["source_hash"] != self.source_hash:
            raise CustodyError("RECEIPT_SOURCE_CHANGED")
        charged = micros(actual_cpu_ms)
        receipt = json.loads(canonical(receipt))
        receipt_digest = digest(receipt)
        request = self.state["requests"][request_id]
        if request["status"] != "PENDING":
            if request.get("receipt_digest") == receipt_digest and request.get("charged_us") == charged:
                return self._result(request)
            raise CustodyError("REQUEST_TERMINAL")
        blocker = None
        try:
            self._guard()
        except CustodyError as error:
            blocker = str(error)
        self._append("commit", {"id": request_id, "charged_us": charged, "actual_cpu_us": charged,
            "receipt": receipt, "receipt_digest": receipt_digest, "acceptance_blocker": blocker})
        return self._result(self.state["requests"][request_id])

    def release_capacity(self, request_id: str, amount_ms: float, *, evidence_digest: str | None = None) -> dict[str, Any]:
        """Transfer bounded unspent service allowance; never create cash or extra endowment."""
        self._guard()
        request = self.state["requests"].get(request_id)
        if not request or request["account"] != "service" or request["status"] != "COMPLETED" or not request["accepted"]:
            raise CustodyError("CAPACITY_REQUIRES_ACCEPTED_SERVICE")
        amount = micros(amount_ms)
        if evidence_digest is not None:
            hash_value(evidence_digest)
        unused = request["ceiling_us"] - request["charged_us"] - request["released_us"]
        cap_left = self.state["config"]["earned_cap_us"] - self.state["earned_released_us"]
        if amount > min(unused, cap_left, self.state["accounts"]["service"]["available_us"]):
            raise CustodyError("RELEASE_CAPACITY_EXCEEDED")
        self._append("release-capacity", {"id": request_id, "amount_us": amount,
            "origin": "RELEASED_ORIGINAL_SERVICE_QUOTA", "evidence_digest": evidence_digest,
            "incremental_saving_proven_by_custody": False, "cash_created": False})
        return self.status()

    def stop(self, reason: str = "EXPLICIT_STOP") -> dict[str, Any]:
        """Append a persistent stop; its history is never removed by resume."""
        self._append("stop", {"reason": str(reason)[:1000], "intervention": True})
        return self.status()

    def resume(self) -> dict[str, Any]:
        """Explicitly resume the same unexpired scope; never extend its original deadline."""
        self._guard(permit_stopped=True)
        if self.state["stopped"]:
            self._append("resume", {"stop_generation": self.state["stop_generation"], "intervention": True})
        return self.status()

    def retain_asset(self, asset_id: str, asset_digest: str, receipt_id: str, *, scope: str,
                     parent_digest: str | None = None) -> dict[str, Any]:
        """Retain scoped research evidence without granting current institutional authority."""
        self._guard()
        identifier(asset_id)
        hash_value(asset_digest)
        if asset_digest in self.state["rejected"]:
            raise CustodyError("REJECTED_ASSET")
        receipt = self.state["requests"].get(receipt_id)
        if not receipt or not receipt.get("accepted"):
            raise CustodyError("ASSET_REQUIRES_ACCEPTED_RECEIPT")
        if parent_digest is not None:
            self._applicable_asset(parent_digest)
        value = {"id": asset_id, "digest": asset_digest, "receipt_id": receipt_id, "scope": str(scope)[:1000],
            "parent_digest": parent_digest, "source_hash": self.source_hash,
            "dependency_digest": self.state["config"]["dependency_digest"], "active_proof": [], "authority": []}
        previous = self.state["assets"].get(asset_digest)
        if previous is not None:
            if previous != value:
                raise CustodyError("ASSET_BINDING_CHANGED")
            return json.loads(canonical(previous))
        self._append("retain-asset", value)
        return json.loads(canonical(value))

    def reject_asset(self, asset_digest: str, reason: str) -> None:
        self._guard()
        hash_value(asset_digest)
        if asset_digest not in self.state["rejected"]:
            self._append("reject-asset", {"digest": asset_digest, "reason": str(reason)[:1000]})

    def select_asset(self, asset_digest: str, *, rollback: bool = False) -> dict[str, Any]:
        """Select a retained applicable asset; rejected descendants cannot re-enter."""
        self._guard()
        asset = self._applicable_asset(asset_digest)
        self._append("rollback-asset" if rollback else "select-asset",
            {"digest": asset_digest, "prior": self.state["selected_asset"], "active_proof": [], "authority": []})
        return json.loads(canonical(asset))

    def _applicable_asset(self, asset_digest: str) -> dict[str, Any]:
        if asset_digest in self.state["rejected"]:
            raise CustodyError("REJECTED_ASSET")
        asset = self.state["assets"].get(asset_digest)
        if asset is None:
            raise CustodyError("UNKNOWN_ASSET")
        if asset["source_hash"] != self.source_hash or asset["dependency_digest"] != self.state["config"]["dependency_digest"]:
            raise CustodyError("STALE_ASSET")
        if asset["parent_digest"] is not None:
            self._applicable_asset(asset["parent_digest"])
        return asset

    def rollback(self, asset_digest: str) -> dict[str, Any]:
        return self.select_asset(asset_digest, rollback=True)

    def checkpoint(self) -> dict[str, Any]:
        return {"sequence": len(self.events) - 1, "head": self.head, "source_hash": self.source_hash,
            "dependency_digest": self.state["config"]["dependency_digest"]}

    def verify_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        if checkpoint != self.checkpoint():
            raise CustodyError("STALE_CHECKPOINT")

    def status(self) -> dict[str, Any]:
        result = json.loads(canonical(self.state))
        result["checkpoint"] = self.checkpoint()
        result["total_charged_cpu_ms"] = sum(a["spent_us"] for a in result["accounts"].values()) / 1000
        result["measurement"] = "CPU allowances and charges; overruns are recorded, not prevented by a native sandbox"
        result["authentication"] = "LOCAL_HASH_CHAIN_NOT_SIGNED_AUTHORITY"
        result["same_host_trust_limit"] = "An actor able to replace both journal and anchor can rewind them; retain checkpoints independently."
        return result

    def close(self) -> None:
        if self.lock is not None:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None

    def __enter__(self) -> Custody:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
