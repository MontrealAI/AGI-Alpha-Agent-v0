# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the `/metrics` endpoint."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import nullcontext
from typing import Any, cast

import pytest

pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _start_server(port: int, env: dict[str, str] | None = None) -> subprocess.Popen[bytes]:
    cmd = [
        sys.executable,
        "-m",
        "src.interface.api_server",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    return subprocess.Popen(
        cmd,
        env=env or os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _start_server_with_retry(
    port: int, env: dict[str, str] | None = None, *, attempts: int = 3
) -> subprocess.Popen[bytes]:
    url = f"http://127.0.0.1:{port}"
    last_err: AssertionError | None = None
    for _ in range(attempts):
        proc = _start_server(port, env)
        try:
            _wait_ready(proc, url)
            return proc
        except AssertionError as err:
            last_err = err
            proc.terminate()
            proc.wait(timeout=5)
    assert last_err is not None
    raise last_err


def _wait_ready(proc: subprocess.Popen[bytes], url: str, *, interval: float = 0.05, attempts: int = 100) -> None:
    for _ in range(attempts):
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise AssertionError(
                f"server exited with code {proc.returncode}\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}"
            )
        try:
            r = httpx.get(f"{url}/metrics")
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(interval)
    stdout, stderr = proc.communicate()
    raise AssertionError(
        f"server did not start within {attempts * interval:.1f}s\n"
        f"exit code {proc.poll()}\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}"
    )


def test_metrics_endpoint_subprocess() -> None:
    port = _free_port()
    proc = _start_server_with_retry(port)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_ready(proc, url)
        resp = httpx.get(f"{url}/metrics")
        assert resp.status_code == 200
        text = resp.text
        assert "api_requests_total" in text
        assert "api_request_seconds" in text
        assert "dgm_best_score" in text
        assert "dgm_archive_mean" in text
        assert "dgm_lineage_depth" in text
        assert text.startswith("# HELP")
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_metrics_curl() -> None:
    port = _free_port()
    proc = _start_server_with_retry(port)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_ready(proc, url)
        out = subprocess.check_output(["curl", "-sf", f"{url}/metrics"])
        text = out.decode()
        assert "api_requests_total" in text
        assert "api_request_seconds" in text
        assert "dgm_best_score" in text
        assert "dgm_archive_mean" in text
        assert "dgm_lineage_depth" in text
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_tracing_env_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    endpoint = "http://collector:4317"
    called: list[str] = []

    class DummyExporter:
        def __init__(self, endpoint: str | None = None, *args: Any, **_kw: Any) -> None:  # noqa: D401 - simple init
            called.append(endpoint or "")

    class DummyTracer:
        def __init__(self) -> None:
            self.spans: list[str] = []

        def start_as_current_span(self, name: str) -> Any:
            self.spans.append(name)
            return nullcontext()

    class DummyTrace:
        def __init__(self) -> None:
            self.tracer = DummyTracer()

        def set_tracer_provider(self, _provider: Any) -> None:
            pass

        def get_tracer(self, _name: str) -> DummyTracer:
            return self.tracer

    class DummyMetrics:
        def set_meter_provider(self, _provider: Any) -> None:  # noqa: D401 - simple stub
            pass

        def get_meter(self, _name: str) -> None:
            return None

    import importlib
    import alpha_factory_v1.core.utils.tracing as tracing

    if not hasattr(tracing, "OTLPSpanExporter"):
        pytest.skip("OTLP exporter not available")

    monkeypatch.setattr(tracing, "OTLPSpanExporter", DummyExporter)
    monkeypatch.setattr(tracing, "OTLPMetricExporter", DummyExporter)
    monkeypatch.setattr(tracing, "trace", DummyTrace())
    monkeypatch.setattr(tracing, "metrics", DummyMetrics())
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)

    tracing = importlib.reload(tracing)
    assert called == [endpoint, endpoint]
    assert tracing.tracer is not None
    with tracing.span("demo"):
        pass
    dummy = cast(DummyTracer, tracing.tracer)
    assert "demo" in dummy.spans
