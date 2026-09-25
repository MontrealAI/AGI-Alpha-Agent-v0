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
    assert dependencies == set(jobs) - {gate} - excluded
    assert all(not jobs[name].get("continue-on-error", False) for name in dependencies)
    # Deployment is excluded only because this badge is explicitly about main validation.
    for name in excluded:
        assert "refs/tags/" in jobs[name]["if"]
