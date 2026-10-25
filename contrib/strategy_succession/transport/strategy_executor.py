"""Local fixed-method transport using the released Alpha signed journal boundary.

This contribution is engineering acceptance, not scientific confirmation or
production authority. Only operator-installed reviewed pure workers are callable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import stat
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Protocol, cast

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from alpha_factory_v1.core.runtime.api import RequestBoundary
from alpha_factory_v1.core.runtime.store import Conflict, Journal, canonical, digest
from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads
from alpha_factory_v1.core.runtime.successor.state import ActionGateway, ActionRequest

KEY = "@strategy-executor:v1"
METHODS = {"run-mission", "construct", "run-journey"}
COUNTERS = ("service_work", "improvement_work", "native_calls", "native_solve_seconds")
SCIENTIFIC_SOURCE_HASH = "7e5a1dd2dcf7eb00ec055f1858d5dd722cc950f15f33314bb94c456c753845a7"
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


class FixedWorker(Protocol):
    def execute(self, method: str, payload: dict[str, Any], limits: dict[str, Any],
                checkpoint: Callable[..., None]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SourceFile:
    label: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class Limits:
    service_work: int = 0
    improvement_work: int = 0
    native_calls: int = 0
    native_solve_seconds: float = 0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("invalid operator budget")
            if name != "native_solve_seconds" and (not isinstance(value, int) or value > 10**12):
                raise ValueError("work and call limits require bounded integers")
            if name == "native_solve_seconds" and value > 3600:
                raise ValueError("native solve ceiling exceeds one hour")


@dataclass(frozen=True)
class ExecutorPolicy:
    executor_id: str
    sources: tuple[SourceFile, ...]
    methods: dict[str, Limits]
    total: Limits
    max_requests: int = 8
    grant_seconds: int = 600
    request_seconds: int = 300
    max_input_bytes: int = 32_768
    max_output_bytes: int = 512_000
    allow_native: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", self.executor_id):
            raise ValueError("invalid installed executor identity")
        if not self.sources or len(self.sources) > 256 or len({s.label for s in self.sources}) != len(self.sources):
            raise ValueError("installed source inventory is empty or ambiguous")
        if any(not re.fullmatch(r"[A-Za-z0-9_./-]{1,160}", s.label) or
               not re.fullmatch(r"[0-9a-f]{64}", s.sha256) for s in self.sources):
            raise ValueError("source identities must be explicit")
        if not self.methods or not set(self.methods) <= METHODS:
            raise ValueError("unsupported installed method")
        object.__setattr__(self, "methods", MappingProxyType(dict(self.methods)))
        for method, limit in self.methods.items():
            if method == "run-mission" and limit.improvement_work != 0:
                raise ValueError("service method cannot use improvement work")
            if method == "construct" and limit.service_work != 0:
                raise ValueError("construction cannot use service work")
            if method == "run-journey" and (limit.service_work <= 0 or limit.improvement_work <= 0):
                raise ValueError("journey requires two separately funded accounts")
        if not 1 <= self.max_requests <= 256 or not 1 <= self.request_seconds <= 1800:
            raise ValueError("invalid installed request bound")
        if not self.request_seconds <= self.grant_seconds <= 3600:
            raise ValueError("invalid installed lease bound")
        if type(self.allow_native) is not bool or not 1 <= self.max_input_bytes <= 131_072 or not 1 <= self.max_output_bytes <= 1_000_000:
            raise ValueError("invalid installed native or payload policy")


def _zero() -> dict[str, float | int]:
    return {name: 0 for name in COUNTERS}


def _bounded_json(value: Any, maximum: int) -> Any:
    data = canonical(value)
    if len(data) > maximum:
        raise ValueError("JSON payload exceeds installed bound")
    result = json.loads(data)
    def depth(item: Any, level: int = 0) -> None:
        if level > 32:
            raise ValueError("JSON nesting exceeds installed bound")
        if isinstance(item, dict):
            for child in item.values():
                depth(child, level + 1)
        elif isinstance(item, list):
            for child in item:
                depth(child, level + 1)
    depth(result)
    return result


class StrategyExecutor:
    """Reserve exact local envelopes and never replay uncertain work automatically."""

    def __init__(self, journal: Journal, worker: FixedWorker, policy: ExecutorPolicy,
                 *, clock: Callable[[], float] = time.time) -> None:
        self.journal, self.worker, self.policy, self.clock = journal, worker, policy, clock
        self._owned_run: tuple[str, str] | None = None
        journal.verify()
        self.source_map = {s.label: s.sha256 for s in policy.sources}
        self.source_hash = digest(self.source_map)
        home_info, database_info = journal.root.stat(), journal.path.stat()
        authority_id = digest({"local_home": str(journal.root), "home_device": home_info.st_dev,
                               "home_inode": home_info.st_ino, "database_device": database_info.st_dev,
                               "database_inode": database_info.st_ino})
        self.binding = digest({"executor": policy.executor_id, "sources": self.source_map,
                               "local_authority_incarnation": authority_id,
                               "methods": {k: asdict(v) for k, v in policy.methods.items()},
                               "total": asdict(policy.total), "max_requests": policy.max_requests,
                               "grant_seconds": policy.grant_seconds, "request_seconds": policy.request_seconds,
                               "max_input_bytes": policy.max_input_bytes, "max_output_bytes": policy.max_output_bytes,
                               "allow_native": policy.allow_native})
        with _LOCKS_GUARD:
            self.execution_lock = _LOCKS.setdefault(str(journal.root), threading.Lock())
        with journal.transaction() as cx:
            try:
                old = journal.latest(KEY, cx)
                if old["binding"] != self.binding:
                    raise Conflict("installed executor policy changed; use a separately reviewed journal")
            except KeyError:
                journal.append(cx, KEY, {"schema": "strategy-executor/v1", "binding": self.binding,
                               "source_hash": self.source_hash, "executor_id": policy.executor_id,
                               "state": "ready", "plans": {}, "reserved": _zero(), "spent": _zero(),
                               "request_count": 0, "production_authority": False})

    def _source(self) -> None:
        for source in self.policy.sources:
            before = source.path.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 8_000_000:
                raise ValueError("installed worker source is unavailable or unsupported")
            data = source.path.read_bytes()
            after = source.path.lstat()
            if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (
                    after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size):
                raise ValueError("installed source changed during inspection")
            if hashlib.sha256(data).hexdigest() != source.sha256:
                raise ValueError("installed source identity changed")

    def _load(self, cx: Any = None) -> dict[str, Any]:
        value = self.journal.latest(KEY, cx)
        if value["binding"] != self.binding:
            raise Conflict("executor source or policy binding changed")
        return value

    def _save(self, cx: Any, value: dict[str, Any]) -> dict[str, Any]:
        return self.journal.append(cx, KEY, self.journal.document(value))

    def _global_ready(self, cx: Any = None) -> None:
        if self.journal.latest("@control", cx)["state"] != "ready":
            raise Conflict("the existing journal operator control is paused")

    def status(self) -> dict[str, Any]:
        self.journal.verify()
        value = self._load()
        try:
            self._source()
            source_available = True
        except (ValueError, OSError):
            source_available = False
        running = [p for p in value["plans"].values() if p["state"] == "running"]
        owned = any(self._owned_run == (p["plan_id"], p.get("lease_id")) for p in running)
        active = True if owned else None if running else False
        observation = "running-in-this-executor" if owned else "awaiting-evidence" if running else "idle"
        lease_state = "expired" if any(self.clock() >= p["lease_expires_at"] for p in running) else "current" if running else "none"
        return {**value, "source_available": source_available, "total": asdict(self.policy.total),
                "methods": {k: asdict(v) for k, v in self.policy.methods.items()},
                "journal_identity": self.journal.identity, "active_after_browser_close": active,
                "record_running": bool(running), "execution_observation": observation, "lease_state": lease_state,
                "global_control": self.journal.latest("@control")["state"],
                "connection": "local-authenticated", "max_concurrency": 1}

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        if set(request) != {"method", "input", "request_id"}:
            raise ValueError("prepare requires only method, input and request_id")
        method, ident = request["method"], request["request_id"]
        if not isinstance(method, str) or method not in self.policy.methods:
            raise ValueError("method is not installed")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", ident):
            raise ValueError("invalid idempotency identity")
        if not isinstance(request["input"], dict):
            raise ValueError("fixed method input must be a JSON object")
        payload = _bounded_json(request["input"], self.policy.max_input_bytes)
        request_hash = digest({"method": method, "input": payload, "request_id": ident})
        plan_id = digest({"request_id": ident})[:32]
        self._source()
        with self.journal.transaction() as cx:
            self._global_ready(cx)
            value = self._load(cx)
            if plan_id in value["plans"]:
                plan = value["plans"][plan_id]
                if plan["request_hash"] != request_hash:
                    raise Conflict("idempotency identity already binds different inputs")
                return cast(dict[str, Any], plan)
            if value["state"] != "ready" or value["request_count"] >= self.policy.max_requests:
                raise Conflict("executor is paused, stopped or request capacity is exhausted")
            now = self.clock()
            plan = {"plan_id": plan_id, "request_id": ident, "request_hash": request_hash,
                    "method": method, "input": payload, "executor_id": self.policy.executor_id,
                    "source_hash": self.source_hash, "policy_binding": self.binding,
                    "caps": asdict(self.policy.methods[method]), "prepared_at": now,
                    "expires_at": now + self.policy.grant_seconds, "request_seconds": self.policy.request_seconds,
                    "state": "prepared", "production_authority": False, "observed": _zero(), "partial_receipts": []}
            plan["plan_digest"] = digest(plan)
            value["plans"][plan_id] = plan
            value["request_count"] += 1
            self._save(cx, value)
            return plan

    def _plan(self, value: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        if set(request) != {"plan_id", "plan_digest"}:
            raise ValueError("operation requires exact plan_id and plan_digest")
        if not isinstance(request["plan_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", request["plan_id"]) or not isinstance(request["plan_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", request["plan_digest"]):
            raise ValueError("invalid exact plan identity")
        plan = value["plans"][request["plan_id"]]
        if not secrets.compare_digest(str(plan["plan_digest"]), str(request["plan_digest"])):
            raise Conflict("approval does not match the displayed exact plan")
        return cast(dict[str, Any], plan)

    def approve(self, request: dict[str, Any]) -> dict[str, Any]:
        self._source()
        with self.journal.transaction() as cx:
            self._global_ready(cx)
            value = self._load(cx)
            plan = self._plan(value, request)
            if value["state"] != "ready" or self.clock() >= plan["expires_at"]:
                raise Conflict("executor grant is stopped, paused or expired")
            if plan["state"] == "approved":
                return plan
            if plan["state"] != "prepared":
                raise Conflict("this plan cannot receive another approval")
            plan["state"] = "approved"
            plan["approved_at"] = self.clock()
            self._save(cx, value)
            return plan

    def control(self, state: str) -> dict[str, Any]:
        if state not in {"ready", "paused", "stopped"}:
            raise ValueError("unsupported executor control")
        with self.journal.transaction() as cx:
            value = self._load(cx)
            if value["state"] == "stopped" and state != "stopped":
                raise Conflict("STOP is permanent for this installed envelope")
            value["state"] = state
            self._save(cx, value)
        return self.status()

    def _partial_receipt(self, plan: dict[str, Any], receipt: Any) -> dict[str, Any]:
        """Check fixed phase bytes and attach source/plan-bound local attribution."""
        partial = _bounded_json(receipt, self.policy.max_output_bytes)
        if not isinstance(partial, dict) or set(partial) != {"phase_index", "receipt_hash", "task", "result", "checker", "selectedmethod"}:
            raise ValueError("unsupported fixed phase receipt")
        if type(partial["phase_index"]) is not int or not 0 <= partial["phase_index"] <= 2:
            raise ValueError("partial phase index exceeds its bound")
        if not isinstance(partial["receipt_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", partial["receipt_hash"]):
            raise ValueError("invalid phase receipt hash")
        if not all(isinstance(partial[k], dict) for k in ("task", "result", "checker")):
            raise ValueError("phase task, result and checker must be structured")
        if not isinstance(partial["selectedmethod"], str) or not 1 <= len(partial["selectedmethod"]) <= 128:
            raise ValueError("invalid fixed phase method")
        task_id = partial["task"].get("id")
        if not isinstance(task_id, str) or not 1 <= len(task_id.strip()) <= 128 or any(ord(c) < 32 for c in task_id):
            raise ValueError("phase receipt requires an explicit bounded task identity")
        if partial["checker"].get("valid") is not True or partial["result"].get("task_id") != task_id:
            raise ValueError("phase receipt has no matching checked delivery")
        def integers_only(value: Any) -> None:
            if isinstance(value, float) or isinstance(value, int) and not isinstance(value, bool) and abs(value) > 2**53 - 1:
                raise ValueError("fixed phase receipts require safe integer quantities")
            if isinstance(value, dict):
                for child in value.values():
                    integers_only(child)
            elif isinstance(value, list):
                for child in value:
                    integers_only(child)
        integers_only(partial)
        original = {"source_hash": self.source_hash, "scientific_source_hash": SCIENTIFIC_SOURCE_HASH,
                    "task": partial["task"], "result": partial["result"], "checker": partial["checker"],
                    "method": partial["selectedmethod"], "proof": [], "authority": []}
        if digest(original) != partial["receipt_hash"]:
            raise ValueError("phase bytes do not match the source-bound worker receipt")
        body = {"schema": "strategy-executor-partial/v1", "source_hash": self.source_hash,
                "scientific_source_hash": SCIENTIFIC_SOURCE_HASH, "policy_binding": self.binding,
                "request_hash": plan["request_hash"], **partial, "proof": [], "authority": []}
        return {**body, "transport_digest": digest(body)}

    def _checkpoint(self, plan_id: str, lease_id: str, *, receipt: Any = None, **increments: Any) -> None:
        if not set(increments) <= set(COUNTERS):
            raise ValueError("unknown work counter")
        self._source()
        with self.journal.transaction() as cx:
            self._global_ready(cx)
            value = self._load(cx)
            plan = value["plans"][plan_id]
            if value["state"] != "ready" or plan["state"] != "running" or plan["lease_id"] != lease_id:
                raise Conflict("execution was stopped, paused or superseded")
            if self.clock() >= min(plan["expires_at"], plan["lease_expires_at"]):
                raise Conflict("execution lease expired")
            receipt_changed = False
            if receipt is not None:
                retained = self._partial_receipt(plan, receipt)
                partials = plan.setdefault("partial_receipts", [])
                index = retained["phase_index"]
                if index < len(partials):
                    if partials[index] != retained:
                        raise Conflict("an existing phase receipt cannot be substituted")
                    if any(increments.values()):
                        raise Conflict("duplicate receipt delivery cannot repeat cost increments")
                else:
                    if index != len(partials) or len(partials) >= 3:
                        raise Conflict("phase receipt ordering or count exceeds its envelope")
                    if any(previous["receipt_hash"] == retained["receipt_hash"] or
                           previous["task"]["id"] == retained["task"]["id"] for previous in partials):
                        raise Conflict("a retained delivery cannot be relabelled as another phase")
                    _bounded_json([*partials, retained], self.policy.max_output_bytes)
                    partials.append(retained)
                    receipt_changed = True
            for name, amount in increments.items():
                if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
                    raise ValueError("invalid work increment")
                if name != "native_solve_seconds" and not isinstance(amount, int):
                    raise ValueError("work and calls require integer increments")
                if name.startswith("native_") and amount and not self.policy.allow_native:
                    raise Conflict("native execution is not enabled by installed policy")
                if plan["observed"][name] + amount > plan["caps"][name]:
                    raise Conflict("request work ceiling exhausted")
                plan["observed"][name] += amount
            if increments or receipt_changed:
                self._save(cx, value)

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.execution_lock.acquire(blocking=False):
            # A completed duplicate can be returned without acquiring an execution slot.
            value = self._load()
            plan = self._plan(value, request)
            if plan["state"] in {"completed", "rejected"}:
                return plan
            raise Conflict("one executor request is already active")
        plan_id: str | None = None
        lease_id = secrets.token_hex(16)
        try:
            self._source()
            with self.journal.transaction() as cx:
                self._global_ready(cx)
                value = self._load(cx)
                plan = self._plan(value, request)
                if plan["state"] in {"completed", "rejected"}:
                    return plan
                if value["state"] != "ready" or self.clock() >= plan["expires_at"]:
                    raise Conflict("executor approval is paused, stopped or expired")
                if plan["state"] != "approved" or any(p["state"] == "running" for p in value["plans"].values()):
                    raise Conflict("request is unapproved, already running or requires reconciliation")
                total = asdict(self.policy.total)
                if any(value["spent"][k] + value["reserved"][k] + plan["caps"][k] > total[k] for k in COUNTERS):
                    raise Conflict("separate installed account or native ceiling exhausted")
                for name in COUNTERS:
                    value["reserved"][name] += plan["caps"][name]
                plan_id = plan["plan_id"]
                plan.update(state="running", lease_id=lease_id, started_at=self.clock(),
                            lease_expires_at=min(plan["expires_at"], self.clock() + self.policy.request_seconds))
                self._save(cx, value)
                payload = _bounded_json(plan["input"], self.policy.max_input_bytes)
                method, caps = plan["method"], dict(plan["caps"])
            self._owned_run = (plan_id, lease_id)
            def checkpoint(**units: Any) -> None:
                self._checkpoint(cast(str, plan_id), lease_id, **units)
            def fixed_handler(action: ActionRequest) -> dict[str, Any]:
                checkpoint()
                if action.context_digest != plan["request_hash"] or action.target != method:
                    raise Conflict("gateway action context mismatch")
                return self.worker.execute(method, payload, {**caps, "wall_seconds": self.policy.request_seconds,
                                           "allow_native": self.policy.allow_native,
                                           "source_hash": self.source_hash}, checkpoint)
            gateway = ActionGateway({("strategy-fixed", "execute"): fixed_handler})
            action = ActionRequest(action_id="strategy-" + plan_id, subject=self.policy.executor_id,
                                   release_digest=self.source_hash, environment_digest=self.binding,
                                   action="execute", tool="strategy-fixed", target=method,
                                   context_digest=plan["request_hash"], resources={"requests": 1}, scope="sandbox")
            outcome = gateway.execute(action)
            checkpoint()
            outcome = _bounded_json(outcome, self.policy.max_output_bytes)
            if not isinstance(outcome, dict) or set(outcome) != {"result", "costs", "source_hash", "verified"}:
                raise ValueError("fixed worker returned an unsupported outcome")
            costs = outcome["costs"]
            if not isinstance(costs, dict) or set(costs) != {*COUNTERS, "unknown_costs"}:
                raise ValueError("fixed worker cost inventory is incomplete")
            if outcome["source_hash"] != self.source_hash or type(outcome["verified"]) is not bool:
                raise ValueError("fixed worker source or verification field mismatch")
            if not isinstance(costs["unknown_costs"], list) or len(costs["unknown_costs"]) > 32 or any(
                    not isinstance(v, str) or len(v) > 300 for v in costs["unknown_costs"]):
                raise ValueError("unknown cost inventory exceeds its bound")
            with self.journal.transaction() as cx:
                self._global_ready(cx)
                value = self._load(cx)
                current = value["plans"][plan_id]
                if value["state"] != "ready" or current["state"] != "running" or current["lease_id"] != lease_id:
                    raise Conflict("completion lost its current executor lease")
                if self.clock() >= min(current["expires_at"], current["lease_expires_at"]):
                    raise Conflict("completion arrived after executor expiry")
                for name in COUNTERS:
                    amount = costs[name]
                    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
                        raise ValueError("actual work counters must be finite")
                    if name != "native_solve_seconds" and not isinstance(amount, int):
                        raise ValueError("actual work and calls require integers")
                    if name.startswith("native_") and amount and not self.policy.allow_native:
                        raise ValueError("native execution was not enabled")
                    if not current["observed"][name] <= amount <= current["caps"][name]:
                        raise ValueError("actual work contradicts observed counters or caps")
                _bounded_json({"partial_receipts": current.get("partial_receipts", []), "outcome": outcome},
                              self.policy.max_output_bytes)
                for name in COUNTERS:
                    value["reserved"][name] -= current["caps"][name]
                    value["spent"][name] += costs[name]
                current.update(state="completed" if outcome["verified"] else "rejected", completed_at=self.clock(), outcome=outcome,
                               outcome_hash=digest(outcome), observed={k: costs[k] for k in COUNTERS})
                self._save(cx, value)
                # The transaction commits before this result is acknowledged.
                result = _bounded_json(current, self.policy.max_output_bytes + self.policy.max_input_bytes + 8192)
            return cast(dict[str, Any], result)
        except BaseException:
            if plan_id is not None:
                with self.journal.transaction() as cx:
                    value = self._load(cx)
                    current = value["plans"][plan_id]
                    if current["state"] == "running" and current["lease_id"] == lease_id:
                        current.update(state="unknown", interrupted_at=self.clock(),
                                       error="Execution did not commit a verified outcome; inspect before new work.",
                                       costs_status="reserved-ceilings-remain-charged")
                        self._save(cx, value)
            raise
        finally:
            self._owned_run = None
            self.execution_lock.release()

    def reconcile(self, request: dict[str, Any]) -> dict[str, Any]:
        if set(request) != {"plan_id", "record_digest", "note"} or not isinstance(request["note"], str) or not 1 <= len(request["note"]) <= 2000:
            raise ValueError("reconciliation needs exact current record and operator note")
        with self.journal.transaction() as cx:
            value = self._load(cx)
            if value["digest"] != request["record_digest"]:
                raise Conflict("reconciliation record is stale")
            plan = value["plans"][request["plan_id"]]
            if plan["state"] == "running" and self.clock() < plan["lease_expires_at"]:
                raise Conflict("an active lease cannot be reconciled")
            if plan["state"] not in {"running", "unknown"}:
                raise Conflict("only uncertain work needs reconciliation")
            plan.update(state="reconciled", reconciled_at=self.clock(), reconciliation_note=request["note"],
                        costs_status="unknown-ceilings-retained-no-refund", outcome_status="unknown")
            self._save(cx, value)
            return cast(dict[str, Any], plan)

    def export(self, plan_id: str) -> dict[str, Any]:
        self.journal.verify()
        value = self._load()
        plan = value["plans"][plan_id]
        body = {"schema": "strategy-executor-evidence/v1", "journal_identity": self.journal.identity,
                "journal_record_digest": value["digest"], "source_hash": self.source_hash,
                "executor_id": self.policy.executor_id, "plan": plan, "production_authority": False,
                "cost_units": {"service_work": "declared fixed-method units", "improvement_work": "declared construction units",
                               "native_calls": "charged native invocation attempts; includes failures before solver startup", "native_solve_seconds": "charged solve allowance seconds; observed solver wall/CPU separate telemetry"},
                "limits": "Local fixed-method attribution; not independent proof, money or inherited authority."}
        body_hash = digest(body)
        import base64
        return {"body": body, "sha256": body_hash, "public_key": self.journal.public,
                "signature": base64.b64encode(self.journal.key.sign(bytes.fromhex(body_hash))).decode()}


def create_strategy_app(journal: Journal, worker: FixedWorker, policy: ExecutorPolicy,
                        *, static_files: dict[str, Path] | None = None,
                        clock: Callable[[], float] = time.time) -> FastAPI:
    """Serve only fixed strategy routes behind Alpha's existing request boundary."""
    executor = StrategyExecutor(journal, worker, policy, clock=clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.strategy_executor = executor
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    app.add_middleware(RequestBoundary)
    token = (journal.root / "api.token").read_text().strip()

    def authorize(authorization: str = Header(default="")) -> None:
        if not secrets.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
            raise HTTPException(401, "Access token required")

    @app.exception_handler(Conflict)
    async def conflict(_request: Request, _exc: Conflict) -> JSONResponse:
        return JSONResponse({"error": "Executor state conflict; inspect retained status before retrying."}, status_code=409)

    @app.exception_handler(ValueError)
    @app.exception_handler(KeyError)
    @app.exception_handler(OSError)
    async def invalid(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse({"error": "Executor input, source or evidence validation failed."}, status_code=422)

    @app.exception_handler(Exception)
    async def failure(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse({"error": "Fixed executor stopped without a committed reply; inspect retained status."}, status_code=502)

    @app.get("/api/strategy-executor/status", dependencies=[Depends(authorize)])
    def status() -> dict[str, Any]:
        return executor.status()

    @app.get("/api/strategy-executor/export/{plan_id}", dependencies=[Depends(authorize)])
    def export(plan_id: str) -> dict[str, Any]:
        return executor.export(plan_id)

    @app.post("/api/strategy-executor/{action}", dependencies=[Depends(authorize)])
    async def operate(action: str, request: Request) -> dict[str, Any]:
        document = safe_json_loads(await request.body(), max_bytes=512 * 1024)
        if not isinstance(document, dict):
            raise ValueError("executor operation must be a JSON object")
        operations: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "prepare": executor.prepare, "approve": executor.approve, "run": executor.run,
            "reconcile": executor.reconcile,
            "control": lambda value: executor.control(value["state"]) if set(value) == {"state"} else
            (_ for _ in ()).throw(ValueError("control requires only state")),
        }
        if action not in operations:
            raise ValueError("unknown fixed executor operation")
        try:
            return cast(dict[str, Any], await run_in_threadpool(operations[action], document))
        except (Conflict, ValueError, KeyError, OSError):
            raise
        except Exception:
            # A ServerErrorMiddleware handler alone still rethrows the original
            # callback exception to the ASGI server and its error log.
            raise HTTPException(502, "Fixed executor stopped without a committed reply; inspect retained status.") from None

    for route, path in (static_files or {}).items():
        if route not in {"/", "/strategy.js", "/strategy.css"} or not path.is_file() or path.is_symlink():
            raise ValueError("static assets must be fixed operator-installed files")
        def fixed_asset(current: Path) -> Callable[[], FileResponse]:
            def asset() -> FileResponse:
                return FileResponse(current)
            return asset
        app.add_api_route(route, fixed_asset(path), methods=["GET"], include_in_schema=False)
    return app
