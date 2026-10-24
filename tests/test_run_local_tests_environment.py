# SPDX-License-Identifier: Apache-2.0
"""Exercise local asset paths at the real offline child-process boundary."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_local_assets_reach_credential_clean_offline_child(tmp_path: Path) -> None:
    insight_root = tmp_path / "insight assets"
    fetch_root = tmp_path / "fallback assets"
    insight_root.mkdir()
    fetch_root.mkdir()
    probe = tmp_path / "test_runner_boundary.py"
    probe.write_text(
        f"""# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import runpy
import socket
import pytest


def test_child_boundary():
    insight_root = Path({str(insight_root)!r})
    fetch_root = Path({str(fetch_root)!r})
    assert os.environ["INSIGHT_ASSET_ROOT"] == str(insight_root)
    assert os.environ["FETCH_ASSETS_DIR"] == str(fetch_root)
    asset_root = runpy.run_path({str(ROOT / "tests" / "test_assets_replaced.py")!r})["_asset_root"]
    assert asset_root() == insight_root
    del os.environ["INSIGHT_ASSET_ROOT"]
    assert asset_root() == fetch_root
    for key in ("OPENAI_API_KEY", "GITHUB_TOKEN", "UNRELATED_PRIVATE_TOKEN"):
        assert key not in os.environ
    assert os.environ["NEO4J_PASSWORD"] == "local-tests-only-strong-password"
    assert os.environ["API_TOKEN"] == "test-token"
    assert os.environ["ALPHA_TEST_OFFLINE"] == "1"
    with socket.socket() as client:
        with pytest.raises(OSError, match="external network disabled by offline test runner"):
            client.connect(("198.51.100.1", 443))
