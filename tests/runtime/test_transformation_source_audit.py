# SPDX-License-Identifier: Apache-2.0
"""Executed formulation ablations, exact reports and separately signed measurement."""
from __future__ import annotations

import copy
import ast
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import transformation_source_audit as s
from alpha_factory_v1.core.runtime.successor.measurement import MeasurementLedger
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.transformation_source_audit_cli import main
from alpha_factory_v1.core.runtime.successor.trust import local_principals, sign_record


def source(path, body):
    raw = body.encode()
    return s.SourceFile(
        path=path,
        source=body,
        sha256=hashlib.sha256(raw).hexdigest(),
        git_blob=hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
    )


@pytest.mark.parametrize(
    "statement, expected",
    [
        ("first, (second, third) = (1, (2, 3))", [("first", 1), ("second", 2), ("third", 3)]),
        ("[first, [second, third]] = [1, [2, 3]]", [("first", 1), ("second", 2), ("third", 3)]),
        ("record.count: int = 4", [("count", 4)]),
        ("settings['count'] += 5", [("settings", 5), ("count", 5)]),
        ("(count := 6)", [("count", 6)]),
        ("settings[index] = 7", [("settings", 7), ("index", 7)]),
        ("settings[first, (second, third)] = 8", [("settings", 8), ("first", 8), ("second", 8), ("third", 8)]),
        ("settings[labels.index] = 9", [("settings", 9), ("index", 9), ("labels", 9)]),
        ("settings['count', index] = 10", [("settings", 10), ("count", 10), ("index", 10)]),
    ],
)
def test_static_assignment_binding_names_and_literal_values(statement, expected):
    node = ast.parse(statement).body[0]
    if isinstance(node, ast.Expr):
        node = node.value
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    actual = [
        (name, ast.literal_eval(value))
        for target in targets
        for name, value in s._assignment_bindings(target, node.value)
    ]
    assert actual == expected
    source("fixture/ordinary.py", statement)


def test_static_assignment_unknown_and_starred_values_remain_conservative():
    for statement in ["first, (second, third) = supplied", "first, *remaining = (1, 2, 3)"]:
        node = ast.parse(statement).body[0]
        bindings = list(s._assignment_bindings(node.targets[0], node.value))
        assert [name for name, _ in bindings] == (
            ["first", "second", "third"] if "supplied" in statement else ["first", "remaining"]
        )
        assert all(value is node.value for _, value in bindings)
        source("fixture/ordinary.py", statement)


def package(root="fixture", stale=False, cycle=False):
    prefix = "# SPDX-License-Identifier: Apache-2.0\n" + f"CAPTURE = {root!r}\n"
    return s.SourcePackage(
        repository="public/fixture",
        commit="a" * 40,
        root=root,
        stale_worker_proposal=stale,
        files=[
            source(
                root + "/a.py",
                prefix
                + "from . import b, c\ndef alpha(): pass\n"
                + ("def fresh_function(): return 7\n" if root != "fixture" else ""),
            ),
            source(root + "/b.py", prefix + "from .c import gamma\nclass Beta: pass\n"),
            source(root + "/c.py", prefix + ("from .a import alpha\n" if cycle else "") + "def gamma(): pass\n"),
        ],
    )


def request(loop, dev=None, confirm=None, **changes):
    dev = dev or [package()]
    confirm = confirm or [package("fresh", stale=True)]
    return s.AuditRequest(
        campaign_id="921719bd-e52b-4d57-a4f6-6516df6b8260",
        development=dev,
        confirmation_digest=digest("source-audit-confirmation", confirm),
        confirmation_count=len(confirm),
        permitted_actions=["parse-static-source", "compare-local", "write-artifact"],
        **{**loop.measurement_context(), **changes},
    )


def prepared(tmp_path, **changes):
    loop = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "journal"))
    req = request(loop, **changes)
    queued = loop.create(req)
    loop.approve(req.campaign_id, queued["binding_digest"])
    return loop, req


