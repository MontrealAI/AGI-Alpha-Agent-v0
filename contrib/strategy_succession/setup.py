# SPDX-License-Identifier: Apache-2.0
"""Build only the reviewed source and exact declared runtime payload."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).resolve().parent


def guarded_sources() -> None:
    """Refuse a stale manifest instead of regenerating source approval."""
    profile = json.loads((ROOT / "ENGINEERING_MANIFEST.json").read_text())
    if profile.get("schema") != "strategy-engineering-installation/v1":
        raise ValueError("Expected the reviewed engineering installation profile")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    payload = set(project["tool"]["setuptools"]["package-data"]["strategy_succession_engineering"])
    payload.update({"serve.py", "__init__.py"})
    files = profile["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= 256:
        raise ValueError("Invalid exact installed file inventory")
    if set(files) != payload - {"ENGINEERING_MANIFEST.json"}:
        raise ValueError("Installation profile must hash the exact complete package payload")
    for name, expected in files.items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or relative.as_posix() != name
            or any(p in {"", ".", ".."} for p in name.split("/"))
            or "\\" in name
            or name not in payload
        ):
            raise ValueError("Installation profile requests an unlisted package file")
        path = ROOT / name
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Installation profile has an invalid source hash")
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(
                "Source differs from the reviewed installation manifest; do not regenerate it during build"
            )
    worker = json.loads((ROOT / "worker" / "SOURCE_FILES.json").read_text())
    if worker.get("scientific_source_hash") != profile["scientific_source_hash"]:
        raise ValueError("Scientific source identity is inconsistent")
    for entry in worker["files"]:
        name = "worker/" + entry["path"]
        if files.get(name) != entry["sha256"]:
            raise ValueError("Worker source inventory is not covered by the reviewed package profile")


class GuardedBuild(build_py):
    def find_package_modules(self, package: str, package_dir: str) -> list[tuple[str, str, str]]:
        modules = super().find_package_modules(package, package_dir)
        if any(module not in {"__init__", "serve", "setup"} for _, module, _ in modules):
            raise ValueError("Unexpected Python module at the fixed package root")
        return [entry for entry in modules if entry[1] in {"__init__", "serve"}]

    def run(self) -> None:
        guarded_sources()
        super().run()
        built = Path(self.build_lib) / "strategy_succession_engineering"
        expected = set(json.loads((ROOT / "ENGINEERING_MANIFEST.json").read_text())["files"])
        expected.add("ENGINEERING_MANIFEST.json")
        observed = {path.relative_to(built).as_posix() for path in built.rglob("*") if path.is_file()}
        if observed != expected or any(path.is_symlink() for path in built.rglob("*")):
            raise ValueError("Build output differs from the exact manifest; use a fresh build directory")


setup(cmdclass={"build_py": GuardedBuild})
