# SPDX-License-Identifier: Apache-2.0
"""Linux authored supervisor-death tests; no research cases or result claims."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parent
RECEIPTS = ROOT / "receipts" / "supervisor-sigkill"
pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or not Path("/proc/self/stat").is_file(),
    reason="Linux /proc process-state qualification only",
)


def _append(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, json.dumps(value, separators=(",", ":")).encode() + b"\n")
        os.fsync(fd)
    finally:
        os.close(fd)


def current_pid_namespace() -> str:
    return str(Path("/proc/self/ns/pid").readlink())


def current_proc_pid() -> int:
    status = Path("/proc/self/status").read_text()
    tgid = int(next(line.split()[1] for line in status.splitlines() if line.startswith("Tgid:")))
    if tgid != int(Path("/proc/self").readlink().name):
        raise RuntimeError("Mounted proc self identity is inconsistent")
    return tgid


def _namespace_rows():
    namespace = current_pid_namespace()
    for directory in Path("/proc").iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            if str((directory / "ns/pid").readlink()) != namespace:
                continue
            status = (directory / "status").read_text()
            fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
            nested = fields.get("NSpid", str(directory.name)).split()
            yield {
                "proc_pid": int(directory.name),
                "namespace_pid": int(nested[-1]),
                "parent_proc_pid": int(fields["PPid"].strip()),
                "namespace_inode": namespace,
            }
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


def namespace_pid_to_proc(namespace_pid: int, *, parent_proc_pid: int | None = None) -> int:
    if type(namespace_pid) is not int or namespace_pid <= 0:
        raise ValueError("A positive current-namespace PID is required")
    matching = [
        row["proc_pid"]
        for row in _namespace_rows()
        if row["namespace_pid"] == namespace_pid
        and (parent_proc_pid is None or row["parent_proc_pid"] == parent_proc_pid)
    ]
    if len(matching) != 1:
        raise ProcessLookupError("Current-namespace PID has no unique visible proc identity")
    return matching[0]


def proc_pid_to_namespace(proc_pid: int) -> int:
    if type(proc_pid) is not int or proc_pid <= 0:
        raise ValueError("A positive mounted-proc PID is required")
    matching = [row["namespace_pid"] for row in _namespace_rows() if row["proc_pid"] == proc_pid]
    if len(matching) != 1:
        raise ProcessLookupError("Proc PID is absent or outside this PID namespace")
    return matching[0]


def proc_children(parent_proc_pid: int) -> set[int]:
    return {row["proc_pid"] for row in _namespace_rows() if row["parent_proc_pid"] == parent_proc_pid}


def _state(pid: int) -> dict:
    try:
        body = Path(f"/proc/{pid}/stat").read_text()
        fields = body[body.rfind(")") + 2 :].split()
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        status = Path(f"/proc/{pid}/status").read_text()
        namespace = next((line.split()[1:] for line in status.splitlines() if line.startswith("NSpid:")), [str(pid)])
        return {
            "pid": pid,
            "namespace_pid": int(namespace[-1]),
            "state": fields[0],
            "start_ticks": fields[19],
            "command": command,
        }
    except (FileNotFoundError, ProcessLookupError):
        return {"pid": pid, "namespace_pid": None, "state": "GONE", "start_ticks": None, "command": ""}


def _running(current: dict, original: dict) -> bool:
    return current["state"] not in {"GONE", "Z", "X"} and current["start_ticks"] == original["start_ticks"]


def _read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _wait_for(predicate, timeout: float):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.01)
    raise AssertionError("Authored supervisor test observation exceeded its finite deadline")


def _kill_group(pid: int | None) -> None:
    if pid is not None:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _supervisor(directory: Path, case: str) -> None:
    from fixed_worker import FixedWorker
    import fixed_worker

    worker = FixedWorker(ROOT)
    manifest_hash = worker.verify_sources()
    actual_popen = fixed_worker.subprocess.Popen

    class RecordedInput:
        def __init__(self, stream):
            self.stream, self.pending = stream, []

        @property
        def closed(self):
            return self.stream.closed

        def write(self, value):
            written = self.stream.write(value)
            for line in value.splitlines():
                message = json.loads(line)
                if "ack" in message:
                    self.pending.append(message["ack"])
            return written

        def flush(self):
            self.stream.flush()
            for seq in self.pending:
                _append(directory / "ack.jsonl", {"seq": seq, "time": time.monotonic()})
            self.pending = []

        def close(self):
            self.stream.close()

    def recording_popen(*args, **kwargs):
        child = actual_popen(*args, **kwargs)
        command = args[0] if args else kwargs.get("args")
        if isinstance(command, list) and str(ROOT / "fixed_worker.mjs") in command:
            parent_proc_pid = current_proc_pid()
            proc_pid = namespace_pid_to_proc(child.pid, parent_proc_pid=parent_proc_pid)
            record = _state(proc_pid)
            assert proc_pid_to_namespace(proc_pid) == child.pid
            record["namespace_inode"] = current_pid_namespace()
            record["supervisor_proc_pid"] = parent_proc_pid
            assert record["state"] not in {"GONE", "Z", "X"}
            _append(directory / "node.jsonl", {**record, "time": time.monotonic()})
            child.stdin = RecordedInput(child.stdin)
        return child

    fixed_worker.subprocess.Popen = recording_popen

    def checkpoint(**increments):
        progress = worker.last_progress
        if progress is None:
            return
        entry = {
            "seq": progress["seq"],
            "phase": progress["phase"],
            "time": time.monotonic(),
            "increments": {key: value for key, value in increments.items() if key != "receipt"},
            "receipt_phase": increments.get("receipt", {}).get("phase_index"),
        }
        _append(directory / "checkpoint.jsonl", entry)
        if case == "waiting-ack" and progress["phase"] == "source-and-operating-scope-verified":
            _append(directory / "blocked.jsonl", {"seq": progress["seq"], "time": time.monotonic()})
            while True:
                time.sleep(0.05)

    task = {
        "schema": "release-plan/v1",
        "id": "authored-supervisor-crash-plan",
        "kind": "plan",
        "jobs": [
            {"id": "J1", "duration": 2, "crew": 1, "deps": []},
            {"id": "J2", "duration": 1, "crew": 1, "deps": []},
            {"id": "J3", "duration": 2, "crew": 1, "deps": ["J1"]},
        ],
        "capacity": [2] * 16,
        "release": {},
        "locked": {},
        "deadline": 10,
        "public_or_synthetic": "synthetic",
        "planning_only": True,
    }
    native = case == "native-active"
    caps = {
        "service_work": 200000,
        "improvement_work": 0,
        "native_calls": 2 if native else 0,
        "native_solve_seconds": 8 if native else 0,
        "wall_seconds": 20,
        "allow_native": native,
        "source_hash": manifest_hash,
    }
    answer = worker.execute("run-mission", {"task": task}, caps, checkpoint)
    _append(directory / "unexpected-completion.jsonl", {"verified": answer["verified"]})


def _children(proc_pid: int):
    return proc_children(proc_pid)


def _specialist_child(node_pid: int):
    for pid in _children(node_pid):
        child = _state(pid)
        if "python_bridge.py specialist" in child["command"] and child["state"] not in {"GONE", "Z", "X"}:
            return child
    return None


def _case(tmp_path: Path, case: str) -> dict:
    directory = tmp_path / case
    directory.mkdir()
    manifest_before = hashlib.sha256((ROOT / "SOURCE_FILES.json").read_bytes()).hexdigest()
    node_executable = shutil.which("node")
    assert node_executable and Path(node_executable).is_absolute()
    env = {
        "PATH": os.pathsep.join((str(Path(node_executable).parent), str(Path(sys.executable).parent))),
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    supervisor = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--supervisor", str(directory), case],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    node = child = None
    try:

        def observed_node():
            record = next(iter(_read_lines(directory / "node.jsonl")), None)
            if record is None and supervisor.poll() is not None:
                out, err = supervisor.communicate(timeout=1)
                raise AssertionError("Supervisor startup failed: " + err.decode(errors="replace")[-3000:])
            return record

        node = _wait_for(observed_node, 5)
        if case == "waiting-ack":
            blocked = _wait_for(lambda: next(iter(_read_lines(directory / "blocked.jsonl")), None), 5)
            assert not _read_lines(directory / "ack.jsonl")
            observation = {"blocked_seq": blocked["seq"], "meaning": "Supervisor callback blocked before ACK flush"}
        else:
            child = _wait_for(lambda: _specialist_child(node["pid"]), 6)
            observation = {
                "native_process_at_kill": child,
                "meaning": "Actual approved fixed Python bridge specialist process active; startup/solve subphase not inferred",
            }
        before_checkpoints = _read_lines(directory / "checkpoint.jsonl")
        before_acks = _read_lines(directory / "ack.jsonl")
        assert len({value["seq"] for value in before_acks}) == len(before_acks)
        killed_at = time.monotonic()
        supervisor.kill()
        supervisor.wait(timeout=2)
        assert supervisor.returncode == -signal.SIGKILL
        states = []
        node_ended_at = native_ended_at = None
        end = killed_at + 10
        while time.monotonic() < end:
            node_state = _state(node["pid"])
            native_state = _state(child["pid"]) if child else None
            elapsed = time.monotonic() - killed_at
            if node_ended_at is None and not _running(node_state, node):
                node_ended_at = elapsed
            if child and native_ended_at is None and not _running(native_state, child):
                native_ended_at = elapsed
            states.append(
                {
                    "seconds_after_supervisor_kill": elapsed,
                    "node_state": node_state["state"],
                    "native_state": native_state["state"] if native_state else None,
                }
            )
            if node_ended_at is not None and (not child or native_ended_at is not None):
                break
            time.sleep(0.02)
        assert node_ended_at is not None, "Node survived the documented outer bound after supervisor death"
        assert not child or native_ended_at is not None, "Native child survived the documented outer bound"
        after_checkpoints = _read_lines(directory / "checkpoint.jsonl")
        after_acks = _read_lines(directory / "ack.jsonl")
        assert before_checkpoints == after_checkpoints
        assert before_acks == after_acks
        assert not (directory / "unexpected-completion.jsonl").exists()
        assert not any(value["receipt_phase"] is not None for value in after_checkpoints)
        manifest_after = hashlib.sha256((ROOT / "SOURCE_FILES.json").read_bytes()).hexdigest()
        assert manifest_before == manifest_after
        stdout, stderr = supervisor.communicate(timeout=1)
        receipt = {
            "schema": "authored-supervisor-sigkill-engineering-check/v1",
            "case": case,
            "research_confirmation": False,
            "source_manifest_sha256": manifest_before,
            "supervisor_exit_code": supervisor.returncode,
            "node_pid": node["namespace_pid"],
            "node_proc_pid": node["pid"],
            "native_pid": child["namespace_pid"] if child else None,
            "native_proc_pid": child["pid"] if child else None,
            "observation": observation,
            "node_orphan_window_seconds": node_ended_at,
            "native_orphan_window_seconds": native_ended_at,
            "accepted_checkpoint_count_before_kill": len(before_checkpoints),
            "ack_flush_count_before_kill": len(before_acks),
            "checkpoint_sequences": [value["seq"] for value in before_checkpoints],
            "ack_sequences": [value["seq"] for value in before_acks],
            "no_further_accepted_phase_or_ack": True,
            "duplicate_ack_observed": False,
            "states": states,
            "supervisor_stdout_bytes": len(stdout),
            "supervisor_stderr_bytes": len(stderr),
            "meaning": "SIGKILL prevents supervisor cleanup. Node learns stdin EOF at its next awaited checkpoint. A currently executing native call may continue until completion or fixed outer timeout. Z denotes non-running zombie, not an executing process. No automatic restart or authority transfer is tested.",
        }
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        (RECEIPTS / f"{case}.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=2)
        if node:
            _kill_group(node["namespace_pid"])
        _kill_group(supervisor.pid)
        for stream in (supervisor.stdout, supervisor.stderr):
            if stream:
                stream.close()


def test_sigkill_supervisor_while_node_awaits_checkpoint_ack(tmp_path):
    receipt = _case(tmp_path, "waiting-ack")
    assert receipt["ack_flush_count_before_kill"] == 0
    assert receipt["node_orphan_window_seconds"] <= 10


def test_sigkill_supervisor_during_actual_native_call_is_bounded(tmp_path):
    receipt = _case(tmp_path, "native-active")
    assert receipt["native_pid"] is not None
    assert receipt["native_orphan_window_seconds"] <= 10
    assert receipt["node_orphan_window_seconds"] <= 10


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--supervisor":
        raise SystemExit("This engineering helper is invoked only by its authored pytest cases.")
    _supervisor(Path(sys.argv[2]), sys.argv[3])
