# SPDX-License-Identifier: Apache-2.0
"""Exercise the catalog's installed-launch and prerequisite boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from alpha_factory_v1.demos import catalog


def entry(name: str) -> dict:
    return next(item for item in catalog.entries() if item["id"] == name)


@pytest.mark.parametrize("shadow", ["module", "package"])
@pytest.mark.parametrize("extra_path", ["", os.pathsep, "." + os.pathsep])
def test_run_directory_cannot_replace_the_demo_package(tmp_path, monkeypatch, capfd, shadow, extra_path):
    caller = tmp_path / "caller"
    caller.mkdir()
    output = tmp_path / "output with spaces"
    output.mkdir()
    source = output / "alpha_factory_v1.py"
    if shadow == "package":
        source = output / "alpha_factory_v1" / "__init__.py"
        source.parent.mkdir()
    source.write_text('print("UNTRUSTED_OUTPUT_EXECUTED"); raise SystemExit(86)\n')
    monkeypatch.chdir(caller)
    monkeypatch.setenv("PYTHONPATH", extra_path)
    monkeypatch.setenv("NO_DISCLAIMER", "1")
    assert catalog.main(["run", "solving_agi_governance", "--output-dir", str(output)]) == 0
    stdout, stderr = capfd.readouterr()
    assert "UNTRUSTED_OUTPUT_EXECUTED" not in stdout + stderr
    assert source.exists()


def test_invalid_output_is_reported_without_traceback_or_data_loss(tmp_path, capsys):
    output = tmp_path / "existing-file"
    output.write_text("keep this result")
    assert catalog.main(["run", "solving_agi_governance", "--output-dir", str(output)]) == 1
    captured = capsys.readouterr()
    assert "Could not launch" in captured.err and "Traceback" not in captured.err
    assert output.read_text() == "keep this result"


def test_launch_from_existing_output_does_not_import_its_sitecustomize(tmp_path, monkeypatch, capfd):
    (tmp_path / "sitecustomize.py").write_text('print("UNTRUSTED_OUTPUT_EXECUTED")\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", ".")
    monkeypatch.setenv("NO_DISCLAIMER", "1")
    assert catalog.main(["run", "solving_agi_governance", "--output-dir", str(tmp_path)]) == 0
    stdout, stderr = capfd.readouterr()
    assert "UNTRUSTED_OUTPUT_EXECUTED" not in stdout + stderr


def test_missing_optional_module_stops_before_creating_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catalog.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(catalog.subprocess, "run", lambda *a, **k: pytest.fail("unexpected launch"))
    output = tmp_path / "unused"
    assert catalog.main(["run", "alpha_super_planner_v1", "--output-dir", str(output)]) == 2
    assert "Missing Python modules: rich" in capsys.readouterr().out
    assert not output.exists()


def test_missing_bundled_data_stops_before_downloading_or_writing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(catalog, "DEMOS_ROOT", tmp_path / "incomplete-install")
    monkeypatch.setattr(catalog.subprocess, "run", lambda *a, **k: pytest.fail("unexpected launch"))
    output = tmp_path / "unused"
    assert catalog.main(["run", "macro_sentinel", "--output-dir", str(output)]) == 2
    assert "Missing bundled files:" in capsys.readouterr().out
    assert not output.exists()


def test_check_json_has_no_launch_or_state_side_effects(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalog.subprocess, "run", lambda *a, **k: pytest.fail("unexpected launch"))
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-appear-in-output")
    assert catalog.main(["check", "solving_agi_governance", "--json"]) == 0
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["passed"] is True and report["offline_defaults"] is True
    assert "must-not-appear-in-output" not in output
    assert list(tmp_path.iterdir()) == []


def test_library_check_does_not_claim_a_runnable_backend(capsys):
    assert catalog.main(["check", "utils", "--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["runnable"] is False and report["passed"] is False


def test_offline_settings_do_not_modify_parent_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "parent-only")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "parent-only")
    monkeypatch.setenv("AF_TRACING", "true")
    monkeypatch.setenv("NEO4J_URI", "bolt://parent-database.invalid:7687")
    monkeypatch.setenv("PGHOST", "parent-database.invalid")
    result = catalog.environment_for(entry("meta_agentic_tree_search_v0"), tmp_path)
    assert result["OPENAI_API_KEY"] == result["ANTHROPIC_API_KEY"] == ""
    assert result["NO_LLM"] == result["HF_HUB_OFFLINE"] == result["PYTHONSAFEPATH"] == "1"
    assert result["AF_TRACING"] == "false"
    assert result["OPENAI_AGENTS_DISABLE_TRACING"] == "true"
    assert result["NEO4J_URI"] == result["PGHOST"] == ""
    assert os.environ["OPENAI_API_KEY"] == "parent-only"
    assert os.environ["NEO4J_URI"] == "bolt://parent-database.invalid:7687"
    assert os.environ["PGHOST"] == "parent-database.invalid"
    assert all(Path(path).is_absolute() for path in result["PYTHONPATH"].split(os.pathsep))


def test_tree_search_ignores_output_directory_provider_configuration(tmp_path, monkeypatch):
    from alpha_factory_v1.demos.meta_agentic_tree_search_v0 import lab_cli

    config = tmp_path / "configs" / "default.yaml"
    config.parent.mkdir()
    config.write_text("rewriter: openai\nepisodes: 999\n")
    (tmp_path / "scenarios.json").write_text("[]")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    command = catalog.command_for(entry("meta_agentic_tree_search_v0"), tmp_path)
    assert lab_cli.main(command[3:]) == 0
    output = next((tmp_path / "search-runs").glob("*/run.json"))
    report = json.loads(output.read_text())
    assert report["input"]["id"] == "release-design"
    assert report["input"]["seed"] == 42
    assert report["result"]["proposal"]["state"] == "UNAPPROVED"


def test_marketplace_dry_run_uses_its_bundled_job(tmp_path, monkeypatch):
    from alpha_factory_v1.demos.alpha_agi_marketplace_v1 import marketplace

    replacement = tmp_path / "alpha_factory_v1/demos/alpha_agi_marketplace_v1/examples/sample_job.json"
    replacement.parent.mkdir(parents=True)
    replacement.write_text('{"agent":"wrong-job-from-output"}')
    monkeypatch.chdir(tmp_path)
    command = catalog.command_for(entry("alpha_agi_marketplace_v1"), tmp_path)
    args = marketplace.parse_args(command[3:])
    assert Path(args.job_file).is_relative_to(catalog.DEMOS_ROOT)
    assert marketplace.load_job(args.job_file)["agent"] != "wrong-job-from-output"
    assert args.dry_run


def test_unavailable_import_metadata_is_a_missing_prerequisite(monkeypatch):
    def broken(_name):
        raise ValueError("module has no spec")

    monkeypatch.setattr(catalog.importlib.util, "find_spec", broken)
    report = catalog.prerequisites_for(entry("alpha_super_planner_v1"))
    assert report["missing_modules"] == ["rich"] and report["passed"] is False


def test_check_does_not_import_native_training_backends(monkeypatch):
    observed = []
    monkeypatch.setattr(catalog.importlib.util, "find_spec", lambda name: observed.append(name) or object())
    before = set(sys.modules)
    report = catalog.prerequisites_for(entry("aiga_meta_evolution"))
    assert report["passed"] is True
    assert set(observed) == {"numpy", "torch", "gymnasium", "pandas"}
    assert set(sys.modules) == before
