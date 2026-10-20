# SPDX-License-Identifier: Apache-2.0
"""Exercise project-bound handoffs with labeled model/actuator doubles, never paid providers."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import computer
from alpha_factory_v1.core.runtime.successor.computer_handoff import (
    ComputerHandoff,
    ComputerStrategy,
    write_computer_return,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.transport import read_document


def handoff_document() -> dict[str, Any]:
    """Match the browser's explicit fields, project serialization and task defaults."""
    project = {
        "schema": "successor-alpha-project/v1",
        "id": "0f55c5dc-f335-4096-a29e-3bfd70b2345c",
        "revision": 0,
        "name": "Public software research",
        "goal": "Choose a simpler public-document workflow",
        "createdAt": "2026-10-18T00:00:00.000Z",
        "updatedAt": "2026-10-18T00:00:00.000Z",
        "cycles": [],
        "opportunities": [],
        "qualification": "not_independently_qualified",
        "authority": "none",
    }
    project_raw = canonical(project).decode()
    task = computer.ComputerTask(
        goal="Compare public documentation strategies and enter a reviewable recommendation.",
        html='<main><h1>Public research</h1><textarea aria-label="Recommendation"></textarea></main>',
        input_rights="public",
        license="Public source material, reviewed by operator",
        max_turns=3,
    )
    document = {
        "schema": "successor-alpha-computer-handoff/v1",
        "attemptId": "ea9c2ab9-7471-45da-868f-dccdd978aee4",
        "projectRaw": project_raw,
        "projectSha256": hashlib.sha256(project_raw.encode()).hexdigest(),
        "sourceHash": "b" * 64,
        "task": task.model_dump(mode="json"),
        "strategy": {
            "originalGoal": "Choose a simpler public-document workflow",
            "valueHypothesis": "Maintainers may reduce repeated public-document comparison work; not yet measured.",
            "selected": "reframe",
            "hypotheses": ["Read every document", "Compare only the public decision criteria"],
            "combination": "Use a broad index followed by a focused comparison",
            "reframing": "Determine whether one shared public format removes repeated comparison work",
            "successCriteria": ["A reviewer can trace each recommendation to the supplied material"],
        },
        "authority": "none",
        "settlement": "not_connected",
    }
    document["task"]["goal"] = ComputerStrategy.model_validate(document["strategy"]).goal()
    return document


class ControlledComputer:
    """Explicit actuator double; its PNG bytes are not real browser evidence."""

    def __init__(self, *args: Any) -> None:
        pass

    def observe(self) -> dict[str, Any]:
        return {
            "png": base64.b64encode(b"CONTROLLED_TEST_DOUBLE_PNG").decode(),
            "text": "Controlled double: recommendation for human review",
        }

    def act(self, action: dict[str, Any]) -> dict[str, Any]:
        return self.observe()

    def close(self) -> None:
        pass


def args_for(tmp_path: Path) -> argparse.Namespace:
    path = tmp_path / "mission.json"
    path.write_bytes(canonical(handoff_document()))
    return argparse.Namespace(
        home=tmp_path / "operator",
        computer_command="prepare",
        file=path,
        provider="responses",
        model="CONTROLLED_TEST_MODEL",
        base_url="http://127.0.0.1:12345/v1",
        key_env="SUCCESSOR_UNUSED_TEST_KEY",
        image="sha256:" + "a" * 64,
        output=tmp_path / "result",
        permit="",
    )


def test_project_component_over_one_mb_is_accepted_within_existing_transport_bound(tmp_path: Path) -> None:
    document = handoff_document()
    # Legal JSON whitespace exercises exact bytes without manufacturing invalid historical cycles.
    document["projectRaw"] = " " * 1_050_000 + document["projectRaw"]
    document["projectSha256"] = hashlib.sha256(document["projectRaw"].encode()).hexdigest()
    raw = canonical(document)
    assert 1_000_000 < len(document["projectRaw"].encode()) < len(raw) < 2_000_000
    args = args_for(tmp_path)
    args.file.write_bytes(raw)
    prepared = computer.handle(args)
    assert prepared["handoff"]["projectSha256"] == document["projectSha256"]
    assert not args.home.exists() and not args.output.exists()


def test_larger_project_component_does_not_expand_outer_two_mb_transport(tmp_path: Path) -> None:
    document = handoff_document()
    document["projectRaw"] = " " * 1_999_000 + document["projectRaw"]
    document["projectSha256"] = hashlib.sha256(document["projectRaw"].encode()).hexdigest()
    assert len(document["projectRaw"].encode()) < 2_000_000
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(raw) > 2_000_000
    path = tmp_path / "oversized-handoff.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="bounded regular JSON"):
        read_document(path)
    with pytest.raises(ValueError, match="byte limit"):
        ComputerHandoff.model_validate(document)


