# SPDX-License-Identifier: Apache-2.0
"""Browserless smoke must retain mandatory browser coverage in its qualified job."""
from pathlib import Path
import shlex
import ast
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


def test_supplier_real_browser_observation_is_in_required_browser_suite() -> None:
    name = "test_real_chromium_observation_matches_independent_reviewer"
    unit = ROOT / "tests/runtime/test_supplier_browser_spec.py"
    browser = ROOT / "tests/runtime/test_supplier_browser_browser.py"

    def names(path):
        return {node.name for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}

    assert name not in names(unit)
    assert name in names(browser)
    smoke = yaml.load((ROOT / ".github/workflows/smoke.yml").read_text(), Loader=UniqueWorkflowLoader)
    steps = smoke["jobs"]["smoke"]["steps"]
    run = next(step["run"] for step in steps if step.get("name") == "Exercise the installed operator lifecycle")
    assert "--ignore=tests/runtime/test_supplier_browser_browser.py" in shlex.split(run)
    assert "--ignore=tests/runtime/test_supplier_browser_spec.py" not in shlex.split(run)
    release = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=UniqueWorkflowLoader)
    release_steps = [step for job in release["jobs"].values() for step in job.get("steps", [])]
    runtime_steps = [step for step in release_steps if "python -m pytest tests/runtime " in step.get("run", "")]
    assert runtime_steps
    assert all("--ignore=tests/runtime/test_supplier_browser_browser.py" not in step["run"] for step in runtime_steps)
    assert any("playwright install --with-deps chromium" in step.get("run", "") for step in release_steps)


def test_business_sum_binding_runs_before_merge_on_every_python() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/smoke.yml").read_text(), Loader=UniqueWorkflowLoader)
    assert "pull_request" in workflow["on"]
    job = workflow["jobs"]["smoke"]
    assert set(job["strategy"]["matrix"]["python-version"]) == {"3.11", "3.12", "3.13"}
    step = next(
        step
        for step in job["steps"]
        if step.get("name") == "Run focused smoke tests on every platform and Python version"
    )
    assert "if" not in step
    assert "continue-on-error" not in step
    command = next(line for line in step["run"].splitlines() if "business1-sum-binding.xml" in line)
    assert shlex.split(command) == [
        "python",
        "-m",
        "pytest",
        "--noconftest",
        "-o",
        "addopts=",
        "tests/test_openai_bridge_integration.py",
        "-q",
        "--junitxml=evidence/business1-sum-binding.xml",
    ]