def test_all64_execute_same_complete_exact_report_and_manual_closure():
    p = package()
    expected = s.reference_report(p, s.Meter(1_000_000))
    assert expected["files"][0]["transitive_dependencies"] == ["fixture.b", "fixture.c"]
    assert expected["files"][1]["public_symbols"] == ["Beta"]
    assert expected["files"][2]["license"] == "Apache-2.0"
    artifacts = []
    for program in s.programs():
        meter = s.Meter(1_000_000)
        result = s.execute(p, program, meter)
        assert result["exact"] and result["artifact"] == expected
        assert meter.costs["read"] > 0 and meter.costs["check"] > 0
        artifacts.append(result["artifact_digest"])
    assert len(set(artifacts)) == 1


@pytest.mark.parametrize("axis", s.AXES)
def test_each_axis_changes_executed_trace_and_is_ablated(axis):
    p = package()
    old, new = s.Meter(1_000_000), s.Meter(1_000_000)
    unchanged = s.execute(p, s.AuditProgram(), old)
    changed = s.execute(p, s.AuditProgram.model_validate({axis: True}), new)
    assert unchanged["artifact"] == changed["artifact"]
    assert old.trace != new.trace and old.costs != new.costs
    event = {
        "indexed": "keyed-query",
        "query_once": "retain-facts",
        "dependency_queue": "dependency-queue-pop",
        "fragments": "reuse-fragment",
        "package_batch": "package-job",
        "checked_handoff": "checked-CAS",
    }[axis]
    assert old.trace[event] == 0 and new.trace[event] > 0
    if axis == "query_once":
        assert new.trace["parse-ast"] < old.trace["parse-ast"]
    if axis == "package_batch":
        assert new.trace["package-job"] == len(p.files)
        assert old.trace["per-file-subtask"] == 4 * len(p.files)


def test_dependency_work_queue_handles_cycle_without_dropping_self_reachable_peers():
    p = package(cycle=True)
    for program in [s.AuditProgram(), s.AuditProgram(dependency_queue=True)]:
        result = s.execute(p, program, s.Meter(1_000_000))
        assert result["exact"]
        for row in result["artifact"]["files"]:
            assert row["transitive_dependencies"] == sorted({"fixture.a", "fixture.b", "fixture.c"} - {row["module"]})


def test_checked_handoff_rejects_actual_stale_overwrite_same_goal_and_tools():
    p = package(stale=True)
    before = s.execute(p, s.AuditProgram(), s.Meter(1_000_000))
    meter = s.Meter(1_000_000)
    after = s.execute(p, s.AuditProgram(checked_handoff=True), meter)
    assert not before["exact"] and before["artifact"]["files"][0]["public_symbols"] == ["STALE_UNAPPROVED_SYMBOL"]
    assert after["exact"] and meter.trace["reject-stale-or-invalid"] == 4


def test_public_source_is_parsed_never_executed_and_dynamic_unknowns_stay_visible(tmp_path):
    marker = tmp_path / "must-not-exist"
    f = source(
        "fixture/a.py", f"open({str(marker)!r},'w').write('executed')\n__import__('socket')\ndef alpha(): pass\n"
    )
    p = package().model_copy(update={"files": [f]})
    result = s.execute(p, s.AuditProgram(), s.Meter(1_000_000))
    assert not marker.exists()
    assert result["artifact"]["files"][0]["findings"] == ["missing-SPDX-header", "dynamic-import-not-resolved"]


def test_wire_hash_bounds_path_and_exact_scalar_guards():
    p = package().model_dump()
    for mutate in [
        lambda x: x["files"][0].update(source="wrong"),
        lambda x: x["files"][0].update(path="fixture//a.py"),
        lambda x: x.update(files=x["files"] * 2),
        lambda x: x.update(stale_worker_proposal=1),
        lambda x: x.update(root="fixture//nested"),
    ]:
        bad = copy.deepcopy(p)
        mutate(bad)
        with pytest.raises(ValidationError):
            s.SourcePackage.model_validate(bad)
    with pytest.raises(ValidationError):
        s.AuditProgram(indexed=1)


def test_no_approval_no_authority_no_paid_cap(tmp_path):
    loop = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "journal"))
    req = request(loop)
    queued = loop.create(req)
    with pytest.raises(PermissionError):
        loop.freeze(req.campaign_id)
    with pytest.raises(Conflict):
        loop.approve(req.campaign_id, "0" * 64)
    for changes in [{"publicOnly": 1}, {"execution_units": True}, {"USDCBaseUnits": "1"}, {"AGIALPHABaseUnits": "1"}]:
        with pytest.raises(ValidationError):
            s.AuditRequest.model_validate({**req.model_dump(), **changes})
    assert loop.show(req.campaign_id)["revision"] == queued["revision"]
    envelope = loop.envelope(req.campaign_id)
    assert envelope["authority"] == "none" and not envelope["native_v1_compatible"]


