# SPDX-License-Identifier: Apache-2.0
"""Inert public-download/source/environment refusals; no mission or study execution."""

from __future__ import annotations

import io
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

import pytest

from scripts import accept_public_strategy as public


class Response(io.BytesIO):
    """Minimal public HTTP response; never performs network I/O."""

    status = 200


def release(raw: bytes = b"checked public body") -> dict[str, Any]:
    """Describe one exact inert public asset."""
    return {
        "tag_name": "v1.44.0",
        "assets": [
            {
                "id": 7,
                "name": "sample.json",
                "size": len(raw),
                "digest": "sha256:" + public.sha(raw),
                "browser_download_url": "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/download/v1.44.0/sample.json",
            }
        ],
    }


def test_actual_public_body_identity_and_no_authorization_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A complete body is retained only under its exact public digest."""
    raw = b"checked public body"

    def open_public(request: Any, timeout: int) -> Response:
        assert "Authorization" not in request.headers and timeout == 60
        return Response(raw)

    monkeypatch.setattr(public, "urlopen", open_public)
    receipt = public.fetch_asset(release(raw), "sample.json", tmp_path / "sample.json")
    assert receipt["sha256"] == public.sha(raw) and receipt["bytes"] == len(raw)
    assert (tmp_path / "sample.json").read_bytes() == raw


@pytest.mark.parametrize("body", [b"tampered same bytes!", b"short", b"checked public body plus extra"])
def test_changed_truncated_or_growing_body_never_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    """A failed transport remains failed rather than accepting its published label."""
    monkeypatch.setattr(public, "urlopen", lambda *_a, **_k: Response(body))
    with pytest.raises(ValueError, match="size/hash mismatch|exceeded"):
        public.fetch_asset(release(), "sample.json", tmp_path / "partial.json")
    assert (tmp_path / "partial.json").exists()


def test_missing_asset_and_foreign_url_refuse_before_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing or redirected selection cannot select another public executable."""

    def forbidden(*_a: Any, **_k: Any) -> None:
        pytest.fail("Network entered before exact asset admission")

    monkeypatch.setattr(public, "urlopen", forbidden)
    with pytest.raises(ValueError, match="missing"):
        public.fetch_asset(release(), "missing.whl", tmp_path / "missing.whl")
    value = release()
    value["assets"][0]["browser_download_url"] = "https://untrusted.example/sample.json"
    with pytest.raises(ValueError, match="escaped"):
        public.fetch_asset(value, "sample.json", tmp_path / "other.json")


def test_existing_body_is_never_overwritten_or_retried(tmp_path: Path) -> None:
    """Partial previous downloads remain available for diagnosis."""
    path = tmp_path / "sample.json"
    path.write_bytes(b"failed first attempt")
    with pytest.raises(ValueError, match="overwrite or retry"):
        public.fetch_asset(release(), "sample.json", path)
    assert path.read_bytes() == b"failed first attempt"


