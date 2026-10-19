# SPDX-License-Identifier: Apache-2.0
"""Exercise real supervised processes; loopback HTTP is an explicit test-only transport substitution."""

from __future__ import annotations

import base64
import contextlib
import gzip
import json
import subprocess
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from unittest.mock import patch

import httpx
import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import computer, computer_read


@contextlib.contextmanager
def streaming_server(*, slow: bool) -> Iterator[tuple[str, threading.Event]]:
    """Serve actual delayed bytes only on loopback; production URL checks remain unchanged."""
    connected = threading.Event()
    finish = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            connected.set()
            try:
                for _ in range(100 if slow else 1):
                    self.wfile.write(b"public technical fixture")
                    self.wfile.flush()
                    if slow and finish.wait(0.05):
                        break
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/fixture", connected
    finally:
        finish.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def substitute_reader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    target: str | None = None,
    dns_wait: bool = False,
    startup_delay: float = 0,
) -> tuple[list[subprocess.Popen[bytes]], Path]:
    """Run the actual reader in an isolated child with explicit DNS/transport laboratory substitutions."""
    ready = tmp_path / "dns-entered"
    script = tmp_path / "controlled-reader.py"
    script.write_text(
        "import importlib.util, socket, time, pathlib\n"
        f"time.sleep({startup_delay!r})\n"
        f"spec=importlib.util.spec_from_file_location('read_fixture',{str(computer.READ_WORKER)!r})\n"
        "reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)\n"
        "original_dns=socket.getaddrinfo\n"
        "def controlled_dns(host,*args,**kwargs):\n"
        " if host=='example.org':\n"
        f"  pathlib.Path({str(ready)!r}).write_text('entered')\n"
        + ("  time.sleep(30)\n" if dns_wait else "")
        + "  return [(2,1,6,'',('1.1.1.1',443))]\n"
        " return original_dns(host,*args,**kwargs)\n"
        "reader.socket.getaddrinfo=controlled_dns\n"
        + (
            "OriginalClient=reader.httpx.Client\n"
            "class ControlledClient:\n"
            " def __init__(self,**kwargs):self.client=OriginalClient(**kwargs)\n"
            " def __enter__(self):self.client.__enter__();return self\n"
            " def __exit__(self,*args):return self.client.__exit__(*args)\n"
            f" def stream(self,method,url,**kwargs):return self.client.stream(method,{target!r},headers=kwargs['headers'])\n"
            "reader.httpx.Client=ControlledClient\n"
            if target
            else ""
        )
        + "reader.main()\n",
        encoding="utf-8",
    )
    real_popen = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def start(command: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
        assert command[:5] == [computer.sys.executable, "-I", "-S", "-B", "-X"]
        assert command[5].startswith("pycache_prefix=") and command[6:] == ["-c", computer.READ_BOOTSTRAP]
        assert list(Path(command[5].split("=", 1)[1]).iterdir()) == []
        assert set(kwargs["env"]) <= {"SYSTEMROOT", "WINDIR"}
        child = real_popen(command, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(computer, "READ_WORKER", script)
    monkeypatch.setattr(computer.subprocess, "Popen", start)
    return children, ready


def phase_deadline(monkeypatch: pytest.MonkeyPatch, reached: Callable[[], bool]) -> Callable[[], float | None]:
    """Advance only the supervised module's clock after the actual blocking phase starts."""
    started = time.monotonic()
    entered: float | None = None

    def monotonic() -> float:
        nonlocal entered
        now = time.monotonic()
        if entered is None and reached():
            entered = now
        if now - started >= 15:
            pytest.fail("reader fixture did not reach and close its blocking phase within 15 seconds")
        return started if entered is None else started + computer.READ_TIMEOUT + 1

    monkeypatch.setattr(computer, "time", SimpleNamespace(monotonic=monotonic))
    return lambda: entered


def test_bounded_reader_returns_actual_http_bytes_without_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SUCCESSOR_TEST_CREDENTIAL", "must-not-reach-reader")
    with streaming_server(slow=False) as (target, _):
        children, _ = substitute_reader(monkeypatch, tmp_path, target=target)
        broker = computer.ReadBroker(["https://example.org/public"])
        result = broker.fetch("https://example.org/public", "GET")
    assert base64.b64decode(result["body"]) == b"public technical fixture"
    assert broker.bytes == len(b"public technical fixture") and broker.requests == 1
    assert len(children) == 1 and children[0].poll() == 0


@pytest.mark.parametrize("blocked", ["dns", "stream"])
@pytest.mark.parametrize("startup_delay", [0, 1.3])
def test_phase_clock_read_deadline_kills_and_reaps_blocked_dns_or_slow_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, blocked: str, startup_delay: float
) -> None:
    with streaming_server(slow=True) as (target, connected):
        children, ready = substitute_reader(
            monkeypatch, tmp_path, target=target, dns_wait=blocked == "dns", startup_delay=startup_delay
        )
        entered = phase_deadline(monkeypatch, ready.exists if blocked == "dns" else connected.is_set)
        broker = computer.ReadBroker(["https://example.org/public"])
        with pytest.raises(TimeoutError, match="wall-clock"):
            broker.fetch("https://example.org/public", "GET")
        phase_started = entered()
        assert phase_started is not None
        phase_elapsed = time.monotonic() - phase_started
    assert ready.exists() and (blocked == "dns" or connected.is_set())
    assert phase_elapsed < 2.5 and len(children) == 1 and children[0].poll() is not None
    assert broker.bytes == 1_500_000 and broker.requests == 1


def test_real_read_deadline_includes_cold_child_startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    children, ready = substitute_reader(monkeypatch, tmp_path, startup_delay=30)
    monkeypatch.setattr(computer, "READ_TIMEOUT", 0.2)
    broker = computer.ReadBroker(["https://example.org/public"])
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="wall-clock"):
        broker.fetch("https://example.org/public", "GET")
    assert time.monotonic() - started < 2.5 and not ready.exists()
    assert len(children) == 1 and children[0].poll() is not None
    assert broker.bytes == 1_500_000 and broker.requests == 1


