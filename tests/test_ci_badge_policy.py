# SPDX-License-Identifier: Apache-2.0
"""New validation jobs must not escape the result used by the public badge."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize(
    "workflow,gate,excluded",
    [("ci.yml", "integration-result", {"deploy"}), ("smoke.yml", "smoke-result", set())],
)
def test_badge_aggregate_covers_every_required_job(workflow: str, gate: str, excluded: set[str]) -> None:
    jobs = yaml.safe_load((Path(".github/workflows") / workflow).read_text())["jobs"]
    dependencies = jobs[gate]["needs"]
    dependencies = {dependencies} if isinstance(dependencies, str) else set(dependencies)
    # Qualification is downstream of the aggregate, never a circular dependency
    # or an unchecked exception to validation coverage.
    marker = "full-software-qualification"
    assert dependencies == set(jobs) - {gate, marker} - excluded
    assert set(jobs[marker]["needs"]) == dependencies | {gate}
    assert jobs[marker]["name"] == "Full software qualification"
    assert jobs[marker]["if"] == (
        "${{ !cancelled() && needs.paper-scope.outputs.mode == 'full' && github.ref == 'refs/heads/main' }}"
    )
    assert jobs["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    assert all(not jobs[name].get("continue-on-error", False) for name in dependencies | {gate, marker})
    # Deployment is excluded only because this badge is explicitly about main validation.
    for name in excluded:
        assert "refs/tags/" in jobs[name]["if"]