def test_full_campaign_freeze_fresh_confirmation_negative_retained_and_exact_replay(tmp_path):
    loop, req = prepared(tmp_path)
    frozen = loop.freeze(req.campaign_id)
    assert frozen["state"] == "frozen" and len(frozen["development"][0]["methods"]) == 64
    result = loop.confirm(req.campaign_id, [package("fresh", stale=True)], frozen["freeze"]["digest"])
    assert result["state"] == "completed" and result["result"]["decision"] == "reject-frozen-candidate"
    assert len(result["confirmation"]["rows"][0]["methods"]) == 64
    assert result["result"]["hand_engineered"] in result["result"]["valid_totals"]
    assert not result["result"]["beats_unrestricted"]
    assert result["result"]["full_campaign_units"] == sum(result["spent"].values())
    again = loop.confirm(req.campaign_id, [package("fresh", stale=True)], frozen["freeze"]["digest"])
    assert again["revision"] == result["revision"] and again["spent"] == result["spent"]
    with pytest.raises(Conflict):
        loop.confirm(req.campaign_id, [package("changed")], frozen["freeze"]["digest"])


def test_confirmation_must_match_all_committed_packages_and_fresh_source(tmp_path):
    loop, req = prepared(tmp_path)
    frozen = loop.freeze(req.campaign_id)
    with pytest.raises(ValueError):
        loop.confirm(req.campaign_id, [package("wrong")], frozen["freeze"]["digest"])
    with pytest.raises(Conflict):
        loop.confirm(req.campaign_id, [package("fresh", stale=True)], "0" * 64)
    other = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "other"))
    repeated = [package(stale=True)]
    r = request(other, confirm=repeated)
    q = other.create(r)
    other.approve(r.campaign_id, q["binding_digest"])
    f = other.freeze(r.campaign_id)
    rejected = other.confirm(r.campaign_id, repeated, f["freeze"]["digest"])
    assert rejected["result"]["reason"] == "confirmation-source-already-observed"
    assert not rejected["confirmation"]["complete"]


def test_budget_partial_evidence_terminal_and_no_free_retry(tmp_path):
    loop, req = prepared(tmp_path, execution_units=1000)
    record = loop.freeze(req.campaign_id)
    assert record["state"] == "completed" and record["result"]["metrics"] is None
    assert 0 < sum(record["spent"].values()) <= 1010
    with pytest.raises(Conflict):
        loop.freeze(req.campaign_id)


def test_pause_resume_cancel_native_stop_and_source_binding(tmp_path, monkeypatch):
    loop, req = prepared(tmp_path)
    loop.control(req.campaign_id, "pause")
    with pytest.raises(Conflict):
        loop.freeze(req.campaign_id)
    loop.control(req.campaign_id, "resume")
    with loop.journal.transaction() as cx:
        loop.journal.append(cx, "@control", {"state": "stopped"})
    with pytest.raises(Conflict):
        loop.freeze(req.campaign_id)
    with loop.journal.transaction() as cx:
        loop.journal.append(cx, "@control", {"state": "ready"})
    monkeypatch.setattr(s, "_source_digest", lambda: "f" * 64)
    with pytest.raises(Conflict):
        loop.freeze(req.campaign_id)
    monkeypatch.undo()
    loop.control(req.campaign_id, "cancel")
    with pytest.raises(Conflict):
        loop.control(req.campaign_id, "resume")
    assert loop.show(req.campaign_id)["approval"] is None


