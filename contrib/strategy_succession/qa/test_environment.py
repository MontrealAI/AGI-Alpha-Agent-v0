# SPDX-License-Identifier: Apache-2.0
"""Launch admission checks; no mission, journal or runtime qualification is created."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import serve


@pytest.fixture
def environment(monkeypatch, tmp_path):
    dependencies = dict(
        line.split("==")
        for line in (serve.ROOT / "requirements-qualification.txt").read_text().splitlines()
        if line and not line.startswith("#")
    )
    profile = {
        "schema": "engineering-environment/v1",
        "system": "Linux",
        "machine": "x86_64",
        "os_id": "ubuntu",
        "os_version_id": "24.04",
        "libc": {"name": "glibc", "version": "2.39"},
        "python_implementation": "CPython",
        "python_version": "3.12.14",
        "node_version": "24.22.1",
        "dependencies": dependencies,
    }
    node = tmp_path / "node"
    node.write_text("test executable identity only")
    monkeypatch.setattr(serve.platform, "freedesktop_os_release", lambda: {"ID": "ubuntu", "VERSION_ID": "24.04"})
    monkeypatch.setattr(serve.platform, "system", lambda: "Linux")
    monkeypatch.setattr(serve.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(serve.platform, "libc_ver", lambda: ("glibc", "2.39"))
    monkeypatch.setattr(serve.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(serve.platform, "python_version", lambda: "3.12.14")
    monkeypatch.setattr(serve.shutil, "which", lambda _: str(node))
    monkeypatch.setattr(serve.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="v24.22.1\n"))
    monkeypatch.setattr(serve.importlib.metadata, "version", lambda name: dependencies[name])
    return profile, node


def test_exact_reviewed_combination_returns_checked_node(environment):
    profile, node = environment
    assert serve.qualified_environment(profile) == str(node.resolve())


@pytest.mark.parametrize("observed", ["v22.0.0", "v24.22.2", ""])
def test_unknown_node_is_refused_before_operator_state(environment, monkeypatch, tmp_path, observed):
    profile, _ = environment
    monkeypatch.setattr(serve.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=observed))
    touched = []
    monkeypatch.setattr(serve, "Journal", lambda *a, **k: touched.append("journal"))
    monkeypatch.setattr(serve, "FixedWorker", lambda *a, **k: touched.append("worker"))
    manifest = tmp_path / "profile.json"
    manifest.write_text(
        json.dumps({"schema": "strategy-engineering-installation/v1", "qualified_environment": profile})
    )
    with pytest.raises(ValueError, match="Node version is unqualified"):
        serve.create(tmp_path / "nonexistent-operator-home", manifest)
    assert touched == []


@pytest.mark.parametrize(
    "attribute,value",
    [("python_version", "3.12.15"), ("python_implementation", "PyPy"), ("system", "Darwin"), ("machine", "aarch64")],
)
def test_unknown_python_or_host_is_refused(environment, monkeypatch, attribute, value):
    profile, _ = environment
    monkeypatch.setattr(serve.platform, attribute, lambda: value)
    with pytest.raises(ValueError, match="Host or Python environment is unqualified"):
        serve.qualified_environment(profile)


@pytest.mark.parametrize("component", ["os", "libc"])
def test_unknown_os_or_libc_is_refused(environment, monkeypatch, component):
    profile, _ = environment
    if component == "os":
        monkeypatch.setattr(serve.platform, "freedesktop_os_release", lambda: {"ID": "ubuntu", "VERSION_ID": "26.04"})
    else:
        monkeypatch.setattr(serve.platform, "libc_ver", lambda: ("glibc", "2.40"))
    with pytest.raises(ValueError, match="Host or Python environment is unqualified"):
        serve.qualified_environment(profile)


@pytest.mark.parametrize("name", ["numpy", "scipy", "alpha-factory-v1"])
def test_unknown_dependency_is_refused(environment, monkeypatch, name):
    profile, _ = environment
    monkeypatch.setattr(
        serve.importlib.metadata,
        "version",
        lambda package: "unknown" if package == name else profile["dependencies"][package],
    )
    with pytest.raises(ValueError, match="Dependency version is unqualified: " + name):
        serve.qualified_environment(profile)


def test_environment_cannot_omit_dependency_or_add_unknown_profile_field(environment):
    profile, _ = environment
    missing = copy.deepcopy(profile)
    del missing["dependencies"]["numpy"]
    with pytest.raises(ValueError, match="complete pinned dependency inventory"):
        serve.qualified_environment(missing)
    with pytest.raises(ValueError, match="exact reviewed environment profile"):
        serve.qualified_environment({**profile, "auto_qualify": True})


def test_symlink_profile_is_refused_before_operator_state(environment, monkeypatch, tmp_path):
    profile, _ = environment
    original = tmp_path / "profile.json"
    original.write_text(
        json.dumps({"schema": "strategy-engineering-installation/v1", "qualified_environment": profile})
    )
    alias = tmp_path / "profile-link.json"
    alias.symlink_to(original)
    monkeypatch.setattr(serve, "Journal", lambda *a, **k: pytest.fail("operator state was opened"))
    with pytest.raises(ValueError, match="regular reviewed installation profile"):
        serve.create(tmp_path, alias)


def test_exact_environment_does_not_grant_native_authority(environment, monkeypatch, tmp_path):
    profile, node = environment
    captured = {}

    class TestJournal:
        def __init__(self, home):
            self.root = home

        def verify(self):
            return {"valid": True}

    monkeypatch.setattr(serve, "Journal", TestJournal)
    monkeypatch.setattr(serve, "ExecutorPolicy", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(serve, "FixedWorker", lambda *a, **kwargs: captured.update(worker=kwargs))

    def app(journal, worker, policy, **kwargs):
        captured["policy"] = policy
        return SimpleNamespace(state=SimpleNamespace())

    monkeypatch.setattr(serve, "create_strategy_app", app)
    document = {
        "schema": "strategy-engineering-installation/v1",
        "qualified_environment": profile,
        "qualified_runtime_versions": ["1.42.0"],
        "runtime_python_files": {},
        "files": {},
        "runtime_enforcement_files": [],
        "native_scipy_version": "unqualified-if-enabled",
        "executor_id": "test-only",
        "per_plan_caps": {
            "service_work": 500000,
            "improvement_work": 3000000,
            "native_calls": 6,
            "native_solve_seconds": 20,
        },
        "total_caps": {
            "service_work": 1000000,
            "improvement_work": 6000000,
            "native_calls": 12,
            "native_solve_seconds": 40,
        },
        "max_requests": 4,
        "grant_seconds": 600,
        "request_seconds": 120,
        "max_output_bytes": 1000000,
    }
    manifest = tmp_path / "profile.json"
    manifest.write_text(json.dumps(document))
    serve.create(tmp_path, manifest, native=False)
    policy = captured["policy"]
    assert policy.allow_native is False
    assert policy.total.native_calls == policy.total.native_solve_seconds == 0
    assert all(limit.native_calls == limit.native_solve_seconds == 0 for limit in policy.methods.values())
    assert captured["worker"]["node"] == str(node.resolve())
    profile_source = next(source for source in policy.sources if source.label == "installation-profile")
    assert profile_source.path == manifest.resolve()
    assert profile_source.sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()
