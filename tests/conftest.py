# SPDX-License-Identifier: Apache-2.0
import importlib.util
import os
import shutil
import signal
import socket
import sys
import types
import warnings
from pathlib import Path
from typing import Any

import pytest

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
_RUN_AIGA = os.getenv("ENABLE_AIGA_TESTS") == "1"
_DEFAULT_TIMEOUT_SEC = int(os.getenv("PYTEST_TIMEOUT_SEC", "600"))
_INSIGHT_DIST_TESTS = {
    "test_browser_ui.py",
    "test_evolution_panel_reload.py",
    "test_install_button.py",
    "test_pwa_offline.py",
    "test_pwa_update_reload.py",
    "test_quickstart_offline.py",
    "test_simulator_loader.py",
    "test_sw_offline_reload.py",
    "test_wasm_base64.py",
    "test_workbox_integrity.py",
    "test_sw_integrity.py",
    "test_umap_fallback.py",
}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_torch: mark test that depends on the torch package",
    )
    config.addinivalue_line(
        "markers",
        "timeout(seconds): override the default per-test timeout in seconds",
    )


def _resolve_timeout(item: pytest.Item) -> int:
    marker = item.get_closest_marker("timeout")
    if marker and marker.args:
        try:
            return int(marker.args[0])
        except (TypeError, ValueError):
            return _DEFAULT_TIMEOUT_SEC
    return _DEFAULT_TIMEOUT_SEC


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Any:
    if not hasattr(signal, "SIGALRM"):
        yield
        return
    timeout_sec = _resolve_timeout(item)
    if timeout_sec <= 0:
        yield
        return

    def _handler(signum: int, frame: object | None) -> None:
        raise TimeoutError(f"Test exceeded timeout of {timeout_sec} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_sec)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "requires_torch" in item.keywords and not _HAS_TORCH:
        pytest.skip("torch required", allow_module_level=True)
    if item.fspath and item.fspath.basename in _INSIGHT_DIST_TESTS:
        repo_root = Path(__file__).resolve().parents[1]
        dist_dir = repo_root / "alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/dist"
        if not dist_dir.exists():
            pytest.skip("dist/index.html missing; run npm run build", allow_module_level=True)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _RUN_AIGA:
        return

    skip_aiga = pytest.mark.skip(
        reason="Set ENABLE_AIGA_TESTS=1 to exercise the AIGA meta-evolution demo",
    )
    for item in items:
        if "test_aiga" in item.nodeid:
            item.add_marker(skip_aiga)


@pytest.fixture
def non_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable outbound networking for the duration of a test."""

    def _blocked(*_a: Any, **_kw: Any) -> None:
        raise OSError("network disabled")

    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    try:
        import requests

        monkeypatch.setattr(requests.sessions.Session, "request", _blocked)
    except Exception:
        pass
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


@pytest.fixture(scope="session", autouse=True)
def cleanup_ledger_dir() -> None:
    """Remove the default ledger directory created during tests."""
    yield
    ledger = Path("ledger")
    if ledger.exists():
        shutil.rmtree(ledger, ignore_errors=True)
