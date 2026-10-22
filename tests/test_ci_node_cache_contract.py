from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml


def _assert_cache_lifecycle(workflow: dict) -> None:
    # Job IDs and commands define this contract; decorative display labels and
    # the ordering/names of neighbouring jobs do not.
    job = workflow["jobs"]["tests"]
    assert job["env"]["NPM_CONFIG_CACHE"] == "${{ github.workspace }}/.npm-cache/tests"
    steps = job["steps"]
    ensure = [step for step in steps if 'mkdir -p "$NPM_CONFIG_CACHE"' in step.get("run", "").splitlines()]
    setup = [step for step in steps if step.get("uses", "").startswith("actions/setup-node@")]
    assert len(ensure) == len(setup) == 1
    assert setup[0]["with"]["cache"] == "npm"
    assert steps.index(ensure[0]) < steps.index(setup[0])
    assert "if" not in ensure[0] and not ensure[0].get("continue-on-error", False)
    lifecycle = [
        line.strip()
        for step in steps
        for line in step.get("run", "").splitlines()
        if 'rm -rf "$NPM_CONFIG_CACHE"' in line or 'mkdir -p "$NPM_CONFIG_CACHE"' in line
    ]
    assert lifecycle == ['mkdir -p "$NPM_CONFIG_CACHE"']


def _workflow() -> dict:
    return yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))


def test_setup_node_cache_path_lifecycle_is_preserved() -> None:
    _assert_cache_lifecycle(_workflow())


def test_cache_contract_does_not_depend_on_display_labels_or_neighbour_jobs() -> None:
    workflow = _workflow()
    job = deepcopy(workflow["jobs"]["tests"])
    job["name"] = "Any descriptive integration label"
    for step in job["steps"]:
        if "name" in step:
            step["name"] = "A renamed display label"
    _assert_cache_lifecycle({"jobs": {"tests": job}})


@pytest.mark.parametrize("mutation", ["path", "missing", "late", "delete", "conditional", "advisory", "cache-disabled"])
def test_cache_contract_rejects_broken_lifecycle(mutation: str) -> None:
    workflow = _workflow()
    job = workflow["jobs"]["tests"]
    steps = job["steps"]
    ensure = next(step for step in steps if 'mkdir -p "$NPM_CONFIG_CACHE"' in step.get("run", "").splitlines())
    setup = next(step for step in steps if step.get("uses", "").startswith("actions/setup-node@"))
    if mutation == "path":
        job["env"]["NPM_CONFIG_CACHE"] = "${{ github.workspace }}/different-cache"
    elif mutation == "missing":
        steps.remove(ensure)
    elif mutation == "late":
        steps.remove(ensure)
        steps.append(ensure)
    elif mutation == "delete":
        steps.append({"run": 'rm -rf "$NPM_CONFIG_CACHE"'})
    elif mutation == "conditional":
        ensure["if"] = "false"
    elif mutation == "advisory":
        ensure["continue-on-error"] = True
    else:
        setup["with"]["cache"] = ""
    with pytest.raises(AssertionError):
        _assert_cache_lifecycle(workflow)
