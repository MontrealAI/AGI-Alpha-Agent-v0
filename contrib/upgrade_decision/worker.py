# SPDX-License-Identifier: Apache-2.0
"""A fixed worker component; an existing operator must separately adopt its policy."""

from __future__ import annotations

import base64
import importlib.util
import math
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .core import IDENT, MAX_PACK_BYTES, canonical, load, mission_key, sha
from .delivery import accounting, package

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "contrib/productive-capability-ledger/transport-v1/source_worker.py"
spec = importlib.util.spec_from_file_location("alpha_upgrade_source_process", BASE)
if spec is None or spec.loader is None:
    raise ValueError("existing bounded source-process transport unavailable")
source_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_worker)


BaseWorker: Any = source_worker.SourceAssuranceWorker


class UpgradeDecisionWorker(BaseWorker):  # type: ignore[misc]
    def __init__(self, registry: Path, *, python: Path, node: Path, git: Path) -> None:
        self.python, self.node, self.git = (self._executable(p) for p in (python, node, git))
        self.registry = registry.absolute()
        self.registry_bytes = source_worker._read(self.registry, 32_768)
        value = load(self.registry_bytes)
        if (
            set(value) != {"schema", "cases"}
            or value["schema"] != "alpha-upgrade-catalog/v1"
            or not isinstance(value["cases"], dict)
            or not 1 <= len(value["cases"]) <= 32
        ):
            raise ValueError("exact bounded public offering catalog required")
        self.cases = value["cases"]
        self.packs: dict[str, bytes] = {}
        self.paths: list[Path] = [self.registry]
        for ident, case in self.cases.items():
            if (
                not IDENT.fullmatch(ident)
                or not isinstance(case, dict)
                or set(case) != {"title", "pack", "sha256", "missionKey"}
            ):
                raise ValueError("invalid catalog case")
            if (
                not isinstance(case["title"], str)
                or len(case["title"]) > 200
                or not isinstance(case["pack"], str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+\.json", case["pack"])
            ):
                raise ValueError("catalog contains unsupported text or path")
            path = self.registry.parent / case["pack"]
            data = source_worker._read(path, MAX_PACK_BYTES)
            if sha(data) != case["sha256"] or load(data).get("id") != ident:
                raise ValueError("catalog source pack identity changed")
            if mission_key(load(data)) != case["missionKey"]:
                raise ValueError("catalog underlying mission identity changed")
            self.packs[ident] = data
            self.paths.append(path)
        self.paths.extend(
            [
                HERE / name
                for name in (
                    "__init__.py",
                    "core.py",
                    "component.py",
                    "export_packet.py",
                    "vendor/verify_component.py",
                    "delivery.py",
                    "worker.py",
                    "costs.mjs",
                    "offering.html",
                    "offering.css",
                    "offering.js",
                    "NOTICES.md",
                    "CAPABILITY.json",
                    "WORKLOAD.json",
                )
            ]
        )
        self.paths.extend(
            [
                BASE,
                BASE.parent / "strategy.js",
                BASE.parent / "strategy.css",
                ROOT / "examples/successor-alpha/automated-costs.mjs",
                ROOT / "examples/successor-alpha/shadow-ledger.mjs",
                ROOT / "examples/successor-alpha/fixtures/automated-costs-unknown.json",
                ROOT / "contrib/strategy_succession/transport/strategy_executor.py",
                ROOT / "alpha_factory_v1/core/runtime/store.py",
                ROOT / "alpha_factory_v1/core/runtime/api.py",
                ROOT / "alpha_factory_v1/core/runtime/successor/state.py",
                ROOT / "alpha_factory_v1/core/runtime/successor/protocol.py",
                ROOT / "alpha_factory_v1/core/runtime/successor/signatures.py",
            ]
        )
        self.identities = {str(path): sha(source_worker._read(path, 8_000_000)) for path in self.paths}

    def _sources(self) -> None:
        for path in self.paths:
            if sha(source_worker._read(path, 8_000_000)) != self.identities[str(path)]:
                raise ValueError("installed offering source, catalog or evidence changed")

    def source_record(self) -> dict[str, Any]:
        self._sources()
        files = [
            {
                "name": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
                "sha256": self.identities[str(path)],
            }
            for path in self.paths
        ]
        mapping = {"upgrade/" + str(i): self.identities[str(path)] for i, path in enumerate(self.paths)}
        return {
            "schema": "alpha-upgrade-source-record/v1",
            "adapterBase": "c4a7febc02fb9d607e9da5ece2101c4b6b36fc64",
            "writerSource": "05658097540e5b771aeae71244ab74734e10355d",
            "files": files,
            "sourceMapSha256": sha(canonical(mapping)),
            "authority": "Source identities only; no operational adoption or independent attestation.",
        }

    def prepare_input(self, case_id: str) -> dict[str, Any]:
        self._sources()
        if case_id not in self.cases:
            raise ValueError("this request is not installed in the public offering catalog")
        return {
            "schema": "alpha-upgrade-selection/v1",
            "case_id": case_id,
            "pack_sha256": self.cases[case_id]["sha256"],
        }

    def request_id(self, case_id: str) -> str:
        self.prepare_input(case_id)
        return "upgrade-" + str(self.cases[case_id]["missionKey"])[:48]

    def cancel_mission(self, payload: dict[str, Any]) -> None:
        self._selection(payload)

    def before_recovery(self, payload: dict[str, Any], checkpoint: Callable[..., None]) -> None:
        self._sources()
        self._selection(payload)
        checkpoint()

    def _selection(self, payload: dict[str, Any]) -> bytes:
        if set(payload) != {"schema", "case_id", "pack_sha256"} or payload["schema"] != "alpha-upgrade-selection/v1":
            raise ValueError("only an exact prepared public selection is supported")
        ident = payload["case_id"]
        if (
            not isinstance(ident, str)
            or ident not in self.cases
            or payload["pack_sha256"] != self.cases[ident]["sha256"]
        ):
            raise ValueError("unlisted or changed source selection")
        return self.packs[ident]

    def execute(
        self, method: str, payload: dict[str, Any], limits: dict[str, Any], checkpoint: Callable[..., None]
    ) -> dict[str, Any]:
        self._sources()
        if (
            method != "run-mission"
            or limits.get("allow_native") is not False
            or any(limits.get(k) != 0 for k in ("improvement_work", "native_calls", "native_solve_seconds"))
        ):
            raise ValueError("only this fixed inert source review is supported")
        attempts = limits.get("service_work")
        if (
            type(attempts) is not int
            or not 1 <= attempts <= 2
            or not isinstance(limits.get("source_hash"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", limits["source_hash"])
        ):
            raise ValueError("exact source-bound attempt reservation required")
        if attempts > 1:
            if limits.get("attempt_precharged") is not True or not 1 <= limits.get("attempt_number", 0) <= attempts:
                raise ValueError("the existing journal must precharge each recovery attempt")
            checkpoint()
        else:
            checkpoint(service_work=1)
        pack = load(self._selection(payload))
        started, cpu = time.perf_counter_ns(), time.process_time_ns()
        wall = limits.get("wall_seconds")
        if (
            not isinstance(wall, (float, int))
            or isinstance(wall, bool)
            or not math.isfinite(wall)
            or not 0 < wall <= 90
        ):
            raise ValueError("finite existing mission lease required")
        deadline = time.monotonic() + wall
        entry = "component.py" if pack.get("schema") == "alpha-component-delivery-input/v1" else "core.py"
        record = self._process(
            [self.python, "-I", str(HERE / entry)], pack, min(30, deadline - time.monotonic()), checkpoint
        )
        if record.get("refused"):
            return {
                "result": {
                    "refused": True,
                    "reason": record["reason"],
                    "customerAcceptance": "unknown",
                    "completeCost": "unknown",
                },
                "costs": {
                    "service_work": limits.get("attempt_number", 1),
                    "improvement_work": 0,
                    "native_calls": 0,
                    "native_solve_seconds": 0,
                    "unknown_costs": [
                        "complete currency costs",
                        "refused-attempt process resources",
                        "customer effort",
                    ],
                },
                "verified": True,
                "source_hash": limits["source_hash"],
            }
        if record.get("engineeringAcceptance") is not True:
            raise ValueError("source-contract verification failed; retain original charged attempt")
        record["implementation"] = self.source_record()
        record["implementation"]["approvedSourceHash"] = limits["source_hash"]
        cost_record, ledger = accounting(record)
        analysis = self._process(
            [self.node, str(HERE / "costs.mjs")],
            {"accounting": cost_record, "ledger": ledger},
            min(10, deadline - time.monotonic()),
            checkpoint,
        )
        bundle = package(
            record, pack, cost_record, ledger, analysis, notices=source_worker._read(HERE / "NOTICES.md", 32768)
        )
        checkpoint()
        self._sources()
        return {
            "result": {
                "schema": "alpha-upgrade-delivery/v1",
                "caseId": pack["id"],
                "missionKey": record["missionKey"],
                "nextAction": record["nextAction"],
                "selectedCalls": len(record["calls"]),
                "engineeringAcceptance": True,
                "customerAcceptance": "unknown",
                "operationalAdoption": "NOT APPROVED",
                "download": {
                    "filename": pack["id"] + ".zip",
                    "mime": "application/zip",
                    "bytes": len(bundle),
                    "sha256": sha(bundle),
                    "base64": base64.b64encode(bundle).decode("ascii"),
                },
                "costSummary": analysis,
                "observations": {
                    "parentCpuNs": time.process_time_ns() - cpu,
                    "elapsedNs": time.perf_counter_ns() - started,
                    "basis": "measured",
                    "scope": "Fixed worker child wait, canonical accounting, rendering and ZIP assembly; parent CPU excludes child CPU, which is separately recorded for core stages. Transport/journal/customer effort and final delivery are unknown, not zero.",
                },
            },
            "costs": {
                "service_work": limits.get("attempt_number", 1),
                "improvement_work": 0,
                "native_calls": 0,
                "native_solve_seconds": 0,
                "unknown_costs": [
                    "complete marginal, recurring and fully loaded currency costs",
                    "authoring and integration",
                    "setup/upkeep",
                    "customer effort",
                    "interrupted attempts' unobserved resources",
                ],
            },
            "verified": True,
            "source_hash": limits["source_hash"],
        }


def source_inventory(worker: UpgradeDecisionWorker) -> tuple[Any, ...]:
    transport = source_worker.load_transport()
    return tuple(
        transport.SourceFile("upgrade/" + str(i), path, worker.identities[str(path)])
        for i, path in enumerate(worker.paths)
    )


def create_app(journal: Any, worker: UpgradeDecisionWorker, policy: Any) -> Any:
    """Accept an explicitly supplied policy; do not install or widen one."""
    transport = source_worker.load_transport()
    required = {(str(path), digest) for path, digest in ((s.path, s.sha256) for s in source_inventory(worker))}
    actual = {(str(s.path), s.sha256) for s in policy.sources}
    if (
        not required <= actual
        or set(policy.methods) != {"run-mission"}
        or policy.allow_native
        or policy.recovery_attempts not in (0, 2)
    ):
        raise ValueError("this component requires separate exact-source, pure-work policy adoption")
    cap = policy.methods["run-mission"]
    if cap.service_work != (policy.recovery_attempts or 1) or any(
        getattr(cap, name) != 0 for name in ("improvement_work", "native_calls", "native_solve_seconds")
    ):
        raise ValueError("offering may not borrow construction/native allowance")
    page = source_worker._read(HERE / "offering.html", 32768).decode()
    menu = re.search(r'<script id="offering-catalog" type="application/json">(.*?)</script>', page, re.DOTALL)
    if menu is None or load(menu[1].encode()) != load(worker.registry_bytes):
        raise ValueError("the reviewed interface catalog must match the adopted registry")
    app = transport.create_strategy_app(
        journal,
        worker,
        policy,
        static_files={
            "/": HERE / "offering.html",
            "/strategy.js": HERE / "offering.js",
            "/strategy.css": HERE / "offering.css",
        },
    )
    return app
