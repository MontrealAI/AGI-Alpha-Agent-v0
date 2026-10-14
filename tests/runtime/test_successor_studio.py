# SPDX-License-Identifier: Apache-2.0
"""Real bounded native work with explicitly synthetic RPC observations."""

from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from test_successor_ascension import AWARD_TX, CLOSE_TX, POST_TX, SPEC, WORKER, UnitRPC, words

from alpha_factory_v1.core.runtime import ascension as legacy
from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import ascension, studio, workbench
from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher
from alpha_factory_v1.core.runtime.successor.protocol import (
    ExecutionAuthorization,
    Institution,
    JobContract,
    JobGraph,
    MissionConstitution,
    canonical,
    digest,
)
from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, local_principals, sign_record

MARK, SEED = "0x" + "77" * 20, "0x" + "88" * 20
PROJECT = "7b527dd7-8548-4504-93d0-2d98b29e79f0"
CYCLE = "52b295a8-0788-4b3a-bd8f-10a779dd253b"


class StudioRPC(UnitRPC):
    """Unit-only MARK/seed observations; these are not real-chain settlement evidence."""

    def __init__(self, plan: dict[str, Any], index: int) -> None:
        super().__init__()
        self.plan, self.index = plan, index
        code_hash = "0x" + legacy.keccak(b"\x01").hex()
        self.context = self.context.model_copy(
            update={
                "mark": MARK,
                "mark_code_hash": code_hash,
                "seed": SEED,
                "seed_code_hash": code_hash,
                "seed_id": "1",
            }
        )
        route = self.event(
            POST_TX, 2, "MissionRouted(uint256,uint32,uint256,bytes32)", ascension.indexed_leaf(index, SPEC)
        )
        route["address"] = MARK
        route["topics"] += [words(index), words(1)]
        self.events[POST_TX].append(route)

    def __call__(self, method: str, params: list[Any]) -> Any:
        if method == "eth_call":
            selector = params[0]["data"][2:10]
            values = {
                "mark()": words(MARK),
                "jobs()": words(self.context.market),
                "seed()": words(SEED),
                "plan(uint256)": words(self.plan["planRoot"], len(self.plan["jobs"])),
                "jobSeed(uint256)": words(1),
            }
            for name, value in values.items():
                if legacy.keccak(name.encode())[:4].hex() == selector:
                    return value
            result = super().__call__(method, params)
            if selector == legacy.keccak(b"jobs(uint256)")[:4].hex():
                return words(MARK) + result[66:]
            return result
        return super().__call__(method, params)


def request(*, negative: bool = True) -> dict[str, Any]:
    spec = workbench.invoke({"operation": "example", "family": "numerical"})
    if negative:
        spec["inputs"].update(coefficients=[0, 0, 0, 0, 1], steps=2, tolerancePpm=0)
    return {
        "schema": studio.REQUEST_SCHEMA,
        "project_id": PROJECT,
        "cycle_id": CYCLE,
        "plan": legacy.compile_plan([SPEC, SPEC]),
        "plan_index": 1,
        "work_spec": spec,
    }


def prepared_runtime(tmp_path: Path, *, negative: bool = True) -> tuple[Any, ...]:
    incoming = request(negative=negative)
    proposed = studio.prepare_work(
        incoming,
        institution_id="institution",
        mission_id="mission",
        producer="local-producer",
        acceptance_owner="local-controller",
        valid_until="2099-01-01T00:00:00Z",
    )
    trust, keys = local_principals()
    anchors = dict(trust._anchors)
    anchors[WORKER] = TrustAnchor(
        keys["local-producer"].public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"worker"})
    )
    store = SuccessorStore(Journal.initialize(tmp_path / "home"), TrustRegistry(anchors))
    store.create_institution(
        Institution(
            id="institution",
            controller="local-controller",
            constitution=MissionConstitution(
                mission_id="mission", owner="local-controller", objective="Inspect a numerical report"
            ),
        ),
        {"calls": 10},
    )
    terms = JobContract.model_validate(proposed["job_contract"])
    graph = JobGraph(
        jobs=[terms]
        + [
            terms.model_copy(update={"job_id": "companion-" + family, "family": family})
            for family in ("constitution", "evidence", "formation", "challenge", "admission", "renewal")
        ]
    )
    rpc = StudioRPC(incoming["plan"], incoming["plan_index"])
    reader = ascension.MarketReader(rpc.context, rpc)
    seal = studio.seal_work(store, incoming, reader, proposed, graph)
    rpc.height = 3
    unsigned = ExecutionAuthorization(
        authorization_id="studio-test",
        acting_identity=WORKER,
        job_terms_digest=digest("job-terms", terms),
        release_digest=terms.release_digest,
        environment_digest=terms.environment_digest,
        capabilities=[studio.TOOL],
        reservation_id="studio-resource",
        expires_at="2098-01-01T00:00:00Z",
    )
    binding = studio.bind_work(
        store.journal,
        incoming,
        seal,
        reader,
        market_job_id="1",
        posting_tx=POST_TX,
        assignment_tx=AWARD_TX,
        execution_authorization=unsigned.model_dump(mode="json"),
    )
    auth = unsigned.model_copy(update={"market_binding_digest": binding["digest"]})
    authorization = sign_record(keys["local-controller"], "local-controller", "execution", auth)
    dispatcher = JobDispatcher(store, "institution")
    return incoming, proposed, store, keys, rpc, reader, seal, binding, authorization, dispatcher


