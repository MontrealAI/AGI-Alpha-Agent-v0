# SPDX-License-Identifier: Apache-2.0
"""Complete campaign units, durable freeze, bounded costs and leakage controls."""

import argparse
import uuid

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.campaign_experiment import (
    CampaignExperiment,
    CampaignUnit,
    DiscoveryPolicy,
    PolicyStudy,
)
from alpha_factory_v1.core.runtime.successor.transformation import (
    DiscoveryRequest,
    DiscoveryLoop,
    SourceClaim,
    SourceDocument,
    pilot_request,
    validate_envelope,
)


def document(label, trivial=False):
    weights = [2, 1, 5, 4]
    dependencies = [[], [], ["b"], ["b"]]
    if trivial:
        weights, dependencies = [5, 4, 2, 1], [[], [], [], []]
    return SourceDocument(
        title="Constructed public release-note argument " + label,
        source_url="https://example.org/constructed-study/" + label,
        claims=[
            SourceClaim(
                id=name,
                text=f"Constructed {label} clause {name}.",
                weight=weight,
                depends_on=deps,
                provenance="explicit finite fixture; not external evidence",
            )
            for name, weight, deps in zip("abcd", weights, dependencies)
        ],
    )


def unit(label, *, trivial=False, exhausted=False):
    raw = pilot_request().model_dump()
    raw["development"] = [document(label + "-development", trivial).model_dump()]
    raw["charter"]["max_clauses"] = 2
    if exhausted:
        raw["charter"]["budgets"]["execution_units"] = 0
    return CampaignUnit(
        unit_id=label, request=DiscoveryRequest.model_validate(raw), terminal=[document(label + "-terminal", trivial)]
    )


def spec():
    charter = pilot_request().charter.model_dump()
    charter["max_clauses"] = 2
    return PolicyStudy(
        study_id=str(uuid.uuid4()),
        charter=charter,
        terminal_campaigns=2,
        population="constructed independent graph campaigns, not human outcomes",
        sampling_protocol="separately supplied whole campaigns after policy freeze; fixture only",
        search_cost_ppm_per_unit=1,
        incumbent_policy="enumerate-all",
        policies=[
            DiscoveryPolicy(
                identity="enumerate-all",
                operator_ids=["representation", "production", "complementary"],
                max_candidates=5,
            ),
            DiscoveryPolicy(identity="direct-pair", operator_ids=["complementary"], max_candidates=3),
            DiscoveryPolicy(identity="fixed-frame", operator_ids=[], max_candidates=2),
        ],
    )


def prepare(tmp_path, *, exhausted=False):
    experiment = CampaignExperiment(Journal.initialize(tmp_path / "agent"))
    basis = spec()
    if exhausted:
        raw = basis.model_dump()
        raw["charter"]["budgets"]["execution_units"] = 0
        basis = PolicyStudy.model_validate(raw)
    proposed = experiment.create(basis)
    experiment.approve(basis.study_id, proposed["binding"])
    return experiment, basis


def test_complete_fresh_campaigns_learn_bounded_search_policy_and_keep_native_controls(tmp_path):
    experiment, basis = prepare(tmp_path)
    trained = experiment.train(basis.study_id, [unit("training-one"), unit("training-two")])
    assert trained["state"] == "trained"
    assert trained["freeze"]["manifest"]["selected_policy"] == "direct-pair"
    assert len(trained["training"]["runs"]) == 6
    terminal = [unit("confirmation-one"), unit("confirmation-two")]
    result = experiment.confirm(basis.study_id, terminal, trained["freeze"]["digest"])
    assert result["state"] == "completed"
    assert result["confirmation"]["observed_policy_gain_ppm"] > 0
    assert len(result["confirmation"]["paired_campaign_differences_ppm"]) == 2
    assert result["approval"] is None
    exported = experiment.export(basis.study_id)
    for run in result["confirmation"]["runs"]:
        native = validate_envelope(exported["campaigns"][run["campaign_id"]])
        assert native["result"]["beats_unrestricted"] is False
        assert native["review"]["status"] == "pending"
    assert experiment.confirm(basis.study_id, terminal, trained["freeze"]["digest"])["digest"] == result["digest"]


