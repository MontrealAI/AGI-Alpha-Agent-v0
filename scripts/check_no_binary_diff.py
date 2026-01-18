#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail if the git diff includes binary file changes."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BINARY_EXTENSIONS = re.compile(
    r"\.(wasm|zip|gz|png|jpg|jpeg|webp|gif|pdf|ico|mp4|mp3|woff2?|ttf|otf|bin|exe|dll|so|dylib)$",
    re.IGNORECASE,
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, capture_output=True)


def _event_base_sha(event_path: Path) -> str | None:
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pull_request = payload.get("pull_request")
    if isinstance(pull_request, dict):
        base = pull_request.get("base", {})
        if isinstance(base, dict):
            sha = base.get("sha")
            if isinstance(sha, str) and sha:
                return sha
    return None


def _resolve_base_ref() -> str:
    override = os.getenv("BINARY_DIFF_BASE_SHA")
    if override:
        return override

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if event_path:
        sha = _event_base_sha(Path(event_path))
        if sha:
            return sha

    base_ref = os.getenv("GITHUB_BASE_REF")
    if base_ref:
        return f"origin/{base_ref}"

    return "origin/main"


def _ensure_base_available(base_ref: str) -> str | None:
    result = _run(["git", "rev-parse", "--verify", f"{base_ref}^{{commit}}"])
    if result.returncode == 0:
        return base_ref
    if base_ref.startswith("origin/"):
        branch = base_ref.split("/", 1)[1]
        fetch = _run(["git", "fetch", "origin", branch])
        if fetch.returncode == 0:
            return base_ref
    fallback = _run(["git", "rev-parse", "--verify", "main^{commit}"])
    if fallback.returncode == 0:
        return "main"
    return None


def _collect_binary_paths(diff_name_status: str) -> list[str]:
    matches: list[str] = []
    for line in diff_name_status.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if not parts:
            continue
        for path in parts[1:]:
            if BINARY_EXTENSIONS.search(path):
                matches.append(path)
    return matches


def _collect_numstat_binaries(diff_numstat: str) -> list[str]:
    matches: list[str] = []
    for line in diff_numstat.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0] == "-" and parts[1] == "-":
            path = parts[2]
            matches.append(path)
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Only inspect staged changes.",
    )
    parser.add_argument(
        "--range",
        help="Explicit git diff range (e.g. base...HEAD).",
    )
    args = parser.parse_args()

    if args.range:
        name_status = _run(["git", "diff", "--name-status", args.range])
        numstat = _run(["git", "diff", "--numstat", args.range])
    elif args.staged:
        name_status = _run(["git", "diff", "--name-status", "--cached"])
        numstat = _run(["git", "diff", "--numstat", "--cached"])
    else:
        base_ref = _resolve_base_ref()
        base_ref = _ensure_base_available(base_ref)
        if base_ref:
            name_status = _run(["git", "diff", "--name-status", f"{base_ref}...HEAD"])
            numstat = _run(["git", "diff", "--numstat", f"{base_ref}...HEAD"])
        else:
            name_status = _run(["git", "diff", "--name-status"])
            cached = _run(["git", "diff", "--name-status", "--cached"])
            name_status = subprocess.CompletedProcess(
                name_status.args,
                name_status.returncode or cached.returncode,
                stdout=name_status.stdout + cached.stdout,
                stderr=name_status.stderr + cached.stderr,
            )
            numstat = _run(["git", "diff", "--numstat"])
            cached_numstat = _run(["git", "diff", "--numstat", "--cached"])
            numstat = subprocess.CompletedProcess(
                numstat.args,
                numstat.returncode or cached_numstat.returncode,
                stdout=numstat.stdout + cached_numstat.stdout,
                stderr=numstat.stderr + cached_numstat.stderr,
            )
    if name_status.returncode != 0:
        print(name_status.stderr, file=sys.stderr)
        return name_status.returncode
    if numstat.returncode != 0:
        print(numstat.stderr, file=sys.stderr)
        return numstat.returncode

    binary_paths = set(_collect_binary_paths(name_status.stdout))
    binary_paths.update(_collect_numstat_binaries(numstat.stdout))

    if binary_paths:
        print("ERROR: binary files changed in diff:", file=sys.stderr)
        for path in sorted(binary_paths):
            print(f"  - {path}", file=sys.stderr)
        return 1

    print("No binary diffs detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
