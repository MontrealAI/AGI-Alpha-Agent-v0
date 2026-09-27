# SPDX-License-Identifier: Apache-2.0
"""Adversarial checks for the native-to-contract evidence boundary."""

from __future__ import annotations

import json
import base64
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from alpha_factory_v1.core.runtime import ascension
from alpha_factory_v1.core.runtime.cli import main
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.samples import examples
from alpha_factory_v1.core.runtime.store import Conflict, Journal, canonical, digest


def specification(**changes: object) -> dict[str, object]:
    return {
        "goal": "Allocate the supplied budget",
        "successMetric": "Replay constraints and integer totals",
        "bounty": "100000000000000000000",
        "duration": 86400,
        "priceWeight": 6000,
        **changes,
    }


@pytest.mark.parametrize("count", [1, 2, 3, 5, 127, 128])
def test_every_compiled_proof_reconstructs_the_root(count: int) -> None:
    plan = ascension.compile_plan([specification(goal=f"Job {i}: α insight") for i in range(count)])
    assert ascension.verify_plan(plan)["jobs"] == count
    assert plan["totalBounty"] == str(count * 100 * 10**18)
    for job in plan["jobs"]:
        value = bytes.fromhex(job["leaf"][2:])
        for sibling in job["proof"]:
            value = ascension.keccak(b"".join(sorted([value, bytes.fromhex(sibling[2:])])))
        assert "0x" + value.hex() == plan["planRoot"]


@pytest.mark.parametrize(
    "change",
    [
        {"bounty": "99"},
        {"bounty": str(2**96)},
        {"bounty": 100},
        {"bounty": "0100"},
        {"bounty": "1e20"},
        {"duration": True},
        {"duration": 1.5},
        {"duration": 90 * 86400 + 1},
        {"priceWeight": -1},
        {"priceWeight": 10001},
        {"goal": "α" * 257},
        {"successMetric": ""},
        {"unknown": 1},
    ],
)
def test_specs_reject_lossy_values_and_contract_limit_violations(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ascension.compile_plan([specification(**change)])


@pytest.mark.parametrize("source", [[], [specification()] * 129, {}, "jobs"])
def test_plan_cardinality(source: object) -> None:
    with pytest.raises(ValueError):
        ascension.compile_plan(source)


@pytest.mark.parametrize("tamper", ["proof", "index", "total", "token", "extra", "bool-index", "order"])
def test_metadata_and_proof_tampering_fails(tamper: str) -> None:
    plan = ascension.compile_plan([specification(goal="Job one"), specification(goal="Job two")])
    if tamper == "proof":
        plan["jobs"][0]["proof"] = []
    elif tamper == "index":
        plan["jobs"][0]["index"] = 1
    elif tamper == "bool-index":
        plan["jobs"][0]["index"] = False
    elif tamper == "total":
        plan["totalBounty"] = "200"
    elif tamper == "token":
        plan["token"] = "USDC"
    elif tamper == "order":
        plan["jobs"].reverse()
    else:
        plan["uncommitted"] = True
    with pytest.raises(ValueError):
        ascension.verify_plan(plan)


@pytest.mark.parametrize("data", [b'{"a":1,"a":2}', b'{"value":NaN}', b'{"value":Infinity}'])
def test_ambiguous_json_rejected(data: bytes) -> None:
    with pytest.raises(ValueError):
        ascension.parse(data, 1000)
    with pytest.raises(ValueError):
        ascension.parse(b" " * 1001, 1000)


def reviewed(tmp_path: Path) -> tuple[Journal, dict, str]:
    journal = Journal.initialize(tmp_path / "state")
    mission = Mission.model_validate(
        {
            "goal": specification()["goal"],
            "work": {
                "kind": "allocation",
                "budget": 10,
                "items": [{"id": "one", "cost": 3, "value": 8}, {"id": "two", "cost": 7, "value": 10}],
            },
        }
    )
    engine = Engine(journal)
    result = engine.execute(journal.submit(mission)["id"])
    plan = ascension.compile_plan([specification()])
    with pytest.raises(Conflict):
        ascension.delivery(journal, plan, 0, result["id"])
    engine.review(
        result["id"],
        result["revision"],
        digest(result["result"]),
        True,
        "Independently checked both selected items and all totals.",
    )
    return journal, plan, result["id"]


def test_reviewed_handoff_binds_bytes_identity_plan_goal_and_arithmetic(tmp_path: Path) -> None:
    journal, plan, ident = reviewed(tmp_path)
    data = ascension.delivery(journal, plan, 0, ident)
    result = ascension.verify_delivery(data, journal.public, plan["planRoot"])
    assert result["valid"] and result["nativeVerification"]["passed"]
    assert result["resultHash"] == "0x" + ascension.keccak(data).hex()
    assert result["mission"] == ident
    with pytest.raises(ValueError, match="canonical"):
        ascension.verify_delivery(data + b"\n", journal.public, plan["planRoot"])
    with pytest.raises(ValueError, match="trusted key"):
        ascension.verify_delivery(data, "00" * 32, plan["planRoot"])
    with pytest.raises(ValueError, match="on-chain root"):
        ascension.verify_delivery(data, journal.public, "0x" + "00" * 32)
    wrong = ascension.compile_plan([specification(goal="Another task")])
    with pytest.raises(ValueError, match="exactly match"):
        ascension.delivery(journal, wrong, 0, ident)
    for index in (-1, 1, True):
        with pytest.raises(ValueError, match="index"):
            ascension.delivery(journal, plan, index, ident)
    changed = json.loads(data)
    changed["body"]["plan"]["jobs"][0]["spec"]["successMetric"] = "No checks"
    with pytest.raises(ValueError, match="signature is invalid"):
        ascension.verify_delivery(canonical(changed), journal.public, plan["planRoot"])


def test_samples_work_outside_checkout_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["examples", "--output", "inputs"]) == 0
    before = {p.name: p.read_bytes() for p in (tmp_path / "inputs").iterdir()}
    assert set(before) == {
        "research.json",
        "allocation.json",
        "schedule.json",
        "forecast.json",
        "code.json",
        "ascension-jobs.json",
    }
    assert main(["examples", "--output", "inputs"]) == 1
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "inputs").iterdir()}
    assert main(["ascension-compile", "inputs/ascension-jobs.json", "--output", "plan.json"]) == 0
    assert main(["ascension-check", "plan.json"]) == 0
    assert main(["ascension-compile", "inputs/ascension-jobs.json", "--output", "plan.json"]) == 1
    assert not (tmp_path / "agent-state").exists()