def install_doubles(monkeypatch: pytest.MonkeyPatch, *, fail: bool = False) -> None:
    actual_run = computer.run_session

    class BrokenComputer(ControlledComputer):
        def act(self, action: dict[str, Any]) -> dict[str, Any]:
            raise OSError("Controlled uncertain action")

    def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return actual_run(*args, **kwargs, factory=BrokenComputer if fail else ControlledComputer)

    def advise(self: computer.HTTPAdvisor, task: computer.ComputerTask, observation: dict[str, Any]) -> dict[str, Any]:
        return (
            {"actions": [{"type": "type", "text": "Controlled double"}], "done": False, "summary": ""}
            if fail
            else {"actions": [], "done": True, "summary": "Controlled completion claim, unverified"}
        )

    monkeypatch.setattr(computer, "run_session", run)
    monkeypatch.setattr(computer.HTTPAdvisor, "next", advise)


@pytest.mark.parametrize("field", ["sourceHash", "strategy", "projectRaw", "valueHypothesis"])
def test_project_strategy_and_source_change_the_existing_permit(field: str) -> None:
    first = ComputerHandoff.model_validate(handoff_document())
    changed = handoff_document()
    if field == "sourceHash":
        changed[field] = "c" * 64
    elif field == "strategy":
        changed[field]["selected"] = "combine"
        changed["task"]["goal"] = ComputerStrategy.model_validate(changed["strategy"]).goal()
    elif field == "valueHypothesis":
        changed["strategy"][field] = "Public source reviewers may obtain a clearer comparison; unmeasured."
        changed["task"]["goal"] = ComputerStrategy.model_validate(changed["strategy"]).goal()
    else:
        project = json.loads(changed[field])
        project["revision"] += 1
        changed[field] = canonical(project).decode()
        changed["projectSha256"] = hashlib.sha256(changed[field].encode()).hexdigest()
    second = ComputerHandoff.model_validate(changed)
    advisor = computer.HTTPAdvisor("responses", "CONTROLLED", "http://127.0.0.1/v1", "")
    image = "sha256:" + "a" * 64
    assert first.context() != second.context()
    assert computer.commitment(first.task, advisor, image, first.context()) != computer.commitment(
        second.task, advisor, image, second.context()
    )


@pytest.mark.parametrize("selected", ["baseline", "combine", "reframe"])
def test_executable_goal_retains_full_strategy_slate_without_expanding_execution(selected: str) -> None:
    document = handoff_document()
    document["strategy"]["selected"] = selected
    strategy = ComputerStrategy.model_validate(document["strategy"])
    document["task"]["goal"] = strategy.goal()
    handoff = ComputerHandoff.model_validate(document)
    for candidate in [*strategy.hypotheses, strategy.combination, strategy.reframing, *strategy.successCriteria]:
        assert candidate in handoff.task.goal
    assert f"Selected approach ({selected}):" in handoff.task.goal
    assert "Candidate strategies:" in handoff.task.goal
    assert (
        "Other candidates are planning context, not permission to execute additional strategies." in handoff.task.goal
    )
    assert handoff.task.allowed_urls == [] and handoff.task.max_turns == 3 and handoff.task.max_actions == 30
    assert handoff.authority == "none" and handoff.settlement == "not_connected"


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "root",
        "authority",
        "defaults",
        "extra",
        "blank",
        "unbounded",
        "goal",
        "attempt",
        "value-missing",
        "value-long",
        "unselected-strategy",
    ],
)
def test_malformed_handoffs_are_rejected_before_execution(mutation: str) -> None:
    document = handoff_document()
    if mutation == "hash":
        document["projectSha256"] = "d" * 64
    elif mutation == "root":
        document["projectRaw"] = '{"schema":"other/v1"}'
        document["projectSha256"] = hashlib.sha256(document["projectRaw"].encode()).hexdigest()
    elif mutation == "authority":
        document["authority"] = "production"
    elif mutation == "defaults":
        del document["task"]["schema_version"]
    elif mutation == "extra":
        document["strategy"]["command"] = "arbitrary executable"
    elif mutation == "blank":
        document["strategy"]["hypotheses"][0] = " "
    elif mutation == "unbounded":
        document["strategy"]["reframing"] = "x" * 1001
    elif mutation == "goal":
        document["task"]["goal"] = "Unrelated goal"
    elif mutation == "attempt":
        document["attemptId"] = "not-a-uuid"
    elif mutation == "value-missing":
        del document["strategy"]["valueHypothesis"]
    elif mutation == "unselected-strategy":
        document["strategy"]["hypotheses"][1] = "Changed alternative that the executable goal did not disclose"
    else:
        document["strategy"]["valueHypothesis"] = "x" * 1001
    with pytest.raises(ValueError):
        ComputerHandoff.model_validate(document)


