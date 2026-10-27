# SPDX-License-Identifier: Apache-2.0
"""Log a bounded hosted-agent repair trial without claiming OS isolation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("path outside participant workspace")
    if any(part in {"state.json", "events.jsonl", "frozen_submission"} for part in Path(relative).parts):
        raise ValueError("runner metadata is read-only")
    return candidate


def append(root: Path, event: dict[str, Any]) -> None:
    with (root / "events.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(event, sort_keys=True) + "\n")


def state_write(root: Path, state: dict[str, Any]) -> None:
    (root / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def inventory(root: Path) -> dict[str, Any]:
    return {
        str(path.relative_to(root)): {"sha256": digest(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def act(root: Path, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    state = json.loads((root / "state.json").read_text())
    now = time.time()
    if state["started_at"] is None:
        state["started_at"] = now
    elapsed = now - state["started_at"]
    if state["closed"] and action != "status":
        raise ValueError("trial already closed; frozen submission remains immutable")
    if action == "status":
        return {**state, "elapsed_seconds": elapsed, "files": inventory(root / "tasks")}
    if action == "finish":
        dest = root / "frozen_submission"
        if dest.exists():
            raise ValueError("refusing to overwrite frozen submission")
        shutil.copytree(root / "tasks", dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        state.update(
            closed=True,
            finished_at=now,
            elapsed_seconds=elapsed,
            within_envelope=elapsed <= state["wall_seconds_limit"] and state["operations"] <= state["operations_limit"],
            submission_inventory=inventory(dest),
        )
        append(root, {"kind": "finish", "timestamp": now, "elapsed_seconds": elapsed})
        state_write(root, state)
        return {k: v for k, v in state.items() if k != "submission_inventory"}
    if elapsed > state["wall_seconds_limit"] or state["operations"] >= state["operations_limit"]:
        raise ValueError("observable budget exhausted; call finish to preserve current work")
    state["operations"] += 1
    started = time.perf_counter()
    event: dict[str, Any] = {"kind": action, "timestamp": now, "operation": state["operations"], **payload}
    result: dict[str, Any]
    if action == "read":
        path = confined(root, payload["path"])
        data = path.read_text(encoding="utf-8")
        event.update(sha256=digest(path), bytes=path.stat().st_size)
        result = {"path": payload["path"], "text": data}
    elif action == "write":
        path = confined(root, payload["path"])
        if not path.is_relative_to(root / "tasks"):
            raise ValueError("write only inside tasks")
        data = sys.stdin.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        event.update(sha256=digest(path), bytes=path.stat().st_size, content=data)
        result = {"written": payload["path"], "sha256": digest(path), "bytes": path.stat().st_size}
    elif action == "run":
        directory = confined(root, "tasks/" + payload["case"])
        argv = payload["argv"]
        if not argv or Path(argv[0]).name not in {"python", "python3", "python3.12"}:
            raise ValueError("only Python commands are allowed by this protocol")
        timeout = min(45.0, max(0.1, state["wall_seconds_limit"] - elapsed))
        try:
            proc = subprocess.run(argv, cwd=directory, capture_output=True, text=True, timeout=timeout, check=False)
            result = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        except subprocess.TimeoutExpired as exc:
            result = {"returncode": 124, "stdout": str(exc.stdout or ""), "stderr": str(exc.stderr or ""), "timeout": True}
        event.update(result)
        state["test_executions"] += 1
    else:
        raise ValueError("unknown action")
    event["tool_elapsed_seconds"] = time.perf_counter() - started
    state["tool_elapsed_seconds"] += event["tool_elapsed_seconds"]
    state["output_bytes"] += len(json.dumps(result).encode())
    append(root, event)
    state_write(root, state)
    result.update(operation=state["operations"], remaining_operations=state["operations_limit"] - state["operations"],
                  elapsed_seconds=time.time() - state["started_at"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("action", choices=["read", "write", "run", "finish", "status"])
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    payload: dict[str, Any] = {}
    if args.action in {"read", "write"}:
        payload["path"] = args.arguments[0]
    if args.action == "run":
        payload.update(case=args.arguments[0], argv=args.arguments[1:])
    try:
        with (args.workspace.resolve() / "runner.lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            print(json.dumps(act(args.workspace.resolve(), args.action, payload), indent=2))
    except (ValueError, IndexError, FileNotFoundError) as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