@pytest.mark.parametrize("negative", [True, False])
def test_actual_work_keccak_sha_paid_verdict_and_explicit_runtime_acceptance(tmp_path: Path, negative: bool) -> None:
    incoming, _, store, keys, rpc, reader, seal, binding, authorization, dispatcher = prepared_runtime(
        tmp_path, negative=negative
    )
    result = studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    assert result["candidate_verdict"] == ("FAIL" if negative else "PASS")
    assert result["artifact_sha256"] != result["artifact_keccak256"]
    assert seal["body"]["plan_binding"]["indexed_leaf"] != seal["body"]["market_spec_hash"]
    assert result["authority_status"] == "not_granted"
    assert (
        studio.verify_work_result(incoming, result, public_key=store.journal.public)["authentication"]
        == "configured-operator"
    )
    assert studio.execute_work(dispatcher, incoming, seal, binding, authorization) == result
    rpc.artifact_hash = result["artifact_keccak256"]
    rpc.close("paid")
    rpc.height = 4
    settled = studio.settle_work(store.journal, incoming, result, reader, settlement_tx=CLOSE_TX)
    assert settled["job_acceptance"] == "accepted"
    assert settled["settlement_status"] == "paid"
    assert settled["candidate_verdict"] == result["candidate_verdict"]
    assert studio.settle_work(store.journal, incoming, result, reader, settlement_tx=CLOSE_TX) == settled
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    owner_decision = studio.acceptance_request(incoming, result, public_key=store.journal.public)
    envelope = sign_record(keys["local-controller"], "local-controller", "job-acceptance", owner_decision)
    completed = studio.accept_work(dispatcher, incoming, result, envelope)
    assert studio.accept_work(dispatcher, incoming, result, envelope) == completed
    state = store.read("institution")
    assert state["resources"]["reserved"] == {"calls": 0}
    assert state["resources"]["spent"] == {"calls": 1}
    assert not state["grants"] and not state["admissions"] and state["serving_release"] is None


def test_request_and_result_tamper_refused_and_history_survives_authority_revocation(tmp_path: Path) -> None:
    incoming, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    changed = deepcopy(incoming)
    changed["work_spec"]["inputs"]["steps"] = 4
    with pytest.raises(ValueError, match="another exact Studio request"):
        studio.execute_work(dispatcher, changed, seal, binding, authorization)
    result = studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    for field, value in (
        ("artifact_utf8", result["artifact_utf8"] + " "),
        ("artifact_keccak256", result["artifact_sha256"]),
        ("cycle_id", PROJECT),
        ("candidate_verdict", "PASS"),
    ):
        broken = {**result, field: value}
        with pytest.raises(ValueError):
            studio.verify_work_result(incoming, broken, public_key=store.journal.public)
    store.trust.revoke("local-controller")
    with pytest.raises(ValueError, match="not currently trusted"):
        studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    assert studio.retained_work(store.journal, incoming, binding["digest"]) == result


def test_revoke_during_real_work_suppresses_delivery_and_blocks_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    incoming, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    original = workbench.invoke

    def revoke(value: dict[str, Any], checkpoint: Any = lambda: None) -> dict[str, Any]:
        if value.get("operation") == "run":
            store.trust.revoke("local-controller")
        return original(value, checkpoint)

    monkeypatch.setattr(workbench, "invoke", revoke)
    with pytest.raises(ValueError, match="bounded job tool failed"):
        studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    record = store.journal.latest("@successor:studio:execution:" + binding["digest"])
    assert record["state"] == "interrupted" and "result" not in record
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}
    with pytest.raises(Conflict, match="No completed"):
        studio.retained_work(store.journal, incoming, binding["digest"])


