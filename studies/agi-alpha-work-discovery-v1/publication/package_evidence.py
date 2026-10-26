# SPDX-License-Identifier: Apache-2.0
"""Plan, assemble and verify a complete, byte-bound repository-shaped companion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

STUDY = Path(__file__).resolve().parents[1]
REPOSITORY = STUDY.parents[1]
MANIFEST_NAME = "COMPANION-MANIFEST.json"
RELEASE_NAME = "COMPANION-RELEASE.json"
ZIP_DATE = (2026, 10, 26, 0, 0, 0)
PACKAGING_PREFIXES = ("package-plan", "review-files", "package-release", "package-receipt", "companion-verify")


def sha256(data: bytes) -> str:
    """Return a content digest."""
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    """Hash a regular file without loading a large tool binary into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def encode(value: Any) -> bytes:
    """Encode deterministic JSON with a final newline."""
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def load(path: Path) -> Any:
    """Read JSON evidence without modifying it."""
    return json.loads(path.read_bytes())


def write_new(path: Path, data: bytes) -> None:
    """Refuse to overwrite an existing evidence file."""
    with path.open("xb") as stream:
        stream.write(data)


def safe_archive_path(value: str) -> str:
    """Require a portable relative ZIP member name."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"Unsafe archive path: {value!r}")
    if value.startswith("/") or any(ord(char) < 32 for char in value):
        raise ValueError(f"Unsafe archive path: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"Unsafe archive path: {value!r}")
    return PurePosixPath(value).as_posix()


def contained(path: Path, root: Path) -> Path:
    """Resolve a path while requiring it to remain inside a declared source tree."""
    resolved = path.resolve(strict=True)
    resolved.relative_to(root.resolve(strict=True))
    return resolved


def safe_link_target(archive_path: str, target: str, archive_root: str) -> str:
    """Permit only relative links to another member of the same declared tree."""
    if not target or target.startswith("/") or "\\" in target or ":" in target:
        raise ValueError(f"Unsafe symlink target: {target!r}")
    destination = safe_archive_path(posixpath.normpath(posixpath.join(posixpath.dirname(archive_path), target)))
    if archive_root and not (destination == archive_root or destination.startswith(archive_root + "/")):
        raise ValueError(f"Symlink escapes its declared archive tree: {archive_path}")
    return destination


def regular_bytes(path: Path) -> bytes:
    """Read a regular, non-symlink source."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required regular file is absent or linked: {path}")
    return path.read_bytes()


def exclusion(relative: str, is_directory: bool, policy: dict[str, Any]) -> str | None:
    """Return an explicit omission reason, never a silent include/exclude decision."""
    parts = PurePosixPath(relative).parts
    name = parts[-1]
    if any(part in policy["exclusion_policy"]["directories"] for part in parts):
        return "development cache, repository metadata or virtual environment"
    if name in {"chrome", "chromedriver", "chromium", "chrome-wrapper"} or any(
        part.startswith(("chrome-linux", "chromium-", "chrome-headless-shell", ".playwright")) for part in parts
    ):
        return "browser runtime intentionally excluded; preserve QA JSON only"
    if name.endswith((".pyc", ".pyo", ".swp", ".tmp")):
        return "temporary interpreter/editor output"
    if name == ".env" or name.startswith(".env.") and name not in {".env.sample", ".env.example"}:
        raise ValueError("Unapproved environment/credential file encountered; packaging stopped")
    image = name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
    if image and (
        relative.startswith("demo/evidence/")
        or any(part in {"qa", "qa-pages", "rendered-pages", "pdf-pages", "screenshots"} for part in parts)
    ):
        return "internal browser/PDF visual QA image; not a user deliverable"
    if relative.startswith("paper/") and (
        name.endswith((".aux", ".toc", ".out", ".log", ".fls", ".fdb_latexmk", ".synctex.gz", ".xdv"))
        or name.startswith("build")
        and name.endswith((".stdout", ".stderr", ".txt"))
    ):
        return "temporary LaTeX build output; final PDF/source/figures retained"
    if relative.startswith("publication/") and (
        name.startswith(PACKAGING_PREFIXES) or name.endswith((".zip", ".zip.sha256"))
    ):
        return "generated packaging metadata or archive; emitted separately to avoid self-reference"
    if is_directory and name == "pydeps":
        return "development Python tooling environment, not a runtime dependency"
    return None