def test_prepare_and_existing_runtime_emit_a_bound_portable_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = args_for(tmp_path)
    prepared = computer.handle(args)
    assert not args.home.exists() and not args.output.exists()
    handoff = ComputerHandoff.model_validate(handoff_document())
    assert "\nValue hypothesis (unverified): " + handoff.strategy.valueHypothesis + "\n" in handoff.task.goal
    assert "\nCandidate strategies:\n" in handoff.task.goal
    for index, hypothesis in enumerate(handoff.strategy.hypotheses):
        assert f"{index + 1}. {hypothesis}\n" in handoff.task.goal
    assert "\nProposed combination: " + handoff.strategy.combination + "\n" in handoff.task.goal
    assert "\nAlternative formulation: " + handoff.strategy.reframing + "\n" in handoff.task.goal
    assert "strategy candidates considered, the approach actually tested" in handoff.task.goal
    assert "Distinguish tested results from untested ideas." in handoff.task.goal
    assert prepared["handoff"]["executionContext"] == handoff.context()
    args.computer_command, args.permit = "run", prepared["commitment"]
    install_doubles(monkeypatch)
    result = computer.handle(args)
    returned = json.loads((args.output / "computer-return.json").read_text())
    assert result["state"] == "review" and returned["verified"] is False
    assert returned["receipt"]["execution_context"] == handoff.context()
    assert returned["receipt"]["provider"] == returned["execution"]["provider"]
    assert returned["observedText"] == "Controlled double: recommendation for human review"
    assert returned["signedReceipt"]["payload"] == Journal.document(returned["receipt"])
    assert returned["handoffSha256"] == hashlib.sha256(canonical(handoff.document())).hexdigest()
    execution = returned["execution"]
    assert returned["taskCommitment"] == digest(
        "computer-task",
        {
            "task": handoff_document()["task"],
            "provider": execution["provider"],
            "image": execution["image"],
            "worker_sha256": execution["workerSha256"],
            "execution_context": returned["executionContext"],
        },
    )
    assert returned["authority"] == "none" and returned["settlement"] == "not_connected"
    assert returned["receipt"]["billing"] == "UNKNOWN"
    assert json.loads((args.output / "handoff.json").read_text()) == handoff_document()


def test_wrong_project_permit_never_opens_a_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = args_for(tmp_path)
    prepared = computer.handle(args)
    document = handoff_document()
    document["strategy"]["selected"] = "combine"
    document["task"]["goal"] = ComputerStrategy.model_validate(document["strategy"]).goal()
    args.file.write_bytes(canonical(document))
    args.computer_command, args.permit = "run", prepared["commitment"]
    install_doubles(monkeypatch)
    with pytest.raises(ValueError, match="permit"):
        computer.handle(args)
    assert not args.output.exists()


def test_interrupted_return_keeps_uncertain_effect_and_no_success_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = args_for(tmp_path)
    prepared = computer.handle(args)
    args.computer_command, args.permit = "run", prepared["commitment"]
    install_doubles(monkeypatch, fail=True)
    with pytest.raises(OSError, match="Controlled uncertain"):
        computer.handle(args)
    returned = json.loads((args.output / "computer-return.json").read_text())
    assert returned["receipt"]["state"] == "interrupted"
    assert returned["receipt"]["events"][-1]["status"] == "reserved"
    assert returned["observedText"] is None and returned["verified"] is False
    assert returned["receipt"]["cleanup"] == "VERIFIED"


def test_return_refuses_modified_visible_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = args_for(tmp_path)
    prepared = computer.handle(args)
    args.computer_command, args.permit = "run", prepared["commitment"]
    install_doubles(monkeypatch)
    computer.handle(args)
    (args.output / "visible-text.txt").write_text("Changed after native receipt")
    advisor = computer.HTTPAdvisor(args.provider, args.model, args.base_url, "")
    with pytest.raises(ValueError, match="digest"):
        write_computer_return(
            ComputerHandoff.model_validate(handoff_document()), Journal(args.home), advisor, args.image, args.output
        )


@pytest.mark.parametrize("interrupted", [False, True])
def test_return_retains_signed_session_source_after_reader_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interrupted: bool
) -> None:
    reader = tmp_path / "retained-reader.py"
    reader.write_bytes(computer.READ_WORKER.read_bytes())
    monkeypatch.setattr(computer, "READ_WORKER", reader)
    args = args_for(tmp_path)
    approved = computer.worker_source_digest()
    prepared = computer.handle(args)
    args.computer_command, args.permit = "run", prepared["commitment"]
    install_doubles(monkeypatch, fail=interrupted)
    real_run = computer.run_session

    def run_then_replace(*values: Any, **options: Any) -> dict[str, Any]:
        try:
            return real_run(*values, **options)
        finally:
            reader.write_text("raise RuntimeError('replacement must not select exported source identity')\n")

    monkeypatch.setattr(computer, "run_session", run_then_replace)
    if interrupted:
        with pytest.raises(OSError, match="Controlled uncertain"):
            computer.handle(args)
    else:
        computer.handle(args)
    returned = json.loads((args.output / "computer-return.json").read_text())
    assert computer.worker_source_digest() != approved
    assert returned["taskCommitment"] == prepared["commitment"]
    assert returned["execution"]["workerSha256"] == approved
    assert returned["receipt"]["worker_sha256"] == approved
    assert returned["signedReceipt"]["payload"]["worker_sha256"] == approved
    assert returned["receipt"]["state"] == ("interrupted" if interrupted else "review")
    assert returned["authority"] == "none" and returned["verified"] is False