def test_fixed_frame_is_retained_when_changes_only_add_search_cost(tmp_path):
    experiment, basis = prepare(tmp_path)
    basis_raw = basis.model_dump()
    basis_raw.update(study_id=str(uuid.uuid4()), incumbent_policy="fixed-frame")
    basis = PolicyStudy.model_validate(basis_raw)
    proposed = experiment.create(basis)
    experiment.approve(basis.study_id, proposed["binding"])
    trained = experiment.train(basis.study_id, [unit("simple", trivial=True)])
    assert trained["freeze"]["manifest"]["selected_policy"] == "fixed-frame"


def test_no_construction_before_explicit_comparison_approval(tmp_path):
    experiment = CampaignExperiment(Journal.initialize(tmp_path / "agent"))
    basis = spec()
    experiment.create(basis)
    with pytest.raises(PermissionError):
        experiment.train(basis.study_id, [unit("unauthorized")])
    with pytest.raises(Conflict):
        experiment.approve(basis.study_id, "f" * 64)


def test_terminal_sample_is_frozen_whole_and_cannot_be_replaced(tmp_path):
    experiment, basis = prepare(tmp_path)
    with pytest.raises(Conflict):
        experiment.confirm(basis.study_id, [unit("early")], "f" * 64)
    trained = experiment.train(basis.study_id, [unit("train")])
    with pytest.raises(ValueError, match="entire"):
        experiment.confirm(basis.study_id, [unit("partial")], trained["freeze"]["digest"])
    experiment.confirm(basis.study_id, [unit("first"), unit("second")], trained["freeze"]["digest"])
    with pytest.raises(Conflict, match="replaced"):
        experiment.confirm(basis.study_id, [unit("third"), unit("fourth")], trained["freeze"]["digest"])


def test_renaming_study_or_clause_metadata_does_not_reset_known_exposure(tmp_path):
    experiment, basis = prepare(tmp_path)
    training = unit("original")
    experiment.train(basis.study_id, [training])
    other = spec()
    proposed = experiment.create(other)
    experiment.approve(other.study_id, proposed["binding"])
    raw = training.model_dump()
    raw["unit_id"] = "renamed"
    raw["request"]["campaign_id"] = str(uuid.uuid4())
    raw["request"]["development"][0]["title"] = "renamed title"
    raw["request"]["development"][0]["claims"][0]["text"] = raw["request"]["development"][0]["claims"][0][
        "text"
    ].upper()
    with pytest.raises(Conflict, match="known"):
        experiment.train(other.study_id, [CampaignUnit.model_validate(raw)])


def test_restart_after_completed_child_resumes_without_second_terminal_run(tmp_path, monkeypatch):
    experiment, basis = prepare(tmp_path)
    original = experiment._campaign
    failed = False

    def interrupted(*args, **kwargs):
        nonlocal failed
        result = original(*args, **kwargs)
        if not failed:
            failed = True
            raise RuntimeError("process interrupted after durable child completed")
        return result

    monkeypatch.setattr(experiment, "_campaign", interrupted)
    training = [unit("restart")]
    with pytest.raises(RuntimeError):
        experiment.train(basis.study_id, training)
    reopened = CampaignExperiment(Journal(experiment.journal.root))
    trained = reopened.train(basis.study_id, training)
    assert trained["state"] == "trained"
    assert len(trained["training"]["runs"]) == 3
    assert len({run["campaign_id"] for run in trained["training"]["runs"]}) == 3


