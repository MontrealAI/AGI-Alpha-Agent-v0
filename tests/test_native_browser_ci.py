# SPDX-License-Identifier: Apache-2.0
"""Browserless smoke must retain mandatory browser coverage in its qualified job."""
from pathlib import Path
import shlex
import re
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_native_browser_acceptance_is_one_command_with_both_suites() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/mark-wallet.yml").read_text())
    steps = workflow["jobs"]["wallet"]["steps"]
    run = next(
        step["run"] for step in steps if step.get("name") == "Bounded native bridge, authority and operator checks"
    )
    assert len(run.splitlines()) == 1, "Folded YAML must not split the pytest shell command"
    args = shlex.split(run)
    assert args[:3] == ["python", "-m", "pytest"]
    for name in ["test_budget_browser.py", "test_ecosystem_browser.py", "test_supplier_browser_browser.py"]:
        assert "tests/runtime/" + name in args
    assert any("playwright install --with-deps chromium" in step.get("run", "") for step in steps)


class UniqueWorkflowLoader(yaml.SafeLoader):
    # GitHub uses YAML 1.2: `on` remains a string, while true/false are booleans.
    yaml_implicit_resolvers = {
        key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:bool"]
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key {key!r} at {key_node.start_mark}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueWorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$"), list("tTfF")
)
UniqueWorkflowLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def test_workflows_have_no_duplicate_mapping_keys() -> None:
    for path in sorted((ROOT / ".github/workflows").glob("*.y*ml")):
        yaml.load(path.read_text(), Loader=UniqueWorkflowLoader)


@pytest.mark.parametrize(
    "source",
    [
        "on: push\non: pull_request\n",
        "jobs:\n  wallet:\n    steps:\n      - env:\n          AXE_SCRIPT: axe.min.js\n        env:\n          PYTHONPATH: '.'\n",
        "jobs: {wallet: {env: {A: one, A: two}}}",
    ],
)
def test_duplicate_workflow_keys_fail_at_every_depth(source) -> None:
    with pytest.raises(ValueError, match="Duplicate YAML key"):
        yaml.load(source, Loader=UniqueWorkflowLoader)


def test_workflow_loader_preserves_on_and_boolean_semantics() -> None:
    parsed = yaml.load("on: {pull_request: {}}\nenabled: true\nlabel: off\n", Loader=UniqueWorkflowLoader)
    assert parsed == {"on": {"pull_request": {}}, "enabled": True, "label": "off"}


def test_native_browser_auditor_and_runtime_environment_are_combined() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/mark-wallet.yml").read_text())
    step = next(
        step
        for step in workflow["jobs"]["wallet"]["steps"]
        if step.get("name") == "Bounded native bridge, authority and operator checks"
    )
    assert step["env"] == {
        "AXE_SCRIPT": "tests/browser/node_modules/axe-core/axe.min.js",
        "PYTHONPATH": ".",
        "NO_DISCLAIMER": "1",
    }