def test_installed_release_change_or_forged_acceptance_never_reaches_new_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    incoming, _, store, keys, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    environment = studio.installed_environment()
    with monkeypatch.context() as changed:
        changed.setattr(studio, "installed_environment", lambda: {**environment, "node": "v99.0.0"})
        with pytest.raises(ValueError, match="environment changed"):
            studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    result = studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    decision = studio.acceptance_request(incoming, result, public_key=store.journal.public)
    decision["output_digest"] = "a" * 64
    forged = sign_record(keys["local-controller"], "local-controller", "job-acceptance", decision)
    with pytest.raises(ValueError, match="exact delivered artifact"):
        studio.accept_work(dispatcher, incoming, result, forged)
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}


def test_hostile_work_and_endpoint_fields_are_rejected_before_preparation() -> None:
    incoming = request()
    with pytest.raises(ValueError, match="unexpected fields"):
        studio.validate_request({**incoming, "rpc_url": "http://127.0.0.1/private"})
    with pytest.raises(ValueError, match="exact existing plan index"):
        studio.validate_request({**incoming, "plan_index": True})
    incoming["work_spec"]["inputs"]["command"] = "echo forbidden"
    with pytest.raises(ValueError):
        studio.prepare_work(
            incoming,
            institution_id="institution",
            mission_id="mission",
            producer="producer",
            acceptance_owner="reviewer",
            valid_until="2099-01-01T00:00:00Z",
        )
    assert b"command" in canonical(incoming)


def test_fresh_controller_actor_and_authorization_binding_required_before_effect(tmp_path: Path) -> None:
    incoming, _, store, keys, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    for changes in (
        {"acting_identity": "local-producer"},
        {"expires_at": "2020-01-01T00:00:00Z"},
        {"environment_digest": "f" * 64},
        {"market_binding_digest": "f" * 64},
    ):
        tampered = sign_record(
            keys["local-controller"], "local-controller", "execution", {**authorization.payload, **changes}
        )
        with pytest.raises(ValueError):
            studio.execute_work(dispatcher, incoming, seal, binding, tampered)
    spoof = sign_record(keys["local-producer"], "local-producer", "execution", authorization.payload)
    with pytest.raises(ValueError, match="not currently trusted"):
        studio.execute_work(dispatcher, incoming, seal, binding, spoof)
    assert store.read("institution")["resources"]["reserved"] == {}


def test_concurrent_dispatch_invokes_actual_work_only_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    incoming, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    original, executions = workbench.invoke, []

    def counted(value: dict[str, Any], checkpoint: Any = lambda: None) -> dict[str, Any]:
        if value.get("operation") == "run":
            executions.append(value["spec"])
        return original(value, checkpoint)

    monkeypatch.setattr(workbench, "invoke", counted)
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [
            pool.submit(studio.execute_work, dispatcher, incoming, seal, binding, authorization) for _ in range(2)
        ]
        results = []
        for attempt in attempts:
            try:
                results.append(attempt.result())
            except Conflict:
                pass
    assert results and len(executions) == 1
    assert all(result == results[0] for result in results)
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}


