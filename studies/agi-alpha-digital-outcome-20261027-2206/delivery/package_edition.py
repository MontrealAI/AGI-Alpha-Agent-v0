# SPDX-License-Identifier: Apache-2.0
"""Build a complete review-edition ZIP without changing frozen scientific evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "AGI_ALPHA_Flywheel_Digital_R1_Source_Evidence.zip"
GAP_SHA256 = "be2fd06f7ed3dde74741799020c566ae78609a91ab0afc5a6026f5dec9fe5921"
FIXED_DATE = (2026, 10, 27, 22, 6, 6)


def digest(data: bytes) -> str:
    """Return SHA-256 for exact bytes."""
    return hashlib.sha256(data).hexdigest()


def safe_file(root: Path, path: Path, *, read: bool = True) -> tuple[bytes, int]:
    """Read only a regular file beneath root without following any symlink.

    Descriptor-relative O_NOFOLLOW traversal covers the root's ancestors and
    every candidate parent, so a link replacement between selection and a later
    read cannot redirect that read. No resolve occurs before this traversal.
    """
    root_absolute = root.absolute()
    candidate = path.absolute()
    if ".." in root_absolute.parts or ".." in candidate.parts:
        raise ValueError(f"Parent traversal is not an included file path: {path}")
    try:
        relative = candidate.relative_to(root_absolute)
    except ValueError as exc:
        raise ValueError(f"Included file is outside the authorized root: {path}") from exc
    if not relative.parts:
        raise ValueError(f"Included path is not a regular file: {path}")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory_fd = os.open(root_absolute.anchor, directory_flags)
    file_fd = -1
    try:
        for component in (*root_absolute.parts[1:], *relative.parts[:-1]):
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        mode = os.fstat(file_fd).st_mode
        if not stat.S_ISREG(mode):
            raise ValueError(f"Included path is not a regular file: {path}")
        # Check canonical containment only after raw-path no-follow validation.
        if not candidate.resolve(strict=True).is_relative_to(root_absolute.resolve(strict=True)):
            raise ValueError(f"Included file resolves outside the authorized root: {path}")
        if not read:
            return b"", stat.S_IMODE(mode)
        stream = os.fdopen(file_fd, "rb")
        file_fd = -1
        with stream:
            return stream.read(), stat.S_IMODE(mode)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ValueError(f"Included file or ancestor is unsafe: {path}") from exc
    finally:
        if file_fd >= 0:
            os.close(file_fd)
        os.close(directory_fd)


def read_member(root: Path, name: str, path: Path) -> tuple[bytes, int]:
    """Apply the sole exact inherited-archive exception to the common safe read."""
    prior_root = root.parent / "agi_alpha_gap_20261027"
    inherited = prior_root / "deliverables/AGI_ALPHA_Gap_Experiment.zip"
    if name == "AGI_ALPHA_Gap_Experiment.zip" and path.absolute() == inherited.absolute():
        return safe_file(prior_root, path)
    return safe_file(root, path)


def select_prior(root: Path, requested: Path | None) -> Path:
    """Select only the local prior artifact or its fixed authorized inherited source."""
    local = root / "AGI_ALPHA_Gap_Experiment.zip"
    inherited = root.parent / "agi_alpha_gap_20261027/deliverables/AGI_ALPHA_Gap_Experiment.zip"
    if requested is not None:
        prior = requested.absolute()
        if prior not in {local.absolute(), inherited.absolute()}:
            raise ValueError("--prior-gap must be the study-local artifact or the fixed inherited source")
    else:
        try:
            safe_file(root, local, read=False)
            prior = local
        except FileNotFoundError:
            prior = inherited
    data, _ = read_member(root, "AGI_ALPHA_Gap_Experiment.zip", prior)
    if digest(data) != GAP_SHA256:
        raise ValueError("Prior gap archive identity mismatch")
    return prior


def verify_frozen(root: Path) -> int:
    """Refuse packaging if any original arm artifact has changed."""
    frozen = json.loads(safe_file(root, root / "experiment/source_freeze.json")[0])
    for relative, expected in frozen["files"].items():
        if digest(safe_file(root, root / "experiment" / relative)[0]) != expected:
            raise ValueError(f"Frozen file mismatch: {relative}")
    return len(frozen["files"])


def include_files(root: Path) -> dict[str, Path]:
    """Select source/evidence without secrets, raw prose, duplicate work or render caches."""
    selected: dict[str, Path] = {}
    for directory in [
        "experiment",
        "vendor",
        "boost_challenge",
        "conventional",
        "audit",
        "economics",
        "delivery",
        "edition",
    ]:
        for path in sorted((root / directory).rglob("*")):
            relative = path.relative_to(root)
            if "__pycache__" in relative.parts:
                continue
            if directory == "edition" and (
                path.suffix in {".aux", ".log", ".out", ".toc"} or ("qa" in relative.parts and path.suffix != ".json")
            ):
                continue
            if directory == "delivery" and "work" in relative.parts:
                continue
            if path.name == "package_receipt.json":
                continue
            if stat.S_ISDIR(path.lstat().st_mode):
                continue
            safe_file(root, path, read=False)
            selected[str(relative)] = path
    for relative_name in [
        "discovery/INITIAL_SCREEN.md",
        "discovery/beta_screen_reproduction.json",
        "repo_audit/AUDIT.md",
        "repo_audit/current_reuse_verification.json",
        "repo_audit/preserved_gap_hashes.json",
        "publication/preflight_summary.json",
        "publication/refresh_receipts.json",
        "publication/VERIFICATION_PLAN.md",
        "publication/review_receipts/cfee251_review.json",
        "LinkedIn_Draft_Digital_R1.txt",
        "browser_reading.md",
    ]:
        path = root / relative_name
        try:
            safe_file(root, path, read=False)
        except FileNotFoundError:
            continue
        selected[relative_name] = path
    for path in sorted((root / "discovery/beta_sources").glob("*")):
        safe_file(root, path, read=False)
        selected[str(path.relative_to(root))] = path
    # Preserve every frozen item, even if a future freeze legitimately records a cache file.
    frozen = json.loads(safe_file(root, root / "experiment/source_freeze.json")[0])
    for relative in frozen["files"]:
        path = root / "experiment" / relative
        safe_file(root, path, read=False)
        selected["experiment/" + relative] = path
    return selected


def normalized_sources(files: dict[str, Path], root: Path = ROOT) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    """Add only a separately mapped SPDX comment to original AGI ALPHA source copies."""
    copies: dict[str, bytes] = {}
    mappings: list[dict[str, Any]] = []
    for relative, path in files.items():
        if path.suffix not in {".py", ".cpp"} or relative.split("/")[0] not in {
            "experiment",
            "boost_challenge",
            "audit",
        }:
            continue
        original, _ = safe_file(root, path)
        if b"SPDX-License-Identifier:" in original[:512]:
            continue
        marker = (
            b"// SPDX-License-Identifier: Apache-2.0\n"
            if path.suffix == ".cpp"
            else b"# SPDX-License-Identifier: Apache-2.0\n"
        )
        if original.startswith(b"#!"):
            first, separator, rest = original.partition(b"\n")
            normalized = first + separator + marker + rest
        else:
            normalized = marker + original
        ast_equal: bool | None = None
        if path.suffix == ".py":
            ast_equal = ast.dump(ast.parse(original), include_attributes=False) == ast.dump(
                ast.parse(normalized), include_attributes=False
            )
            if not ast_equal:
                raise ValueError(f"Normalization changed Python AST: {relative}")
        target = "normalized_sources/" + relative
        copies[target] = normalized
        mappings.append(
            {
                "original": relative,
                "normalized": target,
                "original_sha256": digest(original),
                "normalized_sha256": digest(normalized),
                "change": "Apache-2.0 SPDX comment only; original unchanged",
                "python_ast_equal": ast_equal,
            }
        )
    return copies, mappings


def write_entry(archive: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    """Write deterministic, safe relative-path archive entries."""
    if name.startswith("/") or ".." in Path(name).parts:
        raise ValueError(f"Unsafe archive path: {name}")
    info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compresslevel=9)


def main() -> None:
    """Package current final artifacts and verify every member against the manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "deliverables" / ARCHIVE_NAME)
    parser.add_argument("--prior-gap", type=Path, help="Exact study-local or fixed inherited prior-artifact path only")
    parser.add_argument("--replace", action="store_true", help="Replace this task's unissued preview archive")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and not args.replace:
        raise SystemExit("Output exists; use --replace only for an unissued preview")
    if output == ROOT / "AGI_ALPHA_Gap_Experiment.zip":
        raise SystemExit("Cannot overwrite the preserved gap archive")
    count = verify_frozen(ROOT)
    prior = select_prior(ROOT, args.prior_gap)
    if output == prior.absolute() or (output.exists() and output.samefile(prior)):
        raise ValueError("Cannot overwrite the preserved prior gap archive")
    files = include_files(ROOT)
    files["AGI_ALPHA_Gap_Experiment.zip"] = prior
    for source in files.values():
        if output == source.absolute() or (output.exists() and output.samefile(source)):
            raise ValueError("Cannot overwrite a selected source or evidence input")
    virtual, mappings = normalized_sources(files)
    virtual["LICENSE"] = safe_file(ROOT, ROOT / "delivery/native_reuse/LICENSE")[0]
    virtual["README.md"] = (
        "# AGI ALPHA FLYWHEEL - DIGITAL-20261027-R1\n\n"
        "Research review edition. Read [the complete paper](edition/AGI_ALPHA_Flywheel_Digital_R1.pdf), "
        "[the executive brief](edition/AGI_ALPHA_Flywheel_Digital_R1_Brief.pdf), or "
        "[the complete offline browser edition](edition/AGI_ALPHA_Flywheel_Digital_R1.html). "
        "The common manuscript, compilable LaTeX, bibliography and figure sources are in `edition/`.\n\n"
        "Distribution and original-versus-normalized source identities are explained in "
        "[DISTRIBUTION_POLICY.md](delivery/DISTRIBUTION_POLICY.md). "
        "The archive contains the preserved earlier kinetics edition under its unchanged identity.\n\n"
        + safe_file(ROOT, ROOT / "delivery/README.md")[0].decode("utf-8")
    ).encode()
    virtual["normalization_manifest.json"] = (
        json.dumps(
            {
                "edition": "DIGITAL-20261027-R1",
                "purpose": "Publication license normalization only, never primary evidence or replay substitution",
                "copies": mappings,
            },
            indent=2,
        )
        + "\n"
    ).encode()
    entries: dict[str, dict[str, Any]] = {}
    for name, path in sorted(files.items()):
        data, _ = read_member(ROOT, name, path)
        entries[name] = {"sha256": digest(data), "bytes": len(data)}
    for name, data in sorted(virtual.items()):
        if name in entries:
            raise ValueError(f"Duplicate archive entry: {name}")
        entries[name] = {"sha256": digest(data), "bytes": len(data)}
    manifest = {
        "edition": "DIGITAL-20261027-R1",
        "frozen_original_files_verified": count,
        "manifest_scope": "Every archive member except archive_manifest.json itself; no self-hash claim",
        "normalization_copies": len(mappings),
        "entries": entries,
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            data, mode = read_member(ROOT, name, path)
            write_entry(archive, name, data, mode)
        for name, data in sorted(virtual.items()):
            write_entry(archive, name, data)
        write_entry(archive, "archive_manifest.json", manifest_bytes)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
        if set(archive.namelist()) != set(entries) | {"archive_manifest.json"}:
            raise ValueError("ZIP member set mismatch")
        for name, record in entries.items():
            data = archive.read(name)
            if digest(data) != record["sha256"] or len(data) != record["bytes"]:
                raise ValueError(f"Archive readback hash mismatch: {name}")
    if verify_frozen(ROOT) != count:
        raise ValueError("Frozen count changed during packaging")
    receipt = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": str(output),
        "archive_sha256": digest(output.read_bytes()),
        "archive_bytes": output.stat().st_size,
        "members": len(entries) + 1,
        "uncompressed_bytes": sum(row["bytes"] for row in entries.values()) + len(manifest_bytes),
        "all_member_crc_and_sha256_verified": True,
        "frozen_original_files_before_and_after": count,
        "normalized_source_copies": len(mappings),
        "raw_third_party_issue_prose_redistributed": False,
        "prior_gap_sha256": GAP_SHA256,
        "status": "Built local review package; publication and attachment delivery require separate verification",
    }
    (ROOT / "delivery/package_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
