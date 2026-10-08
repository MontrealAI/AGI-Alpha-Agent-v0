# SPDX-License-Identifier: Apache-2.0
"""Create and safely restore content-preserving release packs below 450 MB."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from contextlib import ExitStack
from functools import partial
from pathlib import Path, PurePosixPath
from typing import IO, Any

MAX_ASSET_BYTES = 450_000_000
MAX_TOTAL_BYTES = 20_000_000_000
MAX_ENTRIES = 200_000
SCHEMA = "agialpha.release-packs.v1"
GROUPS = {"core", "models", "media", "research"}


def open_binary(path: Path) -> IO[bytes]:
    """Open an ordinary source file as a typed binary stream."""
    return path.open("rb")


def digest(path: Path) -> str:
    """Hash full file bytes without loading large assets into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_name(name: Any) -> str:
    """Require a normalized relative portable path with no extraction ambiguity."""
    if not isinstance(name, str) or not name or len(name.encode()) > 1024:
        raise ValueError("Invalid archive path")
    parts = PurePosixPath(name).parts
    if (
        name.startswith("/")
        or "\\" in name
        or ":" in name
        or any(ord(char) < 32 for char in name)
        or not parts
        or any(part in {"", ".", ".."} for part in name.split("/"))
        or len(parts) > 32
        or any(part.endswith((".", " ")) for part in parts)
        or any(re.fullmatch(r"(?i)(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part) for part in parts)
    ):
        raise ValueError("Unsafe archive path")
    return name


def classify(name: str) -> str:
    """Separate optional inference and archives from the usable small web core."""
    path = PurePosixPath(name)
    if {"local-llm", "pyodide", "models", "wasm", "wasm_llm"}.intersection(path.parts):
        return "models"
    # Shared gallery assets are mandatory service-worker precache dependencies,
    # even when their owning page lives in an optional research directory.
    if path.suffix.lower() in {".js", ".mjs", ".css", ".svg", ".json"} and {
        "assets",
        "stylesheets",
    }.intersection(path.parts):
        return "core"
    if {"research", "manuscript", "archive", "presentation"}.intersection(path.parts):
        return "research"
    if path.suffix.lower() in {".mp4", ".mp3", ".pptx", ".pdf", ".gif", ".png", ".jpg", ".jpeg", ".webp"}:
        return "media"
    return "core"


def require_asset_limits(folder: Path) -> list[dict[str, Any]]:
    """Fail closed before upload if any release asset exceeds the decimal ceiling."""
    result = []
    for path in sorted(folder.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Release assets must be ordinary files: {path.name}")
        if path.stat().st_size > MAX_ASSET_BYTES:
            raise ValueError(f"Release asset exceeds {MAX_ASSET_BYTES} bytes: {path.name}")
        result.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest(path)})
    return result


def pack(source: Path, output: Path, prefix: str, *, commit: str, version: str, limit: int = MAX_ASSET_BYTES) -> Path:
    """Pack a directory or ZIP, preserving every file and chunking oversized files."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", prefix):
        raise ValueError("Invalid pack prefix")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("An exact source commit and release version are required")
    if not 4096 <= limit <= MAX_ASSET_BYTES:
        raise ValueError("Pack size limit outside supported bounds")
    if output.is_symlink():
        raise ValueError("Pack output cannot be a symbolic link")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.glob(prefix + "-*")):
        raise ValueError("Pack output already exists; use a new prefix or directory")
    files: list[dict[str, Any]] = []
    packs: list[dict[str, Any]] = []
    with ExitStack() as stack:
        readers: list[tuple[str, int, Callable[[], IO[bytes]]]] = []
        if source.is_dir() and not source.is_symlink():
            if output.resolve().is_relative_to(source.resolve()):
                raise ValueError("Output must not be inside the source")
            for path in sorted(source.rglob("*")):
                if path.is_symlink() or not (path.is_file() or path.is_dir()):
                    raise ValueError("Only ordinary files and directories may be packed")
                if path.is_file():
                    readers.append(
                        (
                            safe_name(path.relative_to(source).as_posix()),
                            path.stat().st_size,
                            partial(open_binary, path),
                        )
                    )
        elif source.is_file() and not source.is_symlink():
            archive = stack.enter_context(zipfile.ZipFile(source))
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if stat.S_IFMT(info.external_attr >> 16) not in {0, stat.S_IFREG}:
                    raise ValueError("Archive links and special files are forbidden")
                readers.append((safe_name(info.filename), info.file_size, partial(archive.open, info)))
        else:
            raise ValueError("Source must be an ordinary directory or ZIP")
        if len(readers) > MAX_ENTRIES or sum(row[1] for row in readers) > MAX_TOTAL_BYTES:
            raise ValueError("Distribution inventory exceeds bounds")
        if len({row[0].casefold() for row in readers}) != len(readers):
            raise ValueError("Duplicate or case-ambiguous source paths")
        if any(row[0].startswith(".release-parts/") for row in readers):
            raise ValueError("Source uses the reserved chunk namespace")
        readers.sort(key=lambda row: (classify(row[0]), row[0]))
        current: zipfile.ZipFile | None = None
        current_group = ""
        estimated = 22
        counter = 0
        total = 0
        for name, size, opener in readers:
            group = classify(name)
            parts = []
            whole = hashlib.sha256()
            remaining = size
            # Stored ZIPs have bounded overhead; no compression-ratio or memory guess is needed.
            chunk_size = min(64 * 1024 * 1024, limit - 2048 - len(name.encode()) * 4)
            if chunk_size < 1:
                raise ValueError("Filename is too long for pack size limit")
            with opener() as stream:
                index = 0
                while remaining or index == 0:
                    block = stream.read(min(chunk_size, remaining))
                    if not isinstance(block, bytes):
                        raise TypeError("Source reader must return binary data")
                    if remaining and not block:
                        raise ValueError("Source changed while packaging")
                    whole.update(block)
                    member = (
                        name
                        if size <= chunk_size
                        else f".release-parts/{hashlib.sha256(name.encode()).hexdigest()}/{index}"
                    )
                    required = len(block) + len(member.encode()) * 4 + 1024
                    if current is None or current_group != group or estimated + required > limit:
                        if current is not None:
                            current.close()
                        counter += 1
                        pack_name = f"{prefix}-{group}-{counter:03d}.zip"
                        current = stack.enter_context(zipfile.ZipFile(output / pack_name, "x", zipfile.ZIP_STORED))
                        packs.append({"name": pack_name, "group": group})
                        current_group, estimated = group, 22
                    entry = zipfile.ZipInfo(member, (1980, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFREG | 0o644) << 16
                    current.writestr(entry, block)
                    parts.append(
                        {
                            "pack": packs[-1]["name"],
                            "member": member,
                            "bytes": len(block),
                            "sha256": hashlib.sha256(block).hexdigest(),
                        }
                    )
                    remaining -= len(block)
                    estimated += required
                    index += 1
                if stream.read(1):
                    raise ValueError("Source changed while packaging")
            total += size
            files.append({"path": name, "group": group, "bytes": size, "sha256": whole.hexdigest(), "parts": parts})
    for item in packs:
        target = output / item["name"]
        item.update(bytes=target.stat().st_size, sha256=digest(target))
        if item["bytes"] > limit:
            raise ValueError("Pack size invariant violated")
    manifest = {
        "schema": SCHEMA,
        "commit": commit,
        "version": version,
        "max_asset_bytes": limit,
        "total_bytes": total,
        "packs": packs,
        "files": files,
    }
    target = output / f"{prefix}-packs.json"
    target.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if target.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Inventory exceeds the supported restore limit")
    return target


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys before interpreting a distribution manifest."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate manifest key")
        result[key] = value
    return result


def restore(manifest_path: Path, destination: Path, *, groups: Iterable[str] | None = None) -> dict[str, Any]:
    """Validate packs fully and promote an independent staged tree atomically."""
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Invalid or oversized pack manifest")
    manifest = json.loads(manifest_path.read_bytes(), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported pack manifest")
    if set(manifest) != {"schema", "commit", "version", "max_asset_bytes", "total_bytes", "packs", "files"}:
        raise ValueError("Unexpected manifest fields")
    if not isinstance(manifest["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]):
        raise ValueError("Invalid source identity")
    if not isinstance(manifest["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]):
        raise ValueError("Invalid release version")
    selected = set(groups) if groups is not None else GROUPS
    if not selected or not selected <= GROUPS:
        raise ValueError("Unknown pack group")
    files, packs = manifest["files"], manifest["packs"]
    if (
        not isinstance(files, list)
        or not isinstance(packs, list)
        or len(files) > MAX_ENTRIES
        or len(packs) > MAX_ENTRIES
    ):
        raise ValueError("Invalid distribution inventory")
    if type(manifest["total_bytes"]) is not int or not 0 <= manifest["total_bytes"] <= MAX_TOTAL_BYTES:
        raise ValueError("Distribution exceeds extraction limit")
    if type(manifest["max_asset_bytes"]) is not int or not 4096 <= manifest["max_asset_bytes"] <= MAX_ASSET_BYTES:
        raise ValueError("Invalid distribution size ceiling")
    names: set[str] = set()
    paths: set[str] = set()
    expected: dict[str, dict[str, dict[str, Any]]] = {}
    actual_total = 0
    for file in files:
        if not isinstance(file, dict) or set(file) != {"path", "group", "bytes", "sha256", "parts"}:
            raise ValueError("Invalid file record")
        name = safe_name(file["path"])
        if name.casefold() in paths or file["group"] not in GROUPS:
            raise ValueError("Duplicate file or unknown group")
        paths.add(name.casefold())
        if type(file["bytes"]) is not int or not 0 <= file["bytes"] <= MAX_TOTAL_BYTES:
            raise ValueError("Invalid file size")
        if not isinstance(file["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", file["sha256"]):
            raise ValueError("Invalid file digest")
        if not isinstance(file["parts"], list) or not 1 <= len(file["parts"]) <= MAX_ENTRIES:
            raise ValueError("Invalid chunk count")
        part_total = 0
        for part in file["parts"]:
            if not isinstance(part, dict) or set(part) != {"pack", "member", "bytes", "sha256"}:
                raise ValueError("Invalid chunk")
            pack_name, member = safe_name(part["pack"]), safe_name(part["member"])
            if "/" in pack_name or type(part["bytes"]) is not int or not 0 <= part["bytes"] <= MAX_ASSET_BYTES:
                raise ValueError("Invalid pack or chunk size")
            if not isinstance(part["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", part["sha256"]):
                raise ValueError("Invalid chunk digest")
            members = expected.setdefault(pack_name, {})
            if member in members:
                raise ValueError("Duplicate chunk member")
            members[member] = {**part, "group": file["group"]}
            part_total += part["bytes"]
        if part_total != file["bytes"]:
            raise ValueError("Chunk sizes differ from file size")
        actual_total += file["bytes"]
    if actual_total != manifest["total_bytes"]:
        raise ValueError("Inventory total differs")
    if os.path.lexists(destination):
        raise ValueError("Restore destination already exists; use a new directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        archives: dict[str, zipfile.ZipFile] = {}
        for item in packs:
            if not isinstance(item, dict) or set(item) != {"name", "group", "bytes", "sha256"}:
                raise ValueError("Invalid pack record")
            name = safe_name(item["name"])
            if "/" in name or name in names or item["group"] not in GROUPS or name not in expected:
                raise ValueError("Invalid or duplicate pack")
            names.add(name)
            if any(part["group"] != item["group"] for part in expected[name].values()):
                raise ValueError("Pack crosses group boundary")
            if type(item["bytes"]) is not int or not 0 <= item["bytes"] <= manifest["max_asset_bytes"]:
                raise ValueError("Oversized pack")
            if item["group"] not in selected:
                continue
            path = manifest_path.parent / name
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size != item["bytes"]
                or digest(path) != item["sha256"]
            ):
                raise ValueError(f"Pack checksum or size mismatch: {name}")
            archive = stack.enter_context(zipfile.ZipFile(path))
            infos = archive.infolist()
            if len(infos) != len(expected[name]) or {info.filename for info in infos} != set(expected[name]):
                raise ValueError("Unexpected or duplicate archive members")
            for info in infos:
                mode = info.external_attr >> 16
                if info.is_dir() or stat.S_IFMT(mode) not in {0, stat.S_IFREG} or info.flag_bits & 1:
                    raise ValueError("Archive contains links, special files or encryption")
                if info.file_size != expected[name][info.filename]["bytes"] or info.compress_type != zipfile.ZIP_STORED:
                    raise ValueError("Archive metadata differs from bounded stored chunks")
            archives[name] = archive
        if names != set(expected):
            raise ValueError("Missing pack record")
        with tempfile.TemporaryDirectory(prefix=".release-restore-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "contents"
            staged.mkdir()
            for file in files:
                if file["group"] not in selected:
                    continue
                target = staged / file["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                whole = hashlib.sha256()
                with target.open("xb") as output:
                    for part in file["parts"]:
                        checksum = hashlib.sha256()
                        copied = 0
                        with archives[part["pack"]].open(part["member"]) as stream:
                            while block := stream.read(1024 * 1024):
                                copied += len(block)
                                if copied > part["bytes"]:
                                    raise ValueError("Chunk exceeds declared bound")
                                checksum.update(block)
                                whole.update(block)
                                output.write(block)
                        if copied != part["bytes"] or checksum.hexdigest() != part["sha256"]:
                            raise ValueError("Chunk checksum mismatch")
                if whole.hexdigest() != file["sha256"]:
                    raise ValueError("Reconstructed file checksum mismatch")
            # POSIX rename may replace an empty directory: reserve that directory first.
            # Windows rename already refuses any existing destination.
            try:
                if os.name != "nt":
                    destination.mkdir(mode=0o700)
                staged.rename(destination)
            except FileExistsError as exc:
                raise ValueError("Restore destination appeared during verification") from exc
    return {
        "commit": manifest["commit"],
        "version": manifest["version"],
        "groups": sorted(selected),
        "files": sum(f["group"] in selected for f in files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("pack")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--prefix", required=True)
    create.add_argument("--commit", required=True)
    create.add_argument("--version", required=True)
    extract = commands.add_parser("restore")
    extract.add_argument("--manifest", type=Path, required=True)
    extract.add_argument("--destination", type=Path, required=True)
    extract.add_argument("--groups", nargs="+", choices=sorted(GROUPS))
    args = parser.parse_args()
    if args.command == "pack":
        print(pack(args.source, args.output, args.prefix, commit=args.commit, version=args.version))
    else:
        print(json.dumps(restore(args.manifest, args.destination, groups=args.groups)))


if __name__ == "__main__":
    main()
