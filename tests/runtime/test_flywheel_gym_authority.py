# SPDX-License-Identifier: Apache-2.0
"""Current signed-plan authority on local, synthetic workflow refinement."""

from __future__ import annotations

import builtins
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.successor import flywheel_gym as gym
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, sign_record
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    state = f.setup.__wrapped__(tmp_path)
    s.funding(state)
    return state


def signed_plan(state: dict[str, Any]) -> Any:
    plan = gym.GymPlan(
        campaign_id="authority-refinement",
        mission_id="additional-authority-rd",
        original=PlacementWorkflow(version=1),
        alternatives=[
            PlacementWorkflow(version=2, order="largest-demand", bound="residual", capacity_pruning=True),
            PlacementWorkflow(version=2, order="regret", bound="residual"),
        ],
        tasks=[
            gym.GymTask(
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
    return sign_record(
        state["keys"]["controller"],
        "controller",
        "flywheel-gym-plan",
        {"journal_identity": state["journal"].identity, "plan": plan.model_dump()},
    )


@pytest.mark.parametrize("change", ["revocation", "role-loss"])
@pytest.mark.parametrize("when", ["before-first-task", "during-step", "after-outcome", "candidate-selection"])
def test_current_controller_loss_stops_training_and_freeze_without_erasing_liability(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch, change: str, when: str
) -> None:
    state, signed = setup, signed_plan(setup)
    steps: list[str] = []
    outcomes: list[dict[str, Any]] = []
    checks = 0

    def lose_authority() -> None:
        if change == "revocation":
            state["trust"].revoke("controller")
        else:
            prior = state["trust"]._anchors["controller"]
            state["trust"]._anchors["controller"] = TrustAnchor(prior.public_key, frozenset())

    def current_environment() -> str:
        nonlocal checks
        checks += 1
        if when == "before-first-task" and checks == 2:
            lose_authority()
        return state["service"]._execution_binding()

    step = gym.PlacementEnvironment.step
    outcome = gym.PlacementEnvironment.outcome

    def tracked_step(env: Any, action: Any, active: Any) -> Any:
        steps.append(env.task.task_id)
        if when == "during-step" and len(steps) == 1:
            lose_authority()
        return step(env, action, active)

    def tracked_outcome(env: Any) -> dict[str, Any]:
        value = outcome(env)
        outcomes.append(value)
        if when == "after-outcome" and len(outcomes) == 1:
            lose_authority()
        return value

    def select(*args: Any, **kwargs: Any) -> Any:
        value = builtins.min(*args, **kwargs)
        if when == "candidate-selection":
            lose_authority()
        return value

    monkeypatch.setattr(gym.PlacementEnvironment, "step", tracked_step)
    monkeypatch.setattr(gym.PlacementEnvironment, "outcome", tracked_outcome)
    monkeypatch.setattr(gym, "min", select, raising=False)
    campaign = gym.GymCampaign(
        state["costs"],
        state["service"].checkpoint,
        state["service"].execution_digest,
        current_environment=current_environment,
    )
    result = campaign.run(signed)
    assert result["status"] == "failed-or-uncertain" and result["error"] == "ValueError"
    assert result["candidate"] is None and "candidate_digest" not in result
    expected = {
        "before-first-task": (0, 0),
        "during-step": (1, 0),
        "after-outcome": (1, 1),
        "candidate-selection": (12, 12),
    }
    step_count, completed_count = expected[when]
    assert len(steps) == step_count and len(result["trials"]) == completed_count
    assert [trial["result"] for trial in result["trials"]] == [item["result"] for item in outcomes]
    assert result["plan"] == signed.model_dump() and result["authority_granted"] is False
    if when == "during-step":
        assert result["pending"]["task"] == "training-2101" and result["logical_units"] > 0
    persisted = state["journal"].latest(gym.KEY + "authority-refinement")
    assert persisted["status"] == result["status"] and persisted["trials"] == result["trials"]
    costs = state["costs"].snapshot()["charges"]
    assert set(costs) == {"gym/authority-refinement"}
    charge = costs["gym/authority-refinement"]
    assert charge["bucket"] == "C" and charge["accrued_micro_usd"] is None and charge["paid_micro_usd"] == 0
    assert charge["signed"] == signed.model_dump()
    before_retry = state["journal"].verify()
    with pytest.raises(ValueError, match="not currently trusted"):
        campaign.run(signed)
    assert state["journal"].verify() == before_retry
    assert len(steps) == step_count


@pytest.mark.parametrize("control", ["normal", "unrelated-revocation"])
def test_current_gym_controller_controls_preserve_normal_training(setup: dict[str, Any], control: str) -> None:
    state, signed = setup, signed_plan(setup)
    checks = 0

    def current_environment() -> str:
        nonlocal checks
        checks += 1
        if control == "unrelated-revocation" and checks == 2:
            state["trust"].revoke("evaluator")
        return state["service"]._execution_binding()

    result = gym.GymCampaign(
        state["costs"],
        state["service"].checkpoint,
        state["service"].execution_digest,
        current_environment=current_environment,
    ).run(signed)
    assert result["status"] == "frozen-awaiting-protected-evaluation"
    assert result["candidate"] is not None and len(result["trials"]) == 12
    assert result["authority_granted"] is False
    assert state["journal"].verify()["valid"]