"""
    )
    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "HOME": str(tmp_path / "home"),
        "LANG": "C.UTF-8",
        "INSIGHT_ASSET_ROOT": str(insight_root),
        "FETCH_ASSETS_DIR": str(fetch_root),
        "OPENAI_API_KEY": "fixture-openai-only",
        "GITHUB_TOKEN": "fixture-github-only",
        "UNRELATED_PRIVATE_TOKEN": "fixture-private-only",
        "NEO4J_PASSWORD": "fixture-password-only",
        "API_TOKEN": "fixture-api-only",
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_local_tests",
            "--noconftest",
            "-c",
            "/dev/null",
            "-p",
            "no:cacheprovider",
            str(probe),
            "-q",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


HELD_NODEIDS = (
    "tests/test_successor_capability_delivery.py::test_native_source_helper_refuses_unsafe_metadata_without_installing_or_running_commands",
    "tests/test_successor_capability_delivery.py::test_native_source_helper_refuses_non_admitted_worktree_metadata",
    "tests/test_successor_capability_delivery.py::test_native_browser_attack_bank_is_predeclared_and_not_selected_by_the_producer",
    "tests/test_successor_capability_delivery.py::test_both_native_requests_are_actual_ui_downloads_with_one_pre_fleet_history",
)
HELD_SELECTIONS = (
    (
        "successor-capability.yml",
        "capability",
        "Computation, history and delivery gates",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -c /dev/null --rootdir=. -p no:cacheprovider "
        "tests/test_held_native_source_guard.py "
        "tests/test_run_local_tests_environment.py tests/test_discovery_lab_validation.py "
        "tests/test_autonomous_enterprises_source.py tests/test_paper_checkout_bytes.py "
        "tests/test_successor_capability_delivery.py -q 2>&1 | tee capability-evidence/logs/delivery.log",
        "capability-delivery",
        "capability-evidence/held-probes.json",
    ),
    (
        "agent-release.yml",
        "regression",
        "Offline regression including notebooks (four held native tests excluded)",
        "python -m scripts.run_local_tests",
        "python -m scripts.run_local_tests -q --cov --cov-config=pyproject.toml --cov-fail-under=80 "
        "--cov-report=xml:evidence/coverage.xml --junitxml=evidence/regression.xml",
        "agent-full-regression",
        "evidence/held-probes.json",
    ),
)


def held_step(case: tuple[str, ...]) -> tuple[str, list[str]]:
    workflow = yaml.safe_load((ROOT / ".github/workflows" / case[0]).read_text())
    job = workflow["jobs"][case[1]]
    artifact_root = str(Path(case[6]).parent)
    assert any(
        step.get("uses", "").startswith("actions/upload-artifact@")
        and step.get("if") == "always()"
        and step.get("with", {}).get("path", "").rstrip("/") == artifact_root
        for step in job["steps"]
    )
    run = next(step["run"] for step in job["steps"] if step.get("name") == case[2])
    lines = run.replace("\\\n", "").splitlines()
    command = next(line.strip() for line in lines if line.strip().startswith(case[3]))
    return run, shlex.split(command)


def assert_exact_held_selection(argv: list[str], baseline: str) -> None:
    selected = [arg.removeprefix("--deselect=") for arg in argv if arg.startswith("--deselect=")]
    assert len(selected) == len(HELD_NODEIDS) and set(selected) == set(HELD_NODEIDS)
    assert [arg for arg in argv if not arg.startswith("--deselect=")] == shlex.split(baseline)


def assert_truthful_held_record(run: str, invocation: str, destination: str) -> None:
    script = run.split("python - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
    tree = ast.parse(script)
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert tuple(ast.literal_eval(assignments["held"])) == HELD_NODEIDS
    record = assignments["record"]
    assert isinstance(record, ast.Dict)
    fields = {ast.literal_eval(key): value for key, value in zip(record.keys, record.values) if key is not None}
    assert ast.literal_eval(fields["schema"]) == "agialpha.held-test-selection.v1"
    assert ast.literal_eval(fields["invocation"]) == invocation
    assert ast.literal_eval(fields["status"]) == "EXCLUSION_PLANNED"
    assert ast.literal_eval(fields["qualified"]) is False
    tests = fields["tests"]
    assert isinstance(tests, ast.ListComp) and len(tests.generators) == 1
    assert isinstance(tests.generators[0].iter, ast.Name) and tests.generators[0].iter.id == "held"
    assert isinstance(tests.elt, ast.Dict)
    row = {ast.literal_eval(key): value for key, value in zip(tests.elt.keys, tests.elt.values) if key is not None}
    assert set(row) == {"nodeid", "status"}
    assert isinstance(row["nodeid"], ast.Name) and row["nodeid"].id == "node"
    assert ast.literal_eval(row["status"]) == "EXCLUSION_PLANNED"
    meaning = ast.literal_eval(fields["meaning"])
    assert "selection intention only" in meaning
    assert "Actual deselection requires observed job output" in meaning
    assert "their outcomes are not qualified" in meaning
    writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "write_text"
    ]
    assert len(writes) == 1
    writer = writes[0].func
    assert isinstance(writer, ast.Attribute)
    target = writer.value
    assert isinstance(target, ast.Call)
    assert ast.literal_eval(target.args[0]) == destination


def test_held_selection_keeps_every_other_existing_argument() -> None:
    for case in HELD_SELECTIONS:
        _, argv = held_step(case)
        assert_exact_held_selection(argv, case[4])


def test_held_selection_rejects_missing_and_unrelated_deselections() -> None:
    for case in HELD_SELECTIONS:
        _, argv = held_step(case)
        assert_exact_held_selection(argv, case[4])
        for node in HELD_NODEIDS:
            with pytest.raises(AssertionError):
                assert_exact_held_selection([arg for arg in argv if arg != "--deselect=" + node], case[4])
        with pytest.raises(AssertionError):
            assert_exact_held_selection(argv + ["--deselect=tests/unrelated.py::test_required"], case[4])
        with pytest.raises(AssertionError):
            assert_exact_held_selection(argv + ["--ignore=tests/unrelated.py"], case[4])


def test_held_selection_records_only_planned_exclusion() -> None:
    for case in HELD_SELECTIONS:
        run, _ = held_step(case)
        assert_truthful_held_record(run, case[5], case[6])


def test_held_selection_record_rejects_false_qualification() -> None:
    for case in HELD_SELECTIONS:
        run, _ = held_step(case)
        assert_truthful_held_record(run, case[5], case[6])
        with pytest.raises(AssertionError):
            assert_truthful_held_record(run.replace("'qualified': False", "'qualified': True"), case[5], case[6])


def test_pre_run_selection_record_rejects_completed_nonexecution_claim() -> None:
    for case in HELD_SELECTIONS:
        run, _ = held_step(case)
        with pytest.raises(AssertionError):
            assert_truthful_held_record(
                run.replace("'status': 'EXCLUSION_PLANNED'", "'status': 'LOCAL_NOT_RUN'"), case[5], case[6]
            )


def test_capability_deselection_uses_the_owned_checkout_root(tmp_path: Path) -> None:
    """Only two newly written assert-True controls run; no product test is imported."""
    _, argv = held_step(HELD_SELECTIONS[0])
    root_options = [arg for arg in argv if arg.startswith("--rootdir=")]
    assert root_options == ["--rootdir=."]
    root = tmp_path / "owned selection"
    (root / "tests").mkdir(parents=True)
    (root / "tests/test_owned_selection.py").write_text(
        "def test_control_one():\n    assert True\n\ndef test_control_two():\n    assert True\n"
    )
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    for label, options, expected in (
        ("unfixed", [], "2 passed"),
        ("fixed", root_options, "1 passed, 1 deselected"),
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--noconftest",
                "-c",
                "/dev/null",
                "-p",
                "no:cacheprovider",
                *options,
                "tests/test_owned_selection.py",
                "-q",
                "--deselect=tests/test_owned_selection.py::test_control_two",
            ],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert expected in result.stdout
        if label == "unfixed":
            assert "deselected" not in result.stdout
        print(f"Owned inert selection {label}: {result.stdout.strip()}")