def test_handoff_cli_never_overwrites_and_requires_an_external_anchor(tmp_path: Path) -> None:
    journal, plan, ident = reviewed(tmp_path)
    source, output = tmp_path / "plan.json", tmp_path / "delivery.json"
    source.write_bytes(canonical(plan))
    args = [
        "--home",
        str(journal.root),
        "ascension-deliver",
        str(source),
        "--index",
        "0",
        "--mission",
        ident,
        "--output",
        str(output),
    ]
    assert main(args) == 0
    data = output.read_bytes()
    assert main(args) == 1 and output.read_bytes() == data
    assert (
        main(
            ["ascension-verify-delivery", str(output), "--public-key", journal.public, "--plan-root", plan["planRoot"]]
        )
        == 0
    )


def test_trusted_code_receipt_still_requires_explicit_replay_permission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, plan, ident = reviewed(tmp_path)
    envelope = json.loads(ascension.delivery(journal, plan, 0, ident))
    receipt = envelope["body"]["nativeExport"]["receipt"]
    document = receipt["body"]["document"]
    document["request"]["work"] = {
        "kind": "code",
        "candidate": "def solve(): return 1",
        "heldout": [{"args": [], "expected": 1}],
    }
    receipt["canonical_body"] = canonical(receipt["body"]).decode()
    receipt["hash"] = digest(receipt["body"])
    receipt["signature"] = base64.b64encode(journal.key.sign(bytes.fromhex(receipt["hash"]))).decode()
    envelope["signature"] = base64.b64encode(
        journal.key.sign(hashlib.sha256(canonical(envelope["body"])).digest())
    ).decode()
    replay = Mock(side_effect=AssertionError("Unrequested code replay"))
    monkeypatch.setattr(ascension, "verify_result", replay)
    with pytest.raises(ValueError, match="explicit --replay-code"):
        ascension.verify_delivery(canonical(envelope), journal.public, plan["planRoot"])
    replay.assert_not_called()
