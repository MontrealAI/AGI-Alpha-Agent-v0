# SPDX-License-Identifier: Apache-2.0
"""Exact-source lint compatibility refuses mutations and broader exemptions."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import check_strategy_research_source as guard

ROOT = Path(__file__).resolve().parents[1]


def write_config(root: Path, config: dict) -> None:
    lines = ["[tool.ruff]"]
    for key, value in config.items():
        if key != "lint":
            lines.append(json.dumps(key) + " = " + json.dumps(value))
    lines.append("[tool.ruff.lint]")
    for key, value in config["lint"].items():
        if not isinstance(value, dict):
            lines.append(json.dumps(key) + " = " + json.dumps(value))
    for key, value in config["lint"].items():
        if isinstance(value, dict):
            lines.append("[tool.ruff.lint." + key + "]")
            lines.extend(json.dumps(name) + " = " + json.dumps(rules) for name, rules in value.items())
    (root / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def prepared(tmp_path: Path):
    pins = guard.load_pins()
    for name, identity in pins["files"].items():
        source = ROOT / identity["source_path"]
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    metadata = tmp_path / guard.NON_RUFF_PROJECT
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_bytes((ROOT / guard.NON_RUFF_PROJECT).read_bytes())
    config = copy.deepcopy(pins["ruff_baseline"])
    config["lint"]["per-file-ignores"] = copy.deepcopy(pins["ruff_per_file_ignores"])
    write_config(tmp_path, config)
    return tmp_path, pins, config


def test_all_original_bodies_and_two_exact_vendored_sources_match(prepared):
    root, pins, _ = prepared
    report = guard.require_preserved(root)
    assert report["matched"] is True
    assert len(report["checks"]) == 241
    assert len([name for name in pins["files"] if name.startswith(guard.STUDY + "/")]) == 239
    assert len(pins["ruff_per_file_ignores"]) == 14
    assert report["runtimeQualified"] is False and report["productionAuthority"] is False
    assert all(item["matched"] for item in report["checks"])
    assert len(report["projectConfigurationChecks"]) == 1
    assert report["projectConfigurationChecks"][0]["matched"] is True
    assert report["projectConfigurationChecks"][0]["ruffTablePresent"] is False


@pytest.mark.parametrize("mutation", ["same-length", "missing", "leaf-symlink", "ancestor-symlink"])
def test_exact_regular_source_required(prepared, mutation):
    root, _, _ = prepared
    path = root / guard.STUDY / "companion/analyze.py"
    if mutation == "same-length":
        body = path.read_bytes()
        path.write_bytes(bytes([body[0] ^ 1]) + body[1:])
    elif mutation == "missing":
        path.unlink()
    elif mutation == "leaf-symlink":
        retained = root / "retained-original.py"
        path.rename(retained)
        path.symlink_to(retained)
    else:
        parent = path.parent
        retained = root / "retained-companion"
        parent.rename(retained)
        parent.symlink_to(retained, target_is_directory=True)
    with pytest.raises(ValueError, match="source or exact lint"):
        guard.require_preserved(root)


def test_vendored_checker_mutation_cannot_inherit_the_exception(prepared):
    root, _, _ = prepared
    path = root / "contrib/strategy_succession/worker/scientific/review/check.py"
    path.write_bytes(path.read_bytes() + b"\n")
    assert guard.check(root)["matched"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "extra-path",
        "extra-rule",
        "rule-prefix",
        "missing-exception",
        "global-ignore",
        "global-exclude",
        "global-select",
        "extend-config",
        "extend-per-file",
    ],
)
def test_effective_ruff_scope_cannot_broaden(prepared, mutation):
    root, _, config = prepared
    ignores = config["lint"]["per-file-ignores"]
    first = next(iter(ignores))
    if mutation == "extra-path":
        ignores[guard.STUDY + "/**/*.py"] = ["E701"]
    elif mutation == "extra-rule":
        ignores[first].append("F821")
    elif mutation == "rule-prefix":
        ignores[first] = ["F"]
    elif mutation == "missing-exception":
        del ignores[first]
    elif mutation == "global-ignore":
        config["lint"]["ignore"] = ["ALL"]
    elif mutation == "global-exclude":
        config["exclude"].append(guard.STUDY)
    elif mutation == "global-select":
        config["lint"]["select"] = ["E701"]
    elif mutation == "extend-config":
        config["extend"] = "another-config.toml"
    else:
        config["lint"]["extend-per-file-ignores"] = {"*.py": ["F841"]}
    write_config(root, config)
    report = guard.check(root)
    assert report["matched"] is False and report["configurationErrors"]


@pytest.mark.parametrize("name", ["ruff.toml", ".ruff.toml", "pyproject.toml"])
def test_nested_configuration_cannot_override_preserved_lint_scope(prepared, name):
    root, _, _ = prepared
    (root / guard.STUDY / "review" / name).write_text("# unreviewed override\n", encoding="utf-8")
    report = guard.check(root)
    assert report["matched"] is False
    assert any("Unreviewed Ruff configuration" in error for error in report["configurationErrors"])


def test_root_alternate_configuration_is_refused(prepared):
    root, _, _ = prepared
    (root / "ruff.toml").write_text("# would take priority over pyproject\n", encoding="utf-8")
    assert guard.check(root)["matched"] is False


@pytest.mark.parametrize("mutation", ["change-metadata", "add-ruff", "missing", "symlink"])
def test_only_exact_pinned_non_ruff_package_metadata_is_allowed(prepared, mutation):
    root, _, _ = prepared
    metadata = root / guard.NON_RUFF_PROJECT
    if mutation == "change-metadata":
        metadata.write_bytes(metadata.read_bytes() + b"\n# unreviewed metadata edit\n")
    elif mutation == "add-ruff":
        metadata.write_bytes(metadata.read_bytes() + b"\n[tool.ruff]\nexclude = ['worker/scientific']\n")
    elif mutation == "missing":
        metadata.unlink()
    else:
        retained = root / "original-project.toml"
        metadata.rename(retained)
        metadata.symlink_to(retained)
    report = guard.check(root)
    assert report["matched"] is False
    assert report["projectConfigurationChecks"][0]["matched"] is False


def test_other_nested_metadata_remains_unreviewed_even_without_a_ruff_table(prepared):
    root, _, _ = prepared
    path = root / "contrib/strategy_succession/worker/pyproject.toml"
    path.write_text("[project]\nname = 'unreviewed'\n", encoding="utf-8")
    assert guard.check(root)["matched"] is False


def test_even_matching_metadata_pin_cannot_admit_a_nested_ruff_table(prepared, monkeypatch):
    root, pins, _ = prepared
    metadata = root / guard.NON_RUFF_PROJECT
    body = metadata.read_bytes() + b"\n[tool.ruff]\n"
    metadata.write_bytes(body)
    pins["non_ruff_project_configs"][guard.NON_RUFF_PROJECT] = {
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    monkeypatch.setattr(guard, "load_pins", lambda: pins)
    report = guard.check(root)
    assert report["matched"] is False
    assert report["projectConfigurationChecks"][0]["ruffTablePresent"] is True


def test_pinned_package_metadata_does_not_shadow_the_repository_ruff_profile(prepared):
    root, _, _ = prepared
    target = "contrib/strategy_succession/worker/scientific/review/check.py"
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-settings", target],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    selected = next(line for line in result.stdout.splitlines() if line.startswith("Settings path: "))
    observed = json.loads(selected.split(": ", 1)[1])
    assert Path(observed).resolve() == (root / "pyproject.toml").resolve()


def test_static_pin_table_changes_require_reviewed_guard_source_change(tmp_path, monkeypatch):
    pins = tmp_path / "changed-pins.json"
    pins.write_bytes(guard.PINS_FILE.read_bytes() + b"\n")
    monkeypatch.setattr(guard, "PINS_FILE", pins)
    with pytest.raises(ValueError, match="pin table differs"):
        guard.load_pins()


def test_static_pin_table_symlink_is_refused(tmp_path, monkeypatch):
    target = tmp_path / "pins.json"
    target.symlink_to(guard.PINS_FILE)
    monkeypatch.setattr(guard, "PINS_FILE", target)
    with pytest.raises(ValueError, match="symlink"):
        guard.load_pins()


def test_guard_has_no_regeneration_or_source_selector():
    result = subprocess.run([sys.executable, str(Path(guard.__file__)), "--regenerate"], capture_output=True, text=True)
    assert result.returncode == 2 and "no root, source, pin or regeneration selectors" in result.stderr


def test_unused_assignment_exception_is_limited_to_reviewed_exact_checker_bodies():
    pins = guard.load_pins()
    scoped = {name for name, rules in pins["ruff_per_file_ignores"].items() if "F841" in rules}
    assert scoped == {
        guard.STUDY + "/review/check.py",
        guard.STUDY + "/review/results/audit_main.py",
        "contrib/strategy_succession/worker/scientific/review/check.py",
    }
    assert all(set(rules) <= {"E701", "E702", "F841"} for rules in pins["ruff_per_file_ignores"].values())


def test_prior_dependency_metadata_cannot_reuse_the_updated_pin(prepared):
    root, _, _ = prepared
    metadata = root / guard.NON_RUFF_PROJECT
    body = metadata.read_bytes()
    assert b'"starlette==1.7.0"' in body
    metadata.write_bytes(body.replace(b'"starlette==1.7.0"', b'"starlette==0.52.1"'))
    report = guard.check(root)
    assert report["matched"] is False
    assert report["projectConfigurationChecks"][0]["matched"] is False
