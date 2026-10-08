# SPDX-License-Identifier: Apache-2.0
"""Exact adapter adversarial tests; RPC doubles are unit fixtures, never settlement evidence."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime import ascension as legacy
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import ascension as adapter
from alpha_factory_v1.core.runtime.successor.protocol import ExecutionAuthorization, JobContract, digest

MARKET = "0x" + "11" * 20
WORKER = "0x" + "22" * 20
BUSINESS = "0x" + "33" * 20
VALIDATORS = ["0x" + value * 20 for value in ("44", "55", "66")]
POST_TX, AWARD_TX, CLOSE_TX = ["0x" + value * 32 for value in ("aa", "bb", "cc")]
SPEC = {
    "goal": "Evaluate exact report",
    "successMetric": "Accept correct negative results",
    "bounty": "10103",
    "duration": 86400,
    "priceWeight": 6000,
}
ARTIFACT = b'{"candidate_verdict":"FAIL","correctness_failures":1,"report_correct":true}'


def words(*values: int | str) -> str:
    return "0x" + "".join(
        (int(value, 16) if isinstance(value, str) else value).to_bytes(32, "big").hex() for value in values
    )


def job_contract(**changes: Any) -> JobContract:
    return JobContract.model_validate(
        {
            "job_id": "evaluation",
            "institution_id": "institution",
            "mission_id": "mission",
            "family": "verification",
            "goal": SPEC["goal"],
            "worker": None,
            "acceptance_owner": "operator",
            "release_digest": "a" * 64,
            "environment_digest": "b" * 64,
            "valid_until": "2099-01-01T00:00:00Z",
            "resources": {"calls": 1},
            **changes,
        }
    )


def authorization(seal: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return ExecutionAuthorization.model_validate(
        {
            "authorization_id": "execution-1",
            "acting_identity": WORKER,
            "job_terms_digest": seal["body"]["job_terms_digest"],
            "release_digest": "a" * 64,
            "environment_digest": "b" * 64,
            "reservation_id": "reserved-1",
            "expires_at": "2098-01-01T00:00:00Z",
            "capabilities": ["evaluate"],
            **changes,
        }
    ).model_dump(mode="json")


class UnitRPC:
    """Explicit deterministic RPC double for boundary tests, never real chain evidence."""

    def __init__(self) -> None:
        self.height = 1
        self.chain = 31337
        self.state = 2
        self.yes, self.no = 2, 0
        self.block_hashes = {number: "0x" + f"{number:064x}" for number in range(1, 6)}
        self.artifact_hash = "0x" + legacy.keccak(ARTIFACT).hex()
        self.context = adapter.MarketContext(
            chain_id=str(self.chain),
            market=MARKET,
            market_code_hash="0x" + legacy.keccak(b"\x01").hex(),
            token_code_hash="0x" + legacy.keccak(b"\x01").hex(),
            scope="disposable-local-fixture",
            confirmations=1,
        )
        self.events: dict[str, list[dict[str, Any]]] = {
            POST_TX: [
                self.event(
                    POST_TX, 2, "JobPosted(uint256,address,bytes32,string,string,uint96,uint64,uint64)", "0x", BUSINESS
                )
            ],
            AWARD_TX: [
                self.event(AWARD_TX, 3, "Assigned(uint256,address,uint96,uint64)", words(8001, 4099680000), WORKER)
            ],
        }
        self.close("paid")
        self.state = 2

    def event(self, tx: str, block: int, signature: str, data: str, recipient: str | None = None) -> dict[str, Any]:
        topics = ["0x" + legacy.keccak(signature.encode()).hex(), words(1)]
        if recipient:
            topics.append(words(recipient))
        return {
            "address": MARKET,
            "topics": topics,
            "data": data,
            "transactionHash": tx,
            "blockHash": self.block_hashes[block],
            "blockNumber": hex(block),
            "logIndex": "0x0",
            "removed": False,
        }

    def close(self, status: str) -> None:
        if status == "paid":
            self.state, self.yes, self.no, refund = 4, 2, 0, 10103 - 8001
            values = adapter.payout_breakdown(8001, 10103)
            payouts = [
                self.event(CLOSE_TX, 4, "Payout(uint256,address,uint256,uint256)", words(gross, burned), who)
                for who, gross, burned in zip([WORKER, *VALIDATORS[:2]], values["gross"], values["burned"], strict=True)
            ]
        elif status == "refunded":
            self.state, self.yes, self.no, refund, payouts = 6, 1, 0, 10103, []
        else:
            self.state, self.yes, self.no, refund = 5, 0, 2, 10103 + 1000 - 10
            payouts = [self.event(CLOSE_TX, 4, "Payout(uint256,address,uint256,uint256)", words(1000, 10), BUSINESS)]
        self.refund = refund
        reviews = [
            self.event(
                CLOSE_TX,
                4,
                "Validated(uint256,address,bool,bytes32,bytes32)",
                words(int(status != "failed"), self.artifact_hash, "0x" + "de" * 32),
                who,
            )
            for who in VALIDATORS[: self.yes + self.no]
        ]
        self.events[CLOSE_TX] = (
            reviews + payouts + [self.event(CLOSE_TX, 4, "Closed(uint256,uint8,uint256)", words(self.state, refund))]
        )

    def __call__(self, method: str, params: list[Any]) -> Any:
        if method == "eth_getLogs":
            return [event for event in self.events[CLOSE_TX] if event["topics"][0] == params[0]["topics"][0]]
        if method == "eth_chainId":
            return hex(self.chain)
        if method == "eth_getCode":
            return "0x01"
        if method == "eth_getBlockByNumber":
            number = self.height if params[0] == "latest" else int(params[0], 16)
            return {"number": hex(number), "hash": self.block_hashes[number], "timestamp": "0x70000000"}
        if method == "eth_getTransactionReceipt":
            tx = params[0]
            block = {POST_TX: 2, AWARD_TX: 3, CLOSE_TX: 4}[tx]
            return {
                "status": "0x1",
                "transactionHash": tx,
                "blockNumber": hex(block),
                "blockHash": self.block_hashes[block],
                "logs": self.events[tx],
            }
        if method == "eth_call":
            call = params[0]["data"]
            selector, arguments = call[2:10], call[10:]

            def match(name: str) -> bool:
                return legacy.keccak(name.encode())[:4].hex() == selector

            if match("decimals()"):
                return words(18)
            if match("token()"):
                return words(adapter.TOKEN)
            if match("nextId()"):
                return words(0 if self.height == 1 else 1)
            if match("jobs(uint256)"):
                state = self.state if int(params[1], 16) >= 4 else 2
                return words(
                    BUSINESS,
                    BUSINESS,
                    WORKER,
                    10103,
                    8001,
                    1000,
                    5,
                    100,
                    200,
                    4099680000,
                    86400,
                    6000,
                    self.yes if state >= 4 else 0,
                    self.no if state >= 4 else 0,
                    state,
                    adapter.market_spec_hash(SPEC),
                    self.artifact_hash if state >= 4 else adapter.ZERO_HASH,
                    self.refund if state >= 4 else 0,
                    0,
                )
            if match("committees(uint256,uint256)"):
                return words(VALIDATORS[int(arguments[64:], 16)])
            if match("votes(uint256,address)"):
                return words(1 if "0x" + arguments[-40:] in VALIDATORS[:2] else 0)
        raise AssertionError((method, params))


def prepared(tmp_path: Path) -> tuple[Journal, UnitRPC, dict[str, Any], dict[str, Any]]:
    journal = Journal.initialize(tmp_path / "journal")
    rpc = UnitRPC()
    reader = adapter.MarketReader(rpc.context, rpc)
    seal = adapter.seal_terms(journal, job_contract(), SPEC, reader)
    rpc.height = 3
    binding = adapter.bind_assignment(
        journal,
        seal,
        reader,
        market_job_id="1",
        posting_tx=POST_TX,
        assignment_tx=AWARD_TX,
        execution_authorization=authorization(seal),
    )
    delivery = adapter.bind_delivery(journal, binding, ARTIFACT, candidate_verdict="FAIL")
    return journal, rpc, binding, delivery


@pytest.mark.parametrize("index", [-1, 2**32, True, 1.0, "1"])
def test_index_must_fit_uint32_without_coercion(index: Any) -> None:
    with pytest.raises(ValueError):
        adapter.indexed_leaf(index, SPEC)


def test_identical_specs_at_nonzero_index_keep_market_and_plan_commitments_distinct() -> None:
    plan = legacy.compile_plan([SPEC, SPEC, SPEC])
    assert len({job["leaf"] for job in plan["jobs"]}) == 3
    assert adapter.market_spec_hash(SPEC) == plan["jobs"][0]["leaf"]
    assert adapter.indexed_leaf(2, SPEC) == plan["jobs"][2]["leaf"] != adapter.market_spec_hash(SPEC)
    assert adapter.indexed_leaf(2**32 - 1, SPEC).startswith("0x")


def test_seal_freezes_richer_terms_even_when_legacy_spec_is_unchanged(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "journal")
    rpc = UnitRPC()
    reader = adapter.MarketReader(rpc.context, rpc)
    contract = job_contract()
    seal = adapter.seal_terms(journal, contract, SPEC, reader)
    assert adapter.seal_terms(journal, contract, SPEC, reader) == seal
    assert seal["body"]["market_job_id"] is None
    assert seal["body"]["assigned_worker"] is None
    assert seal["body"]["job_terms_digest"] == digest("job-terms", contract)
    with pytest.raises(ValueError, match="already sealed"):
        adapter.seal_terms(journal, job_contract(resources={"calls": 999}), SPEC, reader)


@pytest.mark.parametrize(
    "change",
    [
        {"acting_identity": BUSINESS},
        {"release_digest": "c" * 64},
        {"environment_digest": "c" * 64},
        {"job_terms_digest": "d" * 64},
        {"expires_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_assignment_requires_exact_worker_terms_release_environment_and_expiry(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    journal = Journal.initialize(tmp_path / "journal")
    rpc = UnitRPC()
    reader = adapter.MarketReader(rpc.context, rpc)
    seal = adapter.seal_terms(journal, job_contract(), SPEC, reader)
    rpc.height = 3
    with pytest.raises(ValueError):
        adapter.bind_assignment(
            journal,
            seal,
            reader,
            market_job_id="1",
            posting_tx=POST_TX,
            assignment_tx=AWARD_TX,
            execution_authorization=authorization(seal, **change),
        )


def test_negative_report_acceptance_and_concurrent_import_do_not_admit_candidate(tmp_path: Path) -> None:
    journal, rpc, binding, delivery = prepared(tmp_path)
    rpc.height = 4
    rpc.close("paid")

    def imported() -> dict[str, Any]:
        return adapter.import_settlement(
            journal, binding, delivery, ARTIFACT, adapter.MarketReader(rpc.context, rpc), settlement_tx=CLOSE_TX
        )

    with ThreadPoolExecutor(max_workers=4) as workers:
        records = list(workers.map(lambda _: imported(), range(8)))
    assert all(record == records[0] for record in records)
    result = records[0]
    assert result["job_acceptance"] == "accepted" and result["settlement_status"] == "paid"
    assert result["candidate_verdict"] == "FAIL"
    assert (
        result["institutional_admission"] == result["authority_status"] == result["memory_admission"] == "not_granted"
    )
    assert result["customer_realized_value"] is None
    with journal.transaction() as cx:
        assert (
            cx.execute("SELECT count(*) FROM events WHERE mission LIKE '@successor:ascension:settlement:%'").fetchone()[
                0
            ]
            == 1
        )
    alternate = deepcopy(binding)
    alternate["body"]["mission_id"] = "someone-else"
    alternate = adapter._signed(journal, "ascension-execution-binding", alternate["body"])
    alternate_delivery = adapter.bind_delivery(journal, alternate, ARTIFACT, candidate_verdict="FAIL")
    with pytest.raises(ValueError, match="already attributed"):
        adapter.import_settlement(
            journal,
            alternate,
            alternate_delivery,
            ARTIFACT,
            adapter.MarketReader(rpc.context, rpc),
            settlement_tx=CLOSE_TX,
        )


@pytest.mark.parametrize("status,acceptance", [("refunded", "unresolved_no_quorum"), ("failed", "rejected")])
def test_missing_quorum_is_not_failed_work(tmp_path: Path, status: str, acceptance: str) -> None:
    journal, rpc, binding, delivery = prepared(tmp_path)
    rpc.height = 4
    rpc.close(status)
    result = adapter.import_settlement(
        journal, binding, delivery, ARTIFACT, adapter.MarketReader(rpc.context, rpc), settlement_tx=CLOSE_TX
    )
    assert result["job_acceptance"] == acceptance
    if status == "refunded":
        assert result["payouts"] == [] and result["refund_base_units"] == SPEC["bounty"]
    else:
        assert result["payouts"][0]["burned"] == "10"


@pytest.mark.parametrize("tamper", ["artifact", "chain", "code", "job", "worker", "reorg", "refund", "rounding"])
def test_settlement_rejects_identity_content_and_economic_mismatches(tmp_path: Path, tamper: str) -> None:
    journal, rpc, binding, delivery = prepared(tmp_path)
    rpc.height = 4
    rpc.close("paid")
    artifact = ARTIFACT
    context = rpc.context
    if tamper == "artifact":
        artifact += b" "
    elif tamper == "chain":
        rpc.chain = 1
    elif tamper == "code":
        context = context.model_copy(update={"market_code_hash": adapter.ZERO_HASH})
    elif tamper in {"job", "worker"}:
        body = deepcopy(binding["body"])
        body["market_job_id" if tamper == "job" else "selected_worker"] = "2" if tamper == "job" else BUSINESS
        binding = adapter._signed(journal, "ascension-execution-binding", body)
        delivery = adapter.bind_delivery(journal, binding, artifact, candidate_verdict="FAIL")
    elif tamper == "reorg":
        rpc.block_hashes[4] = "0x" + "ee" * 32
    elif tamper == "refund":
        rpc.refund += 1
    else:
        rpc.events[CLOSE_TX][2]["data"] = words(7601, 77)
    with pytest.raises(ValueError):
        adapter.import_settlement(
            journal, binding, delivery, artifact, adapter.MarketReader(context, rpc), settlement_tx=CLOSE_TX
        )


def test_rounding_is_per_payout_not_aggregate() -> None:
    values = adapter.payout_breakdown(199, 200)
    assert values == {"gross": [191, 4, 4], "burned": [1, 0, 0], "net": [190, 4, 4], "refund": 1}
    values = adapter.payout_breakdown(399, 400)
    assert sum(values["burned"]) == 3
    assert sum(adapter.payout_breakdown(10103, 10103)["burned"]) == 99 != 10103 // 100


def test_runtime_dispatch_binding_requires_an_external_key_and_the_exact_authorization(tmp_path: Path) -> None:
    journal, _, binding, _ = prepared(tmp_path)
    authorization = dict(binding["body"]["execution_authorization"], market_binding_digest=binding["digest"])
    verified = adapter.verify_execution_binding(binding, journal.public, authorization)
    assert verified["selected_worker"] == WORKER
    with pytest.raises(ValueError, match="configured trust"):
        adapter.verify_execution_binding(binding, "ee" * 32, authorization)
    with pytest.raises(ValueError, match="does not bind"):
        adapter.verify_execution_binding(binding, journal.public, dict(authorization, market_binding_digest=None))
    with pytest.raises(ValueError, match="changed after"):
        adapter.verify_execution_binding(binding, journal.public, dict(authorization, capabilities=["deploy"]))


def test_retroactive_terms_and_changed_preassigned_worker_are_rejected(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "journal")
    rpc = UnitRPC()
    reader = adapter.MarketReader(rpc.context, rpc)
    seal = adapter.seal_terms(journal, job_contract(worker=BUSINESS), SPEC, reader)
    rpc.height = 3
    with pytest.raises(ValueError, match="exact job/worker"):
        adapter.bind_assignment(
            journal,
            seal,
            reader,
            market_job_id="1",
            posting_tx=POST_TX,
            assignment_tx=AWARD_TX,
            execution_authorization=authorization(seal),
        )
    other = Journal.initialize(tmp_path / "late-journal")
    late = adapter.seal_terms(other, job_contract(), SPEC, reader)
    with pytest.raises(ValueError, match="Historical job"):
        adapter.bind_assignment(
            other,
            late,
            reader,
            market_job_id="1",
            posting_tx=POST_TX,
            assignment_tx=AWARD_TX,
            execution_authorization=authorization(late),
        )


def test_settlement_export_retains_signed_bytes_without_accepting_unknown_adapter_versions(tmp_path: Path) -> None:
    journal, rpc, binding, delivery = prepared(tmp_path)
    rpc.height = 4
    rpc.close("paid")
    adapter.import_settlement(
        journal, binding, delivery, ARTIFACT, adapter.MarketReader(rpc.context, rpc), settlement_tx=CLOSE_TX
    )
    records = adapter.list_settlements(journal, "institution")
    assert len(records) == 1
    assert isinstance(records[0]["canonical_body"], str)
    assert records[0]["public_key"] == journal.public
    assert adapter.list_settlements(journal, "different-institution") == []
    with journal.transaction() as cx:
        assert adapter.list_settlements(journal, "institution", cx) == records
    unknown = adapter._signed(journal, "ascension-execution-binding", {**binding["body"], "schema_version": 2})
    with pytest.raises(ValueError, match="Unexpected signed"):
        adapter.verify_execution_binding(
            unknown,
            journal.public,
            dict(binding["body"]["execution_authorization"], market_binding_digest=unknown["digest"]),
        )


def test_historical_settlement_validates_exact_signed_wrapper_without_reimport(tmp_path: Path) -> None:
    journal, rpc, binding, delivery = prepared(tmp_path)
    rpc.height = 4
    rpc.close("paid")
    adapter.import_settlement(
        journal, binding, delivery, ARTIFACT, adapter.MarketReader(rpc.context, rpc), settlement_tx=CLOSE_TX
    )
    record = adapter.list_settlements(journal, "institution")[0]
    assert adapter.validate_historical_settlement(record) == record
    altered = deepcopy(record)
    altered["settlement"]["institution_id"] = "different-institution"
    with pytest.raises(ValueError, match="exact signed body"):
        adapter.validate_historical_settlement(altered)
    with pytest.raises(ValueError, match="signed bytes"):
        adapter.validate_historical_settlement({**record, "canonical_body": record["canonical_body"] + " "})
    with pytest.raises(ValueError, match="provenance key"):
        adapter.validate_historical_settlement({**record, "public_key": "ee" * 32})
    with pytest.raises(ValueError, match="depth"):
        adapter.validate_historical_settlement({**record, "canonical_body": "[" * 33 + "]" * 33})
    with pytest.raises(ValueError, match="wrapper"):
        adapter.validate_historical_settlement({**record, "trusted": True})
    journal.verify()