@pytest.mark.parametrize("blocked", ["dns", "stream"])
def test_stop_kills_blocked_reader_without_waiting_for_network_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, blocked: str
) -> None:
    with streaming_server(slow=True) as (target, connected):
        children, ready = substitute_reader(
            monkeypatch, tmp_path, target=target, dns_wait=blocked == "dns", startup_delay=1.3
        )
        stopped_at: list[float] = []

        def checkpoint() -> None:
            stopped = ready.exists() if blocked == "dns" else connected.is_set()
            if stopped:
                stopped_at.append(time.monotonic())
                raise Conflict("operator stopped test session")

        broker = computer.ReadBroker(["https://example.org/public"], checkpoint)
        with pytest.raises(Conflict, match="stopped"):
            broker.fetch("https://example.org/public", "GET")
        assert stopped_at and time.monotonic() - stopped_at[0] < 2
    assert len(children) == 1 and children[0].poll() is not None
    assert broker.bytes == 1_500_000


def test_task_deadline_propagates_from_checkpoint_and_reaps_reader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    children, ready = substitute_reader(monkeypatch, tmp_path, dns_wait=True)

    def checkpoint() -> None:
        if ready.exists():
            raise TimeoutError("session wall-clock budget exhausted")

    with pytest.raises(TimeoutError, match="session wall-clock"):
        computer.ReadBroker(["https://example.org/public"], checkpoint).fetch("https://example.org/public", "GET")
    assert children[0].poll() is not None


def test_preexisting_stop_starts_no_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    def checkpoint() -> None:
        raise Conflict("operator stopped test session")

    with patch.object(computer.subprocess, "Popen") as start, pytest.raises(Conflict, match="stopped"):
        computer.ReadBroker(["https://example.org/public"], checkpoint).fetch("https://example.org/public", "GET")
    start.assert_not_called()


def test_invalid_unicode_payload_starts_no_reader() -> None:
    url = "https://example.org/\ud800"
    with patch.object(computer.subprocess, "Popen") as start, pytest.raises(ValueError, match="surrogate Unicode"):
        computer.ReadBroker([url]).fetch(url, "GET")
    start.assert_not_called()


def test_private_or_mixed_dns_never_opens_http(monkeypatch: pytest.MonkeyPatch) -> None:
    for addresses in (["127.0.0.1"], ["1.1.1.1", "127.0.0.1"]):
        monkeypatch.setattr(
            computer_read.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", (ip, 443)) for ip in addresses]
        )
        with patch.object(computer_read.httpx, "Client") as client:
            assert "error" in computer_read.read_public("https://example.org/public", "GET", 1024)
        client.assert_not_called()


