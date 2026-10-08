# SPDX-License-Identifier: Apache-2.0
"""Private disaster recovery preserves role identity without changing portable-export trust."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from alpha_factory_v1.core.runtime.store import Journal, private_write
from alpha_factory_v1.core.runtime.successor.protocol import EvidenceRecord, Institution, MissionConstitution, canonical
from alpha_factory_v1.core.runtime.successor.state import EvidenceSubmission, SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import retained_local_principals, sign_record

BASE_MEMBERS = {"config.json", "identity.key", "api.token", "journal.sqlite3", "manifest.json"}
ROLE_MEMBERS = {
    "successor-principals/principals.json",
    "successor-principals/local-controller.key",
    "successor-principals/local-producer.key",
    "successor-principals/local-verifier.key",
}


def initialized(tmp_path: Path) -> Journal:
    journal = Journal.initialize(tmp_path / "home")
    retained_local_principals(journal.root / "successor-principals")
    return journal


def archive_files(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def write_archive(
    path: Path, files: dict[str, bytes], *, symlink: str | None = None, duplicate: str | None = None
) -> None:
    content = {name: data for name, data in files.items() if name != "manifest.json"}
    content["manifest.json"] = canonical({name: hashlib.sha256(data).hexdigest() for name, data in content.items()})
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in content.items():
            member = zipfile.ZipInfo(name)
            member.create_system = 3
            member.external_attr = ((stat.S_IFLNK if name == symlink else stat.S_IFREG) | 0o600) << 16
            archive.writestr(member, data)
        if duplicate:
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr(duplicate, content[duplicate])


def test_legacy_backup_bytes_and_member_contract_remain_compatible(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "legacy")
    original = journal.verify()
    backup = tmp_path / "legacy.zip"
    journal.backup(backup)
    assert set(archive_files(backup)) == BASE_MEMBERS
    restored = Journal.restore(backup, tmp_path / "restored")
    assert restored.verify() == original
    assert not (restored.root / "successor-principals").exists()


def test_private_backup_restores_exact_keys_and_resumes_signed_state(tmp_path: Path) -> None:
    journal = initialized(tmp_path)
    trust, keys = retained_local_principals(journal.root / "successor-principals")
    store = SuccessorStore(journal, trust)
    store.create_institution(
        Institution(
            id="institution",
            controller="local-controller",
            constitution=MissionConstitution(
                mission_id="metrics", owner="local-controller", objective="bounded private recovery rehearsal"
            ),
        ),
        {"calls": 5},
    )

    def submission(ident: str) -> EvidenceSubmission:
        return EvidenceSubmission(
            institution_id="institution",
            evidence=EvidenceRecord(
                evidence_id=ident,
                source="synthetic public recovery fixture",
                acquired_at="2026-01-01T00:00:00Z",
                content_digest="a" * 64,
                permitted_uses=["formation"],
                valid_until="2099-01-01T00:00:00Z",
                scope="metrics",
                uncertainty="no performance claim",
                accepted_by="local-controller",
            ),
        )

    first = sign_record(keys["local-controller"], "local-controller", "evidence", submission("first"))
    store.record_evidence("institution", first, request_id="first")
    before = journal.verify()
    backup = tmp_path / "private.zip"
    journal.backup(backup)
    assert set(archive_files(backup)) == BASE_MEMBERS | ROLE_MEMBERS
    if os.name != "nt":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    restored = Journal.restore(backup, tmp_path / "restored")
    assert restored.verify() == before
    restored_trust, restored_keys = retained_local_principals(restored.root / "successor-principals")
    for name in ROLE_MEMBERS:
        assert (restored.root / name).read_bytes() == (journal.root / name).read_bytes()
        if os.name != "nt":
            assert stat.S_IMODE((restored.root / name).stat().st_mode) == 0o600
    assert restored_trust.verify(first, "evidence", "acceptance") == first.payload
    resumed = SuccessorStore(restored, restored_trust)
    assert resumed.read("institution")["evidence"] == store.read("institution")["evidence"]
    second = sign_record(restored_keys["local-controller"], "local-controller", "evidence", submission("second"))
    resumed.record_evidence("institution", second, request_id="second")
    assert set(resumed.read("institution")["evidence"]) == {"first", "second"}
    assert restored.verify()["events"] == before["events"] + 1
    assert journal.verify() == before


def test_explicit_public_trust_registry_is_preserved_without_private_role_generation(tmp_path: Path) -> None:
    journal = Journal.initialize(tmp_path / "external")
    key = Ed25519PrivateKey.generate()
    registry = {
        "schema_version": 1,
        "principals": {
            "external-controller": {
                "public_key": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
                "roles": ["controller"],
                "provenance": "local",
                "independence_attestation": "",
            }
        },
    }
    data = canonical(registry)
    private_write(journal.root / "successor-trust.json", data)
    backup = tmp_path / "external.zip"
    journal.backup(backup)
    assert set(archive_files(backup)) == BASE_MEMBERS | {"successor-trust.json"}
    restored = Journal.restore(backup, tmp_path / "restored")
    assert (restored.root / "successor-trust.json").read_bytes() == data
    assert not (restored.root / "successor-principals").exists()


@pytest.mark.parametrize("attack", ["missing", "unexpected", "key-mismatch", "duplicate-key", "symlink", "permissions"])
def test_backup_refuses_incomplete_or_unsafe_role_state(tmp_path: Path, attack: str) -> None:
    journal = initialized(tmp_path)
    root = journal.root / "successor-principals"
    key = root / "local-producer.key"
    if attack == "missing":
        key.unlink()
    elif attack == "unexpected":
        private_write(root / "other-secret.key", b"not-in-the-inventory")
    elif attack == "key-mismatch":
        key.write_bytes(Ed25519PrivateKey.generate().private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
    elif attack == "duplicate-key":
        manifest = root / "principals.json"
        data = manifest.read_bytes()
        manifest.write_bytes(b'{"scope":"local-rehearsal",' + data[1:])
    elif attack == "symlink":
        target = tmp_path / "private-key"
        key.rename(target)
        key.symlink_to(target)
    else:
        if os.name == "nt":
            pytest.skip("POSIX permission-bit enforcement; Windows private ACL validation is a separate platform gate")
        key.chmod(0o644)
    output = tmp_path / "must-not-exist.zip"
    with pytest.raises(ValueError):
        journal.backup(output)
    assert not output.exists()
    assert not list(journal.root.glob("backup-*.sqlite3"))


@pytest.mark.parametrize("attack", ["partial", "unexpected", "traversal", "symlink", "duplicate", "key-mismatch"])
def test_restore_rejects_bad_optional_members_before_creating_destination(tmp_path: Path, attack: str) -> None:
    journal = initialized(tmp_path)
    backup = tmp_path / "source.zip"
    journal.backup(backup)
    files = archive_files(backup)
    symlink = duplicate = None
    if attack == "partial":
        del files["successor-principals/local-verifier.key"]
    elif attack == "unexpected":
        files["successor-principals/undeclared.key"] = b"unexpected"
    elif attack == "traversal":
        files["successor-principals/../../escaped"] = b"outside destination"
    elif attack == "symlink":
        symlink = "successor-principals/local-producer.key"
    elif attack == "duplicate":
        duplicate = "successor-principals/principals.json"
    else:
        files["successor-principals/local-verifier.key"] = b"x" * 32
    bad = tmp_path / "bad.zip"
    write_archive(bad, files, symlink=symlink, duplicate=duplicate)
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        Journal.restore(bad, destination)
    assert not destination.exists() and not (tmp_path / "escaped").exists()


def test_restore_failure_does_not_leave_private_partial_state(tmp_path: Path) -> None:
    journal = initialized(tmp_path)
    backup = tmp_path / "source.zip"
    journal.backup(backup)
    files = archive_files(backup)
    files["identity.key"] = b"invalid"
    bad = tmp_path / "bad.zip"
    write_archive(bad, files)
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        Journal.restore(bad, destination)
    assert not destination.exists()


def test_restore_refuses_input_symlink_and_preserves_existing_destination(tmp_path: Path) -> None:
    journal = initialized(tmp_path)
    backup = tmp_path / "source.zip"
    journal.backup(backup)
    alias = tmp_path / "alias.zip"
    alias.symlink_to(backup)
    with pytest.raises(ValueError):
        Journal.restore(alias, tmp_path / "not-created")
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep"
    marker.write_text("retained")
    with pytest.raises(FileExistsError):
        Journal.restore(backup, existing)
    assert marker.read_text() == "retained"