def test_wrong_public_tag_source_and_draft_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A normal release label cannot authorize another source commit."""
    published = {
        "tag_name": "v1.44.0",
        "published_at": "2026-10-25T01:00:00Z",
        "draft": False,
        "prerelease": False,
        "assets": [],
    }
    monkeypatch.setattr(
        public,
        "public_json",
        lambda url: published if "/releases/" in url else {"object": {"type": "commit", "sha": "b" * 40}},
    )
    with pytest.raises(ValueError, match="another source"):
        public.release_identity("1.44.0", "a" * 40)
    published["draft"] = True
    with pytest.raises(ValueError, match="normally public"):
        public.release_identity("1.44.0", "b" * 40)


@pytest.mark.parametrize("change", ["shared-site", "wrong-version", "checkout", "companion-checkout"])
def test_dirty_or_shadowed_environment_is_not_public_installation(tmp_path: Path, change: str) -> None:
    """Actual interpreter observations must identify the new isolated environment."""
    prefix = tmp_path / "venv"
    report = {
        "prefix": str(prefix),
        "version": "1.42.0",
        "system_site_packages": False,
        "module": str(prefix / "site/alpha_factory_v1/__init__.py"),
        "companion": str(prefix / "site/strategy_succession_engineering"),
    }
    public.verify_environment(report, prefix, "1.42.0", companion=True)
    if change == "shared-site":
        report["system_site_packages"] = True
    elif change == "wrong-version":
        report["version"] = "1.44.0"
    elif change == "checkout":
        report["module"] = str(tmp_path / "checkout/alpha_factory_v1/__init__.py")
    else:
        report["companion"] = str(tmp_path / "checkout/contrib/strategy_succession")
    with pytest.raises(ValueError, match="dirty|Wrong runtime|shadowed"):
        public.verify_environment(report, prefix, "1.42.0", companion=True)


def test_duplicate_or_escaping_checksum_names_refused() -> None:
    """A checksum document cannot silently replace an earlier binding."""
    row = "a" * 64 + "  sample.whl\n"
    assert public.checksum_list(row.encode()) == {"sample.whl": "a" * 64}
    for value in (row + row, "a" * 64 + "  ../escape.whl\n", "not a checksum"):
        with pytest.raises(ValueError, match="Malformed"):
            public.checksum_list(value.encode())


def test_failure_artifacts_redact_token_and_preserve_full_failed_log(tmp_path: Path) -> None:
    """Sensitive failed exports are withheld, while the failed log remains inspectable."""
    work, evidence = tmp_path / "work", tmp_path / "safe"
    for path in (work / "logs", work / "public-results", work / "private", evidence):
        path.mkdir(parents=True)
    token = b"EPHEMERAL_FIXTURE_TOKEN_DO_NOT_EXPORT"
    (work / "private/api.token").write_bytes(token)
    (work / "logs/browser.log").write_bytes(b"case failed: " + token + b"\nfull traceback retained\n")
    (work / "public-results/browser-mission-export.json").write_bytes(b'{"leak":"' + token + b'"}')
    summary: dict[str, Any] = {"state": "FAILED_NOT_QUALIFIED"}
    public.safe_artifacts(work, evidence, summary)
    assert token not in (evidence / "browser.log").read_bytes()
    assert b"full traceback retained" in (evidence / "browser.log").read_bytes()
    assert not (evidence / "browser-mission-export.json").exists()
    assert summary["withheld_sensitive_outputs"][0]["sha256"]
    assert (evidence / "public-installation.json").is_file()


def test_core_wheel_source_and_installed_bytes_cannot_be_substituted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exact public labels cannot hide changed code or a changed installed member."""
    original = b"VERSION = 'inert-fixture'\n"
    blob = hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest()
    data = b'{"schema":"inert-original"}'
    data_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    listing = (
        "100644 blob "
        + blob
        + "\talpha_factory_v1/__init__.py\0"
        + "100644 blob "
        + data_blob
        + "\talpha_factory_v1/schema.json\0"
    ).encode()
    project = b'[project]\nname="alpha-factory-v1"\nversion="1.44.0"\n[project.scripts]\nalpha-agent="fixture:main"\n'
    monkeypatch.setattr(public.subprocess, "check_output", lambda args, **_k: listing if "ls-tree" in args else project)
    wheel = tmp_path / "alpha_factory_v1-1.44.0-py3-none-any.whl"
    site = tmp_path / "site"
    target = site / "alpha_factory_v1/__init__.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    (target.parent / "schema.json").write_bytes(data)

    def fixture(raw: bytes = original, json_body: bytes = data) -> None:
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("alpha_factory_v1/__init__.py", raw)
            archive.writestr("alpha_factory_v1/schema.json", json_body)
            archive.writestr("alpha_factory_v1-1.44.0.dist-info/METADATA", "Name: alpha-factory-v1\nVersion: 1.44.0\n")
            archive.writestr(
                "alpha_factory_v1-1.44.0.dist-info/entry_points.txt", "[console_scripts]\nalpha-agent = fixture:main\n"
            )

    fixture()
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if ".dist-info/" in name:
                path = site / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
    assert public.core_payload(tmp_path, "a" * 40, wheel, site)["python_files"] == 1
    target.write_bytes(b"changed installed body")
    with pytest.raises(ValueError, match="Installed core payload"):
        public.core_payload(tmp_path, "a" * 40, wheel, site)
    fixture(raw=b"changed public body")
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(tmp_path, "a" * 40, wheel)
    fixture(json_body=b'{"schema":"substituted"}')
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(tmp_path, "a" * 40, wheel)
    fixture()
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("alpha_factory_v1/unrecognized.json", b"inert uncommitted payload")
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(tmp_path, "a" * 40, wheel)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("unauthorized.pth", b"inert never executed")
    with pytest.raises(ValueError, match="top-level"):
        public.core_payload(tmp_path, "a" * 40, wheel)


def test_failure_log_cannot_export_escaped_private_key(tmp_path: Path) -> None:
    """A Python bytes literal or uppercase hex must not disclose a recoverable key."""
    work, evidence = tmp_path / "work", tmp_path / "safe"
    for path in (work / "logs", work / "public-results", work / "private", evidence):
        path.mkdir(parents=True)
    key = bytes(range(32))
    (work / "private/identity.key").write_bytes(key)
    raw = (
        b"AssertionError identity="
        + repr(key).encode()
        + b"\nhex="
        + key.hex().upper().encode()
        + b"\n"
        + json.dumps({"identity": repr(key)}).encode()
    )
    (work / "logs/crash.log").write_bytes(raw)
    public.safe_artifacts(work, evidence, {"state": "FAILED_NOT_QUALIFIED"})
    cleaned = (evidence / "crash.log").read_bytes()
    assert repr(key).encode() not in cleaned and key.hex().upper().encode() not in cleaned
    assert json.dumps(repr(key))[1:-1].encode() not in cleaned
    assert b"AssertionError identity=" in cleaned