def test_reader_code_changes_invalidate_fresh_permit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    initial = computer.worker_source_digest()
    modified = tmp_path / "reader.py"
    modified.write_bytes(computer.READ_WORKER.read_bytes() + b"\n# changed implementation\n")
    monkeypatch.setattr(computer, "READ_WORKER", modified)
    assert computer.worker_source_digest() != initial
    modified.write_bytes(b"x" * 128_001)
    with pytest.raises(ValueError, match="source exceeds"):
        computer.worker_source_digest()


def test_reader_failure_retains_received_byte_budget(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    response = json.dumps({"bytes_read": 123, "error": "controlled failure"}).encode()
    fake = tmp_path / "failure.py"
    fake.write_text(f"import sys;sys.stdin.buffer.read();sys.stdout.buffer.write({response!r})", encoding="utf-8")
    monkeypatch.setattr(computer, "READ_WORKER", fake)
    broker = computer.ReadBroker(["https://example.org/public"])
    with pytest.raises(ValueError, match="refused"):
        broker.fetch("https://example.org/public", "GET")
    assert broker.bytes == 123


def test_compressed_response_is_refused_before_body_read_or_decompression(monkeypatch: pytest.MonkeyPatch) -> None:
    compressed = gzip.compress(b"x" * 1_048_576)
    read = []
    requests = []

    class CompressedStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            read.append(True)
            yield compressed

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"content-encoding": "gzip"}, stream=CompressedStream())

    original = httpx.Client
    monkeypatch.setattr(computer_read.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("1.1.1.1", 443))])
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    result = computer_read.read_public("https://example.org/public", "GET", 1024)
    assert "error" in result and result["bytes_read"] == 0 and read == []
    assert requests[0].headers["accept-encoding"] == "identity" and len(compressed) < 2048


@pytest.mark.parametrize("reason", ["stop", "deadline"])
def test_native_interruption_retains_reserved_action_cleanup_and_no_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reason: str
) -> None:
    children, ready = substitute_reader(monkeypatch, tmp_path, dns_wait=True, startup_delay=1.3)
    if reason == "deadline":
        entered = phase_deadline(monkeypatch, ready.exists)
    journal = Journal.initialize(tmp_path / "home")
    output = tmp_path / "result"
    mission = computer.ComputerTask(
        goal="Read the permitted public technical source",
        html="<main>Controlled browser double</main>",
        allowed_urls=["https://example.org/public"],
        input_rights="public",
        license="Public technical test fixture",
    )
    closed = []
    stopped_at: list[float] = []

    class ControlledAdvisor:
        identity = {"mode": "CONTROLLED_TEST_DOUBLE", "model": "fixed-script", "endpoint": "none"}

        def next(self, *args: Any) -> dict[str, Any]:
            return {"actions": [{"type": "click", "x": 1, "y": 1, "button": "left"}], "done": False, "summary": ""}

    class ControlledComputer:
        def __init__(self, image: str, task: computer.ComputerTask, checkpoint: Any) -> None:
            def checked() -> None:
                if reason == "stop" and ready.exists():
                    key = "@successor-computer:" + json.loads((output / "run.json").read_text())["run_id"]
                    latest = journal.latest(key)
                    if latest["state"] != "stopped":
                        stopped_at.append(time.monotonic())
                        computer._change(journal, key, latest["revision"], state="stopped")
                checkpoint()

            self.broker = computer.ReadBroker(task.allowed_urls, checked)

        def observe(self) -> dict[str, Any]:
            return {"png": base64.b64encode(b"CONTROLLED_SCREENSHOT_DOUBLE").decode(), "text": "Unverified fixture"}

        def act(self, action: Any) -> dict[str, Any]:
            self.broker.fetch("https://example.org/public", "GET")
            return self.observe()

        def close(self) -> None:
            closed.append(True)

    advisor = ControlledAdvisor()
    image = "sha256:" + "a" * 64
    permit = computer.commitment(mission, advisor, image)
    with pytest.raises(Conflict if reason == "stop" else TimeoutError):
        computer.run_session(journal, mission, advisor, image, output, permit, factory=ControlledComputer)
    assert ready.exists()
    if reason == "deadline":
        phase_started = entered()
        assert phase_started is not None and time.monotonic() - phase_started < 2.5
    else:
        assert stopped_at and time.monotonic() - stopped_at[0] < 2.5
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["state"] == ("stopped" if reason == "stop" else "interrupted")
    assert receipt["actions_reserved"] == 1 and receipt["events"][-1]["status"] == "reserved"
    assert receipt["pending"] == "action" and receipt["billing"] == "UNKNOWN"
    assert receipt["cleanup"] == "VERIFIED" and closed == [True] and children[0].poll() is not None
    assert (output / "signed-receipt.json").is_file()
    with pytest.raises(Conflict, match="reconcile"):
        computer.run_session(journal, mission, advisor, image, tmp_path / "retry", permit, factory=ControlledComputer)
    journal.verify()


