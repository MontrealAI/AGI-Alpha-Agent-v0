# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


os.environ.setdefault("PYTEST_NET_OFF", "1")

_INSIGHT_DIR = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1"
_INSIGHT_DIST = _INSIGHT_DIR / "dist"
_NODE_MAJOR_RE = re.compile(r"v?(\d+)")


def _node_major() -> int | None:
    if not shutil.which("node"):
        return None
    try:
        version = subprocess.check_output(["node", "--version"], text=True).strip()
    except subprocess.SubprocessError:
        return None
    match = _NODE_MAJOR_RE.match(version)
    if not match:
        return None
    return int(match.group(1))


def _ensure_insight_node_modules(env: dict[str, str]) -> None:
    if (_INSIGHT_DIR / "node_modules").exists():
        return
    if os.environ.get("PYTEST_NET_OFF") == "1":
        pytest.skip("Insight node_modules missing while network access is disabled")
    subprocess.check_call(["npm", "ci"], cwd=_INSIGHT_DIR, env=env)


def _ensure_insight_dist() -> Path:
    if _INSIGHT_DIST.exists() and (_INSIGHT_DIST / "index.html").exists():
        return _INSIGHT_DIST
    if not shutil.which("npm"):
        pytest.skip("npm not available")
    node_major = _node_major()
    if node_major is None or node_major < 22:
        pytest.skip("Node.js 22+ is required to build the Insight demo")
    env = os.environ.copy()
    env.setdefault("FETCH_ASSETS_SKIP_LLM", "1")
    _ensure_insight_node_modules(env)
    subprocess.check_call(["npm", "run", "build"], cwd=_INSIGHT_DIR, env=env)
    if not _INSIGHT_DIST.exists():
        pytest.skip("Insight browser dist assets missing; run npm build to generate them")
    return _INSIGHT_DIST


def pytest_configure() -> None:
    try:
        from hypothesis import HealthCheck, settings
    except Exception:
        return

    profile_name = os.getenv("HYPOTHESIS_PROFILE", "alpha_factory")
    try:
        settings.register_profile(
            profile_name,
            suppress_health_check=[
                HealthCheck.filter_too_much,
                HealthCheck.function_scoped_fixture,
            ],
        )
    except ValueError:
        pass
    settings.load_profile(profile_name)


@pytest.fixture
def non_network(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PYTEST_NET_OFF", "1")


@pytest.fixture(scope="session")
def insight_dist() -> Path:
    return _ensure_insight_dist()


@pytest.fixture(scope="session")
def insight_repo() -> Path:
    return _INSIGHT_DIR


@pytest.fixture
def scenario(request):  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    name = request.param
    if isinstance(name, str) and name.startswith("scenario_"):
        name = name.removeprefix("scenario_")
    return replay.load_scenario(name)


@pytest.fixture
def scenario_1994_web():  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("1994_web")


@pytest.fixture
def scenario_2001_genome():  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2001_genome")


@pytest.fixture
def scenario_2008_mobile():  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2008_mobile")


@pytest.fixture
def scenario_2012_dl():  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2012_dl")


@pytest.fixture
def scenario_2020_mrna():  # type: ignore[no-untyped-def]
    from alpha_factory_v1.core.simulation import replay

    return replay.load_scenario("2020_mrna")
