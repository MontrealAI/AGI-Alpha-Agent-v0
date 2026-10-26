# SPDX-License-Identifier: Apache-2.0
"""Inert public-download/source/environment refusals; no mission or study execution."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
from typing import Any
import zipfile

import pytest

from scripts import accept_public_strategy as public


class Response(io.BytesIO):
    """Minimal public HTTP response; never performs network I/O."""

    status = 200


def test_public_preparer_qa_uses_exact_commit_despite_index_and_worktree_edits(tmp_path: Path) -> None:
    repo = tmp_path / "repository"
    repo.mkdir()
    html = repo / "docs/try/index.html"
    html.parent.mkdir(parents=True)
    body = b"<!doctype html><title>Committed inert public-preparer fixture</title>"
    html.write_bytes(body)
    subprocess.run(["git", "-C", str(repo), "-c", "init.templateDir=", "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Inert source fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "Committed fixture",
        ],
        check=True,
    )
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    html.write_bytes(b"Uncommitted indexed fixture")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    html.write_bytes(b"Different uncommitted worktree fixture")
    destination = tmp_path / "public-planning-preparer.html"
    record = public.stage_public_planning_preparer(repo, commit, destination)
    assert destination.read_bytes() == body
    assert record == {
        "commit": commit,
        "path": "docs/try/index.html",
        "sha256": public.sha(body),
        "scope": public.checks.PUBLIC_PREPARER_SCOPE,
    }


@pytest.mark.parametrize("commit", ["HEAD", "main", "a" * 39, "--untrusted"])
def test_public_preparer_qa_refuses_unpinned_commit(tmp_path: Path, commit: str) -> None:
    with pytest.raises(ValueError, match="Exact public-preparer source commit"):
        public.stage_public_planning_preparer(tmp_path, commit, tmp_path / "not-created.html")
    assert not (tmp_path / "not-created.html").exists()


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


def test_core_wheel_source_and_installed_bytes_cannot_be_substituted(tmp_path: Path) -> None:
    """Exact public labels cannot hide changed code or a changed installed member."""
    original = b"VERSION = 'inert-fixture'\n"
    data = b'{"schema":"inert-original"}'
    project = b'[project]\nname="alpha-factory-v1"\nversion="1.44.0"\n[project.scripts]\nalpha-agent="fixture:main"\n'
    repo = tmp_path / "repo"
    (repo / "alpha_factory_v1").mkdir(parents=True)
    (repo / "alpha_factory_v1/__init__.py").write_bytes(original)
    (repo / "alpha_factory_v1/schema.json").write_bytes(data)
    (repo / "pyproject.toml").write_bytes(project)
    git(repo, "init", "--quiet")
    git(repo, "config", "user.name", "Public Acceptance Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "add", ".")
    git(repo, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Exact inert accepted source")
    commit = git(repo, "rev-parse", "HEAD")
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
    accepted = public.core_payload(repo, commit, wheel, site)
    assert accepted["python_files"] == 1 and len(accepted["inventory_sha256"]) == 64
    # Current worktree and HEAD do not replace the accepted immutable commit.
    (repo / "alpha_factory_v1/__init__.py").write_bytes(b"changed source after acceptance")
    assert public.core_payload(repo, commit, wheel, site) == accepted
    git(repo, "add", ".")
    git(repo, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Different source remains unqualified")
    different = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(repo, different, wheel)
    assert public.core_payload(repo, commit, wheel, site) == accepted
    target.write_bytes(b"changed installed body")
    with pytest.raises(ValueError, match="Installed core payload"):
        public.core_payload(repo, commit, wheel, site)
    fixture(raw=b"changed public body")
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(repo, commit, wheel)
    fixture(json_body=b'{"schema":"substituted"}')
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(repo, commit, wheel)
    fixture()
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("alpha_factory_v1/unrecognized.json", b"inert uncommitted payload")
    with pytest.raises(ValueError, match="Core package body"):
        public.core_payload(repo, commit, wheel)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("unauthorized.pth", b"inert never executed")
    with pytest.raises(ValueError, match="top-level"):
        public.core_payload(repo, commit, wheel)


def git(root: Path, *args: str) -> str:
    """Use real ephemeral Git objects, never a computed or mocked SHA1 identity."""
    return subprocess.check_output(
        ["git", "-C", str(root), "-c", f"core.hooksPath={os.devnull}", *args], stderr=subprocess.PIPE, text=True
    ).strip()


@pytest.mark.parametrize("commit", ["HEAD", "main", "A" * 40, "a" * 39])
def test_core_payload_refuses_non_exact_source_before_opening_a_wheel(tmp_path: Path, commit: str) -> None:
    """Public source qualification cannot silently select another ref or working tree."""
    with pytest.raises(ValueError, match="exact accepted commit"):
        public.core_payload(tmp_path, commit, tmp_path / "never-opened.whl")


@pytest.mark.parametrize(
    "raw",
    [
        b'<testsuite><testcase name="checked"/></testsuite>',
        b'<testsuites><testsuite><testcase name="checked"/></testsuite></testsuites>',
    ],
)
def test_bounded_regular_junit_with_actual_passing_case_is_accepted(tmp_path: Path, raw: bytes) -> None:
    """Only synthetic inert XML is parsed; this does not establish an actual QA pass."""
    path = tmp_path / "checked.xml"
    path.write_bytes(raw)
    public.verify_junit(path)


@pytest.mark.parametrize(
    "raw",
    [
        b'<!DOCTYPE testsuite><testsuite><testcase name="checked"/></testsuite>',
        b'<!DOCTYPE testsuite [<!ENTITY x "qualified">]><testsuite><testcase name="&x;"/></testsuite>',
        b'<!DOCTYPE testsuite SYSTEM "https://invalid.test/external.dtd"><testsuite><testcase/></testsuite>',
        b'<!DOCTYPE testsuite [<!ENTITY x SYSTEM "file:///untrusted-local-file">]><testsuite><testcase>&x;</testcase></testsuite>',
        b"<testsuite><testcase>",
        b"",
    ],
)
def test_junit_dtd_entities_external_sources_and_malformed_xml_are_refused(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "untrusted.xml"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="Unsafe or malformed"):
        public.verify_junit(path)


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped", "missing-case"])
def test_junit_unsuccessful_or_empty_results_cannot_qualify(tmp_path: Path, outcome: str) -> None:
    path = tmp_path / "outcome.xml"
    raw = "<testsuite/>" if outcome == "missing-case" else f"<testsuite><testcase><{outcome}/></testcase></testsuite>"
    path.write_text(raw)
    with pytest.raises(ValueError, match="failed, skipped or omitted"):
        public.verify_junit(path)


@pytest.mark.parametrize("case", ["symlink", "symlink-ancestor", "directory", "oversized", "missing", "fifo"])
def test_junit_input_must_be_a_bounded_regular_file_without_symlink_ancestors(tmp_path: Path, case: str) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    path = actual / "report.xml"
    path.write_bytes(b"<testsuite><testcase/></testsuite>")
    if case == "symlink":
        link = actual / "linked.xml"
        link.symlink_to(path)
        path = link
    elif case == "symlink-ancestor":
        parent = tmp_path / "linked-parent"
        parent.symlink_to(actual, target_is_directory=True)
        path = parent / path.name
    elif case == "directory":
        path.unlink()
        path.mkdir()
    elif case == "oversized":
        with path.open("wb") as stream:
            stream.truncate(public.MAX_JUNIT_BYTES + 1)
    elif case == "missing":
        path.unlink()
    else:
        path.unlink()
        os.mkfifo(path)
    with pytest.raises(ValueError, match="JUnit artifact"):
        public.verify_junit(path)


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
