# SPDX-License-Identifier: Apache-2.0
"""Frozen publication source admission is exact and fails closed."""

import hashlib
import shutil
from pathlib import Path

import pytest

from scripts import check_no_binary_diff as gate

ROOT = Path(__file__).resolve().parents[1]
ROWS = gate.AUTHORIZED_INVENTION_PUBLICATION


def copy_asset(root: Path, name: str) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
    return target


def test_exact_inventory_and_originals():
    assert len(ROWS) == 15
    assert sum(name.endswith(".png") for name in ROWS) == 7
    assert sum(name.endswith(".pdf") for name in ROWS) == 7
    assert sum(name.endswith(".zip") for name in ROWS) == 1
    assert gate._invention_publication_admissions(ROOT, list(ROWS)) == set(ROWS)
    assert not any(name.startswith("docs/papers/") for name in ROWS)
    for name, (size, digest) in ROWS.items():
        data = (ROOT / name).read_bytes()
        assert len(data) == size
        assert hashlib.sha256(data).hexdigest() == digest


@pytest.mark.parametrize("name", ROWS)
@pytest.mark.parametrize("tamper", ["same_length", "append", "truncate", "missing", "directory"])
def test_changed_bytes_lengths_and_types_rejected(tmp_path, name, tamper):
    path = copy_asset(tmp_path, name)
    raw = path.read_bytes()
    if tamper == "same_length":
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    elif tamper == "append":
        path.write_bytes(raw + b"x")
    elif tamper == "truncate":
        path.write_bytes(raw[:-1])
    else:
        path.unlink()
        if tamper == "directory":
            path.mkdir()
    assert gate._invention_publication_admissions(tmp_path, [name]) == set()


@pytest.mark.parametrize("parent", [False, True])
def test_file_and_parent_symlinks_rejected(tmp_path, parent):
    name = next(iter(ROWS))
    path = copy_asset(tmp_path, name)
    if parent:
        moved = path.parent.with_name("moved")
        path.parent.rename(moved)
        path.parent.symlink_to(moved, target_is_directory=True)
    else:
        path.unlink()
        path.symlink_to(ROOT / name)
    assert gate._invention_publication_admissions(tmp_path, [name]) == set()


def test_renamed_and_rogue_paths_not_admitted(tmp_path):
    name = next(iter(ROWS))
    original = copy_asset(tmp_path, name)
    for rogue in ["extra.pdf", "extra.zip", "extensionless", name.replace("acceptance", "unreviewed")]:
        target = tmp_path / rogue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        assert gate._invention_publication_admissions(tmp_path, [rogue]) == set()
        assert gate._invention_publication_admissions(tmp_path, [name, rogue]) == {name}


def test_canonical_pdf_not_admitted_by_source_exception():
    assert (
        gate._invention_publication_admissions(ROOT, ["docs/papers/verified-criticism-executable-repair-v1.pdf"])
        == set()
    )


def test_noncanonical_spellings_do_not_alias_authorized_paths():
    name = next(iter(ROWS))
    for altered in [
        "./" + name,
        name.replace("/figures/", "/figures/../figures/"),
        name.replace("/", "\\"),
        "/" + name,
    ]:
        assert gate._invention_publication_admissions(ROOT, [altered]) == set()


def test_no_looser_legacy_or_catalog_fallback():
    from scripts import research_papers as papers

    legacy = gate.AUTHORIZED_MANUSCRIPT | gate.AUTHORIZED_REPORT_PACK | gate.AUTHORIZED_FLAGSHIP_ARTWORK
    assert not ROWS.keys() & legacy.keys()
    assert not ROWS.keys() & papers.asset_hashes(papers.load_catalog(ROOT)).keys()


def test_direct_gate_admits_reviewed_source_but_rejects_tamper_and_extra(tmp_path):
    from tests.test_no_binary_diff_entrypoint import history, run_gate, save

    root, _, event = history(tmp_path)
    for name in ROWS:
        copy_asset(root, name)
    save(root)
    result = run_gate(root, event)
    assert result.returncode == 0, result.stdout + result.stderr
    name = next(name for name in ROWS if name.endswith(".zip"))
    path = root / name
    raw = path.read_bytes()
    path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    save(root)
    result = run_gate(root, event)
    assert result.returncode == 1
    assert name in result.stdout
    path.write_bytes(raw)
    (root / "extra.zip").write_bytes(raw)
    save(root)
    result = run_gate(root, event)
    assert result.returncode == 1
    assert "extra.zip" in result.stdout
