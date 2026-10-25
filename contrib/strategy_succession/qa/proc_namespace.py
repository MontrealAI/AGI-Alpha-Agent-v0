# SPDX-License-Identifier: Apache-2.0
"""Reviewed test-only PID namespace mapping; never signal raw mounted-proc IDs.

Copied utility from worker/test_supervisor_crash.py source SHA256 118d6e8ef22616935632109170ace0ad6a55847834d33e1522e647416ce82fd6.
"""
from pathlib import Path


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
