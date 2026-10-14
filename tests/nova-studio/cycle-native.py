# SPDX-License-Identifier: Apache-2.0
"""Test-only local actors around production Studio/runtime APIs, with read-only EVM RPC."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.ascension import MarketContext, MarketReader, list_settlements
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher
from alpha_factory_v1.core.runtime.successor.protocol import (
    ExecutionAuthorization,
    Family,
    Institution,
    JobContract,
    JobGraph,
    MissionConstitution,
    digest,
)
from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import (
    TrustAnchor,
    TrustRegistry,
    retained_local_principals,
    sign_record,
)
from alpha_factory_v1.core.runtime.successor.workbench import invoke

FAMILIES: list[Family] = ["constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal"]
FUTURE = "2099-01-01T00:00:00Z"


def rpc(method: str, params: list[Any]) -> object:
    print(json.dumps({"rpc": method, "params": params}), flush=True)
    response = json.loads(sys.stdin.readline())
    if "error" in response:
        raise ValueError(response["error"])
    return response["result"]


def local_store(home: Path, worker: str) -> tuple[SuccessorStore, dict[str, Ed25519PrivateKey]]:
    journal = Journal(home) if home.exists() else Journal.initialize(home)
    _, keys = retained_local_principals(home / "cycle-local-fixture-principals")
    roles = {
        "local-controller": {"controller", "admission", "authority", "acceptance", "control", "worker"},
        "local-producer": {"producer", "worker"},
        "local-verifier": {"verifier", "acceptance", "worker"},
    }
    anchors = {
        principal: TrustAnchor(
            keys[principal].public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset(allowed)
        )
        for principal, allowed in roles.items()
    }
    anchors[worker.lower()] = TrustAnchor(
        keys["local-producer"].public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"worker"})
    )
    return SuccessorStore(journal, TrustRegistry(anchors)), keys


def main(source: dict[str, Any]) -> dict[str, Any]:
    from alpha_factory_v1.core.runtime.successor.studio import (
        bind_work,
        acceptance_request,
        accept_work,
        execute_work,
        freeze_evaluation,
        evaluate_work,
        prepare_work,
        seal_work,
        settle_work,
    )

    operation = source["operation"]
    if operation == "example":
        return invoke({"operation": "example", "family": "numerical"})
    request = source["request"]
    identity = request["cycle_id"] + "-" + str(request["plan_index"])
    institution_id, mission_id = "cycle-" + identity, "mission-" + identity
    store, keys = local_store(Path(source["home"]), source["worker"])
    reader = MarketReader(MarketContext.model_validate(source["context"]), rpc)
    if operation == "freeze-evaluation":
        return freeze_evaluation(
            store.journal,
            source["baseline_request"],
            source["baseline_result"],
            request,
            evaluation_id=source["evaluation_id"],
        )
    if operation == "evaluate-comparison":
        return evaluate_work(
            store.journal,
            source["freeze"],
            source["baseline_request"],
            source["baseline_result"],
            request,
            source["result"],
        )
    prepared = prepare_work(
        request,
        institution_id=institution_id,
        mission_id=mission_id,
        producer="local-producer",
        acceptance_owner="local-controller",
        valid_until=FUTURE,
    )
    if operation == "seal":
        institution = Institution(
            id=institution_id,
            controller="local-controller",
            constitution=MissionConstitution(
                mission_id=mission_id,
                owner="local-controller",
                objective=request["plan"]["jobs"][request["plan_index"]]["spec"]["goal"],
                scope="disposable local acceptance; fixture actors are not independent reviewers",
                prohibited_actions=["wallet", "network", "paid-provider", "production-admission"],
                authority_ceiling="sandbox",
            ),
        )
        try:
            store.read(institution_id)
        except KeyError:
            store.create_institution(institution, {"calls": 1})
        terms = JobContract.model_validate(prepared["job_contract"])
        jobs = [terms] + [
            JobContract(
                job_id="local-unexecuted-" + family,
                institution_id=institution_id,
                mission_id=mission_id,
                family=family,
                worker=None,
                acceptance_owner="local-controller",
                release_digest=terms.release_digest,
                environment_digest=terms.environment_digest,
                resources={"calls": 1},
                allowed_tools=["fixed-workbench"],
                valid_until=FUTURE,
            )
            for family in FAMILIES
            if family != terms.family
        ]
        graph = JobGraph(jobs=jobs, edges=[], required_families=FAMILIES, required_functions=[])
        sealed = seal_work(store, request, reader, prepared=prepared, graph=graph)
        return {"prepared": prepared, "seal": sealed, "source_public_key": store.journal.public}
    if operation == "bind":
        terms = JobContract.model_validate(prepared["job_contract"])
        authorization = ExecutionAuthorization(
            authorization_id="authority-" + identity,
            acting_identity=source["worker"].lower(),
            job_terms_digest=digest("job-terms", terms),
            release_digest=terms.release_digest,
            environment_digest=terms.environment_digest,
            capabilities=["fixed-workbench"],
            reservation_id="reservation-" + identity,
            expires_at=source["expires_at"],
        )
        binding = bind_work(
            store.journal,
            request,
            source["seal"],
            reader,
            market_job_id=source["job_id"],
            posting_tx=source["posting_tx"],
            assignment_tx=source["assignment_tx"],
            execution_authorization=authorization.model_dump(mode="json"),
        )
        return {"binding": binding, "proposed_authorization": authorization.model_dump(mode="json")}
    if operation in {"execute", "execute_without_grant", "execute_with_changed_inputs", "execute_revoked"}:
        authorization = ExecutionAuthorization.model_validate(
            {**source["proposed_authorization"], "market_binding_digest": source["binding"]["digest"]}
        )
        signer = "local-producer" if operation == "execute_without_grant" else "local-controller"
        envelope = sign_record(keys[signer], signer, "execution", authorization)
        if operation == "execute_revoked":
            store.trust.revoke("local-controller")
        dispatcher = JobDispatcher(store, institution_id, market_public_key=store.journal.public)
        return execute_work(dispatcher, request, source["seal"], source["binding"], envelope)
    if operation == "accept":
        proposed = acceptance_request(request, source["result"], public_key=store.journal.public)
        before = store.read(institution_id)["resources"]
        dispatcher = JobDispatcher(store, institution_id, market_public_key=store.journal.public)
        decision = sign_record(keys["local-controller"], "local-controller", "job-acceptance", proposed)
        accepted = accept_work(dispatcher, request, source["result"], decision)
        assert accept_work(dispatcher, request, source["result"], decision) == accepted
        return {
            "before": before,
            "after": store.read(institution_id)["resources"],
            "decision": decision.model_dump(mode="json"),
        }
    if operation == "settle":
        settlement = settle_work(
            store.journal, request, source["result"], reader, settlement_tx=source["settlement_tx"]
        )
        records = list_settlements(store.journal, institution_id)
        record = next(record for record in records if record["settlement"] == settlement)
        return {"settlement": settlement, "record": record}
    if operation == "inspect":
        return {"journal": store.journal.verify(), "institution": store.read(institution_id)}
    raise ValueError("Unknown test bridge operation")


if __name__ == "__main__":
    try:
        print(json.dumps({"result": main(json.loads(sys.stdin.readline()))}), flush=True)
    except Exception as error:
        print(json.dumps({"error": type(error).__name__ + ": " + str(error)}), flush=True)
        raise
