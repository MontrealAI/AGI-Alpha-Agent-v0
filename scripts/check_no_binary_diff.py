#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Fail when the git diff includes binary files."""

from __future__ import annotations

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


def _run(*args: str) -> str:
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.strip()


def _event_base_sha() -> str | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        payload = json.loads(Path(event_path).read_text())
    except json.JSONDecodeError:
        return None
    pull_request = payload.get("pull_request") or {}
    base_sha = pull_request.get("base", {}).get("sha")
    if base_sha:
        return str(base_sha)
    return payload.get("before")


def _resolve_base_sha() -> str:
    for key in ("BASE_SHA", "GITHUB_BASE_SHA"):
        base = os.environ.get(key)
        if base:
            return base
    event_base = _event_base_sha()
    if event_base:
        try:
            _run("git", "cat-file", "-e", f"{event_base}^{{commit}}")
        except subprocess.CalledProcessError:
            try:
                _run("git", "fetch", "origin", event_base)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"Failed to fetch base SHA {event_base}.") from exc
        return event_base
    origin_available = True
    try:
        _run("git", "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        origin_available = False

    if origin_available:
        try:
            _run("git", "rev-parse", "--verify", "origin/main")
        except subprocess.CalledProcessError:
            try:
                _run("git", "fetch", "origin", "main")
            except subprocess.CalledProcessError as exc:
                raise RuntimeError("Failed to fetch origin/main for binary diff check.") from exc
        try:
            return _run("git", "merge-base", "HEAD", "origin/main")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Failed to determine merge base against origin/main.") from exc

    for fallback_ref in ("main", "master"):
        try:
            _run("git", "rev-parse", "--verify", fallback_ref)
            return _run("git", "merge-base", "HEAD", fallback_ref)
        except subprocess.CalledProcessError:
            continue
    return _run("git", "rev-parse", "HEAD")


def _binary_paths_from_name_status(diff: str) -> list[str]:
    matches: list[str] = []
    for line in diff.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        paths = parts[1:]
        for path in paths:
            if BINARY_EXTENSIONS.search(path):
                matches.append(path)
    return matches


def _binary_paths_from_numstat(diff: str) -> list[str]:
    matches: list[str] = []
    for line in diff.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0] == "-" and parts[1] == "-":
            matches.append(parts[2])
    return matches


def main() -> int:
    base_sha = _resolve_base_sha()
    name_status = _run("git", "diff", "--name-status", f"{base_sha}...HEAD")
    numstat = _run("git", "diff", "--numstat", f"{base_sha}...HEAD")
    offenders = set(_binary_paths_from_name_status(name_status))
    offenders.update(_binary_paths_from_numstat(numstat))
    if offenders:
        print("Binary files changed in diff range:", file=sys.stderr)
        for path in sorted(offenders):
            print(f" - {path}", file=sys.stderr)
        return 1
    print("No binary file changes detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