def test_pause_cancel_stop_and_stale_code_block_work(tmp_path, monkeypatch):
    experiment, basis = prepare(tmp_path)
    experiment.control(basis.study_id, "pause")
    with pytest.raises(Conflict, match="paused"):
        experiment.train(basis.study_id, [unit("paused")])
    experiment.control(basis.study_id, "resume")
    monkeypatch.setattr("alpha_factory_v1.core.runtime.successor.campaign_experiment._engine_digest", lambda: "f" * 64)
    with pytest.raises(Conflict, match="changed"):
        experiment.train(basis.study_id, [unit("stale")])
    experiment.control(basis.study_id, "cancel")
    with pytest.raises(Conflict, match="canceled"):
        experiment.train(basis.study_id, [unit("canceled")])


def test_failed_terminal_evidence_stays_inconclusive_not_zero_or_gain(tmp_path):
    experiment, basis = prepare(tmp_path, exhausted=True)
    trained = experiment.train(basis.study_id, [unit("failed-training", exhausted=True)])
    result = experiment.confirm(
        basis.study_id,
        [unit("failed-one", exhausted=True), unit("failed-two", exhausted=True)],
        trained["freeze"]["digest"],
    )
    evidence = result["confirmation"]
    assert evidence["observed_policy_gain_ppm"] is None
    assert evidence["paired_campaign_differences_ppm"] is None
    assert all(run["status"] == "inconclusive" for run in evidence["runs"])
    assert all(run["terminal_score_ppm"] is None for run in evidence["runs"])


def test_initial_agents_archive_and_evaluator_cannot_be_changed_by_policy():
    raw = spec().model_dump()
    raw["archive_access"] = "optimizer-private-history"
    with pytest.raises(ValidationError):
        PolicyStudy.model_validate(raw)
    with pytest.raises(ValidationError):
        DiscoveryPolicy(identity="gaming", operator_ids=[], max_candidates=2, evaluator="easier")


def test_child_campaign_cannot_substitute_purpose_or_resource_basis(tmp_path):
    experiment, basis = prepare(tmp_path)
    raw = unit("substitution").model_dump()
    raw["request"]["charter"]["purpose"] = "a different goal"
    with pytest.raises(PermissionError, match="purpose"):
        experiment.train(basis.study_id, [CampaignUnit.model_validate(raw)])
    assert experiment.show(basis.study_id)["state"] == "proposed"


def test_duplicate_train_during_terminal_batch_cannot_reset_freeze(tmp_path):
    experiment, basis = prepare(tmp_path)
    training = [unit("train-before-terminal")]
    trained = experiment.train(basis.study_id, training)
    reserved = experiment._reserve(basis.study_id, [unit("terminal-one"), unit("terminal-two")], "confirmation")
    replay = experiment.train(basis.study_id, training)
    assert replay["state"] == "confirming"
    assert replay["freeze"] == trained["freeze"]
    assert replay["digest"] == reserved["digest"]


def test_parent_pause_between_readiness_and_child_cannot_execute(tmp_path, monkeypatch):
    experiment, basis = prepare(tmp_path)
    original = experiment._campaign

    def pause_before_child(*args, **kwargs):
        experiment.control(basis.study_id, "pause")
        return original(*args, **kwargs)

    monkeypatch.setattr(experiment, "_campaign", pause_before_child)
    with pytest.raises(Conflict, match="paused"):
        experiment.train(basis.study_id, [unit("pause-race")])
    exported = experiment.export(basis.study_id)
    assert experiment.show(basis.study_id)["state"] == "paused"
    assert (
        sum(
            child["spent"]["search_units"] + child["spent"]["execution_units"]
            for child in exported["pending_campaigns"].values()
        )
        == 0
    )


