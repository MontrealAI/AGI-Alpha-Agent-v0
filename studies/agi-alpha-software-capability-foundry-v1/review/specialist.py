# SPDX-License-Identifier: Apache-2.0
"""Independent direct Git specialist, written without the candidate implementation."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile


def _git(repo: Path, arguments: list[str], data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(repo), *arguments],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise ValueError("Git could not supply the exact requested snapshot")
    return result.stdout


def read(
    repo: Path,
    commit: str,
    paths: list[str],
    max_file: int = 8_000_000,
    total: int = 32_000_000,
) -> dict[str, bytes]:
    if not isinstance(commit, str) or re.fullmatch("[0-9a-f]{40}", commit) is None:
        raise ValueError("An exact SHA-1 commit is required")
    if type(max_file) is not int or type(total) is not int or min(max_file, total) < 0:
        raise ValueError("Byte limits must be nonnegative integers")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 256:
        raise ValueError("The requested inventory must contain 1 to 256 files")
    if any(not isinstance(path, str) for path in paths) or len(paths) != len(set(paths)):
        raise ValueError("The requested inventory must contain unique string paths")
    for path in paths:
        if (
            not path
            or PurePosixPath(path).as_posix() != path
            or PurePosixPath(path).is_absolute()
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or any(character in path for character in "\\\x00\n\r")
        ):
            raise ValueError("Unsupported source path")
    listing = _git(repo, ["ls-tree", "-l", "-z", "--full-tree", commit, "--", *paths])
    inventory: dict[str, tuple[str, int]] = {}
    for item in listing.split(b"\0"):
        if not item:
            continue
        try:
            metadata, name = item.split(b"\t", 1)
            mode, kind, oid, length = metadata.split()
            path = name.decode("utf-8")
        except (ValueError, UnicodeError) as error:
            raise ValueError("Unparseable Git tree entry") from error
        if path not in paths or path in inventory:
            raise ValueError("Unexpected Git tree inventory")
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise ValueError("Only committed regular files are supported")
        if re.fullmatch(b"[0-9a-f]{40}", oid) is None or not length.isdigit():
            raise ValueError("Invalid Git blob metadata")
        size = int(length)
        if size > max_file:
            raise ValueError("A source file exceeds its byte limit")
        inventory[path] = (oid.decode("ascii"), size)
    if set(inventory) != set(paths):
        raise ValueError("A required source file is missing")
    if sum(size for _, size in inventory.values()) > total:
        raise ValueError("The source inventory exceeds its total byte limit")
    objects = {oid: size for oid, size in inventory.values()}
    ordered = sorted(objects)
    request = (f"info {commit}\n" + "".join("contents " + oid + "\n" for oid in ordered)).encode("ascii")
    stream = _git(repo, ["cat-file", "--batch-command"], request)
    commit_header, separator, raw = stream.partition(b"\n")
    if not separator or re.fullmatch(commit.encode("ascii") + rb" commit [0-9]+", commit_header) is None:
        raise ValueError("The source identity must refer to a commit")
    expected_length = sum(size + len(oid) + len(str(size)) + 8 for oid, size in objects.items())
    if len(raw) != expected_length:
        raise ValueError("The Git object stream has an unexpected length")
    offset = 0
    blobs: dict[str, bytes] = {}
    for oid in ordered:
        size = objects[oid]
        newline = raw.find(b"\n", offset)
        if newline < 0 or raw[offset:newline] != f"{oid} blob {size}".encode("ascii"):
            raise ValueError("The Git object stream header differs from its tree")
        start = newline + 1
        body = raw[start : start + size]
        offset = start + size + 1
        if len(body) != size or raw[offset - 1 : offset] != b"\n":
            raise ValueError("The Git object stream is truncated")
        actual = hashlib.sha1(f"blob {size}\0".encode("ascii") + body).hexdigest()
        if actual != oid:
            raise ValueError("The returned bytes do not match their committed Git blob")
        blobs[oid] = body
    if offset != len(raw):
        raise ValueError("Unexpected trailing Git object stream data")
    return {path: blobs[inventory[path][0]] for path in sorted(inventory)}


def direct_diagnose(
    repo: Path,
    commit: str,
    paths: list[str],
    archive: Path,
    max_file: int = 8_000_000,
    total: int = 32_000_000,
) -> dict[str, list[str]]:
    if type(max_file) is not int or type(total) is not int or min(max_file, total) < 0:
        raise ValueError("Byte limits must be nonnegative integers")
    archive = Path(archive)
    information = archive.lstat()
    if not stat.S_ISREG(information.st_mode) or information.st_size > total + 1_048_576:
        raise ValueError("The package must be a bounded regular archive")
    descriptor = os.open(archive, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (information.st_dev, information.st_ino):
            raise ValueError("The package changed during inspection")
        raw = stream.read(total + 1_048_577)
        after = os.fstat(stream.fileno())
    if len(raw) > total + 1_048_576 or (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("The package exceeded its bound or changed during inspection")
    package: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as opened_archive:
            entries = opened_archive.infolist()
            if len(entries) > 256:
                raise ValueError("The package exceeds the supported member count")
            if sum(entry.file_size for entry in entries) > total:
                raise ValueError("The uncompressed package exceeds its byte limit")
            seen: set[str] = set()
            for entry in entries:
                name = entry.filename
                if (
                    not name
                    or entry.orig_filename != name
                    or PurePosixPath(name).as_posix() != name
                    or PurePosixPath(name).is_absolute()
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or any(character in name for character in "\\\x00\n\r")
                    or name in seen
                ):
                    raise ValueError("The package contains an unsupported or duplicate member name")
                seen.add(name)
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if entry.is_dir() or entry.external_attr & 0x10 or kind not in {0, stat.S_IFREG}:
                    raise ValueError("The package contains a nonregular member")
                if entry.flag_bits & 1 or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise ValueError("The package uses encryption or unsupported compression")
                if not 0 <= entry.file_size <= max_file:
                    raise ValueError("A package member exceeds its byte limit")
            for entry in entries:
                with opened_archive.open(entry) as stream:
                    body = stream.read(max_file + 1)
                if len(body) != entry.file_size or len(body) > max_file:
                    raise ValueError("A package member differs from its declared length")
                package[entry.filename] = body
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as error:
        raise ValueError("The package is malformed, truncated or fails its CRC") from error
    committed = read(repo, commit, paths, max_file=max_file, total=total)
    common = committed.keys() & package.keys()
    return {
        "changed": sorted(name for name in common if committed[name] != package[name]),
        "missing": sorted(committed.keys() - package.keys()),
        "extra": sorted(package.keys() - committed.keys()),
    }
