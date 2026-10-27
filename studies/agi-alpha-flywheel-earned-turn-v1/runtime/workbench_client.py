# SPDX-License-Identifier: Apache-2.0
"""Persistent local transport to the unchanged Alpha workbench extension seam."""

from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable


class WorkbenchError(RuntimeError):
    """A source-bound local dispatch failed without granting authority."""

    def __init__(self, receipt: dict[str, Any]):
        super().__init__(receipt.get("error", "WORKBENCH_FAILED"))
        self.receipt = receipt


class WorkbenchClient:
    """Drive a fixed Python callback only after the workbench requests execution."""

    def __init__(self, *, timeout: float = 65.0):
        started = time.perf_counter()
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("Node.js 22 or later is required")
        environment = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "WINDIR", "TMPDIR"}}
        self.process = subprocess.Popen(
            [node, str(Path(__file__).with_name("workbench_bridge.mjs"))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment, text=False, bufsize=0,
        )
        self.timeout = timeout
        self.events: list[dict[str, Any]] = []
        self._buffer = b""
        self.ready = self._receive()
        if self.ready.get("kind") != "ready":
            self.close()
            raise WorkbenchError(self.ready)
        self.startup_wall_ms = 1000 * (time.perf_counter() - started)

    def _send(self, message: dict[str, Any]) -> None:
        data = (json.dumps(message, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
        if len(data) > 500_000:
            raise ValueError("TRANSPORT_LIMIT")
        assert self.process.stdin is not None
        self.process.stdin.write(data)

    def _receive(self) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        assert self.process.stdout is not None
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                self.process.kill()
                raise TimeoutError("WORKBENCH_TRANSPORT_DEADLINE")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("WORKBENCH_TRANSPORT_CLOSED")
            self._buffer += chunk
            if len(self._buffer) > 2_000_000:
                self.process.kill()
                raise RuntimeError("WORKBENCH_OUTPUT_LIMIT")
        line, self._buffer = self._buffer.split(b"\n", 1)
        return json.loads(line)

    def run(
        self, mission_id: str, purpose: str, inputs: dict[str, Any],
        callback: Callable[[dict[str, Any]], dict[str, Any]], source_hash: str,
        *, cancelled: Callable[[], bool] = lambda: False,
    ) -> dict[str, Any]:
        """Dispatch once, retain callback failures and return the inspected workbench pack."""
        started = time.perf_counter()
        payload = json.dumps(inputs, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
        callback_calls = 0
        callback_wall_ms = 0.0
        callback_cpu_ms = 0.0
        callback_failure = None
        self._send({"kind": "run", "id": mission_id, "purpose": purpose, "payload_json": payload,
                    "source_hash": source_hash})
        while True:
            message = self._receive()
            self.events.append(message if message.get("kind") != "complete" else {
                "kind": "complete", "id": mission_id, "wall_ms": message["wall_ms"],
                "node_cpu_us": message["node_cpu_us"], "integrity_digest": message["pack"]["integrityDigest"],
            })
            kind = message.get("kind")
            if kind == "phase":
                continue
            if kind == "execute":
                if message.get("id") != mission_id or message.get("payload_json") != payload or callback_calls:
                    raise RuntimeError("CALLBACK_INPUT_BINDING")
                if cancelled():
                    self._send({"kind": "cancel", "id": mission_id})
                    continue
                callback_calls += 1
                callback_started = time.perf_counter()
                cpu_started = time.process_time()
                try:
                    report = callback(json.loads(message["payload_json"]))
                    report_json = json.dumps(report, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
                except Exception as error:
                    callback_failure = {"class": type(error).__name__, "error": str(error)[:2000]}
                    report_json = json.dumps({"valid": False, "qualified": False,
                        "summary": "Fixed local callback failed; prior capabilities retain their previous scope.",
                        "failure": callback_failure}, separators=(",", ":"))
                callback_wall_ms = 1000 * (time.perf_counter() - callback_started)
                callback_cpu_ms = 1000 * (time.process_time() - cpu_started)
                if cancelled():
                    self._send({"kind": "cancel", "id": mission_id})
                else:
                    self._send({"kind": "result", "id": mission_id, "report_json": report_json})
                continue
            stats = {"transport_wall_ms": 1000 * (time.perf_counter() - started),
                "callback_calls": callback_calls, "callback_wall_ms": callback_wall_ms,
                "callback_cpu_ms": callback_cpu_ms, "callback_failure": callback_failure}
            if kind in {"failed", "protocol_error"}:
                raise WorkbenchError({**message, **stats})
            if kind != "complete" or message.get("id") != mission_id:
                raise WorkbenchError({"error": "UNEXPECTED_TRANSPORT_RESPONSE", **stats})
            return {**message, **stats}

    def inspect(self, pack: dict[str, Any]) -> dict[str, Any]:
        """Validate history without replaying the computation or transferring authority."""
        self._send({"kind": "inspect", "id": "read-only", "pack_json": json.dumps(pack, ensure_ascii=False, allow_nan=False)})
        message = self._receive()
        if message.get("kind") != "inspected":
            raise WorkbenchError(message)
        return message["inspection"]

    def close(self) -> None:
        """Close only this foreground transport; no daemon is created."""
        if self.process.poll() is None:
            try:
                self._send({"kind": "close"})
                self.process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait(timeout=2)
        for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
            if pipe is not None:
                pipe.close()

    def __enter__(self) -> WorkbenchClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