def entry_for(path: Path, archive_path: str, source_root: Path, archive_root: str, role: str) -> dict[str, Any]:
    """Bind one file or contained symlink to its exact original bytes."""
    archive_path = safe_archive_path(archive_path)
    metadata = path.lstat()
    record: dict[str, Any] = {"archive_path": archive_path, "source_path": str(path.absolute()), "role": role}
    if stat.S_ISLNK(metadata.st_mode):
        target = os.readlink(path)
        destination = safe_link_target(archive_path, target, archive_root)
        if not contained(path, source_root).is_file():
            raise ValueError(f"Symlink does not resolve to a regular dependency: {path}")
        data = target.encode("utf-8")
        record.update(
            type="symlink",
            bytes=len(data),
            sha256=sha256(data),
            target=target,
            destination=destination,
            archive_root=archive_root,
        )
    elif stat.S_ISREG(metadata.st_mode):
        contained(path, source_root)
        record.update(
            type="file", bytes=metadata.st_size, sha256=file_sha256(path), executable=bool(metadata.st_mode & 0o111)
        )
    else:
        raise ValueError(f"Special files cannot enter the companion: {path}")
    return record


def collect_tree(
    root: Path, archive_root: str, policy: dict[str, Any], role: str, apply_exclusions: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inventory a source tree without following directory symlinks."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Required dependency tree missing or linked: {root}")
    entries: list[dict[str, Any]] = []
    omissions: list[dict[str, Any]] = []

    def walk(directory: Path) -> None:
        for item in sorted(directory.iterdir()):
            rel = item.relative_to(root).as_posix()
            is_directory = item.is_dir() and not item.is_symlink()
            reason = exclusion(rel, is_directory, policy) if apply_exclusions else None
            if reason:
                omitted: dict[str, Any] = {
                    "path": f"{archive_root}/{rel}",
                    "reason": reason,
                    "type": "directory" if is_directory else "file",
                }
                if item.is_file() and not item.is_symlink():
                    omitted.update(bytes=item.stat().st_size, sha256=file_sha256(item))
                omissions.append(omitted)
            elif is_directory:
                walk(item)
            else:
                entries.append(entry_for(item, f"{archive_root}/{rel}", root, archive_root, role))

    walk(root)
    return entries, omissions


