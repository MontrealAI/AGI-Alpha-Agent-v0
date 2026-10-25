# SPDX-License-Identifier: Apache-2.0
"""Keep additive Strategy guides out of every historical release document set."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from scripts import package_agent_release as packaging

from scripts.package_agent_release import release_document_name, release_documents


def test_historical_document_lists_remain_byte_identical() -> None:
    expected = {
        "1.42.0": "c9921062b7d48c624126cc5adb1505dd3dc2a9685315c4aa2518643ae4cd5049",
        "1.43.0": "0befe124935b0c2eb513f5856e352a2e2f8d6627064d335e292d70e5ce4988a5",
        "1.43.99": "66136da7d61f7bcb9f26d2db42b13d30f75219fcceab6bb5a4862aaaaa289b70",
    }
    for version, digest in expected.items():
        raw = json.dumps(release_documents(version), separators=(",", ":")).encode()
        assert hashlib.sha256(raw).hexdigest() == digest


def test_strategy_guide_has_an_exact_new_version_boundary() -> None:
    before, after = map(set, (release_documents("1.43.99"), release_documents("1.44.0")))
    before = {p for p in before if "/RELEASE_NOTES_" not in p}
    after = {p for p in after if "/RELEASE_NOTES_" not in p}
    assert after - before == {"docs/agent/STRATEGY_SUCCESSION.md", "docs/agent/STRATEGY_SECURITY_OPERATOR.md"}
    assert not before - after
    documents = release_documents("1.44.0")
    assert len(documents) == len(set(documents))
    flattened = [release_document_name(p) for p in documents]
    assert len(flattened) == len(set(flattened))


def test_security_guide_is_in_the_actual_operator_archive(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(
        root / "docs/transformational-intelligence/index.html",
        tmp_path / "transformational-intelligence-workspace.html",
    )
    path = packaging.package_operator_guide(root, tmp_path, "1.44.0", "a" * 40)
    with zipfile.ZipFile(path) as archive:
        text = archive.read(packaging.operator_document_name("docs/agent/STRATEGY_SECURITY_OPERATOR.md")).decode()
        assert "1.42.0" in text and "Same-origin" in text and "not automatically reconciled" in text
        assert "separate" in text and "does not activate a map" in text


def test_validation_zip_omits_local_private_capture_and_keeps_qualified_public_artifact(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    local = tmp_path / "local"
    local.mkdir()
    (local / "review.json").write_text('{"record":"retained-local-review"}')
    private = {
        "semgrep-official/attempt-local/official-p-python.yml": "PRIVATE_RULE_BODY_SENTINEL",
        "semgrep-official/attempt-local/scanner.stderr": "PRIVATE_ERROR_PATTERN_SENTINEL",
        "semgrep-official/attempt-local/summary.json": '{"reason":"PRIVATE_PATTERN_SENTINEL"}',
        "quality/semgrep-official/attempt-nested/scanner.json": '{"rule":"PRIVATE_NESTED_SENTINEL"}',
        "semgrep-official/public/attempt-local/summary.json": '{"local_copy":true}',
    }
    ordinary = {
        "runtime/junit.xml": '<testsuite tests="1" failures="0"/>',
        "guides/STRATEGY_SECURITY_OPERATOR.md": Path("docs/agent/STRATEGY_SECURITY_OPERATOR.md").read_text(),
        "repository-python-security/attempt-ci/summary.json": '{"passed":false,"published_rule_bodies":false}',
        "repository-python-security/attempt-ci/policy-identity.json": json.dumps(
            {"rule_ids": ["example.rule"], "sha256": "a" * 64}
        ),
        "repository-python-security/attempt-ci/finding-index.json": '{"projected_findings":[],"raw_result_published":false}',
        "repository-python-security/attempt-ci/source-identities.json": json.dumps(
            {"before": {"example.py": {"sha256": "b" * 64, "bytes": 10}}}
        ),
        "semgrep-official-public/notes.json": '{"ordinary":"unrelated evidence retained"}',
    }
    prior_exclusions = {
        "browser-distribution/pack.zip": "prior-browser-exclusion",
        "pages-distribution/pack.zip": "prior-pages-exclusion",
        "github-pages/index.html": "prior-pages-tree-exclusion",
    }
    for name, text in {**private, **ordinary, **prior_exclusions}.items():
        target = evidence / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    ignored_link = evidence / "pages-distribution/ignored-private-link.json"
    ignored_link.symlink_to(evidence / next(iter(private)))
    before = {p.relative_to(evidence).as_posix(): p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
    destination = tmp_path / "validation.zip"
    packaging.package_validation_evidence(evidence, destination, local)
    after = {p.relative_to(evidence).as_posix(): p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
    assert after == before
    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert not set(private).intersection(names)
        assert not set(prior_exclusions).intersection(names)
        assert "pages-distribution/ignored-private-link.json" not in names
        assert not any(b"PRIVATE_" in archive.read(name) for name in names)
        for name, body in ordinary.items():
            assert archive.read(name) == body.encode()
        assert archive.read("local/review.json") == (local / "review.json").read_bytes()
        omissions = json.loads(archive.read("local/semgrep-private-input-omissions.json"))
        assert omissions["omitted_files"] == sorted(private)
        assert omissions["raw_inputs_modified"] is False
        assert omissions["policy_pass"] is False


@pytest.mark.parametrize("alias", ["file", "directory", "root", "local", "hardlink"])
def test_validation_zip_refuses_aliases_to_private_capture(tmp_path: Path, alias: str) -> None:
    evidence, local = tmp_path / "evidence", tmp_path / "local"
    evidence.mkdir()
    local.mkdir()
    private = evidence / "semgrep-official/attempt-local/official-p-python.yml"
    private.parent.mkdir(parents=True)
    private.write_text("PRIVATE_ALIAS_RULE_SENTINEL")
    if alias == "file":
        (evidence / "ordinary.json").symlink_to(private)
    elif alias == "directory":
        (evidence / "ordinary").symlink_to(private.parent, target_is_directory=True)
    elif alias == "root":
        linked = tmp_path / "linked-evidence"
        linked.symlink_to(evidence, target_is_directory=True)
        evidence = linked
    elif alias == "local":
        (local / "review.json").symlink_to(private)
    else:
        (evidence / "ordinary.json").hardlink_to(private)
    destination = tmp_path / "validation.zip"
    with pytest.raises(ValueError, match="alias|private|regular"):
        packaging.package_validation_evidence(evidence, destination, local)
    if destination.exists():
        with zipfile.ZipFile(destination) as archive:
            assert not any(b"PRIVATE_ALIAS_RULE_SENTINEL" in archive.read(name) for name in archive.namelist())
    assert private.read_text() == "PRIVATE_ALIAS_RULE_SENTINEL"


@pytest.mark.parametrize("replacement", ["symlink", "hardlink"])
def test_validation_zip_refuses_a_private_swap_immediately_before_open(
    tmp_path: Path, monkeypatch, replacement: str
) -> None:
    evidence, local = tmp_path / "evidence", tmp_path / "local"
    evidence.mkdir()
    local.mkdir()
    private = evidence / "semgrep-official/attempt-local/official-p-python.yml"
    private.parent.mkdir(parents=True)
    private.write_text("PRIVATE_BEFORE_OPEN_SENTINEL")
    ordinary = evidence / "ordinary.json"
    ordinary.write_text('{"ordinary":"unchanged"}')
    actual_open = packaging.os.open
    swapped = []

    def replace_then_open(path, flags, *args, **kwargs):
        if Path(path) == ordinary and not swapped:
            assert flags & packaging.os.O_NOFOLLOW
            ordinary.unlink()
            if replacement == "symlink":
                ordinary.symlink_to(private)
            else:
                ordinary.hardlink_to(private)
            swapped.append(True)
        return actual_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(packaging.os, "open", replace_then_open)
    destination = tmp_path / "validation.zip"
    with pytest.raises((ValueError, OSError)):
        packaging.package_validation_evidence(evidence, destination, local)
    assert swapped == [True]
    with zipfile.ZipFile(destination) as archive:
        assert not any(b"PRIVATE_BEFORE_OPEN_SENTINEL" in archive.read(name) for name in archive.namelist())


def test_validation_zip_streams_opened_bytes_after_name_swaps(tmp_path: Path, monkeypatch) -> None:
    evidence, local = tmp_path / "evidence", tmp_path / "local"
    evidence.mkdir()
    local.mkdir()
    private = evidence / "semgrep-official/attempt-local/official-p-python.yml"
    private.parent.mkdir(parents=True)
    private.write_text("PRIVATE_AFTER_OPEN_SENTINEL")
    ordinary = evidence / "ordinary.json"
    safe_body = b'{"ordinary":"captured-descriptor"}'
    ordinary.write_bytes(safe_body)
    original = zipfile.ZipInfo.from_file
    swapped = []

    def replace_metadata_path(filename, *args, **kwargs):
        if Path(filename) == ordinary and not swapped:
            ordinary.unlink()
            ordinary.symlink_to(private)
            swapped.append(True)
        return original(filename, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipInfo, "from_file", replace_metadata_path)
    destination = tmp_path / "validation.zip"
    with pytest.raises(ValueError, match="changed during capture"):
        packaging.package_validation_evidence(evidence, destination, local)
    assert swapped == [True]
    with zipfile.ZipFile(destination) as archive:
        assert archive.read("ordinary.json") == safe_body
        assert not any(b"PRIVATE_AFTER_OPEN_SENTINEL" in archive.read(name) for name in archive.namelist())
