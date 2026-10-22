# SPDX-License-Identifier: Apache-2.0
"""Defer the unchanged exact-main proof without weakening required producers."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONDITION = "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())


def assert_deferred_boundary(policy: dict) -> None:
    jobs = policy["jobs"]
    boundary, package = jobs["historical-ci"], jobs["package"]
    expected = (set(package["needs"]) - {"historical-ci"}) | {"publication-preflight"}
    assert set(boundary["needs"]) == expected
    assert len(boundary["needs"]) == len(expected)
    assert {"runtime", "regression", "quality", "mark-wallet", "finance-lab", "successor-capability"} <= expected
    assert not {"package", "pages", "publish", "historical-ci", "style-advisory"} & expected
    assert boundary["if"] == package["if"] == CONDITION
    assert not boundary.get("continue-on-error") and not package.get("continue-on-error")
    assert "historical-ci" in package["needs"]
    assert boundary["permissions"] == {"contents": "read", "actions": "read"}
    assert boundary["timeout-minutes"] == 125
    commands = [step.get("run") for step in boundary["steps"]]
    assert "python -m scripts.wait_for_release_ci" in commands
    assert "python -m scripts.wait_for_release_ci --candidate" in commands


def test_historical_proof_waits_without_allocating_an_early_runner() -> None:
    assert_deferred_boundary(workflow())


@pytest.mark.parametrize("mutation", ["missing-producer", "advisory", "cycle", "always", "optional", "missing-proof"])
def test_queue_optimization_cannot_weaken_or_deadlock_release(mutation: str) -> None:
    policy = workflow()
    boundary, package = policy["jobs"]["historical-ci"], policy["jobs"]["package"]
    if mutation == "missing-producer":
        boundary["needs"].remove("regression")
    elif mutation == "advisory":
        boundary["needs"].append("style-advisory")
    elif mutation == "cycle":
        boundary["needs"].append("package")
    elif mutation == "always":
        boundary["if"] = "${{ always() }}"
    elif mutation == "optional":
        boundary["continue-on-error"] = True
    else:
        package["needs"].remove("historical-ci")
    with pytest.raises(AssertionError):
        assert_deferred_boundary(policy)


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", "timed_out"])
def test_required_result_is_never_reinterpreted_as_success(result: str) -> None:
    policy = workflow()
    policy["jobs"]["historical-ci"]["if"] = CONDITION.replace(
        "success()", f"(success() || needs.regression.result == '{result}')"
    )
    with pytest.raises(AssertionError):
        assert_deferred_boundary(policy)