def test_concurrent_restart_freeze_is_charged_once(tmp_path):
    loop, req = prepared(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(
            pool.map(lambda _: s.SourceAuditDiscovery(Journal(loop.journal.root)).freeze(req.campaign_id), range(2))
        )
    assert first["revision"] == second["revision"] and first["spent"] == second["spent"]


def sign_revision(loop, keys, proposal, previous=None, wrong_cases=False):
    instrument = s.exact_instrument()
    validation = sign_record(
        keys["local-verifier"],
        "local-verifier",
        "measurement-validation",
        {
            "journal_identity": loop.journal.identity,
            "previous_instrument": previous,
            "instrument_digest": digest("measurement-instrument", instrument),
            "diagnosis": "file-count proxy accepted invented symbols",
            "scope": "constructed local finite audit only",
            "cases": [] if wrong_cases else proposal["proposal"]["cases"],
        },
    )
    approval = sign_record(
        keys["local-controller"],
        "local-controller",
        "measurement-approval",
        {
            "journal_identity": loop.journal.identity,
            "previous_instrument": previous,
            "instrument_digest": digest("measurement-instrument", instrument),
            "validation_digest": digest("measurement-validation", validation.model_dump()),
        },
    )
    return validation, approval


def test_seventh_axis_requires_supplied_distinct_signed_ledger_revision_and_common_new_epoch(tmp_path):
    journal = Journal.initialize(tmp_path / "journal")
    trust, keys = local_principals()
    ledger = MeasurementLedger(journal, trust)
    loop = s.SourceAuditDiscovery(journal, ledger)
    req = request(loop)
    queued = loop.create(req)
    loop.approve(req.campaign_id, queued["binding_digest"])
    proposal = loop.propose_revision(package())
    assert loop.measurement_context()["measurement_epoch"] == 0 and not proposal["authority_granted"]
    assert proposal["proposal"]["cases"][0]["old_score_ppm"] == 1_000_000
    assert proposal["proposal"]["cases"][0]["new_score_ppm"] == 0
    invalid = sign_revision(loop, keys, proposal, wrong_cases=True)
    with pytest.raises(Conflict):
        loop.revise_measurement(proposal["proposal_digest"], *invalid, operation_id="bad")
    validation, approval = sign_revision(loop, keys, proposal)
    with pytest.raises(ValueError):
        loop.revise_measurement(proposal["proposal_digest"], validation, validation, operation_id="same-role")
    epoch = loop.revise_measurement(proposal["proposal_digest"], validation, approval, operation_id="revision-one")
    assert epoch["epoch"] == 1 and loop.measurement_context()["measurement_epoch"] == 1
    with pytest.raises(Conflict):
        loop.freeze(req.campaign_id)
    new_req = request(loop, dev=[package(stale=True)])
    new_req = new_req.model_copy(update={"campaign_id": "f2aa9b52-b0bd-4dfd-9a09-29b8b354d743"})
    q = loop.create(new_req)
    loop.approve(new_req.campaign_id, q["binding_digest"])
    frozen = loop.freeze(new_req.campaign_id)
    methods = frozen["development"][0]["methods"]
    assert methods["000000"]["score_ppm"] == 0 and methods["111111"]["score_ppm"] == 1_000_000
    assert frozen["freeze"]["manifest"]["measurement_epoch"] == 1
    result = loop.confirm(new_req.campaign_id, [package("fresh", stale=True)], frozen["freeze"]["digest"])
    assert not result["result"]["beats_unrestricted"] and not result["result"]["authority_granted"]
    assert ledger.snapshot()["attempts"] == []  # No independent statistical confirmation was manufactured.


def test_revision_freezes_caller_owned_signed_payload_before_ledger_handoff(tmp_path, monkeypatch):
    journal = Journal.initialize(tmp_path / "journal")
    trust, keys = local_principals()
    ledger = MeasurementLedger(journal, trust)
    loop = s.SourceAuditDiscovery(journal, ledger)
    proposal = loop.propose_revision(package())
    expected_cases = copy.deepcopy(proposal["proposal"]["cases"])
    validation, approval = sign_revision(loop, keys, proposal)
    native = ledger.revise_instrument

    def mutate_caller_then_revise(*args, **kwargs):
        validation.payload["cases"][0]["evidence_digest"] = "f" * 64
        approval.payload["validation_digest"] = "0" * 64
        return native(*args, **kwargs)

    monkeypatch.setattr(ledger, "revise_instrument", mutate_caller_then_revise)
    result = loop.revise_measurement(proposal["proposal_digest"], validation, approval, operation_id="stable-revision")
    assert result["validation"]["payload"]["cases"] == expected_cases


def test_measurement_cannot_come_from_divergent_copied_journal_with_same_identity(tmp_path):
    original = Journal.initialize(tmp_path / "original")
    shutil.copytree(original.root, tmp_path / "copy")
    copied = Journal(tmp_path / "copy")
    assert original.identity == copied.identity
    trust, _ = local_principals()
    ledger = MeasurementLedger(copied, trust)
    with pytest.raises(ValueError, match="this journal"):
        s.SourceAuditDiscovery(original, ledger)


def test_actual_immutable_public_fixture_and_cli_new_paths(tmp_path):
    fixture = Path(__file__).resolve().parents[2] / "examples/transformational-source-audit/fixture.json"
    data = json.loads(fixture.read_text())
    assert data["source_commit"] == "d0d18127e3d75b2b1bd13ca448265ba7e75fc21e"
    assert all(
        f["source"].startswith("# SPDX-License-Identifier: Apache-2.0")
        for p in data["development"] + data["confirmation"]
        for f in p["files"]
    )
    output = tmp_path / "result.json"
    args = [
        "--home",
        str(tmp_path / "native"),
        "--output",
        str(output),
        "demo",
        str(fixture),
        "--approve-free-local-audit",
    ]
    result = main(args)
    record = json.loads(output.read_text())
    assert not result["authority_granted"] and record["campaign"]["state"] == "completed"
    assert record["campaign"]["confirmation"]["complete"]
    assert record["campaign"]["result"]["decision"] == "reject-frozen-candidate"
    with pytest.raises(FileExistsError):
        main(args)
    assert not (tmp_path / "other.json").exists()


def test_module_collision_refuses_and_from_import_captured_submodule_is_explicit():
    p = package()
    with pytest.raises(ValidationError, match="duplicate Python module"):
        s.SourcePackage.model_validate(
            {
                **p.model_dump(),
                "files": [
                    source("fixture/foo.py", "x=1\n").model_dump(),
                    source("fixture/foo/__init__.py", "x=2\n").model_dump(),
                ],
            }
        )
    files = [
        source("fixture/__init__.py", "x=1\n"),
        source("fixture/foo.py", "def value():pass\n"),
        source("fixture/use.py", "from fixture import foo\n"),
    ]
    result = s.execute(p.model_copy(update={"files": files}), s.AuditProgram(), s.Meter(1_000_000))
    row = next(row for row in result["artifact"]["files"] if row["module"] == "fixture.use")
    assert row["captured_dependencies"] == ["fixture", "fixture.foo"]
    assert "not runtime resolution" in result["artifact"]["dependency_semantics"]
    relabeled = copy.deepcopy(p.model_dump())
    relabeled.update(repository="other/repository", commit="b" * 40, root="renamed")
    for file in relabeled["files"]:
        file["path"] = file["path"].replace("fixture/", "renamed/")
    assert s.source_fingerprint(s.SourcePackage.model_validate(relabeled)) == s.source_fingerprint(p)


def test_relative_wildcard_depends_on_initializer_and_its_helper_with_manual_expected_closure():
    files = [
        source("root/__init__.py", "from . import helper\n"),
        source("root/helper.py", "def utility(): return 7\n"),
        source("root/use.py", "from . import *\n"),
    ]
    package = s.SourcePackage(repository="public/fixture", commit="a" * 40, root="root", files=files)
    for program in s.programs():
        report = s.execute(package, program, s.Meter(1_000_000))["artifact"]
        use = next(row for row in report["files"] if row["module"] == "root.use")
        initializer = next(row for row in report["files"] if row["module"] == "root")
        assert use["captured_dependencies"] == ["root"]
        assert use["transitive_dependencies"] == ["root", "root.helper"]
        assert use["outside_capture"] == [] and "root.*" not in use["imports"]
        assert initializer["transitive_dependencies"] == ["root.helper"]


def test_meter_charges_every_explicit_fact_parser_ast_visit_and_retains_import_construction():
    file = source("fixture/a.py", "from . import b\ndef public_name(): return __import__('math')\n")
    tree = ast.parse(file.source)
    nodes, top_level = sum(1 for _ in ast.walk(tree)), len(tree.body)
    meter = s.Meter(100_000)
    s._facts(file, meter, captured={"fixture.b"})
    assert meter.trace["ast-node-census-visit"] == nodes
    assert meter.trace["import-ast-visit"] == nodes
    assert meter.trace["dynamic-ast-visit"] == nodes
    assert meter.trace["symbol-ast-visit"] == top_level
    assert meter.costs["read"] == (len(file.source.encode()) + 63) // 64 + 3 * nodes + top_level
    assert meter.costs["construction"] == 4 + 2 + 1  # four fact buckets,two import-target insertions,one symbol.


def second_campaign(loop, confirmation):
    req = request(loop, confirm=confirmation).model_copy(update={"campaign_id": "2a53c453-f671-49ba-9a5d-78a8326a2a7d"})
    queued = loop.create(req)
    loop.approve(req.campaign_id, queued["binding_digest"])
    frozen = loop.freeze(req.campaign_id)
    return req, frozen


def test_two_campaigns_cannot_rename_previously_confirmed_source_into_a_fresh_holdout(tmp_path):
    loop, req = prepared(tmp_path)
    holdout = [package("fresh", stale=True)]
    frozen = loop.freeze(req.campaign_id)
    complete = loop.confirm(req.campaign_id, holdout, frozen["freeze"]["digest"])
    assert complete["confirmation"]["complete"]
    other, other_freeze = second_campaign(loop, holdout)
    refused = loop.confirm(other.campaign_id, holdout, other_freeze["freeze"]["digest"])
    assert refused["result"]["reason"] == "confirmation-source-already-observed"
    assert not refused["confirmation"]["complete"] and refused["spent"] == other_freeze["spent"]
    assert loop.confirm(other.campaign_id, holdout, other_freeze["freeze"]["digest"])["revision"] == refused["revision"]
    assert loop.confirm(req.campaign_id, holdout, frozen["freeze"]["digest"])["revision"] == complete["revision"]


def test_partial_failed_confirmation_consumes_global_source_exposure(tmp_path, monkeypatch):
    loop, req = prepared(tmp_path)
    holdout = [package("fresh", stale=True)]
    frozen = loop.freeze(req.campaign_id)

    def fail(package, program, meter, expected):
        meter.charge("read", 1, "partial-before-budget-failure")
        raise s.BudgetExhausted("partial bounded failure")

    monkeypatch.setattr(s, "_execute", fail)
    failed = loop.confirm(req.campaign_id, holdout, frozen["freeze"]["digest"])
    assert not failed["confirmation"]["complete"] and failed["result"]["metrics"] is None
    assert failed["confirmation"]["packages"] == [package.model_dump() for package in holdout]
    assert failed["spent"]["read"] > frozen["spent"]["read"]
    monkeypatch.undo()
    other, f = second_campaign(loop, holdout)
    refused = loop.confirm(other.campaign_id, holdout, f["freeze"]["digest"])
    assert refused["result"]["reason"] == "confirmation-source-already-observed"


@pytest.mark.parametrize("fail_proposal", [False, True])
def test_measurement_probe_even_failed_exposes_source_before_future_confirmation(tmp_path, monkeypatch, fail_proposal):
    loop = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "journal"))
    holdout = [package("fresh", stale=True)]
    if fail_proposal:
        monkeypatch.setattr(s, "revision_proposal", lambda package: (_ for _ in ()).throw(ValueError("failed probe")))
    proposal = loop.propose_revision(holdout[0])
    if fail_proposal:
        assert proposal["state"] == "failed" and proposal["proposal"] is None
    monkeypatch.undo()
    req, frozen = second_campaign(loop, holdout)
    refused = loop.confirm(req.campaign_id, holdout, frozen["freeze"]["digest"])
    assert refused["result"]["reason"] == "confirmation-source-already-observed"
    exposures = loop.journal.latest(s.EXPOSURES)["captures"]
    assert exposures[s.source_fingerprint(holdout[0])]["kinds"] == ["confirmation", "proposal"]