@pytest.mark.parametrize("control", ["pause", "cancel"])
def test_parent_control_between_native_phases_retains_partial_costs(tmp_path, monkeypatch, control):
    experiment, basis = prepare(tmp_path)
    original = DiscoveryLoop.step

    def controlled(loop, *args, **kwargs):
        record = original(loop, *args, **kwargs)
        if record["state"] == "developed":
            experiment.control(basis.study_id, control)
        return record

    monkeypatch.setattr(DiscoveryLoop, "step", controlled)
    with pytest.raises(Conflict):
        experiment.train(basis.study_id, [unit("phase-control")])
    exported = experiment.export(basis.study_id)
    partial = [child for child in exported["pending_campaigns"].values() if child["state"] == "developed"]
    assert len(partial) == 1
    assert partial[0]["spent"]["search_units"] > 0
    assert partial[0]["spent"]["execution_units"] == 0
    assert experiment.show(basis.study_id)["state"] == ("paused" if control == "pause" else "canceled")


def test_ordinary_native_history_is_known_exposure(tmp_path):
    experiment, basis = prepare(tmp_path)
    known = unit("ordinary-native")
    loop = DiscoveryLoop(experiment.journal)
    current = loop.create(known.request)
    loop.approve(known.request.campaign_id, current["binding_digest"])
    for operation in ("diagnose", "develop", "freeze"):
        current = loop.step(known.request.campaign_id, operation_id=operation)
    loop.confirm(known.request.campaign_id, known.terminal, current["freeze"]["digest"])
    with pytest.raises(Conflict, match="known"):
        experiment.train(basis.study_id, [known])


def test_ordinary_native_api_cannot_bypass_parent_pause_or_cancel(tmp_path, monkeypatch):
    experiment, basis = prepare(tmp_path)
    training = unit("ordinary-control")
    original = DiscoveryLoop.step

    def pause_after_develop(loop, *args, **kwargs):
        current = original(loop, *args, **kwargs)
        if current["state"] == "developed":
            experiment.control(basis.study_id, "pause")
        return current

    monkeypatch.setattr(DiscoveryLoop, "step", pause_after_develop)
    with pytest.raises(Conflict):
        experiment.train(basis.study_id, [training])
    partial = next(
        child
        for child in experiment.export(basis.study_id)["pending_campaigns"].values()
        if child["state"] == "developed"
    )
    child_id = partial["request"]["campaign_id"]
    native = DiscoveryLoop(experiment.journal)
    before = native.show(child_id)
    with pytest.raises(Conflict, match="lease"):
        native.step(child_id, operation_id="bypass-parent")
    with pytest.raises(Conflict, match="lease"):
        native.approve(child_id, before["binding_digest"])
    assert native.show(child_id) == before
    experiment.control(basis.study_id, "cancel")
    with pytest.raises(Conflict, match="lease"):
        native.step(child_id, operation_id="bypass-cancel")


def test_cli_export_and_no_overwrite(tmp_path):
    from alpha_factory_v1.core.runtime.successor.campaign_experiment_cli import handle
    from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads

    experiment, basis = prepare(tmp_path)
    output = tmp_path / "evidence.json"
    args = argparse.Namespace(
        home=experiment.journal.root, output=output, study_action="export", study_id=basis.study_id
    )
    result = handle(args)
    assert result["state"] == "proposed"
    assert safe_json_loads(output.read_bytes())["schema"] == "discovery-policy-evidence/v1"
    with pytest.raises(FileExistsError):
        handle(args)


def test_parent_lease_cannot_be_reused_for_unplanned_child_or_changed_input(tmp_path):
    from alpha_factory_v1.core.runtime.successor.campaign_experiment import study_request

    experiment, basis = prepare(tmp_path)
    training = unit("owned-child")
    experiment._reserve(basis.study_id, [training], "training")
    expected = study_request(basis, training, basis.policies[0], "training")
    for change in ("identity", "source"):
        raw = expected.model_dump()
        if change == "identity":
            raw["campaign_id"] = str(uuid.uuid4())
        else:
            raw["development"][0]["claims"][0]["text"] += " Changed input."
        altered = DiscoveryRequest.model_validate(raw)
        record = experiment.loop.create(altered)
        with pytest.raises(Conflict, match="lease"):
            experiment.loop.approve(altered.campaign_id, record["binding_digest"])
