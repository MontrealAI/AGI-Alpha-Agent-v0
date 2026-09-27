# SPDX-License-Identifier: Apache-2.0
"""Exercise expired workers and real slow-provider responses at runtime boundaries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any
import zipfile

from fastapi.testclient import TestClient
import pytest

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime import engine as runtime
from alpha_factory_v1.core.runtime import provider
from alpha_factory_v1.core.runtime import store
from alpha_factory_v1.core.runtime.models import Mission, RuntimeConfig
from alpha_factory_v1.core.runtime.store import Conflict, Journal


@pytest.mark.parametrize("old_worker_fails", [False, True])
def test_expired_worker_cannot_fail_its_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, old_worker_fails: bool
) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    mission = Mission(
        goal="Extract the supplied fact",
        work={"kind": "research", "sources": [{"id": "S", "title": "Fact", "text": "The capacity is 40 units."}]},
    )
    queued = journal.submit(mission)
    old_started, new_started, release_old, release_new = (threading.Event() for _ in range(4))
    research = runtime.work.research

    def suspended_work(request: Mission) -> dict[str, Any]:
        if not old_started.is_set():
            old_started.set()
            assert release_old.wait(10)
            if old_worker_fails:
                raise RuntimeError("retired provider failed")
        else:
            new_started.set()
            assert release_new.wait(10)
        return research(request)

    monkeypatch.setattr(runtime.work, "research", suspended_work)
    with ThreadPoolExecutor(max_workers=2) as pool:
        old = pool.submit(runtime.Engine(journal).execute, queued["id"])
        try:
            assert old_started.wait(10)
            lease = journal.latest(queued["id"])["lease_expires_ns"]
            replacement = runtime.Engine(Journal(journal.root))
            with monkeypatch.context() as clock:
                clock.setattr(runtime.time, "time_ns", lambda: lease + 1)
                replacement.recover(queued["id"])
            new = pool.submit(replacement.execute, queued["id"])
            assert new_started.wait(10)
            before = journal.latest(queued["id"])
            release_old.set()
            with pytest.raises((Conflict, RuntimeError)):
                old.result(timeout=10)
            assert journal.latest(queued["id"]) == before
            release_new.set()
            assert new.result(timeout=10)["state"] == "review"
            assert journal.verify()["valid"]
        finally:
            release_old.set()
            release_new.set()


@pytest.mark.parametrize("mode", ["trickle", "stalled", "success"])
def test_provider_enforces_total_response_deadline(mode: str) -> None:
    disconnected = threading.Event()
    stop = threading.Event()
    content = {"choices": [{"finish_reason": "stop", "message": {"content": '{"findings": []}'}}]}
    body = json.dumps(content).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body) + (30 if mode == "trickle" else 0)))
            self.end_headers()
            try:
                if mode == "trickle":
                    for _ in range(30):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        if stop.wait(0.1):
                            return
                elif mode == "stalled":
                    if stop.wait(3):
                        return
                self.wfile.write(body)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                disconnected.set()

        def log_message(self, _format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = RuntimeConfig(
        llm_url=f"http://127.0.0.1:{server.server_port}/v1", llm_model="deadline-test", llm_timeout=1
    )
    started = time.monotonic()
    try:
        if mode == "success":
            result, evidence = provider.complete_json({"model": config.llm_model}, config)
            assert result == {"findings": []} and evidence["mode"] == "local_inference"
        else:
            with pytest.raises(TimeoutError, match="deadline"):
                provider.complete_json({"model": config.llm_model}, config)
            assert time.monotonic() - started < 2.5
            if mode == "trickle":
                assert disconnected.wait(1), "timed-out provider connection must close"
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_non_ascii_authorization_is_denied_without_server_error(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    before = journal.verify()
    with TestClient(create_app(journal)) as client:
        response = client.get("/api/status", headers={b"authorization": b"Bearer \xff"})
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert journal.verify() == before


@pytest.mark.parametrize("limit_case", ["snapshot", "manifest"])
def test_backup_refuses_archive_beyond_its_own_restore_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit_case: str
) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    target = tmp_path / "backup.zip"
    reference = tmp_path / "reference.zip"
    journal.backup(reference)
    with zipfile.ZipFile(reference) as archive:
        total = sum(info.file_size for info in archive.infolist())
    monkeypatch.setattr(store, "MAX_RECOVERY_BYTES", 100 if limit_case == "snapshot" else total - 1)
    with pytest.raises(ValueError, match="recovery archive exceeds"):
        journal.backup(target)
    assert not target.exists()
    assert not list(journal.root.glob("backup-*.sqlite3"))
    assert journal.verify()["valid"]
    monkeypatch.setattr(store, "MAX_RECOVERY_BYTES", total)
    journal.backup(target)
    assert Journal.restore(target, tmp_path / "restored").verify() == journal.verify()


def test_backup_write_failure_removes_only_its_partial_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journal = Journal.initialize(tmp_path / "agent")
    target = tmp_path / "backup.zip"

    class FailedArchive(zipfile.ZipFile):
        def writestr(self, *args: Any, **kwargs: Any) -> None:
            super().writestr(*args, **kwargs)
            raise OSError("archive destination full")

    monkeypatch.setattr(store.zipfile, "ZipFile", FailedArchive)
    with pytest.raises(OSError, match="destination full"):
        journal.backup(target)
    assert not target.exists()
    target.write_bytes(b"keep existing recovery checkpoint")
    with pytest.raises(FileExistsError):
        journal.backup(target)
    assert target.read_bytes() == b"keep existing recovery checkpoint"
    assert not list(journal.root.glob("backup-*.sqlite3"))