def evaluation_runtime(store: SuccessorStore, keys: dict[str, Any], incoming: dict[str, Any]) -> tuple[Any, ...]:
    proposed = studio.prepare_work(
        incoming,
        institution_id="evaluation",
        mission_id="fresh-common-inputs",
        producer="local-producer",
        acceptance_owner="local-controller",
        valid_until="2099-01-01T00:00:00Z",
    )
    store.create_institution(
        Institution(
            id="evaluation",
            controller="local-controller",
            constitution=MissionConstitution(
                mission_id="fresh-common-inputs",
                owner="local-controller",
                objective="Compare declared methods on fresh common inputs",
            ),
        ),
        {"calls": 1},
    )
    terms = JobContract.model_validate(proposed["job_contract"])
    graph = JobGraph(
        jobs=[terms]
        + [
            terms.model_copy(update={"job_id": "comparison-" + family, "family": family})
            for family in ("constitution", "evidence", "formation", "challenge", "admission", "renewal")
        ]
    )
    rpc = StudioRPC(incoming["plan"], incoming["plan_index"])
    market = "0x" + "99" * 20
    for logs in rpc.events.values():
        for event in logs:
            if event["address"] == rpc.context.market:
                event["address"] = market
    rpc.context = rpc.context.model_copy(update={"market": market})
    reader = ascension.MarketReader(rpc.context, rpc)
    seal = studio.seal_work(store, incoming, reader, proposed, graph)
    rpc.height = 3
    unsigned = ExecutionAuthorization(
        authorization_id="fresh-comparison",
        acting_identity=WORKER,
        job_terms_digest=digest("job-terms", terms),
        release_digest=terms.release_digest,
        environment_digest=terms.environment_digest,
        capabilities=[studio.TOOL],
        reservation_id="comparison-resource",
        expires_at="2098-01-01T00:00:00Z",
    )
    binding = studio.bind_work(
        store.journal,
        incoming,
        seal,
        reader,
        market_job_id="1",
        posting_tx=POST_TX,
        assignment_tx=AWARD_TX,
        execution_authorization=unsigned.model_dump(mode="json"),
    )
    authorization = sign_record(
        keys["local-controller"],
        "local-controller",
        "execution",
        unsigned.model_copy(update={"market_binding_digest": binding["digest"]}),
    )
    return JobDispatcher(store, "evaluation"), seal, binding, authorization


@pytest.mark.parametrize("positive", [True, False])
def test_frozen_comparison_actual_common_inputs_and_negative_retention(tmp_path: Path, positive: bool) -> None:
    incoming, _, store, keys, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    baseline = studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    fresh = request(negative=not positive)
    fresh["plan_index"] = 0
    fresh["work_spec"]["inputs"]["upper"] = 2
    evaluation = studio.freeze_evaluation(
        store.journal, incoming, baseline, fresh, evaluation_id="53e9f622-4487-4440-9c05-8fb2544c79a7"
    )
    second, sealed, bound, authorized = evaluation_runtime(store, keys, fresh)
    computed = studio.execute_work(second, fresh, sealed, bound, authorized)
    report = studio.evaluate_work(store.journal, evaluation, incoming, baseline, fresh, computed)
    assert report["body"]["outcome"] == ("PASS" if positive else "FAIL")
    assert report["body"]["admission"] == "HOLD"
    assert report["body"]["authority_status"] == "not_granted"
    assert report["body"]["baseline_artifact_keccak256"] == baseline["artifact_keccak256"]
    assert report["body"]["evaluated_artifact_keccak256"] == computed["artifact_keccak256"]
    assert studio.evaluate_work(store.journal, evaluation, incoming, baseline, fresh, computed) == report
    with pytest.raises(Conflict, match="before the fresh execution"):
        studio.freeze_evaluation(
            store.journal, incoming, baseline, fresh, evaluation_id="25f3b76b-6adc-4d2e-a6d9-5cc6c85bb49d"
        )
    changed = deepcopy(fresh)
    changed["work_spec"]["inputs"]["tolerancePpm"] += 1
    with pytest.raises(ValueError):
        studio.evaluate_work(store.journal, evaluation, incoming, baseline, changed, computed)
    assert store.read("evaluation")["serving_release"] is None


def test_comparison_rejects_renaming_and_operator_revocation_checkpoint(tmp_path: Path) -> None:
    incoming, _, store, _, _, _, seal, binding, authorization, dispatcher = prepared_runtime(tmp_path)
    result = studio.execute_work(dispatcher, incoming, seal, binding, authorization)
    changed = deepcopy(incoming)
    changed["work_spec"]["name"] = "Renamed output"
    changed["work_spec"]["inputs"]["steps"] = 128
    with pytest.raises(ValueError, match="distinct polynomial or domain"):
        studio.freeze_evaluation(
            store.journal, incoming, result, changed, evaluation_id="b3526572-44e7-4b04-88ec-a4cb859a60a4"
        )
    other = prepared_runtime(tmp_path / "another")
    request2, _, store2, _, _, _, seal2, binding2, authorization2, dispatcher2 = other

    def changed_config() -> None:
        raise Conflict("operator configuration revoked")

    with pytest.raises(Conflict, match="configuration revoked"):
        studio.execute_work(dispatcher2, request2, seal2, binding2, authorization2, operator_checkpoint=changed_config)
    assert store2.read("institution")["resources"]["reserved"] == {}
