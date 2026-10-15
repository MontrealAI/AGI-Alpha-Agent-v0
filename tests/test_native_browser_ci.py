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
    install = next(step for step in steps if step.get("name") == "Install rendered wallet acceptance tools")
    browser = next(step for step in steps if step.get("name") == "Bounded native bridge, authority and operator checks")
    assert "python -m pip install playwright==1.54.0" in install["run"]
    assert "python -m playwright install --with-deps chromium" in install["run"]
    assert steps.index(install) < steps.index(browser)
    for item in (workflow["jobs"]["wallet"], install, browser):
        assert "if" not in item
        assert "continue-on-error" not in item


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
        "jobs:\n  wallet:\n    steps:\n      - env:\n          AXE_SCRIPT: axe.min.js\n"
        "        env:\n          PYTHONPATH: '.'\n",
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
    runtime = release["jobs"]["runtime"]
    assert set(runtime["strategy"]["matrix"]["python"]) == {"3.11", "3.12", "3.13"}
    step = next(step for step in runtime["steps"] if step.get("name") == "Runtime tests in minimal environment")
    command = next(line for line in step["run"].splitlines() if "python -m pytest tests/runtime " in line)
    args = shlex.split(command)
    assert {arg for arg in args if arg.startswith("--ignore=")} == {
        "--ignore=tests/runtime/test_budget_browser.py",
        "--ignore=tests/runtime/test_ecosystem_browser.py",
        "--ignore=tests/runtime/test_supplier_browser_browser.py",
    }
    assert "tests/runtime" in args
    assert "--confcutdir=tests/runtime" in args
    assert "continue-on-error" not in step
    assert "continue-on-error" not in runtime
    assert release["jobs"]["mark-wallet"]["uses"] == "./.github/workflows/mark-wallet.yml"
    assert "if" not in release["jobs"]["mark-wallet"]
    assert "continue-on-error" not in release["jobs"]["mark-wallet"]
    assert "mark-wallet" in release["jobs"]["package"]["needs"]
    assert "package" in release["jobs"]["pages"]["needs"]
    assert "pages" in release["jobs"]["publish"]["needs"]
    for name in ("package", "pages", "publish"):
        job = release["jobs"][name]
        assert "continue-on-error" not in job
        assert not re.search(r"\b(?:always|failure|cancelled)\s*\(", job.get("if", ""))
    test_native_browser_acceptance_is_one_command_with_both_suites()


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


def test_complete_regression_installs_the_pinned_accessibility_auditor():
    release = yaml.load((ROOT / ".github/workflows/agent-release.yml").read_text(), Loader=UniqueWorkflowLoader)
    steps = release["jobs"]["regression"]["steps"]
    install = next(step for step in steps if step.get("name") == "Original locked development environment")
    acceptance = next(step for step in steps if step.get("name") == "Full offline regression including notebooks")
    assert "npm ci --prefix tests/browser --ignore-scripts" in install["run"].splitlines()
    assert steps.index(install) < steps.index(acceptance)
    assert "if" not in install and "continue-on-error" not in install


def test_mission_recovery_gate_has_exact_pins_and_unconditional_real_suites():
    workflow = yaml.load((ROOT / ".github/workflows/successor-mission.yml").read_text(), Loader=UniqueWorkflowLoader)
    assert workflow["on"]["pull_request"] is None
    job = workflow["jobs"]["mission"]
    assert "if" not in job and "continue-on-error" not in job
    steps = job["steps"]
    actions = [step for step in steps if "uses" in step]
    assert [step["uses"] for step in actions] == [
        "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
        "actions/setup-node@53b83947a5a98c8d113130e565377fae1a50d02f",
        "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405",
        "actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f",
    ]
    assert actions[0]["with"]["persist-credentials"] is False
    selected = {step["name"]: step for step in steps if "name" in step}
    install = selected["Install pinned browser tools"]
    assertions = selected["Strict records and existing workbench"]
    browser = selected["Atomic storage and full browser recovery"]
    for step in [*actions, *selected.values()]:
        if step.get("name") == "Retain discovery browser screenshots":
            assert step["if"] == "always()"
            assert "continue-on-error" not in step
        else:
            assert "if" not in step and "continue-on-error" not in step
    assert steps.index(install) < steps.index(assertions) < steps.index(browser)
    assert install["run"].splitlines() == [
        "python -m pip install playwright==1.54.0 PyYAML==6.0.2 pytest==8.4.1",
        "python -m playwright install --with-deps chromium",
        "npm ci --prefix tests/browser --ignore-scripts",
    ]
    assert assertions["run"].splitlines() == [
        "node --test examples/successor-workbench/mission-record.test.mjs "
        "examples/successor-workbench/mission-app.test.mjs examples/successor-workbench/mission-workflow.test.mjs",
        "node examples/successor-workbench/test.mjs",
        "node --test examples/successor-project/engine.test.mjs",
        "python tests/test_successor_project_delivery.py",
        "node --test examples/alpha-discovery/engine.test.mjs",
        "node --test examples/specialist-evaluation/engine.test.mjs examples/specialist-evaluation/app.test.mjs",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -c /dev/null "
        "-p no:cacheprovider tests/test_native_browser_ci.py tests/test_specialist_evaluation_delivery.py -q",
    ]
    assert browser["run"].splitlines() == [
        "python tests/browser/test_successor_mission_store.py",
        "python tests/browser/test_successor_mission_browser.py",
        "python tests/browser/test_alpha_discovery_browser.py",
        "python tests/browser/test_specialist_evaluation_browser.py",
        "python tests/browser/test_successor_project_browser.py",
    ]
    assert browser["env"]["AXE_SCRIPT"] == "${{ github.workspace }}/tests/browser/node_modules/axe-core/axe.min.js"

    assert browser["env"]["DISCOVERY_SCREENSHOTS"] == "${{ github.workspace }}/discovery-screenshots"
    assert "python scripts/generate_alpha_discovery.py" in selected["Generated source is current"]["run"].splitlines()
    assert selected["Retain discovery browser screenshots"]["with"]["path"] == "discovery-screenshots/"