def test_exposure_capacity_and_missing_legacy_checkpoint_fail_closed(tmp_path, monkeypatch):
    loop, req = prepared(tmp_path)
    frozen = loop.freeze(req.campaign_id)
    monkeypatch.setattr(s, "MAX_EXPOSURES", 1)
    with pytest.raises(Conflict, match="capacity"):
        loop.confirm(req.campaign_id, [package("fresh", stale=True)], frozen["freeze"]["digest"])
    old = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "legacy"))
    with old.journal.transaction() as cx:
        old.journal.append(cx, s.KEY + "prototype", {"state": "historical"})
    with pytest.raises(Conflict, match="checkpoint is missing"):
        old.create(request(old))


def test_all_candidate_cost_and_minimum_oracle_search_examinations_are_charged():
    rows = [{"methods": {s.program_id(p): {"exact": True, "units": 7} for p in s.programs()}}]
    meter = s.Meter(10_000)
    totals = s.SourceAuditDiscovery._totals(rows, meter)
    assert meter.used == 64 * 3  # candidate, exactness and cost visits
    assert s.SourceAuditDiscovery._select(totals, meter, "min") == "000000"
    assert meter.trace["min"] == 64
    assert s.SourceAuditDiscovery._oracle(rows, meter) == 7
    assert meter.trace["oracle-validity-inspection"] == 64
    assert meter.trace["oracle-minimum-comparison"] == 64
    assert meter.used == 64 * 6


