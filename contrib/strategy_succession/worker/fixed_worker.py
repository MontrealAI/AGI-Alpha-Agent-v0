# SPDX-License-Identifier: Apache-2.0
"""Bounded operator-configured transport for the fixed strategy worker."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Callable

COUNTERS = ("service_work", "improvement_work", "native_calls", "native_solve_seconds")
INTEGER_COUNTERS = COUNTERS[:3]
METHODS = frozenset(("run-mission", "construct", "run-journey"))
MAX_INPUT_BYTES = 128 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 64 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _empty_costs() -> dict[str, Any]:
    return {
        "service_work": 0,
        "improvement_work": 0,
        "native_calls": 0,
        "native_solve_seconds": 0.0,
        "unknown_costs": [],
    }


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


class WorkerError(RuntimeError):
    """A failed attempt with known debits and explicitly uncertain residual work."""

    def __init__(self, code: str, costs: dict[str, Any] | None = None, *, interrupted: bool = False):
        super().__init__(code)
        self.code = code
        self.costs = dict(costs or _empty_costs())
        self.costs["unknown_costs"] = list(self.costs.get("unknown_costs", []))
        self.interrupted = interrupted
        self.verified = False


class FixedWorker:
    """Execute fixed source; all paths and interpreters are operator configuration."""

    def __init__(
        self,
        scriptroot: str | Path | None = None,
        *,
        node: str | Path | None = None,
        python: str | Path | None = None,
        on_progress: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.root = Path(scriptroot or Path(__file__).parent).absolute()
        self.node = self._executable(node or shutil.which("node"), "NODE")
        self.python = self._executable(python or sys.executable, "PYTHON")
        self.last_progress: dict[str, Any] | None = None
        self.on_progress = on_progress
        self._execution = threading.Lock()

    @staticmethod
    def _executable(value: str | Path | None, name: str) -> str:
        if value is None or not Path(value).is_absolute():
            raise WorkerError(f"OPERATOR_{name}_ABSOLUTE_PATH_REQUIRED")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise WorkerError(f"OPERATOR_{name}_NOT_EXECUTABLE")
        return str(path)

    def _regular(self, relative: str) -> Path:
        if not isinstance(relative, str) or "\\" in relative:
            raise WorkerError("SOURCE_PATH_SCOPE")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or any(part in ("", ".", "..") for part in pure.parts):
            raise WorkerError("SOURCE_PATH_SCOPE")
        if pure.as_posix() != relative:
            raise WorkerError("SOURCE_PATH_SCOPE")
        if self.root.is_symlink() or not self.root.is_dir():
            raise WorkerError("SOURCE_ROOT_SCOPE")
        current = self.root
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise WorkerError("SOURCE_SYMLINK_REFUSED")
        if not current.is_file() or not current.resolve().is_relative_to(self.root.resolve()):
            raise WorkerError("SOURCE_REGULAR_FILE_REQUIRED")
        return current

    def verify_sources(self) -> str:
        """Check every listed immutable body and return the manifest's raw digest."""
        manifest_path = self._regular("SOURCE_FILES.json")
        if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
            raise WorkerError("SOURCE_MANIFEST_TOO_LARGE")
        raw = manifest_path.read_bytes()
        try:
            manifest = json.loads(raw)
        except (UnicodeError, ValueError) as error:
            raise WorkerError("SOURCE_MANIFEST_JSON") from error
        files = manifest.get("files") if isinstance(manifest, dict) else None
        if not isinstance(files, list) or not 1 <= len(files) <= 128:
            raise WorkerError("SOURCE_MANIFEST_SCOPE")
        seen: set[str] = set()
        total = 0
        for entry in files:
            if not isinstance(entry, dict):
                raise WorkerError("SOURCE_MANIFEST_ENTRY")
            name, expected = entry.get("path"), entry.get("sha256")
            if (
                not isinstance(name, str)
                or name in seen
                or not isinstance(expected, str)
                or not SHA256.fullmatch(expected)
            ):
                raise WorkerError("SOURCE_MANIFEST_ENTRY")
            seen.add(name)
            path = self._regular(name)
            size = path.stat().st_size
            total += size
            if size > MAX_SOURCE_BYTES or total > MAX_TOTAL_SOURCE_BYTES:
                raise WorkerError("SOURCE_SIZE_SCOPE")
            body = path.read_bytes()
            if len(body) != size or hashlib.sha256(body).hexdigest() != expected:
                raise WorkerError("SOURCE_IDENTITY_CHANGED")
        if "fixed_worker.mjs" not in seen:
            raise WorkerError("WORKER_NOT_SOURCE_BOUND")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _limits(limits: dict[str, Any]) -> None:
        if not isinstance(limits, dict):
            raise WorkerError("LIMITS_SCOPE")
        for key in INTEGER_COUNTERS:
            if type(limits.get(key)) is not int or not 0 <= limits[key] <= 100_000_000:
                raise WorkerError("LIMITS_SCOPE")
        if not _number(limits.get("native_solve_seconds")) or limits["native_solve_seconds"] > 300:
            raise WorkerError("LIMITS_SCOPE")
        if not _number(limits.get("wall_seconds")) or not 0 < limits["wall_seconds"] <= 300:
            raise WorkerError("LIMITS_SCOPE")
        if type(limits.get("allow_native")) is not bool:
            raise WorkerError("LIMITS_SCOPE")
        if not isinstance(limits.get("source_hash"), str) or not SHA256.fullmatch(limits["source_hash"]):
            raise WorkerError("SOURCE_HASH_SCOPE")
        if not limits["allow_native"] and limits["native_calls"]:
            raise WorkerError("NATIVE_ALLOWANCE_WITHOUT_APPROVAL")

    @staticmethod
    def _increments(value: Any, known: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) - set(COUNTERS):
            raise WorkerError("CHECKPOINT_COST_SCOPE", known)
        for key, amount in value.items():
            if (key in INTEGER_COUNTERS and type(amount) is not int) or not _number(amount):
                raise WorkerError("CHECKPOINT_COST_SCOPE", known)
            if known[key] + amount > limits[key] + (1e-8 if key == "native_solve_seconds" else 0):
                raise WorkerError("CHECKPOINT_COST_EXCEEDS_CAP", known)
        return value

    @staticmethod
    def _receipt(message: dict[str, Any], known: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any] | None:
        if "receipt" not in message:
            return None
        if message.get("source_hash") != limits["source_hash"]:
            raise WorkerError("RECEIPT_SOURCE_HASH_MISMATCH", known)
        receipt = message["receipt"]
        fields = {"phase_index", "receipt_hash", "task", "result", "checker", "selectedmethod"}
        if not isinstance(receipt, dict) or set(receipt) != fields:
            raise WorkerError("RECEIPT_SCHEMA", known)
        if type(receipt["phase_index"]) is not int or not 0 <= receipt["phase_index"] <= 2:
            raise WorkerError("RECEIPT_PHASE_SCOPE", known)
        identity = receipt["receipt_hash"]
        if not isinstance(identity, str) or not SHA256.fullmatch(identity):
            raise WorkerError("RECEIPT_IDENTITY_SCOPE", known)
        if any(not isinstance(receipt[key], dict) for key in ("task", "result", "checker")):
            raise WorkerError("RECEIPT_DATA_SCOPE", known)
        if receipt["checker"].get("valid") is not True:
            raise WorkerError("RECEIPT_NOT_INDEPENDENTLY_VERIFIED", known)
        method = receipt["selectedmethod"]
        if not isinstance(method, str) or not 1 <= len(method) <= 128:
            raise WorkerError("RECEIPT_METHOD_SCOPE", known)
        try:
            body = json.dumps(receipt, allow_nan=False, separators=(",", ":")).encode()
        except (ValueError, TypeError, RecursionError) as error:
            raise WorkerError("RECEIPT_JSON_SCOPE", known) from error
        if len(body) > MAX_RECEIPT_BYTES:
            raise WorkerError("RECEIPT_TOO_LARGE", known)
        return receipt

    @staticmethod
    def _final(message: dict[str, Any], known: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
        if message.get("source_hash") != limits["source_hash"]:
            raise WorkerError("RESULT_SOURCE_HASH_MISMATCH", known)
        costs = message.get("costs")
        if not isinstance(costs, dict) or set(costs) != {*COUNTERS, "unknown_costs"}:
            raise WorkerError("RESULT_COST_SCOPE", known)
        if not isinstance(costs["unknown_costs"], list) or any(
            not isinstance(v, str) or len(v) > 512 for v in costs["unknown_costs"]
        ):
            raise WorkerError("RESULT_UNKNOWN_COST_SCOPE", known)
        for key in COUNTERS:
            amount = costs[key]
            if (key in INTEGER_COUNTERS and type(amount) is not int) or not _number(amount):
                raise WorkerError("RESULT_COST_SCOPE", known)
            tolerance = 1e-8 if key == "native_solve_seconds" else 0
            if abs(amount - known[key]) > tolerance or amount > limits[key] + tolerance:
                raise WorkerError("RESULT_CHECKPOINT_COST_MISMATCH", known)
        if type(message.get("verified")) is not bool:
            raise WorkerError("RESULT_VERIFICATION_TYPE", costs)
        if "result" not in message:
            raise WorkerError("RESULT_MISSING", known)
        return {key: message[key] for key in ("result", "costs", "source_hash", "verified")}

    @staticmethod
    def _kill(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    def execute(
        self, method: str, payload: dict[str, Any], limits: dict[str, Any], checkpoint: Callable[..., None]
    ) -> dict[str, Any]:
        """Validate, stream bounded work, checkpoint debits and reap all descendants."""
        if method not in METHODS or not isinstance(payload, dict) or not callable(checkpoint):
            raise WorkerError("REQUEST_SCOPE")
        self._limits(limits)
        if os.name != "posix":
            raise WorkerError("PLATFORM_PROCESS_ISOLATION_UNQUALIFIED")
        self.verify_sources()
        try:
            request = (
                json.dumps(
                    {"method": method, "payload": payload, "limits": limits}, allow_nan=False, separators=(",", ":")
                ).encode()
                + b"\n"
            )
        except (ValueError, TypeError, RecursionError) as error:
            raise WorkerError("REQUEST_JSON_SCOPE") from error
        if len(request) > MAX_INPUT_BYTES:
            raise WorkerError("REQUEST_TOO_LARGE")
        if not self._execution.acquire(blocking=False):
            raise WorkerError("WORKER_BUSY")
        known = _empty_costs()
        process = None
        selector = selectors.DefaultSelector()
        self.last_progress = None
        try:
            checkpoint()
            self.verify_sources()
            environment = {
                "PATH": os.pathsep.join(dict.fromkeys((str(Path(self.node).parent), str(Path(self.python).parent)))),
                "LANG": "C.UTF-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "FIXED_PYTHON": self.python,
            }
            process = subprocess.Popen(
                [self.node, str(self._regular("fixed_worker.mjs"))],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.root,
                env=environment,
                start_new_session=True,
            )
            assert process.stdin is not None and process.stdout is not None and process.stderr is not None
            process.stdin.write(request)
            process.stdin.flush()
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            end = time.monotonic() + limits["wall_seconds"]
            output_bytes = 0
            buffer = b""
            stderr = b""
            sequence = -1
            final = None
            while selector.get_map():
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise WorkerError("WORKER_WALL_TIMEOUT", known, interrupted=True)
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output_bytes += len(chunk)
                    if output_bytes > MAX_OUTPUT_BYTES:
                        raise WorkerError("WORKER_OUTPUT_LIMIT", known)
                    if key.data == "stderr":
                        stderr += chunk
                        continue
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        try:
                            message = json.loads(line)
                        except (ValueError, UnicodeError) as error:
                            raise WorkerError("WORKER_PROTOCOL_JSON", known) from error
                        if not isinstance(message, dict) or final is not None:
                            raise WorkerError("WORKER_PROTOCOL_ORDER", known)
                        kind = message.get("type")
                        if kind == "checkpoint":
                            seq = message.get("seq")
                            if type(seq) is not int or seq != sequence + 1:
                                raise WorkerError("CHECKPOINT_SEQUENCE", known)
                            increments = self._increments(message.get("increments"), known, limits)
                            phase = message.get("phase", "")
                            if not isinstance(phase, str) or len(phase) > 128:
                                raise WorkerError("CHECKPOINT_PHASE_SCOPE", known)
                            receipt = self._receipt(message, known, limits)
                            self.last_progress = {"seq": seq, "phase": phase, "increments": dict(increments)}
                            if receipt is not None:
                                self.last_progress["receipt"] = receipt
                            try:
                                if receipt is None:
                                    checkpoint(**increments)
                                else:
                                    checkpoint(receipt=receipt, **increments)
                            except Exception as error:
                                raise WorkerError("CHECKPOINT_REFUSED", known, interrupted=True) from error
                            for counter, amount in increments.items():
                                known[counter] += amount
                            sequence = seq
                            if self.on_progress is not None:
                                self.on_progress(dict(self.last_progress))
                            process.stdin.write(json.dumps({"ack": seq}).encode() + b"\n")
                            process.stdin.flush()
                        elif kind == "result":
                            final = self._final(message, known, limits)
                            process.stdin.close()
                        elif kind == "error":
                            worker_error = message.get("error", "WORKER_REFUSED")
                            if not isinstance(worker_error, str) or len(worker_error) > 512:
                                worker_error = "WORKER_ERROR_SCOPE"
                            raise WorkerError(worker_error, known)
                        else:
                            raise WorkerError("WORKER_PROTOCOL_KIND", known)
            if buffer:
                raise WorkerError("WORKER_PROTOCOL_PARTIAL_LINE", known)
            try:
                code = process.wait(timeout=max(0.01, end - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                raise WorkerError("WORKER_WALL_TIMEOUT", known, interrupted=True) from error
            if code != 0 or final is None:
                raise WorkerError("WORKER_EXIT_WITHOUT_VERIFIED_RESULT", known)
            return final
        except BaseException as error:
            if process is not None:
                self._kill(process)
            if isinstance(error, WorkerError):
                if (
                    process is not None
                    and "Unacknowledged work after the last accepted checkpoint is unknown."
                    not in error.costs["unknown_costs"]
                ):
                    error.costs["unknown_costs"].append(
                        "Unacknowledged work after the last accepted checkpoint is unknown."
                    )
                raise
            failure = WorkerError("WORKER_TRANSPORT_FAILURE", known)
            if process is not None:
                failure.costs["unknown_costs"].append(
                    "Unacknowledged work after the last accepted checkpoint is unknown."
                )
            raise failure from error
        finally:
            selector.close()
            if process is not None:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()
            self._execution.release()