def approved_reader_source() -> bytes:
    response = {
        "bytes_read": 8,
        "response": {"status": 200, "content_type": "text/plain", "body": base64.b64encode(b"approved").decode()},
    }
    return ("import sys\nsys.stdin.buffer.read()\nsys.stdout.write(" + repr(json.dumps(response)) + ")\n").encode()


@pytest.mark.parametrize("replacement", ["after-construction", "at-spawn"])
def test_retained_reader_snapshot_survives_path_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, replacement: str
) -> None:
    reader, marker = tmp_path / "reader.py", tmp_path / "UNAPPROVED_EXECUTED"
    reader.write_bytes(approved_reader_source())
    monkeypatch.setattr(computer, "READ_WORKER", reader)
    broker = computer.ReadBroker(["https://example.org/public"])
    malicious = f"from pathlib import Path\nPath({str(marker)!r}).write_text('unapproved')\n".encode()
    if replacement == "at-spawn":
        real_popen = subprocess.Popen

        def replace_and_start(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
            reader.write_bytes(malicious)
            return real_popen(*args, **kwargs)

        monkeypatch.setattr(computer.subprocess, "Popen", replace_and_start)
    else:
        reader.write_bytes(malicious)
    result = broker.fetch("https://example.org/public", "GET")
    assert base64.b64decode(result["body"]) == b"approved" and broker.bytes == 8
    assert reader.read_bytes() == malicious and not marker.exists()


def test_session_passes_exact_approved_reader_snapshot_and_resets_factory_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    reader, marker = tmp_path / "reader.py", tmp_path / "UNAPPROVED_EXECUTED"
    original = approved_reader_source()
    reader.write_bytes(original)
    monkeypatch.setattr(computer, "READ_WORKER", reader)
    journal = Journal.initialize(tmp_path / "home")
    task = computer.ComputerTask(
        goal="Read approved synthetic fixture",
        html="<main>Synthetic browser double</main>",
        allowed_urls=["https://example.org/public"],
        input_rights="synthetic",
        license="Synthetic public fixture",
    )
    closed = []

    class Advisor:
        identity = {"mode": "CONTROLLED_TEST_DOUBLE", "model": "fixed", "endpoint": "none"}

        def next(self, *args: Any) -> dict[str, Any]:
            return {"actions": [], "done": True, "summary": "Synthetic fixture; not independent acceptance"}

    class Browser:
        def __init__(self, image: str, mission: Any, checkpoint: Any) -> None:
            reader.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unapproved')\n")
            self.broker = computer.ReadBroker(mission.allowed_urls, checkpoint)

        def observe(self) -> dict[str, str]:
            result = self.broker.fetch("https://example.org/public", "GET")
            assert base64.b64decode(result["body"]) == b"approved"
            return {"png": base64.b64encode(b"CONTROLLED_SCREENSHOT_DOUBLE").decode(), "text": "Unverified fixture"}

        def close(self) -> None:
            closed.append(True)

    advisor, image = Advisor(), "sha256:" + "a" * 64
    permit = computer.commitment(task, advisor, image)
    result = computer.run_session(journal, task, advisor, image, tmp_path / "output", permit, factory=Browser)
    assert result["state"] == "review" and closed == [True] and not marker.exists()
    assert computer._APPROVED_READ_SOURCE.get() is None
    assert computer.ReadBroker([]).source == reader.read_bytes() != original
    # A factory exception also releases the scoped snapshot for the next session.
    reader.write_bytes(original)

    def fail_factory(*args: Any) -> None:
        assert computer._APPROVED_READ_SOURCE.get() == original
        raise ValueError("controlled factory failure")

    with pytest.raises(ValueError, match="controlled factory"):
        computer.run_session(
            Journal.initialize(tmp_path / "other-home"),
            task,
            advisor,
            image,
            tmp_path / "other-output",
            permit,
            factory=fail_factory,
        )
    assert computer._APPROVED_READ_SOURCE.get() is None
