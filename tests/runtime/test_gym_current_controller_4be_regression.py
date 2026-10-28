# SPDX-License-Identifier: Apache-2.0
"""Gym authority checkpoints using synthetic trust, funding and training fixtures."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_gym import KEY, GymCampaign, GymPlan, GymTask
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, sign_record
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    state = f.setup.__wrapped__(tmp_path)
    for principal in ("gym-planner", "unused-controller"):
        key = Ed25519PrivateKey.generate()
        state["keys"][principal] = key
        state["trust"]._anchors[principal] = TrustAnchor(
            key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"controller"})
        )
    s.funding(state)
    return state


def plan(state: dict[str, Any]) -> GymPlan:
    return GymPlan(
        campaign_id="isolated-gym-controller-checkpoint",
        mission_id="isolated-optional-gym-development",
        original=PlacementWorkflow(version=1),
        alternatives=[
            PlacementWorkflow(version=2, order="largest-demand", bound="residual", capacity_pruning=True),
            PlacementWorkflow(version=2, order="regret", bound="residual"),
        ],
        tasks=[
            GymTask(
                task_id=f"training-{seed}",
                partition="training",
                family="capacity-contention",
                problem=s.problem(seed, services=5, tight=True),
            )
            for seed in range(2101, 2105)
        ],
        max_logical_units=1_000_000,
        max_seconds=60,
        max_authorized_micro_usd=10_000,
        environment_digest=state["service"].execution_digest,
        expires_at=int(time.time()) + 3600,
    )


def check_original_c_liability(state: dict[str, Any], spec: GymPlan, original: dict[str, Any]) -> None:
    rows = state["costs"].snapshot()["charges"]
    assert len(rows) == 1
    charge = rows["gym/" + spec.campaign_id]
    assert charge["mission_id"] == spec.mission_id and charge["bucket"] == "C"
    assert charge["category"] == "compute" and charge["basis"] == "unknown"
    assert charge["accrued_micro_usd"] is None and charge["paid_micro_usd"] == 0
    assert charge["evidence_digest"] == digest("gym-plan", spec)
    assert charge["signed"] == original
    assert state["costs"].report(spec.mission_id)["unknown_costs"]


@pytest.mark.parametrize("withdrawal", ["revocation", "role-withdrawal", "key-replacement"])
@pytest.mark.parametrize("phase", ["first-action", "within-action", "after-first-trial", "before-freeze"])
def test_original_gym_controller_must_remain_eligible_at_every_active_checkpoint(
    setup: dict[str, Any], withdrawal: str, phase: str
) -> None:
    spec = plan(setup)
    signed = sign_record(
        setup["keys"]["gym-planner"],
        "gym-planner",
        "flywheel-gym-plan",
        {"journal_identity": setup["journal"].identity, "plan": spec.model_dump()},
    )
    original = copy.deepcopy(signed.model_dump())
    total_trials = len(spec.tasks) * (1 + len(spec.alternatives))
    calls, withdrawn = 0, False

    def current_environment() -> str:
        nonlocal calls, withdrawn
        calls += 1
        try:
            completed = len(setup["journal"].latest(KEY + spec.campaign_id)["trials"])
        except KeyError:
            completed = 0
        trigger = (
            phase == "first-action"
            and calls == 2
            or phase == "within-action"
            and calls == 3
            or phase == "after-first-trial"
            and completed == 1
            or phase == "before-freeze"
            and completed == total_trials
        )
        if trigger and not withdrawn:
            withdrawn = True
            anchor = setup["trust"]._anchors["gym-planner"]
            if withdrawal == "revocation":
                setup["trust"].revoke("gym-planner")
            elif withdrawal == "role-withdrawal":
                setup["trust"]._anchors["gym-planner"] = TrustAnchor(anchor.public_key, frozenset())
            else:
                setup["trust"]._anchors["gym-planner"] = setup["trust"]._anchors["unused-controller"]
        return spec.environment_digest

    runner = GymCampaign(
        setup["costs"], setup["service"].checkpoint, spec.environment_digest, current_environment=current_environment
    )
    result = runner.run(signed)
    assert withdrawn
    setup["trust"].anchor("controller", "controller")
    setup["trust"].anchor("accountant", "accounting")
    assert result["status"] == "failed-or-uncertain"
    assert result["error"] == "ValueError"
    assert result["candidate"] is None and not result["authority_granted"]
    assert result["original"] == spec.original.model_dump() and result["plan"] == original
    if phase == "first-action":
        assert not result["trials"] and result["logical_units"] == 0
    elif phase == "within-action":
        assert not result["trials"] and result["logical_units"] > 0 and result["pending"]
    else:
        assert len(result["trials"]) == (1 if phase == "after-first-trial" else total_trials)
    saved = setup["journal"].latest(KEY + spec.campaign_id)
    assert saved["status"] == result["status"] and saved["candidate"] is None
    check_original_c_liability(setup, spec, original)
    ledger = setup["costs"].snapshot()
    # Even a still-trusted operator's new signature cannot revive this campaign.
    replacement = sign_record(setup["keys"]["controller"], "controller", signed.domain, original["payload"])
    with pytest.raises(Conflict, match="already attempted"):
        runner.run(replacement)
    assert setup["costs"].snapshot() == ledger
    assert setup["journal"].latest(KEY + spec.campaign_id)["digest"] == saved["digest"]


@pytest.mark.parametrize("control", ["current-controller", "unrelated-revocation", "caller-envelope-mutation"])
def test_current_signed_gym_plan_completes_without_granting_authority(setup: dict[str, Any], control: str) -> None:
    spec = plan(setup)
    signed = sign_record(
        setup["keys"]["gym-planner"],
        "gym-planner",
        "flywheel-gym-plan",
        {"journal_identity": setup["journal"].identity, "plan": spec.model_dump()},
    )
    original = copy.deepcopy(signed.model_dump())
    calls = 0

    def current_environment() -> str:
        nonlocal calls
        calls += 1
        if control == "unrelated-revocation" and calls == 3:
            setup["trust"].revoke("unused-controller")
        if control == "caller-envelope-mutation":
            signed.payload["plan"]["max_logical_units"] = 1
        return spec.environment_digest

    result = GymCampaign(
        setup["costs"], setup["service"].checkpoint, spec.environment_digest, current_environment=current_environment
    ).run(signed)
    assert result["status"] == "frozen-awaiting-protected-evaluation"
    assert result["candidate"] is not None and not result["authority_granted"]
    assert result["plan"] == original
    assert len(result["trials"]) == len(spec.tasks) * (1 + len(spec.alternatives))
    check_original_c_liability(setup, spec, original)
