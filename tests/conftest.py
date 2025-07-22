# SPDX-License-Identifier: Apache-2.0
import os
import warnings
import pytest
import sys
import types
import importlib.util
import socket
from typing import Any

# Ensure runtime dependencies are present before collecting tests
try:  # pragma: no cover - best effort environment setup
    from check_env import main as check_env_main, has_network

    wheelhouse = os.getenv("WHEELHOUSE")
    args = ["--auto-install"]
    if wheelhouse:
        args += ["--wheelhouse", wheelhouse]
    net_ok = has_network()
    if wheelhouse is None and not net_ok:  # warn when offline with no wheelhouse
        warnings.warn(
            "Neither network access nor a wheelhouse was detected. "
            "Run './scripts/build_offline_wheels.sh' and set WHEELHOUSE before testing.",
            RuntimeWarning,
        )
    rc = check_env_main(args)
    proxy_set = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    net_ok = net_ok or bool(proxy_set) or rc == 0
    os.environ.setdefault("PYTEST_NET_OFF", "0" if net_ok else "1")
    if rc:
        if not wheelhouse and not net_ok:
            reason = "no network and no wheelhouse; run 'python check_env.py --auto-install --wheelhouse <dir>'"
        else:
            reason = "Environment check failed, run 'python check_env.py --auto-install'"
        pytest.skip(reason, allow_module_level=True)
except Exception as exc:  # pragma: no cover - environment issue
    pytest.skip(f"check_env execution failed: {exc}", allow_module_level=True)

# Skip early when heavy optional deps are missing to avoid stack traces
pytest.importorskip("yaml", reason="yaml required")
pytest.importorskip("google.protobuf", reason="protobuf required")
pytest.importorskip("cachetools", reason="cachetools required")
# numpy is a hard requirement for many tests
pytest.importorskip("numpy", reason="numpy required")

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_torch: mark test that depends on the torch package",
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "requires_torch" in item.keywords and not _HAS_TORCH:
        pytest.skip("torch required", allow_module_level=True)


@pytest.fixture
def non_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable outbound networking for the duration of a test."""

    def _blocked(*_a: Any, **_k: Any) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    yield


try:  # skip all tests if the simulation module fails to import
    from alpha_factory_v1.core.simulation import replay
except Exception as exc:  # pragma: no cover - environment issue
    pytest.skip(
        (
            f"Critical import failed: {exc}.\n"
            "Run `python check_env.py --auto-install` "
            "(add `--wheelhouse <dir>` when offline)."
        ),
        allow_module_level=True,
    )

rocketry_stub = types.ModuleType("rocketry")
rocketry_stub.Rocketry = type("Rocketry", (), {})  # type: ignore[attr-defined]
conds_mod = types.ModuleType("rocketry.conds")
conds_mod.every = lambda *_: None  # type: ignore[attr-defined]
rocketry_stub.conds = conds_mod  # type: ignore[attr-defined]
sys.modules.setdefault("rocketry", rocketry_stub)
sys.modules.setdefault("rocketry.conds", conds_mod)


@pytest.fixture(scope="module")  # type: ignore[misc]
def scenario_1994_web() -> replay.Scenario:
    return replay.load_scenario("1994_web")


@pytest.fixture(scope="module")  # type: ignore[misc]
def scenario_2001_genome() -> replay.Scenario:
    return replay.load_scenario("2001_genome")


@pytest.fixture(scope="module")  # type: ignore[misc]
def scenario_2008_mobile() -> replay.Scenario:
    return replay.load_scenario("2008_mobile")


@pytest.fixture(scope="module")  # type: ignore[misc]
def scenario_2012_dl() -> replay.Scenario:
    return replay.load_scenario("2012_dl")


@pytest.fixture(scope="module")  # type: ignore[misc]
def scenario_2020_mrna() -> replay.Scenario:
    return replay.load_scenario("2020_mrna")


@pytest.fixture  # type: ignore[misc]
def scenario(request: pytest.FixtureRequest) -> replay.Scenario:
    return request.getfixturevalue(request.param)
