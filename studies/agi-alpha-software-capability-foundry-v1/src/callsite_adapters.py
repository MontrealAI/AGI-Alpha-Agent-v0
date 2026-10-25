# SPDX-License-Identifier: Apache-2.0
"""Additive, bounded adapters for two pinned production call sites."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Callable

CONTRIB = "contrib/strategy_succession/"
CATALOG = "alpha_factory_v1/demos/catalog.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def committed_files(root: Path, commit: str, reader: Callable) -> dict[str, bytes]:
    """Preserve package configuration and returned names; batch exact bodies."""
    _require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "An exact Git commit is required")
    path = CONTRIB + "pyproject.toml"
    raw = reader(root, commit, [path], max_file=8_000_000, total=8_000_000)[path]
    config = tomllib.loads(raw.decode())
    payload = config["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"]
    names = {*payload, "serve.py", "__init__.py", "pyproject.toml", "setup.py"}
    _require(1 <= len(names) <= 256, "Invalid companion source inventory")
    paths = []
    for name in sorted(names):
        path = PurePosixPath(name)
        _require(
            isinstance(name, str)
            and path.as_posix() == name
            and not path.is_absolute()
            and not any(p in {"", ".", ".."} for p in name.split("/"))
            and "\\" not in name,
            "Companion source path escapes its fixed scope",
        )
        paths.append(CONTRIB + name)
    result = {}
    for start in range(0, len(paths), 256):
        chunk = paths[start : start + 256]
        result.update(reader(root, commit, chunk, max_file=8_000_000, total=8_000_000 * len(chunk)))
    return result


def expected_workers(
    root: Path,
    commit: str,
    inventory: dict[str, tuple[str, str]],
    reader: Callable,
    is_cache_asset: Callable,
    render_scripts: Callable,
    max_blob: int = 25_000_000,
) -> dict[str, bytes]:
    """Keep the paper-only regular-file policy and unchanged worker renderer."""
    def read(paths: list[str]) -> dict[str, bytes]:
        for name in paths:
            if name not in inventory or inventory[name][0] != "100644":
                raise ValueError(f"Paper proof requires ordinary non-executable files: {name}")
        result = {}
        for start in range(0, len(paths), 256):
            chunk = paths[start : start + 256]
            values = reader(root, commit, chunk, max_file=max_blob, total=max_blob * len(chunk))
            for name, body in values.items():
                actual = hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()
                if actual != inventory[name][1]:
                    raise ValueError("Caller inventory differs from the exact requested commit")
            result.update(values)
        return result

    release = json.loads(read([CATALOG])[CATALOG])["release"]
    paths = [name for name in inventory if name.startswith("docs/") and is_cache_asset(Path(name.removeprefix("docs/")))]
    assets = {name.removeprefix("docs/"): body for name, body in read(paths).items()}
    return {"docs/" + name: raw.encode() for name, raw in render_scripts(assets, release).items()}
