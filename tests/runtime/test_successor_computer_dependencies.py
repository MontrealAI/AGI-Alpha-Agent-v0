# SPDX-License-Identifier: Apache-2.0
"""Exercise actual child imports from permit-bound dependency source/resource bytes."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import certifi
import pytest

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import computer, computer_dependencies


def substitute_dependency(monkeypatch: pytest.MonkeyPatch, name: str, origin: Path) -> None:
    original = importlib.util.find_spec

    def find_spec(fullname: str, *args: Any, **kwargs: Any) -> Any:
        if fullname == name:
            return importlib.util.spec_from_file_location(fullname, origin)
        return original(fullname, *args, **kwargs)

    monkeypatch.setattr(computer_dependencies.importlib.util, "find_spec", find_spec)


def dependency_fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    for name, source in (("httpx", "from httpcore import MARKER\n"), ("httpcore", "MARKER='approved'\n")):
        root = tmp_path / name
        root.mkdir()
        origin = root / "__init__.py"
        origin.write_text(source)
        substitute_dependency(monkeypatch, name, origin)
    reader = tmp_path / "reader.py"
    reader.write_text(
        "import base64,httpx,json,sys\nsys.stdin.buffer.read()\nbody=httpx.MARKER.encode()\n"
        "print(json.dumps({'bytes_read':len(body),'response':{'status':200,'content_type':'text/plain',"
        "'body':base64.b64encode(body).decode()}}))\n"
    )
    monkeypatch.setattr(computer, "READ_WORKER", reader)
    return tmp_path / "httpcore/__init__.py", tmp_path / "UNAPPROVED_EXECUTED"


@pytest.mark.parametrize("replacement", ["after-construction", "at-spawn"])
def test_transitive_dependency_replacement_never_executes_later_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, replacement: str
) -> None:
    dependency, marker = dependency_fixture(monkeypatch, tmp_path)
    broker = computer.ReadBroker(["https://example.org/public"])
    malicious = f"from pathlib import Path\nPath({str(marker)!r}).write_text('unapproved')\nMARKER='changed'\n"
    if replacement == "at-spawn":
        real_popen = subprocess.Popen

        def replace_and_start(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
            dependency.write_text(malicious)
            return real_popen(*args, **kwargs)

        monkeypatch.setattr(computer.subprocess, "Popen", replace_and_start)
    else:
        dependency.write_text(malicious)
    response = broker.fetch("https://example.org/public", "GET")
    assert base64.b64decode(response["body"]) == b"approved"
    assert broker.bytes == 8 and not marker.exists()


def test_changed_transitive_dependency_requires_a_fresh_permit_before_factory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dependency, _ = dependency_fixture(monkeypatch, tmp_path)
    task = computer.ComputerTask(
        goal="Synthetic source binding", html="<p>Fixture</p>", input_rights="synthetic", license="Fixture"
    )

    class Advisor:
        identity = {"mode": "CONTROLLED_TEST_DOUBLE", "model": "fixed", "endpoint": "none"}

        def next(self, *args: Any) -> dict[str, Any]:
            raise AssertionError("no model call")

    advisor, image = Advisor(), "sha256:" + "a" * 64
    permit = computer.commitment(task, advisor, image)
    dependency.write_text("MARKER='changed'\n")
    assert computer.commitment(task, advisor, image) != permit
    with pytest.raises(ValueError, match="permit"):
        computer.run_session(Journal.initialize(tmp_path / "home"), task, advisor, image, tmp_path / "output", permit)
    assert not (tmp_path / "output").exists()


def test_factory_dependency_context_keeps_approved_bytes_and_resets_after_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dependency, _ = dependency_fixture(monkeypatch, tmp_path)
    task = computer.ComputerTask(
        goal="Synthetic source binding", html="<p>Fixture</p>", input_rights="synthetic", license="Fixture"
    )

    class Advisor:
        identity = {"mode": "CONTROLLED_TEST_DOUBLE", "model": "fixed", "endpoint": "none"}

        def next(self, *args: Any) -> dict[str, Any]:
            raise AssertionError("no model call")

    advisor, image = Advisor(), "sha256:" + "a" * 64
    approved = computer_dependencies.capture_dependencies()
    permit = computer.commitment(task, advisor, image)

    def fail_factory(*args: Any) -> Any:
        dependency.write_text("MARKER='changed'\n")
        assert computer._APPROVED_READ_DEPENDENCIES.get() == approved
        assert computer.ReadBroker([]).dependencies == approved
        raise ValueError("controlled factory failure")

    with pytest.raises(ValueError, match="controlled factory"):
        computer.run_session(
            Journal.initialize(tmp_path / "home"),
            task,
            advisor,
            image,
            tmp_path / "output",
            permit,
            factory=fail_factory,
        )
    assert computer._APPROVED_READ_DEPENDENCIES.get() is None
    assert computer.ReadBroker([]).dependencies != approved


def test_ca_resource_is_retained_and_still_valid_after_installed_bundle_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "certifi"
    shutil.copytree(Path(certifi.__file__).parent, root, ignore=shutil.ignore_patterns("__pycache__"))
    substitute_dependency(monkeypatch, "certifi", root / "__init__.py")
    approved_digest = hashlib.sha256((root / "cacert.pem").read_bytes()).hexdigest()
    original_reader = computer.READ_WORKER.read_text()
    reader = tmp_path / "reader.py"
    reader.write_text(
        "import certifi,certifi.core,hashlib,httpx,socket,ssl\n"
        "def forbidden(*args,**kwargs):raise AssertionError('temporary certificate path is forbidden')\n"
        "certifi.where=forbidden;certifi.core.as_file=forbidden\n"
        "socket.getaddrinfo=lambda *args,**kwargs:[(2,1,6,'',('1.1.1.1',443))]\n"
        "class Response:\n status_code=200\n headers={}\n"
        " def __enter__(self):return self\n def __exit__(self,*args):pass\n"
        " def iter_raw(self,**kwargs):yield hashlib.sha256(certifi.contents().encode()).hexdigest().encode()\n"
        "class Client:\n"
        " def __init__(self,**kwargs):\n"
        "  assert isinstance(kwargs['verify'],ssl.SSLContext) and kwargs['verify'].cert_store_stats()['x509_ca']>0\n"
        " def __enter__(self):return self\n def __exit__(self,*args):pass\n"
        " def stream(self,*args,**kwargs):return Response()\n"
        "httpx.Client=Client\n" + "exec(compile(" + repr(original_reader) + ",'<actual-reader-ca-fixture>','exec'))\n"
    )
    monkeypatch.setattr(computer, "READ_WORKER", reader)
    broker = computer.ReadBroker(["https://example.org/public"])
    (root / "cacert.pem").write_text("unapproved and invalid replacement")
    response = broker.fetch("https://example.org/public", "GET")
    assert base64.b64decode(response["body"]).decode() == approved_digest


def test_dependency_source_size_is_bounded_before_child_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dependency, _ = dependency_fixture(monkeypatch, tmp_path)
    dependency.write_bytes(b"x" * 1_000_001)
    with pytest.raises(ValueError, match="dependency file exceeds"):
        computer.ReadBroker([])


def test_approved_optional_absence_cannot_import_a_later_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, marker = dependency_fixture(monkeypatch, tmp_path)
    optional = tmp_path / "sniffio.py"
    original = importlib.util.find_spec

    def find_spec(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "sniffio":
            return importlib.util.spec_from_file_location(name, optional) if optional.exists() else None
        return original(name, *args, **kwargs)

    monkeypatch.setattr(computer_dependencies.importlib.util, "find_spec", find_spec)
    reader = computer.READ_WORKER
    reader.write_text(
        "import base64,httpx,importlib.util,json,sys\n"
        "assert importlib.util.find_spec('sniffio') is None\nsys.stdin.buffer.read()\nbody=httpx.MARKER.encode()\n"
        "print(json.dumps({'bytes_read':len(body),'response':{'status':200,'content_type':'text/plain',"
        "'body':base64.b64encode(body).decode()}}))\n"
    )
    approved = computer.worker_source_digest()
    broker = computer.ReadBroker(["https://example.org/public"])
    optional.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unapproved')\n")
    assert computer.worker_source_digest() != approved
    response = broker.fetch("https://example.org/public", "GET")
    assert base64.b64decode(response["body"]) == b"approved" and not marker.exists()


@pytest.mark.parametrize("origin", [None, "/unapproved/sniffio.pyc"])
def test_invalid_optional_install_is_refused_instead_of_omitted(
    monkeypatch: pytest.MonkeyPatch, origin: str | None
) -> None:
    original = importlib.util.find_spec

    def find_spec(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "sniffio":
            return importlib.machinery.ModuleSpec(name, loader=None, origin=origin)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(computer_dependencies.importlib.util, "find_spec", find_spec)
    with pytest.raises(ValueError, match="pure-Python dependency closure"):
        computer_dependencies.capture_dependencies()
