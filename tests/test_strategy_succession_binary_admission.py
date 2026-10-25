# SPDX-License-Identifier: Apache-2.0
"""Exact inert Strategy media admission; no study or executor code is executed."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Any
import warnings
import zipfile

import pytest
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject

from scripts import check_no_binary_diff as gate
from tests.test_no_binary_diff_entrypoint import git, history, save

ROOT = Path(__file__).resolve().parents[1]
STUDY = "studies/agi-alpha-flywheel-strategy-succession-v1/"
ENGINEERING = "contrib/strategy_succession/evidence/"


def binary_manifest() -> dict[str, Any]:
    return json.loads((ROOT / gate.STRATEGY_MANIFEST).read_bytes())


def copy_reviewed_payload(root: Path) -> dict[str, Any]:
    """Copy inert original bodies without importing any scientific or evidence code."""
    data = binary_manifest()
    scientific = json.loads((ROOT / gate.STRATEGY_SCIENTIFIC_MANIFEST).read_bytes())
    modes = {row["repo_path"]: int(row["mode"], 8) & 0o777 for row in scientific["files"]}
    names = {gate.STRATEGY_MANIFEST, gate.STRATEGY_SCIENTIFIC_MANIFEST}
    names.update(row["path"] for row in data["files"])
    names.update(row["repo_path"] for row in scientific["files"])
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
        target.chmod(modes.get(name, 0o644))
    return data


@pytest.fixture
def payload(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "payload"
    root.mkdir()
    data = copy_reviewed_payload(root)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Strategy Admission Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    save(root)
    return root, data


def rewrite_manifest(root: Path, data: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reach semantic guards using a test-only digest, never edit reviewed repository bytes."""
    raw = json.dumps(data).encode()
    (root / gate.STRATEGY_MANIFEST).write_bytes(raw)
    monkeypatch.setattr(gate, "STRATEGY_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest())


def refuses(root: Path, name: str) -> bool:
    try:
        return name not in gate._strategy_admissions(root, [name])
    except (OSError, ValueError):
        return True


def test_all_twenty_reviewed_originals_pass_exact_identity_and_media_validation(payload) -> None:
    root, _ = payload
    rows = gate._load_strategy_manifest(root)
    assert len(rows) == 20
    assert sum(row["size"] for row in rows.values()) == 5_271_810
    assert Counter(row["media_type"] for row in rows.values()) == {
        "application/zip": 8,
        "application/pdf": 10,
        "image/png": 2,
    }
    assert gate._strategy_admissions(root, list(rows)) == set(rows)
    scientific = json.loads((root / gate.STRATEGY_SCIENTIFIC_MANIFEST).read_bytes())
    assert len(scientific["files"]) == 238


def test_original_subset_and_unknown_renamed_copy_are_not_a_suffix_exclusion(payload) -> None:
    root, data = payload
    names = [data["files"][0]["path"], next(row["path"] for row in data["files"] if row["media_type"] == "image/png")]
    extra = ENGINEERING + "unreviewed-copy.zip"
    shutil.copyfile(root / names[0], root / extra)
    assert gate._strategy_admissions(root, [*names, extra]) == set(names)
    assert gate._strategy_admissions(root, [extra]) == set()


@pytest.mark.parametrize("case", ["changed-byte", "changed-length", "deleted", "directory", "symlink", "ancestor"])
def test_evidence_must_remain_the_exact_regular_file(payload, case: str) -> None:
    root, data = payload
    name = data["files"][0]["path"]
    path = root / name
    if case == "changed-byte":
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
    elif case == "changed-length":
        path.write_bytes(path.read_bytes() + b"x")
    elif case == "deleted":
        path.unlink()
    elif case == "directory":
        path.unlink()
        path.mkdir()
    elif case == "symlink":
        path.unlink()
        path.symlink_to(ROOT / name)
    else:
        moved = path.parent.with_name("moved-evidence")
        path.parent.rename(moved)
        path.parent.symlink_to(moved, target_is_directory=True)
    assert refuses(root, name)


@pytest.mark.parametrize("case", ["missing", "changed", "symlink", "ancestor"])
def test_reviewed_binary_manifest_is_immutable_and_regular(payload, case: str) -> None:
    root, data = payload
    path = root / gate.STRATEGY_MANIFEST
    if case == "missing":
        path.unlink()
    elif case == "changed":
        path.write_bytes(path.read_bytes() + b" ")
    elif case == "symlink":
        path.unlink()
        path.symlink_to(ROOT / gate.STRATEGY_MANIFEST)
    else:
        moved = path.parent.with_name("moved-data")
        path.parent.rename(moved)
        path.parent.symlink_to(moved, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        gate._strategy_admissions(root, [data["files"][0]["path"]])


def test_unrelated_binaries_do_not_load_or_inherit_strategy_admission(tmp_path: Path) -> None:
    assert gate._strategy_admissions(tmp_path, ["unknown.zip", "elsewhere/figure.pdf", "x.png"]) == set()


@pytest.mark.parametrize(
    "case", ["schema", "commit", "tree", "scope", "missing-row", "duplicate-row", "total-size", "extra-field"]
)
def test_manifest_source_scope_and_inventory_are_closed(payload, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    root, original = payload
    data = deepcopy(original)
    if case == "schema":
        data["schema"] = "unreviewed/v1"
    elif case == "commit":
        data["source_commit"] = "0" * 40
    elif case == "tree":
        data["source_tree"] = "0" * 40
    elif case == "scope":
        data["scope"] = "Production execution approved"
    elif case == "missing-row":
        data["files"].pop()
    elif case == "duplicate-row":
        data["files"][1] = data["files"][0]
    elif case == "total-size":
        data["files"][0]["size"] += 1
    else:
        data["authority"] = ["forged"]
    rewrite_manifest(root, data, monkeypatch)
    with pytest.raises(ValueError):
        gate._load_strategy_manifest(root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "../outside.zip"),
        ("path", ENGINEERING + "../outside.zip"),
        ("path", ENGINEERING + "./development-checkpoint.zip"),
        ("path", ENGINEERING.replace("/", "\\") + "development-checkpoint.zip"),
        ("size", True),
        ("size", -1),
        ("sha256", "x" * 64),
        ("git_blob", "x" * 40),
        ("media_type", "application/pdf"),
        ("media_type", {}),
        ("unreviewed", True),
    ],
)
def test_manifest_record_paths_types_and_media_are_closed(
    payload, monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    root, data = payload
    data["files"][0][field] = value
    rewrite_manifest(root, data, monkeypatch)
    with pytest.raises(ValueError):
        gate._load_strategy_manifest(root)


@pytest.mark.parametrize("field", ["sha256", "git_blob"])
def test_forged_well_formed_hashes_do_not_admit_original_bytes(
    payload, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    root, data = payload
    row = data["files"][0]
    row[field] = "0" * (64 if field == "sha256" else 40)
    rewrite_manifest(root, data, monkeypatch)
    assert refuses(root, row["path"])


@pytest.mark.parametrize("case", ["kind", "identity", "source-path", "unknown-field", "not-object"])
def test_each_original_requires_its_exact_provenance(payload, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    root, data = payload
    provenance = data["files"][0]["provenance"]
    if case == "kind":
        provenance["kind"] = "successful-production-run"
    elif case == "identity":
        provenance["source_identity"] = "git:" + "0" * 40
    elif case == "source-path":
        provenance["source_path"] = "../unreviewed.zip"
    elif case == "unknown-field":
        provenance["authority"] = True
    else:
        data["files"][0]["provenance"] = "original"
    rewrite_manifest(root, data, monkeypatch)
    with pytest.raises(ValueError):
        gate._load_strategy_manifest(root)


@pytest.mark.parametrize("case", ["malformed", "duplicate-key"])
def test_pinned_digest_does_not_replace_strict_json_parsing(
    payload, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    root, _ = payload
    raw = b"{" if case == "malformed" else b'{"schema":1,"schema":2}'
    (root / gate.STRATEGY_MANIFEST).write_bytes(raw)
    monkeypatch.setattr(gate, "STRATEGY_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        gate._load_strategy_manifest(root)


@pytest.mark.parametrize(
    "case", ["manifest-missing", "manifest-changed", "manifest-symlink", "body-missing", "body-changed", "body-symlink"]
)
def test_entire_scientific_source_identity_is_checked_before_binary_admission(payload, case: str) -> None:
    root, data = payload
    manifest = root / gate.STRATEGY_SCIENTIFIC_MANIFEST
    scientific = json.loads(manifest.read_bytes())
    body_name = next(row["repo_path"] for row in scientific["files"] if row["path"].endswith(".md"))
    path = manifest if case.startswith("manifest") else root / body_name
    if case.endswith("missing"):
        path.unlink()
    elif case.endswith("changed"):
        path.write_bytes(path.read_bytes() + b"x")
    else:
        path.unlink()
        path.symlink_to(ROOT / (gate.STRATEGY_SCIENTIFIC_MANIFEST if case.startswith("manifest") else body_name))
    with pytest.raises((OSError, ValueError)):
        gate._strategy_admissions(root, [data["files"][0]["path"]])


@pytest.mark.parametrize("case", ["path", "sha256", "count"])
def test_scientific_payload_reference_cannot_be_replaced(payload, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    root, data = payload
    if case == "path":
        data["scientific_payload"]["path"] = "some-other-manifest.json"
    elif case == "sha256":
        data["scientific_payload"]["sha256"] = "0" * 64
    else:
        data["scientific_payload"]["body_count"] = 238
    rewrite_manifest(root, data, monkeypatch)
    with pytest.raises(ValueError):
        gate._load_strategy_manifest(root)


@pytest.mark.parametrize("media", ["application/zip", "application/pdf", "image/png"])
def test_media_validation_is_independent_of_attacker_supplied_byte_commitments(
    payload, monkeypatch, media: str
) -> None:
    root, data = payload
    rows = {row["path"]: row for row in data["files"]}
    row = next(row for row in rows.values() if row["media_type"] == media)
    raw = b"X" * row["size"]
    (root / row["path"]).write_bytes(raw)
    row["sha256"] = hashlib.sha256(raw).hexdigest()
    row["git_blob"] = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    # Isolate media parsing here; whole-source refusal is exercised separately above.
    monkeypatch.setattr(gate, "_load_strategy_manifest", lambda _: rows)
    monkeypatch.setattr(gate, "_verify_strategy_scientific_sources", lambda _: None)
    monkeypatch.setattr(
        gate, "_strategy_head", lambda _: {name: ("100644", item["git_blob"]) for name, item in rows.items()}
    )
    assert gate._strategy_admissions(root, [row["path"]]) == set()


def synthetic_pdf(case: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    if case == "two-pages":
        writer.add_blank_page(width=72, height=72)
    elif case == "title":
        writer.add_metadata({"/Title": "Not a reviewed Strategy figure"})
    elif case == "javascript":
        writer.add_js("app.alert('synthetic admission test');")
    elif case == "attachment":
        writer.add_attachment("untrusted.txt", b"synthetic data")
    elif case == "open-action":
        writer._root_object[NameObject("/OpenAction")] = DictionaryObject(
            {NameObject("/S"): NameObject("/Launch"), NameObject("/F"): TextStringObject("untrusted")}
        )
    elif case == "external-link":
        annotation = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/A"): DictionaryObject(
                    {
                        NameObject("/S"): NameObject("/URI"),
                        NameObject("/URI"): TextStringObject("https://invalid.test/"),
                    }
                ),
            }
        )
        writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
    elif case == "encrypted":
        writer.encrypt("synthetic password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_actual_author_pdf_and_figures_have_distinct_inert_media_constraints() -> None:
    rows = binary_manifest()["files"]
    author = next(row for row in rows if row["provenance"]["kind"] == "scientific-author-pdf")
    figure = next(row for row in rows if row["provenance"]["kind"] == "scientific-figure-pdf")
    author_raw, figure_raw = (ROOT / author["path"]).read_bytes(), (ROOT / figure["path"]).read_bytes()
    assert gate._valid_strategy_pdf(author_raw, author=True)
    assert gate._valid_strategy_pdf(figure_raw, author=False)
    assert not gate._valid_strategy_pdf(author_raw, author=False)
    assert not gate._valid_strategy_pdf(figure_raw, author=True)


@pytest.mark.parametrize(
    "case", ["two-pages", "title", "javascript", "attachment", "open-action", "external-link", "encrypted"]
)
def test_figure_pdf_actions_embeds_external_references_and_wrong_shape_are_refused(case: str) -> None:
    assert not gate._valid_strategy_pdf(synthetic_pdf(case), author=False)


@pytest.mark.parametrize("raw", [b"", b"%PDF-1.7\nnot a document", b"PK\x03\x04not a PDF"])
def test_malformed_pdf_bytes_are_refused(raw: bytes) -> None:
    assert not gate._valid_strategy_pdf(raw, author=False)


@pytest.mark.parametrize(
    "case", ["traversal", "absolute", "backslash", "dot", "duplicate", "symlink", "crc", "malformed"]
)
def test_zip_paths_links_duplicates_crc_and_malformed_payloads_are_refused(tmp_path: Path, case: str) -> None:
    buffer = io.BytesIO()
    names = {"traversal": "../outside", "absolute": "/absolute", "backslash": "a\\b", "dot": "a/./b"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            if case == "symlink":
                info = zipfile.ZipInfo("link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b"target")
            else:
                archive.writestr(names.get(case, "safe.txt"), b"synthetic inert bytes")
                if case == "duplicate":
                    archive.writestr("safe.txt", b"second body")
    raw = buffer.getvalue()
    if case == "crc":
        raw = raw.replace(b"synthetic inert bytes", b"Synthetic inert bytes", 1)
    elif case == "malformed":
        raw = b"PK\x03\x04not an archive"
    path = tmp_path / "type-check.zip"
    path.write_bytes(raw)
    assert not gate._valid_strategy_zip(path, raw)


@pytest.mark.parametrize(
    "case", ["member-count", "member-size", "total-size", "unsupported-compression", "special-file"]
)
def test_zip_resource_bounds_and_file_types_remain_enforced(tmp_path: Path, case: str) -> None:
    buffer = io.BytesIO()
    compression = zipfile.ZIP_BZIP2 if case == "unsupported-compression" else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        if case == "member-count":
            for index in range(513):
                archive.writestr(f"item-{index}", b"")
        elif case == "member-size":
            archive.writestr("oversized", b"x" * (4 * 1024 * 1024 + 1))
        elif case == "total-size":
            for index in range(9):
                archive.writestr(f"item-{index}", b"x" * (4 * 1024 * 1024))
        elif case == "special-file":
            info = zipfile.ZipInfo("device")
            info.create_system = 3
            info.external_attr = (stat.S_IFCHR | 0o600) << 16
            archive.writestr(info, b"")
        else:
            archive.writestr("safe.txt", b"synthetic inert bytes")
    raw = buffer.getvalue()
    path = tmp_path / "bounded.zip"
    path.write_bytes(raw)
    assert not gate._valid_strategy_zip(path, raw)


def run_exact_gate(root: Path, base: str) -> subprocess.CompletedProcess[str]:
    env = {
        key: value for key, value in os.environ.items() if key not in {"PYTHONPATH", "PYTHONHOME", "GITHUB_EVENT_PATH"}
    }
    return subprocess.run(
        [sys.executable, "scripts/check_no_binary_diff.py", "--base", base],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_actual_cli_admits_all_twenty_originals_and_still_rejects_an_unknown_binary(tmp_path: Path) -> None:
    root, base, _ = history(tmp_path)
    copy_reviewed_payload(root)
    save(root)
    accepted = run_exact_gate(root, base)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert accepted.stdout.strip() == "No binary changes detected."
    name = ENGINEERING + "unknown.zip"
    (root / name).write_bytes(b"unreviewed\0binary")
    save(root)
    rejected = run_exact_gate(root, base)
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    assert "  - " + name in rejected.stdout


@pytest.mark.parametrize("base", ["main", "HEAD", "a" * 39, "A" * 40, "0" * 40])
def test_explicit_cli_base_must_be_an_available_exact_lowercase_commit_oid(tmp_path: Path, base: str) -> None:
    root, _, _ = history(tmp_path)
    result = run_exact_gate(root, base)
    assert result.returncode != 0
    assert "No binary changes detected." not in result.stdout


def test_explicit_cli_blob_oid_is_not_a_commit_and_cannot_fall_back_to_clean_head(tmp_path: Path) -> None:
    root, _, _ = history(tmp_path)
    blob = git(root, "hash-object", "-w", "README.md")
    result = run_exact_gate(root, blob)
    assert result.returncode != 0
    assert "No binary changes detected." not in result.stdout


def test_explicit_cli_annotated_tag_object_is_not_an_exact_commit_oid(tmp_path: Path) -> None:
    root, _, _ = history(tmp_path)
    git(root, "-c", "tag.gpgsign=false", "tag", "-a", "synthetic-tag", "-m", "Tag object, not commit object")
    tag = git(root, "rev-parse", "refs/tags/synthetic-tag")
    result = run_exact_gate(root, tag)
    assert result.returncode != 0
    assert "No binary changes detected." not in result.stdout


def test_explicit_comparison_failure_cannot_fall_back_to_a_clean_diff(tmp_path: Path, monkeypatch, capsys) -> None:
    base = "a" * 40
    monkeypatch.setattr(gate, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(
        gate, "_run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=base + "\n", stderr="")
    )

    def fail_exact_diff(ref: str, *, exact: bool = False) -> list[str]:
        assert ref == base and exact is True
        raise subprocess.CalledProcessError(128, ["git", "diff"])

    monkeypatch.setattr(gate, "_iter_changed_paths", fail_exact_diff)
    assert gate.main(base) == 1
    output = capsys.readouterr().out
    assert "Cannot compare the exact --base commit" in output
    assert "No binary changes detected." not in output


def test_exact_cli_base_uses_direct_diff_even_when_base_is_not_an_ancestor(tmp_path: Path) -> None:
    root, common, _ = history(tmp_path)
    git(root, "switch", "-c", "unmerged-base")
    (root / "unauthorized.bin").write_bytes(b"unreviewed\0binary")
    base = save(root)
    git(root, "switch", "main")
    assert git(root, "rev-parse", "HEAD") == common
    (root / "ordinary.txt").write_text("A separate branch outcome.\n")
    save(root)
    result = run_exact_gate(root, base)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "  - unauthorized.bin" in result.stdout


def test_actual_cli_after_merge_admits_exact_originals_then_rejects_new_unlisted_binary(tmp_path: Path) -> None:
    root, _, _ = history(tmp_path)
    git(root, "switch", "-c", "reviewed-strategy")
    copy_reviewed_payload(root)
    save(root)
    git(root, "switch", "main")
    (root / "ordinary.txt").write_text("Independent main branch change.\n")
    before_merge = save(root)
    git(root, "-c", "commit.gpgsign=false", "merge", "--no-ff", "reviewed-strategy", "-m", "Synthetic qualified merge")
    merged = git(root, "rev-parse", "HEAD")
    accepted = run_exact_gate(root, before_merge)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    unknown = ENGINEERING + "after-merge-unreviewed.zip"
    (root / unknown).write_bytes(b"unreviewed\0binary")
    save(root)
    rejected = run_exact_gate(root, merged)
    assert rejected.returncode == 1, rejected.stdout + rejected.stderr
    assert "  - " + unknown in rejected.stdout


@pytest.mark.parametrize("target", ["binary", "scientific-body", "binary-manifest"])
def test_actual_cli_refuses_changed_committed_bytes_masked_by_restored_worktree(tmp_path: Path, target: str) -> None:
    root, base, _ = history(tmp_path)
    data = copy_reviewed_payload(root)
    save(root)
    if target == "binary":
        name = data["files"][0]["path"]
    elif target == "binary-manifest":
        name = gate.STRATEGY_MANIFEST
    else:
        scientific = json.loads((root / gate.STRATEGY_SCIENTIFIC_MANIFEST).read_bytes())
        name = next(row["repo_path"] for row in scientific["files"] if row["path"].endswith(".md"))
    path = root / name
    original = path.read_bytes()
    path.write_bytes(original + b"\ncommitted unreviewed replacement\n")
    save(root)
    path.write_bytes(original)
    assert git(root, "status", "--porcelain", "--", name)
    result = run_exact_gate(root, base)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "No binary changes detected." not in result.stdout


@pytest.mark.parametrize("target", ["binary", "scientific-body", "binary-manifest"])
def test_actual_cli_refuses_changed_committed_file_mode_masked_by_restored_worktree(
    tmp_path: Path, target: str
) -> None:
    root, base, _ = history(tmp_path)
    data = copy_reviewed_payload(root)
    save(root)
    if target == "binary":
        name = data["files"][0]["path"]
    elif target == "binary-manifest":
        name = gate.STRATEGY_MANIFEST
    else:
        scientific = json.loads((root / gate.STRATEGY_SCIENTIFIC_MANIFEST).read_bytes())
        name = next(row["repo_path"] for row in scientific["files"] if row["path"].endswith(".md"))
    path = root / name
    path.chmod(0o755)
    save(root)
    path.chmod(0o644)
    result = run_exact_gate(root, base)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "No binary changes detected." not in result.stdout
