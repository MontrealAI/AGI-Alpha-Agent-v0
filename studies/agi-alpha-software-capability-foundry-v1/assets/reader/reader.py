# SPDX-License-Identifier: Apache-2.0
"""Bounded exact Git snapshots. No persistent content or metadata cache."""
from __future__ import annotations
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess

VERSION = "1.0.0"
MAX_PATHS = 256

def _call(repo: Path, args: list[str], data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(repo), *args],
                            input=data, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError("Exact Git snapshot unavailable")
    return result.stdout

def _paths(paths: list[str]) -> None:
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_PATHS:
        raise ValueError("Inventory must contain 1 to 256 paths")
    if any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths):
        raise ValueError("Unique string paths required")
    for p in paths:
        q = PurePosixPath(p)
        if not p or q.as_posix() != p or q.is_absolute() or any(x in {"", ".", ".."} for x in p.split("/")):
            raise ValueError("Noncanonical source path")
        if any(x in p for x in "\\\x00\n\r"):
            raise ValueError("Unsupported path character")

def _inventory(repo: Path, commit: str, paths: list[str], max_file: int, total: int) -> dict[str, tuple[str, int]]:
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Exact SHA-1 commit required")
    if type(max_file) is not int or type(total) is not int or min(max_file, total) < 0:
        raise ValueError("Invalid resource bound")
    _paths(paths)
    raw = _call(repo, ["ls-tree", "-lz", "--full-tree", commit, "--", *paths])
    rows = {}
    for row in raw.split(b"\0"):
        if not row:
            continue
        try:
            metadata, name = row.split(b"\t", 1)
            mode, kind, oid, size = metadata.split()
            path, identity, length = name.decode("utf8"), oid.decode("ascii"), int(size)
        except (ValueError, UnicodeError) as error:
            raise ValueError("Invalid source inventory") from error
        if mode not in {b"100644", b"100755"} or kind != b"blob" or not re.fullmatch(r"[0-9a-f]{40}", identity):
            raise ValueError("Only committed regular blob files are eligible")
        if path not in paths or path in rows or not 0 <= length <= max_file:
            raise ValueError("Unexpected or oversized source")
        rows[path] = (identity, length)
    if set(rows) != set(paths) or sum(n for _, n in rows.values()) > total:
        raise ValueError("Incomplete or oversized inventory")
    return rows

def read(repo: Path, commit: str, paths: list[str], max_file: int = 8_000_000,
         total: int = 32_000_000) -> dict[str, bytes]:
    """Retrieve and hash-check one immutable source inventory, in two processes."""
    rows = _inventory(repo, commit, paths, max_file, total)
    objects = dict.fromkeys(oid for oid, _ in rows.values())
    sizes = {oid: size for oid, size in rows.values()}
    requests = ["info " + commit, *("contents " + oid for oid in objects)]
    raw = _call(repo, ["cat-file", "--batch-command"], ("\n".join(requests) + "\n").encode("ascii"))
    first, separator, stream = raw.partition(b"\n")
    if not separator or not re.fullmatch(commit.encode() + rb" commit [0-9]+", first):
        raise ValueError("Source must be a commit")
    offset, bodies = 0, {}
    for oid in objects:
        size = sizes[oid]
        header = f"{oid} blob {size}\n".encode("ascii")
        if stream[offset:offset + len(header)] != header:
            raise ValueError("Object metadata changed")
        start = offset + len(header)
        body = stream[start:start + size]
        offset = start + size + 1
        if len(body) != size or stream[offset - 1:offset] != b"\n":
            raise ValueError("Truncated Git object")
        check = hashlib.sha1()
        check.update(f"blob {size}\0".encode("ascii"))
        check.update(body)
        if check.hexdigest() != oid:
            raise ValueError("Git object content is corrupt")
        bodies[oid] = body
    if offset != len(stream):
        raise ValueError("Unexpected object stream suffix")
    return {path: bodies[rows[path][0]] for path in sorted(rows)}

def sequential(repo: Path, commit: str, paths: list[str], max_file: int = 8_000_000,
               total: int = 32_000_000) -> dict[str, bytes]:
    """Same accepted domain and hashes; one process per unique source body."""
    rows = _inventory(repo, commit, paths, max_file, total)
    if _call(repo, ["cat-file", "-t", commit]).strip() != b"commit":
        raise ValueError("Source must be a commit")
    bodies = {}
    for oid, size in rows.values():
        if oid in bodies:
            continue
        body = _call(repo, ["cat-file", "blob", oid])
        if len(body) != size or hashlib.sha1(f"blob {size}\0".encode() + body).hexdigest() != oid:
            raise ValueError("Git object content is corrupt")
        bodies[oid] = body
    return {path: bodies[oid] for path, (oid, _) in sorted(rows.items())}
