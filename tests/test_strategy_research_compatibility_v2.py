# SPDX-License-Identifier: Apache-2.0
"""The v2 layer must not inherit exceptions after source/configuration drift."""
from __future__ import annotations

from contextlib import contextmanager
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "strategy_compatibility_v2", ROOT / "scripts/check_strategy_research_compatibility_v2.py"
)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
PROFILE = json.loads((ROOT / "scripts" / GUARD.PROFILE_NAME).read_text())


@pytest.fixture(scope="module")
def checkout(tmp_path_factory):
    root = tmp_path_factory.mktemp("strategy-v2")
    legacy = json.loads((ROOT / "scripts/strategy_research_source_pins.json").read_text())
    names = set(PROFILE["files"]) | set(legacy["files"]) | {"scripts/" + GUARD.PROFILE_NAME}
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    yield root
    shutil.rmtree(root)


@contextmanager
def altered(path, data):
    original = path.read_bytes() if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    try:
        yield
    finally:
        if original is None:
            path.unlink()
        else:
            path.write_bytes(original)


def test_complete_original_and_successor_identity(checkout):
    report = GUARD.require_preserved(checkout)
    assert report["legacy"]["matched"] is True
    assert len(report["legacy"]["checks"]) == 241
    assert len(report["exceptions"]) == 13
    assert not report["productionAuthority"]


@pytest.mark.parametrize("name", sorted(PROFILE["files"]))
def test_each_bound_body_rejects_change(checkout, name):
    path = checkout / name
    with altered(path, path.read_bytes() + b"\n"):
        with pytest.raises(ValueError):
            GUARD.require_preserved(checkout)


@pytest.mark.parametrize("mutation", ["new-file", "new-rule", "duplicate", "changed-pin"])
def test_profile_cannot_expand_or_change(checkout, mutation):
    path = checkout / "scripts" / GUARD.PROFILE_NAME
    profile = json.loads(path.read_text())
    if mutation == "new-file":
        profile["ruff_extend_per_file_ignores"]["unreviewed.py"] = ["E721"]
    elif mutation == "new-rule":
        next(iter(profile["ruff_extend_per_file_ignores"].values())).append("F821")
    elif mutation == "changed-pin":
        profile["predecessor_pins_sha256"] = "0" * 64
    raw = json.dumps(profile).encode()
    if mutation == "duplicate":
        raw = b'{"schema":"duplicate",' + raw[1:]
    with altered(path, raw), pytest.raises(ValueError):
        GUARD.require_preserved(checkout)


@pytest.mark.parametrize(
    "name",
    ["scripts/ruff.toml", "scripts/.ruff.toml", "scripts/pyproject.toml", "contrib/strategy_succession/qa/ruff.toml"],
)
def test_nested_configuration_rejected(checkout, name):
    with altered(checkout / name, b"# even an empty override is unreviewed\n"), pytest.raises(ValueError):
        GUARD.require_preserved(checkout)


def test_missing_and_symlink_body_rejected(checkout):
    name = next(iter(PROFILE["ruff_extend_per_file_ignores"]))
    target = checkout / name
    body = target.read_bytes()
    target.unlink()
    try:
        with pytest.raises(OSError):
            GUARD.require_preserved(checkout)
        target.symlink_to(checkout / "pyproject.toml")
        with pytest.raises(ValueError):
            GUARD.require_preserved(checkout)
    finally:
        if target.is_symlink():
            target.unlink()
        target.write_bytes(body)


@pytest.mark.parametrize(
    "name",
    ["--ignore=E721", "--config=x", "--select=F", "../x.py", "/x.py", "a/../x.py", "./x.py", "a\\x.py", "a//x.py", ""],
)
def test_caller_cannot_supply_options_or_noncanonical_names(checkout, name):
    with pytest.raises(ValueError):
        GUARD.run_ruff(checkout, [name])


def test_empty_selection_still_checks_identity(checkout):
    with altered(checkout / "pyproject.toml", b"# replaced\n"), pytest.raises(ValueError):
        GUARD.run_ruff(checkout, [])


def test_every_target_is_linted_and_guard_runs_after(checkout, monkeypatch):
    calls = []

    def invoke(command, cwd):
        calls.append(command)
        assert cwd == checkout
        assert command[:5] == [GUARD.sys.executable, "-m", "ruff", "check", "--force-exclude"]
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(GUARD.subprocess, "run", invoke)
    assert GUARD.run_ruff(checkout, ["one.py", "two.py", "three.py"], 2) == 0
    assert [c[c.index("--") + 1 :] for c in calls] == [["one.py", "two.py"], ["three.py"]]
    assert all(c.count("--extend-per-file-ignores") == 13 for c in calls)


def test_post_lint_drift_never_reports_success(checkout, monkeypatch):
    target = checkout / "pyproject.toml"
    original = target.read_bytes()

    def invoke(command, cwd):
        target.write_bytes(original + b"\n")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(GUARD.subprocess, "run", invoke)
    try:
        with pytest.raises(ValueError):
            GUARD.run_ruff(checkout, ["one.py"])
    finally:
        target.write_bytes(original)


@pytest.mark.parametrize("value", [True, 0, -1, 1.5])
def test_invalid_batch_never_skips_checks(checkout, value):
    with pytest.raises(ValueError):
        GUARD.run_ruff(checkout, [], value)


def test_exception_does_not_change_exact_type_semantics():
    class IntSubclass(int):
        pass

    predicate = compile("type(value) is int", "unchanged_exact_type", "eval")
    assert eval(predicate, {"value": 1}) is True
    assert eval(predicate, {"value": True}) is False
    assert eval(predicate, {"value": IntSubclass(1)}) is False


def test_all_preserved_exact_builtin_comparisons_reject_subclasses():
    class IntSubclass(int):
        pass

    checked = 0
    for name in PROFILE["ruff_extend_per_file_ignores"]:
        for node in ast.walk(ast.parse((ROOT / name).read_text())):
            if (
                not isinstance(node, ast.Compare)
                or len(node.ops) != 1
                or not isinstance(node.left, ast.Call)
                or not isinstance(node.left.func, ast.Name)
                or node.left.func.id != "type"
                or len(node.comparators) != 1
                or not isinstance(node.comparators[0], ast.Name)
                or node.comparators[0].id not in {"int", "bool"}
                or not isinstance(node.ops[0], (ast.Is, ast.IsNot))
            ):
                continue
            comparison = copy.deepcopy(node)
            comparison.left.args = [ast.Name(id="candidate", ctx=ast.Load())]
            expression = compile(ast.fix_missing_locations(ast.Expression(comparison)), name, "eval")
            expected_type = int if node.comparators[0].id == "int" else bool
            for candidate in (1, True, IntSubclass(1)):
                exact = candidate.__class__ is expected_type
                expected = exact if isinstance(node.ops[0], ast.Is) else not exact
                assert eval(expression, {"candidate": candidate}) is expected
            checked += 1
    assert checked == 51


def test_directory_and_dot_cannot_expand_cli_targets(checkout):
    for name in (".", "scripts"):
        with pytest.raises(ValueError):
            GUARD.run_ruff(checkout, [name])
