# SPDX-License-Identifier: Apache-2.0
"""Capture the fixed pure-Python public-reader dependencies before operator approval."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import stat
from pathlib import Path
from typing import Any

DEPENDENCY_PACKAGES = ("httpx", "httpcore", "h11", "anyio", "sniffio", "certifi", "idna", "typing_extensions")
MAX_DEPENDENCY_FRAME = 8_000_000


def _source_bytes(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 <= info.st_size <= 1_000_000:
            raise ValueError("public-reader dependency file exceeds its bound")
        source = stream.read(1_000_001)
    if not 0 <= len(source) <= 1_000_000:
        raise ValueError("public-reader dependency file exceeds its bound")
    return source


def capture_dependencies() -> bytes:
    """Retain exact source/resource bytes; later imports never reopen these installed paths."""
    modules: dict[str, dict[str, Any]] = {}
    resources: dict[str, str] = {}
    total = 0
    for name in DEPENDENCY_PACKAGES:
        spec = importlib.util.find_spec(name)
        if spec is None and name == "sniffio":
            continue  # Newer locked AnyIO versions do not install this optional compatibility module.
        if spec is None or spec.origin is None or Path(spec.origin).suffix != ".py":
            raise ValueError("public-reader requires its fixed pure-Python dependency closure")
        origin = Path(spec.origin).resolve(strict=True)
        package = spec.submodule_search_locations is not None
        paths: list[Path] = []
        if package:
            for directory, dirs, files in os.walk(origin.parent, followlinks=False):
                dirs[:] = sorted(item for item in dirs if item != "__pycache__")
                if any((Path(directory) / item).is_symlink() for item in dirs):
                    raise ValueError("linked public-reader dependency directories are not supported")
                paths.extend(Path(directory) / item for item in sorted(files) if item.endswith(".py"))
        else:
            paths.append(origin)
        for path in paths:
            relative = path.relative_to(origin.parent)
            is_package = path.name == "__init__.py"
            suffix = relative.parts[:-1] if is_package else (*relative.parts[:-1], path.stem)
            fullname = ".".join((name, *suffix)) if package else name
            if not all(part.isidentifier() for part in fullname.split(".")) or fullname in modules:
                raise ValueError("ambiguous public-reader dependency module")
            source = _source_bytes(path)
            total += len(source)
            modules[fullname] = {"source": base64.b64encode(source).decode("ascii"), "package": is_package}
            if len(modules) > 512 or total > 4_000_000:
                raise ValueError("public-reader dependency closure exceeds its bound")
        if name == "certifi":
            resource = _source_bytes(origin.with_name("cacert.pem"))
            total += len(resource)
            resources["certifi/cacert.pem"] = base64.b64encode(resource).decode("ascii")
    frame = json.dumps({"modules": modules, "resources": resources}, sort_keys=True, separators=(",", ":")).encode()
    if total > 4_000_000 or not 0 < len(frame) <= MAX_DEPENDENCY_FRAME:
        raise ValueError("public-reader dependency closure exceeds its bound")
    return frame


# This fixed bootstrap is itself permit-bound. Third-party modules and the CA
# bundle are loaded from the captured frame, never mutable site-package roots.
READ_BOOTSTRAP = """import importlib.machinery, sys
class SourceOnlyLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)
sys.path_hooks.insert(0, importlib.machinery.FileFinder.path_hook(
    (SourceOnlyLoader, importlib.machinery.SOURCE_SUFFIXES),
    (importlib.machinery.ExtensionFileLoader, importlib.machinery.EXTENSION_SUFFIXES)))
sys.path_importer_cache.clear()
import base64, importlib.abc, importlib.resources.abc, importlib.util, io, json
size = int.from_bytes(sys.stdin.buffer.read(4), 'big')
if not 0 < size <= 128_000:
    raise ValueError('invalid approved reader size')
source = sys.stdin.buffer.read(size)
dependency_size = int.from_bytes(sys.stdin.buffer.read(4), 'big')
if len(source) != size or not 0 < dependency_size <= 8_000_000:
    raise ValueError('invalid approved reader frame')
dependency_frame = sys.stdin.buffer.read(dependency_size)
if len(dependency_frame) != dependency_size:
    raise ValueError('incomplete approved dependency frame')
snapshot = json.loads(dependency_frame)
modules, resources = snapshot['modules'], snapshot['resources']
if not isinstance(modules, dict) or not 0 < len(modules) <= 512 or not isinstance(resources, dict):
    raise ValueError('invalid approved dependency snapshot')
class Resources(importlib.resources.abc.ResourceReader):
    def __init__(self, fullname): self.prefix = fullname.replace('.', '/') + '/'
    def open_resource(self, name): return io.BytesIO(base64.b64decode(resources[self.prefix + name], validate=True))
    def resource_path(self, name): raise FileNotFoundError(name)
    def is_resource(self, name): return self.prefix + name in resources
    def contents(self): return [name[len(self.prefix):] for name in resources if name.startswith(self.prefix)]
class SnapshotLoader(importlib.abc.SourceLoader):
    def __init__(self, fullname): self.fullname = fullname
    def get_filename(self, fullname):
        return '/__approved_public_reader__/' + fullname.replace('.', '/') + ('/__init__.py' if self.is_package(fullname) else '.py')
    def get_data(self, path): return base64.b64decode(modules[self.fullname]['source'], validate=True)
    def get_source(self, fullname): return importlib.util.decode_source(self.get_data(None))
    def get_code(self, fullname): return compile(self.get_data(None), self.get_filename(fullname), 'exec')
    def is_package(self, fullname): return modules[fullname]['package'] is True
    def get_resource_reader(self, fullname): return Resources(fullname)
class SnapshotFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in modules:
            return importlib.util.spec_from_loader(fullname, SnapshotLoader(fullname))
sys.meta_path.insert(0, SnapshotFinder())
exec(compile(source, '<approved-public-reader>', 'exec'))
"""