def validate_frozen_files(study: Path, repository: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Check active exact-source records; preserve all historical records without treating them as current."""
    results = []
    for name in [policy["primary_freeze"], *policy["additional_active_freezes"]]:
        path = study / name
        data = regular_bytes(path)
        record = json.loads(data)
        files = record.get("files", record.get("sourceFiles"))
        if not isinstance(files, list) or not files:
            raise ValueError(f"Active source freeze has no file closure: {name}")
        for item in files:
            source = study / item["path"]
            contained(source, repository)
            content = regular_bytes(source)
            if sha256(content) != item["sha256"] or len(content) != item["bytes"]:
                raise ValueError(f"Active frozen source drift: {name}: {item['path']}")
        results.append({"path": name, "sha256": sha256(data), "checked_files": len(files)})
    return results


def review_exclusion(entry: dict[str, Any]) -> str | None:
    """Keep full-companion binaries/archives separate from the light review publication list."""
    name = entry["archive_path"].lower()
    if name.endswith((".jar", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
        return "tool/source archive retained in full companion only"
    if entry["type"] == "file":
        with Path(entry["source_path"]).open("rb") as stream:
            magic = stream.read(4)
        if magic.startswith((b"\x7fELF", b"MZ")) or magic in {
            b"\xcf\xfa\xed\xfe",
            b"\xfe\xed\xfa\xcf",
            b"\xca\xfe\xba\xbe",
        }:
            return "native executable retained in full companion only"
    return None


def plan_package(
    repository: Path,
    study: Path,
    policy: dict[str, Any],
    gtfs_jar: Path | None = None,
    converter_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a complete inventory and a separate review list; execute no job or archive build."""
    repository = repository.resolve(strict=True)
    study = study.resolve(strict=True)
    prefix = study.relative_to(repository).as_posix()
    if prefix != policy["study_path"]:
        raise ValueError("Study must retain the declared repository-shaped path")
    checked = validate_frozen_files(study, repository, policy)
    for name in policy["required_deliverables"]:
        regular_bytes(study / name)
    entries, omissions = collect_tree(study, prefix, policy, "complete-study", True)

    freeze = load(study / policy["primary_freeze"])
    upstream = [
        str((study / item["path"]).resolve().relative_to(repository))
        for item in freeze["files"]
        if item["path"].startswith("../")
    ]
    for name in sorted(set(upstream + policy["upstream_additions"])):
        source = repository / name
        entries.append(entry_for(source, name, repository, "", "upstream-runtime-or-license"))
    entries.append(
        entry_for(
            study / "publication/PACKAGING.md", "COMPANION-README.md", study, "", "portable-companion-instructions"
        )
    )

    gtfs = policy["external_tools"]["gtfs_validator"]
    bundled_jar = repository / gtfs["archive_path"]
    jar = gtfs_jar or (
        bundled_jar if bundled_jar.is_file() else repository.parent / gtfs["original_relative_to_repository_parent"]
    )
    jar_binding = load(study / gtfs["binding"])["inputs"][gtfs["binding_key"]]
    if (
        not jar.is_file()
        or jar.is_symlink()
        or file_sha256(jar) != jar_binding["sha256"]
        or jar.stat().st_size != jar_binding["bytes"]
    ):
        raise ValueError("Required original GTFS validator JAR missing or mismatched")
    regular_bytes(study / gtfs["upstream_license"])
    entries.append(entry_for(jar, gtfs["archive_path"], jar.parent, prefix, "external-gtfs-validator"))

    converter = policy["external_tools"]["swagger2openapi"]
    bundled_converter = repository / converter["archive_root"]
    tools = converter_root or (
        bundled_converter
        if bundled_converter.is_dir()
        else repository.parent / converter["original_relative_to_repository_parent"]
    )
    tools = tools.resolve(strict=True)
    for filename, expected in [
        ("package.json", converter["package_sha256"]),
        ("package-lock.json", converter["lock_sha256"]),
    ]:
        if sha256(regular_bytes(tools / filename)) != expected:
            raise ValueError(f"Pinned converter {filename} drift")
        entries.append(
            entry_for(
                tools / filename,
                f"{converter['archive_root']}/{filename}",
                tools,
                converter["archive_root"],
                "external-converter",
            )
        )
    node_entries, _ = collect_tree(
        tools / "node_modules", f"{converter['archive_root']}/node_modules", policy, "external-converter", False
    )
    bindings = load(study / converter["binding"])
    expected_node_paths = set()
    for binding in bindings:
        old_path = binding["path"]
        if "/node_modules/" not in old_path:
            continue
        suffix = "node_modules/" + old_path.split("/node_modules/", 1)[1]
        expected_node_paths.add(f"{converter['archive_root']}/{suffix}")
        source = tools / suffix
        if "symlinkTarget" in binding:
            if not source.is_symlink() or os.readlink(source) != binding["symlinkTarget"]:
                raise ValueError(f"Pinned converter symlink drift: {suffix}")
        elif sha256(regular_bytes(source)) != binding["sha256"]:
            raise ValueError(f"Pinned converter dependency drift: {suffix}")
    if expected_node_paths != {item["archive_path"] for item in node_entries}:
        raise ValueError("Installed converter closure has missing or unrecorded files")
    entries.extend(node_entries)

    unique: dict[str, dict[str, Any]] = {}
    folded: dict[str, str] = {}
    for entry in entries:
        name = entry["archive_path"]
        prior = unique.get(name)
        if prior and (prior["sha256"], prior["type"]) != (entry["sha256"], entry["type"]):
            raise ValueError(f"Conflicting archive mapping: {name}")
        if name.casefold() in folded and folded[name.casefold()] != name:
            raise ValueError(f"Case-insensitive extraction collision: {name}")
        unique.setdefault(name, entry)
        folded[name.casefold()] = name
    entries = [unique[name] for name in sorted(unique)]
    for entry in entries:
        if entry["type"] == "symlink" and entry["destination"] not in unique:
            raise ValueError(f"Symlink dependency was omitted: {entry['archive_path']}")
    total = sum(entry["bytes"] for entry in entries)
    if (
        len(entries) > policy["limits"]["maximum_payload_files"]
        or total > policy["limits"]["maximum_uncompressed_bytes"]
    ):
        raise ValueError("Declared package budget exceeded")

    license_records = []
    lock = load(tools / "package-lock.json")
    for package_path in sorted(lock["packages"]):
        if not package_path:
            continue
        package_root = tools / package_path
        package = load(package_root / "package.json")
        license_files = [
            path.name
            for path in sorted(package_root.iterdir())
            if path.is_file() and path.name.lower().startswith(("license", "notice", "copying"))
        ]
        license_records.append(
            {
                "package": package.get("name"),
                "version": package.get("version"),
                "declared_license": package.get("license"),
                "license_files": license_files,
                "standalone_license_text_present": bool(license_files),
                "package_json_archive_path": f"{converter['archive_root']}/{package_path}/package.json",
            }
        )
    plan = {
        "schema": "agi-alpha.work-discovery.companion-manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PLANNED_NOT_A_RELEASE",
        "repository_root_at_capture": str(repository),
        "study_path": prefix,
        "policy_sha256": sha256(encode(policy)),
        "limits": policy["limits"],
        "payload_files": len(entries),
        "payload_bytes": total,
        "entries": entries,
        "omissions": omissions,
        "active_source_checks": checked,
        "external_mappings": [
            {"original": str(jar.absolute()), "archive": gtfs["archive_path"], "sha256": jar_binding["sha256"]},
            {
                "original": str(tools),
                "archive": converter["archive_root"],
                "note": "package.json, package-lock.json and exact node_modules closure only; pydeps excluded",
            },
        ],
        "converter_licenses": license_records,
        "prerequisites": policy["installed_prerequisites"],
        "metadata_scope": {
            MANIFEST_NAME: "This manifest lists every payload member but not its own bytes.",
            RELEASE_NAME: "A separate local release record binds this exact manifest and final PDF/demo; whole ZIP SHA binds both.",
        },
        "provenance_rule": "Original commands and absolute paths remain unchanged. Portable mappings are additive documentation.",
        "qa_omission_note": "Internal browser screenshots/PDF inspection images are intentionally absent. Their paths/hashes and JSON QA remain.",
        "no_execution": "Planning only hashes public artifacts; it does not run the service, model, browser, validator or tests.",
    }
    allowed, review_omissions = [], []
    for entry in entries:
        reason = review_exclusion(entry)
        if reason:
            review_omissions.append({"path": entry["archive_path"], "bytes": entry["bytes"], "reason": reason})
        else:
            allowed.append(
                {
                    "path": entry["archive_path"],
                    "source_path": entry["source_path"],
                    "sha256": entry["sha256"],
                    "bytes": entry["bytes"],
                    "type": entry["type"],
                    "repository_file": Path(entry["source_path"]).is_relative_to(repository),
                }
            )
    review = {
        "schema": "agi-alpha.work-discovery.review-publication-files.v1",
        "full_plan_sha256": sha256(encode(plan)),
        "review_files": allowed,
        "full_companion_only": review_omissions,
        "repository_paths": [entry["path"] for entry in allowed if entry["repository_file"]],
        "note": "Review list only; no files are published or copied. External converter mappings are archive payload, not existing repository paths.",
    }
    return plan, review


def current_payload_bytes(entry: dict[str, Any]) -> bytes:
    """Read and revalidate a planned payload member immediately before packaging."""
    source = Path(entry["source_path"])
    if entry["type"] == "symlink":
        target = entry["target"]
        if not isinstance(target, str):
            raise ValueError("A planned symlink target must be text")
        if not source.is_symlink() or os.readlink(source) != target:
            raise ValueError(f"Planned symlink changed: {source}")
        data = target.encode("utf-8")
    else:
        data = regular_bytes(source)
    if len(data) != entry["bytes"] or sha256(data) != entry["sha256"]:
        raise ValueError(f"Planned file changed: {source}")
    return data


def validate_release(plan: dict[str, Any], plan_bytes: bytes, release: dict[str, Any]) -> None:
    """Require an explicit root release record for these exact finalized artifacts."""
    if (
        release.get("schema") != "agi-alpha.work-discovery.companion-release.v1"
        or release.get("status") != "ROOT_RELEASED_FOR_ARCHIVE_BUILD"
        or release.get("plan_sha256") != sha256(plan_bytes)
    ):
        raise ValueError("An exact root release record is required before the final ZIP")
    files = {entry["archive_path"]: entry for entry in plan["entries"]}
    required = {f"{plan['study_path']}/paper/main.pdf", f"{plan['study_path']}/demo/index.html"}
    final = release.get("final_artifacts", [])
    if {item.get("path") for item in final} != required or len(final) != len(required):
        raise ValueError("Release must bind the final PDF and demo exactly once")
    for item in final:
        if item["sha256"] != files[item["path"]]["sha256"]:
            raise ValueError("Final PDF/demo differs from the root release")


def build_package(plan_path: Path, release_path: Path, output: Path) -> dict[str, Any]:
    """Build only a released plan, preserving all source bytes and refusing overwrites."""
    plan_bytes, release_bytes = regular_bytes(plan_path), regular_bytes(release_path)
    plan, release = json.loads(plan_bytes), json.loads(release_bytes)
    validate_release(plan, plan_bytes, release)
    if plan.get("schema") != "agi-alpha.work-discovery.companion-manifest.v1":
        raise ValueError("Unknown companion manifest")
    if output.suffix != ".zip":
        raise ValueError("Final companion output must use .zip")
    # Validate the entire closure before creating an output; any subsequent drift also fails below.
    for entry in plan["entries"]:
        current_payload_bytes(entry)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for entry in plan["entries"]:
            data = current_payload_bytes(entry)
            info = zipfile.ZipInfo(safe_archive_path(entry["archive_path"]), ZIP_DATE)
            info.create_system = 3
            if entry["type"] == "symlink":
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            else:
                info.external_attr = (stat.S_IFREG | (0o755 if entry.get("executable") else 0o644)) << 16
            info.compress_type = (
                zipfile.ZIP_STORED if info.filename.lower().endswith((".zip", ".jar", ".gz")) else zipfile.ZIP_DEFLATED
            )
            archive.writestr(info, data)
        for name, data in [(MANIFEST_NAME, plan_bytes), (RELEASE_NAME, release_bytes)]:
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.create_system, info.external_attr, info.compress_type = (
                3,
                (stat.S_IFREG | 0o644) << 16,
                zipfile.ZIP_DEFLATED,
            )
            archive.writestr(info, data)
    result = verify_package(output)
    result.update(
        archive=str(output.absolute()), archive_bytes=output.stat().st_size, archive_sha256=file_sha256(output)
    )
    return result


def verify_package(path: Path) -> dict[str, Any]:
    """Verify the archive in place without extracting paths or executing included software."""
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [safe_archive_path(info.filename) for info in members]
        if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
            raise ValueError("Duplicate or extraction-colliding ZIP entries")
        plan_bytes = archive.read(MANIFEST_NAME)
        plan = json.loads(plan_bytes)
        release = json.loads(archive.read(RELEASE_NAME))
        validate_release(plan, plan_bytes, release)
        expected = {entry["archive_path"] for entry in plan["entries"]} | {MANIFEST_NAME, RELEASE_NAME}
        if set(names) != expected:
            raise ValueError("Archive has missing or unmanifested payload")
        if (
            len(plan["entries"]) > plan["limits"]["maximum_payload_files"]
            or sum(info.file_size for info in members) > plan["limits"]["maximum_uncompressed_bytes"] + 10_000_000
        ):
            raise ValueError("Archive budget exceeded")
        for entry in plan["entries"]:
            info = archive.getinfo(entry["archive_path"])
            data = archive.read(info)
            if len(data) != entry["bytes"] or sha256(data) != entry["sha256"]:
                raise ValueError(f"Archive payload mismatch: {entry['archive_path']}")
            mode = info.external_attr >> 16
            if entry["type"] == "symlink":
                if (
                    not stat.S_ISLNK(mode)
                    or data.decode("utf-8") != entry["target"]
                    or entry["destination"] not in expected
                ):
                    raise ValueError("Invalid archived symlink")
                if (
                    safe_link_target(entry["archive_path"], entry["target"], entry["archive_root"])
                    != entry["destination"]
                ):
                    raise ValueError("Archived symlink destination does not reconcile")
            elif not stat.S_ISREG(mode):
                raise ValueError("Unexpected archive entry type")
        return {
            "schema": "agi-alpha.work-discovery.companion-verification.v1",
            "status": "PASS",
            "payload_files": len(plan["entries"]),
            "payload_bytes": plan["payload_bytes"],
            "plan_sha256": sha256(plan_bytes),
            "release_sha256": sha256(archive.read(RELEASE_NAME)),
            "scope": "Complete byte/ZIP-path verification only; no replay, live authentication or financial authority",
        }


def main() -> None:
    """Expose planning separately from the final released build."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan")
    planning.add_argument("--plan", type=Path, required=True)
    planning.add_argument("--review", type=Path, required=True)
    planning.add_argument("--repository", type=Path, default=REPOSITORY)
    planning.add_argument("--gtfs-jar", type=Path)
    planning.add_argument("--converter-root", type=Path)
    building = commands.add_parser("build")
    building.add_argument("--plan", type=Path, required=True)
    building.add_argument("--release", type=Path, required=True)
    building.add_argument("--output", type=Path, required=True)
    building.add_argument("--receipt", type=Path, required=True)
    verification = commands.add_parser("verify")
    verification.add_argument("archive", type=Path)
    verification.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.command == "plan":
        policy = load(STUDY / "publication/package-policy.json")
        study = args.repository / policy["study_path"]
        plan, review = plan_package(args.repository, study, policy, args.gtfs_jar, args.converter_root)
        write_new(args.plan, encode(plan))
        write_new(args.review, encode(review))
        result = {
            "status": "PLANNED_NO_ARCHIVE_CREATED",
            "payload_files": plan["payload_files"],
            "payload_bytes": plan["payload_bytes"],
            "plan_sha256": sha256(encode(plan)),
            "review_files": len(review["review_files"]),
            "omission_records": len(plan["omissions"]),
        }
    elif args.command == "build":
        result = build_package(args.plan, args.release, args.output)
        write_new(args.receipt, encode(result))
    else:
        result = verify_package(args.archive)
        result.update(archive_sha256=file_sha256(args.archive), archive_bytes=args.archive.stat().st_size)
        if args.receipt:
            write_new(args.receipt, encode(result))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
