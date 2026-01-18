#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail if the Git diff includes binary file changes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


BINARY_EXTENSIONS = {
    ".wasm",
    ".zip",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".pdf",
    ".ico",
    ".mp3",
    ".mp4",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def _git_root() -> Path:
    result = _run("git", "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip())


def _load_event_base_sha() -> str | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        data = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    base = data.get("pull_request", {}).get("base", {}).get("sha")
    return base or None


def _ensure_origin_main() -> str | None:
    try:
        _run("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main")
        return "origin/main"
    except subprocess.CalledProcessError:
        pass
    try:
        remotes = _run("git", "remote").stdout.splitlines()
    except subprocess.CalledProcessError:
        return None
    if "origin" in remotes:
        try:
            _run("git", "fetch", "origin", "main", "--quiet")
        except subprocess.CalledProcessError:
            return None
        try:
            _run("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main")
            return "origin/main"
        except subprocess.CalledProcessError:
            return None
    return None


def _verify_ref(ref: str) -> bool:
    try:
        _run("git", "rev-parse", "--verify", f"{ref}^{{commit}}")
        return True
    except subprocess.CalledProcessError:
        return False


def _base_ref() -> str:
    base_sha = _load_event_base_sha()
    if base_sha and _verify_ref(base_sha):
        return base_sha
    origin_main = _ensure_origin_main()
    if origin_main and _verify_ref(origin_main):
        return origin_main
    for candidate in ("main", "master"):
        if _verify_ref(candidate):
            return candidate
    return "HEAD"


def _iter_changed_paths(base_ref: str) -> list[str]:
    try:
        result = _run("git", "diff", "--name-status", f"{base_ref}...HEAD")
    except subprocess.CalledProcessError:
        result = _run("git", "diff", "--name-status", "HEAD")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            paths.extend(parts[1:])
        else:
            paths.extend(parts[1:])
    return [p for p in paths if p]


def _has_binary_diff(base_ref: str) -> list[str]:
    try:
        result = _run("git", "diff", "--numstat", f"{base_ref}...HEAD")
    except subprocess.CalledProcessError:
        result = _run("git", "diff", "--numstat", "HEAD")
    binaries = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0] == "-" and parts[1] == "-":
            binaries.append(parts[2])
    return binaries


def _matches_binary_extension(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in BINARY_EXTENSIONS


def main() -> int:
    _git_root()
    base_ref = _base_ref()
    changed_paths = _iter_changed_paths(base_ref)
    binary_paths = [path for path in changed_paths if _matches_binary_extension(path)]
    binary_paths.extend(_has_binary_diff(base_ref))
    binary_paths = sorted(set(binary_paths))
    if binary_paths:
        joined = "\n".join(f"  - {path}" for path in binary_paths)
        print("ERROR: Binary files changed in diff:")
        print(joined)
        return 1
    print("No binary changes detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
