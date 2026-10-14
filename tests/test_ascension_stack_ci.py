# SPDX-License-Identifier: Apache-2.0
"""Keep stacked Ascension regression fail-closed and bound to its source."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ascension-stack-regression.yml"
BRANCHES = {
    "feat/ascension-native-cycle-20261014",
    "feat/ascension-inspectable-cycle-20261014",
}


def _workflow():
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_uncovered_stack_branches_receive_regression():
    triggers = _workflow()["on"]
    assert set(triggers["push"]["branches"]) == BRANCHES
    assert "pull_request" not in triggers
    assert "workflow_dispatch" in triggers
    assert "pull_request_target" not in triggers
    assert "paths" not in triggers["push"]


def test_candidate_checkout_is_exact_and_read_only():
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["regression"]
    expected = "${{ github.sha }}"
    assert job["env"]["EXPECTED_HEAD_SHA"] == expected
    checkout = job["steps"][0]["with"]
    assert checkout["ref"] == expected
    assert checkout["persist-credentials"] == "false"
    assert checkout["fetch-depth"] == "0"
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"' in job["steps"][1]["run"]
    assert "HEAD^{tree}" in job["steps"][1]["run"]
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_full_regression_retains_coverage_and_offline_runner():
    steps = _workflow()["jobs"]["regression"]["steps"]
    commands = {step["name"]: step["run"] for step in steps if "run" in step}
    regression = commands["Full offline regression including notebooks"]
    assert "python -m scripts.run_local_tests -q --cov " in regression
    assert "--cov-fail-under=80" in regression
    assert "--cov-config=pyproject.toml" in regression
    assert "--junitxml=evidence/regression.xml" in regression
    assert (
        "--require-hashes -r requirements.lock -r requirements-dev.lock"
        in commands["Original locked development environment"]
    )
    assert "--deselect" not in regression
    assert " -m " not in regression.split("scripts.run_local_tests", 1)[1]
    assert " -k " not in regression
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "continue-on-error" not in text
    assert "|| true" not in text


def test_strict_types_and_preservation_remain_required():
    steps = _workflow()["jobs"]["regression"]["steps"]
    command = next(step["run"] for step in steps if step.get("name") == "Strict types and repository checks")
    for config in (
        "runtime",
        "business3",
        "governance",
        "discovery",
        "experience",
        "mats",
        "curriculum",
        "muzero",
        "finance",
        "sovereign",
    ):
        assert f"python -m mypy --config-file mypy-{config}.ini" in command
    assert "python -m mypy --config-file mypy.ini" in command
    for checker in (
        "check_agent_preservation",
        "check_successor_preservation",
        "check_manuscript",
        "check_factory_readiness",
    ):
        assert f"python -m scripts.{checker}" in command


def test_actions_are_pinned_and_failed_evidence_is_retained():
    workflow = _workflow()
    assert set(workflow["jobs"]) == {"regression"}
    job = workflow["jobs"]["regression"]
    assert job["timeout-minutes"] == "45"
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", step["uses"])
    upload = job["steps"][-1]
    assert upload["uses"].startswith("actions/upload-artifact@")
    assert upload["if"] == "always()"
    assert upload["with"]["path"] == "evidence/"
    assert upload["with"]["if-no-files-found"] == "error"
    assert "github.run_attempt" in upload["with"]["name"]
