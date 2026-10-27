# SPDX-License-Identifier: Apache-2.0
"""Consumer-semantic drift is checked by execution, never by schema alone."""

import copy

import pytest

from scripts.experiment_workflow_requalification import ARMS, FRESH, experiment, freeze, grant, identity, run_arm


@pytest.fixture(scope="module")
def qualification():
    return freeze()


def test_executed_fresh_artifacts_and_same_content_parity():
    result = experiment()
    for name in ["fresh-0", "fresh-1", "fresh-2", "fresh-3", "malicious-text"]:
        runs = [r for r in result["runs"] if r["mission"] == name]
        assert all(r["accepted"] for r in runs)
        assert all(t["changed"] and t["production_executor_reused"] for r in runs for t in r["traces"])
        left, right = runs[2], runs[3]
        assert left["counts"] == right["counts"] and left["traces"] == right["traces"]
        assert runs[0]["counts"]["mission_actions"] == 1
        assert runs[1]["counts"]["generic_actions"] == 8
        assert runs[2]["counts"]["generic_actions"] == 0
    assert result["actual_model_calls"] == result["actual_customer_collections"] == 0
    assert result["decision"].startswith("HOLD")
    assert all(summary["logical_counts"]["authority_checks"] == 11 for summary in result["summary"].values())


@pytest.mark.parametrize("effect", ["hidden-seconds", "hidden-cumulative", "hidden-third-only"])
def test_same_schema_hidden_meaning_drift_fails_original_purpose(qualification, effect):
    contract = identity()
    for arm in ARMS:
        result = run_arm(arm, FRESH[0], contract, effect, qualification, grant("fresh", contract), "fresh")
        assert result["status"] == "rejected" and not result["accepted"]
        assert result["traces"][-1]["shape_pass"]
        assert result["traces"][-1]["changed"]


def test_finite_probes_do_not_replace_complete_new_mission_acceptance(qualification):
    contract = identity()
    result = run_arm(
        "identity-reuse", FRESH[0], contract, "hidden-third-only", qualification, grant("fresh", contract), "fresh"
    )
    assert result["counts"]["fresh_probe_actions"] == 2
    assert all(t["accepted"] for t in result["traces"][:2])
    assert result["counts"]["mission_actions"] == 1 and not result["accepted"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("dependencies", ["v2"]),
        ("model", "new-model"),
        ("scope", "other"),
        ("version", 2),
        ("semantics", "seconds"),
        ("permissions", []),
        ("schema", "changed"),
        ("revoked", True),
    ],
)
def test_known_drift_refuses_before_any_action(qualification, field, value):
    contract = identity(**{field: value})
    for arm in ARMS:
        result = run_arm(arm, FRESH[0], contract, "normal", qualification, grant("fresh", contract), "fresh")
        assert result["status"] == "refused" and result["traces"] == []
        assert result["counts"]["mission_actions"] == 0
        assert result["counts"]["authority_checks"] == 0


def test_authority_is_never_inherited_and_tool_text_cannot_grant_it(qualification):
    contract = identity()
    for authority in [
        None,
        grant("wrong", contract),
        grant("fresh", contract, expires=5),
        grant("fresh", contract, allowed=False),
    ]:
        result = run_arm("identity-reuse", FRESH[0], contract, "malicious-text", qualification, authority, "fresh")
        assert result["status"] == "refused" and not result["traces"]
    allowed = run_arm(
        "identity-reuse", FRESH[0], contract, "malicious-text", qualification, grant("fresh", contract), "fresh"
    )
    assert allowed["accepted"] and not allowed["authority_inherited"]
    assert all(not t["authority_granted"] for t in allowed["traces"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("checker", "changed"),
        ("scope", "other"),
        ("workflow", "changed"),
        ("probe_suite", "changed"),
        ("accepted", False),
    ],
)
def test_corrupt_cache_cannot_qualify_different_purpose(qualification, field, value):
    corrupt = copy.deepcopy(qualification)
    corrupt[field] = value
    contract = identity()
    result = run_arm("identity-reuse", FRESH[0], contract, "normal", corrupt, grant("fresh", contract), "fresh")
    assert result["status"] == "refused" and not result["traces"]


def test_corrupt_qualification_artifact_refuses_before_use(qualification):
    corrupt = copy.deepcopy(qualification)
    corrupt["generic_traces"][0]["artifact"]["total_milliseconds"] = -1
    contract = identity()
    result = run_arm("identity-reuse", FRESH[0], contract, "normal", corrupt, grant("fresh", contract), "fresh")
    assert result["status"] == "refused" and not result["traces"]


@pytest.mark.parametrize("values", [(), (-1,), (True,), (10**10,), tuple(range(65))])
def test_unsupported_inputs_refuse_before_tools(qualification, values):
    contract = identity()
    result = run_arm("identity-reuse", values, contract, "normal", qualification, grant("fresh", contract), "fresh")
    assert result["status"] == "refused" and not result["traces"]


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize("effect", ["malformed-return", "forged-return-sha", "forged-return-path"])
def test_return_schema_and_receipt_binding_are_separate_from_artifact_correctness(qualification, arm, effect):
    contract = identity()
    result = run_arm(arm, FRESH[0], contract, effect, qualification, grant("fresh", contract), "fresh")
    assert result["status"] == "rejected" and not result["accepted"]
    trace = result["traces"][-1]
    assert trace["accepted"] and trace["changed"]
    if effect == "malformed-return":
        assert not trace["shape_pass"] and result["reason"] == "tool return schema check failed"
    else:
        assert trace["shape_pass"] and not trace["receipt_matches_artifact"]
        assert result["reason"] == "tool receipt does not bind the observed artifact"