def test_adding_irrelevant_new_file_cannot_refresh_any_previously_seen_source_blob(tmp_path):
    loop, req = prepared(tmp_path)
    holdout = [package("fresh", stale=True)]
    frozen = loop.freeze(req.campaign_id)
    loop.confirm(req.campaign_id, holdout, frozen["freeze"]["digest"])
    enlarged = holdout[0].model_copy(
        update={
            "files": [
                *holdout[0].files,
                source("fresh/extra.py", "# SPDX-License-Identifier: Apache-2.0\ndef irrelevant(): return 19\n"),
            ]
        }
    )
    assert s.source_fingerprint(enlarged) != s.source_fingerprint(holdout[0])
    other, f = second_campaign(loop, [enlarged])
    refused = loop.confirm(other.campaign_id, [enlarged], f["freeze"]["digest"])
    assert refused["result"]["reason"] == "confirmation-source-already-observed"
    assert not refused["confirmation"]["complete"]


def test_terminal_packages_cannot_overlap_on_even_one_source_blob(tmp_path):
    loop = s.SourceAuditDiscovery(Journal.initialize(tmp_path / "journal"))
    first, second = package("fresh"), package("other")
    second = second.model_copy(update={"files": [*second.files[:2], source("other/c.py", first.files[2].source)]})
    req = request(loop, confirm=[first, second])
    q = loop.create(req)
    loop.approve(req.campaign_id, q["binding_digest"])
    frozen = loop.freeze(req.campaign_id)
    refused = loop.confirm(req.campaign_id, [first, second], frozen["freeze"]["digest"])
    assert not refused["confirmation"]["complete"]
    assert refused["result"]["reason"] == "confirmation-source-already-observed"
    assert first.files[2].git_blob in loop.journal.latest(s.EXPOSURES)["blobs"]


@pytest.mark.parametrize(
    "assignment",
    [
        "api_key = 'synthetic-fixture-only'",
        "config={'x-api-key':'synthetic-fixture-only'}",
        "password = 'synthetic-fixture-only'",
        "config={'aws_secret_access_key':'synthetic-fixture-only'}",
        "payload = \"{'aws_secret_access_key': 'synthetic-fixture-only'}\"",
    ],
)
def test_public_credential_source_refused_before_journal_or_cli_home_write(tmp_path, assignment):
    p = package().model_dump()
    raw = (assignment + "\n").encode()
    p["files"][0].update(
        source=raw.decode(),
        sha256=hashlib.sha256(raw).hexdigest(),
        git_blob=hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
    )
    with pytest.raises(ValueError, match="credential"):
        s.SourcePackage.model_validate(p)
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"development": [p], "confirmation": [package("fresh").model_dump()]}))
    with pytest.raises(ValueError, match="credential"):
        main(
            [
                "--home",
                str(tmp_path / "must-not-exist"),
                "--output",
                str(tmp_path / "result.json"),
                "demo",
                str(fixture),
                "--approve-free-local-audit",
            ]
        )
    assert not (tmp_path / "must-not-exist").exists() and not (tmp_path / "result.json").exists()
