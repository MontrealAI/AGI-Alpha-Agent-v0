# SPDX-License-Identifier: Apache-2.0
"""Actual fixed-work execution through the thin enterprise facade."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import enterprise, workbench


def review(home: Path, ident: str, *, decision: str = "accepted") -> dict:
    state = enterprise.show(home, ident)
    return enterprise.handle(
        argparse.Namespace(
            home=home,
            enterprise_id=ident,
            enterprise_command="review",
            decision=decision,
            result_digest=state["result_digest"],
            note="Inspected exact local artifacts; not independent qualification",
        )
    )


def test_real_two_family_launches_are_isolated_and_retained(tmp_path: Path) -> None:
    home = tmp_path / "home"
    configs = [enterprise.new("numerical", "Quadrature"), enterprise.new("public-data", "Data report")]
    for config in configs:
        assert enterprise.activate(home, config)["state"] == "planned"
        outcome = enterprise.operate(home, config["enterprise_id"])
        assert outcome["state"] == "review"
        assert outcome["settlement"] == "NOT_CONNECTED"
        assert outcome["economics"]["computeCost"] is None
        assert outcome["authority"] == []
    assert configs[0]["enterprise_id"] != configs[1]["enterprise_id"]
    review(home, configs[0]["enterprise_id"])
    assert enterprise.show(home, configs[0]["enterprise_id"])["state"] == "accepted"
    assert enterprise.show(home, configs[1]["enterprise_id"])["state"] == "review"
    before = Journal(home).verify()
    assert enterprise.operate(home, configs[0]["enterprise_id"])["attempts"] == 1
    assert Journal(home).verify() == before


def test_configuration_is_immutable_and_activation_is_idempotent(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    enterprise.activate(home, config)
    before = Journal(home).verify()
    enterprise.activate(home, config)
    assert Journal(home).verify() == before
    changed = {**config, "name": "Another"}
    with pytest.raises(Conflict, match="another configuration"):
        enterprise.activate(home, changed)
    assert Journal(home).verify() == before


def test_invalid_configuration_never_creates_home(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    config["work"]["inputs"]["steps"] = -1
    with pytest.raises(ValueError):
        enterprise.activate(home, config)
    assert not home.exists()


@pytest.mark.parametrize("field,value", [("authority", ["pay"]), ("schema", "v2"), ("name", "")])
def test_configuration_cannot_supply_new_authority(field: str, value: object) -> None:
    config = enterprise.new("numerical", "One")
    config[field] = value
    with pytest.raises(ValueError):
        enterprise.validate(config)


def test_stop_before_execution_is_terminal(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    enterprise.handle(argparse.Namespace(home=home, enterprise_command="control", enterprise_id=ident, state="stopped"))
    with pytest.raises(Conflict):
        enterprise.operate(home, ident, resume=True)
    assert enterprise.show(home, ident)["attempts"] == 0


def test_interrupted_execution_requires_explicit_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    original = workbench.invoke

    def interrupted(request: dict, *args: object) -> dict:
        if request["operation"] == "run":
            raise KeyboardInterrupt()
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", interrupted)
    with pytest.raises(KeyboardInterrupt):
        enterprise.operate(home, ident)
    assert enterprise.show(home, ident)["state"] == "interrupted"
    with pytest.raises(Conflict, match="--resume"):
        enterprise.operate(home, ident)
    monkeypatch.setattr(workbench, "invoke", original)
    assert enterprise.operate(home, ident, resume=True)["state"] == "review"


def test_successor_reuses_template_but_not_result_or_permission(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    with pytest.raises(Conflict, match="accept"):
        enterprise.derive(home, ident, name="Two")
    enterprise.operate(home, ident)
    review(home, ident)
    child = enterprise.derive(home, ident, name="Two")
    assert child["work"] == config["work"]
    child["work"]["inputs"]["upper"] = 4
    assert config["work"]["inputs"]["upper"] == 3
    state = enterprise.activate(home, child)
    assert state["state"] == "planned"
    assert state["result_digest"] is None
    assert state["authority"] == []
    assert enterprise.operate(home, child["enterprise_id"])["state"] == "review"
    assert enterprise.show(home, ident)["state"] == "accepted"


def test_forged_parent_does_not_activate(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    enterprise.operate(home, ident)
    review(home, ident)
    child = enterprise.derive(home, ident, name="Two")
    child["parent"]["result_digest"] = "0" * 64
    before = Journal(home).verify()
    with pytest.raises(Conflict, match="exact accepted parent"):
        enterprise.activate(home, child)
    assert Journal(home).verify() == before


def test_export_uses_existing_receipt_and_preserves_output(tmp_path: Path) -> None:
    config, home = enterprise.new("documentation", "Docs"), tmp_path / "home"
    enterprise.activate(home, config)
    enterprise.operate(home, config["enterprise_id"])
    command = argparse.Namespace(
        home=home, enterprise_command="export", enterprise_id=config["enterprise_id"], output=tmp_path / "result"
    )
    enterprise.handle(command)
    assert (command.output / "signed-receipt.json").is_file()
    assert json.loads((command.output / "mission.json").read_text()) == config["work"]
    with pytest.raises(FileExistsError):
        enterprise.handle(command)


def test_invalid_review_cannot_accept_other_result(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    enterprise.activate(home, config)
    enterprise.operate(home, config["enterprise_id"])
    with pytest.raises(Conflict):
        enterprise.handle(
            argparse.Namespace(
                home=home,
                enterprise_command="review",
                enterprise_id=config["enterprise_id"],
                result_digest="0" * 64,
                decision="accepted",
                note="Wrong result",
            )
        )
    assert enterprise.show(home, config["enterprise_id"])["state"] == "review"


def test_adapter_catalog_is_honest_and_nonmutating(tmp_path: Path) -> None:
    home = tmp_path / "absent"
    result = enterprise.adapters(home)
    assert not home.exists()
    assert result["studio"]["configured"] is False
    assert {item.get("currency") for item in result["routes"]} == {None, "AGIALPHA", "USDC"}
    assert result["authority_created"] is False


def test_handoff_uses_existing_studio_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.core.runtime.successor import studio

    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    enterprise.activate(home, config)
    seen = []
    monkeypatch.setattr(studio, "validate_request", lambda request: seen.append(request) or request)
    plan = {"not_a_real_plan": True}
    request = enterprise.handoff(home, config["enterprise_id"], plan, 0)
    assert seen == [request]
    assert request["schema"] == studio.REQUEST_SCHEMA
    assert request["work_spec"] == config["work"]
    assert request["project_id"] == config["enterprise_id"]


def test_real_handoff_rejects_invalid_plan(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    enterprise.activate(home, config)
    with pytest.raises((ValueError, KeyError)):
        enterprise.handoff(home, config["enterprise_id"], {}, 0)


def test_cli_registration_and_dispatch(tmp_path: Path) -> None:
    from alpha_factory_v1.core.runtime.successor import cli

    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=tmp_path / "home")
    cli.add_commands(parser.add_subparsers(dest="command", required=True))
    output = tmp_path / "enterprise.json"
    args = parser.parse_args(["successor-harness", "new", "numerical", "--name", "One", "--output", str(output)])
    result = cli.handle(args)
    assert result["enterprise_id"] == json.loads(output.read_text())["enterprise_id"]
    with pytest.raises(FileExistsError):
        cli.handle(args)


def test_unknown_executor_family_is_rejected() -> None:
    with pytest.raises(ValueError):
        enterprise.new("arbitrary-shell", "Not authorized")


def test_attempt_budget_cannot_be_reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    original = workbench.invoke

    def interrupted(request: dict, *args: object) -> dict:
        if request["operation"] == "run":
            raise KeyboardInterrupt()
        return original(request, *args)

    monkeypatch.setattr(workbench, "invoke", interrupted)
    for attempt in range(3):
        with pytest.raises(KeyboardInterrupt):
            enterprise.operate(home, ident, resume=attempt > 0)
    enterprise.activate(home, config)
    with pytest.raises(Conflict):
        enterprise.operate(home, ident, resume=True)
    assert enterprise.show(home, ident)["attempts"] == 3


def test_parent_acceptance_change_prevents_successor_activation(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    enterprise.operate(home, ident)
    review(home, ident)
    child = enterprise.derive(home, ident, name="Two")
    enterprise.handle(argparse.Namespace(home=home, enterprise_command="control", enterprise_id=ident, state="retired"))
    before = Journal(home).verify()
    with pytest.raises(Conflict, match="exact accepted parent"):
        enterprise.activate(home, child)
    assert Journal(home).verify() == before


def test_successor_can_change_task_family_without_inheriting_acceptance(tmp_path: Path) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    enterprise.operate(home, ident)
    review(home, ident)
    child = enterprise.derive(
        home, ident, name="Documentation successor", work=enterprise.new("documentation", "Template")["work"]
    )
    enterprise.activate(home, child)
    result = enterprise.operate(home, child["enterprise_id"])
    assert result["state"] == "review"
    assert result["review"] is None
    assert result["authority"] == []
    assert result["result_digest"] != enterprise.show(home, ident)["result_digest"]


def test_real_compiled_plan_handoff(tmp_path: Path) -> None:
    from alpha_factory_v1.core.runtime import ascension

    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    enterprise.activate(home, config)
    plan = ascension.compile_plan(
        [
            {
                "goal": "Evaluate exact report",
                "successMetric": "Accept correct negative results",
                "bounty": "10103",
                "duration": 86400,
                "priceWeight": 6000,
            }
        ]
    )
    request = enterprise.handoff(home, config["enterprise_id"], plan, 0)
    assert request["work_spec"] == config["work"]
    assert request["plan"] == plan
    assert enterprise.show(home, config["enterprise_id"])["state"] == "planned"


def test_parent_retirement_during_freeze_prevents_registration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, home = enterprise.new("numerical", "One"), tmp_path / "home"
    ident = config["enterprise_id"]
    enterprise.activate(home, config)
    enterprise.operate(home, ident)
    review(home, ident)
    child = enterprise.derive(home, ident, name="Two")
    original = workbench.freeze

    def retire_then_freeze(journal: Journal, spec: dict, run_id: str) -> dict:
        enterprise.handle(
            argparse.Namespace(home=home, enterprise_command="control", enterprise_id=ident, state="retired")
        )
        return original(journal, spec, run_id)

    monkeypatch.setattr(workbench, "freeze", retire_then_freeze)
    with pytest.raises(Conflict, match="exact accepted parent"):
        enterprise.activate(home, child)
    with pytest.raises(KeyError):
        Journal(home).latest(enterprise._key(child["enterprise_id"]))
    with pytest.raises(KeyError):
        Journal(home).latest(workbench._key(child["enterprise_id"]))
