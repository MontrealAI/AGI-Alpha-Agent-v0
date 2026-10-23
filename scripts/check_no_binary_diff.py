#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail if the Git diff includes binary file changes."""

from __future__ import annotations

import json
import hashlib
import os
import re
import stat
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BINARY_EXTENSIONS = {
    ".wasm",
    ".zip",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".pdf",
    ".ico",
    ".mp3",
    ".mp4",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}

# The repository owner supplied this exact latest manuscript for publication.
# Keep the general binary gate; the exception admits only these immutable bytes.
AUTHORIZED_MANUSCRIPT = {
    "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.pdf": (
        "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a"
    ),
}

AUTHORIZED_MANUSCRIPT.update(
    {
        "docs/manuscript/figures_png/figure10_frontier_synthesis_lattice.png": (
            "b929e1186bbeeb3cf2e4b3ed2ef78b8b5401aefb1007785709c23e9d9bf7d1a0"
        ),
        "docs/manuscript/figures_png/figure11_sovereign_invention_stack.png": (
            "5be3a36cc41df60d3d73919d3951c636b553873c6fcf435eff3840a6e52a6c55"
        ),
        "docs/manuscript/figures_png/figure12_build_test_compression_loop.png": (
            "c578d12b42450a8a8d56811c2f33ad06239891313ebc711a74db71770a8cbc11"
        ),
        "docs/manuscript/figures_png/figure13_distributional_safety_envelope.png": (
            "2b04acd0663fa94f7f60989397a8ffa3bea3b8ff740606a8ff87c2ae7cd5b56b"
        ),
        "docs/manuscript/figures_png/figure14_model_vs_organization_substrate.png": (
            "f6dba956e7fcf5ced793f5fb3086e6420a1a349add9bb06de534d4e32ed66302"
        ),
        "docs/manuscript/figures_png/figure15_real_task_demonstration_harness.png": (
            "f249fe0437b1d4ed5f24d14deb634f319dd056194b4f71fcb98df01c5958c585"
        ),
        "docs/manuscript/figures_png/figure16_mvp_reference_stack.png": (
            "526cbb07222e748ea0924f0c1eae59f703328b73987efd637ce3b13835c21d52"
        ),
        "docs/manuscript/figures_png/figure17_generalized_validated_search.png": (
            "fdf3723080a431ae66374d7e84c64e9a3d41c927462959bc67957086a540f7ee"
        ),
        "docs/manuscript/figures_png/figure18_learned_coordination_substrates.png": (
            "e261ad436e17e660c69de84ed163edef6307b86ac836cd4ebb4ed6176c0c1b02"
        ),
        "docs/manuscript/figures_png/figure19_experience_grounded_machine_labor.png": (
            "2a1fceca43ca4aa420b9d697212e3bcd10c78aad53f27da04a5d485c00706b9e"
        ),
        "docs/manuscript/figures_png/figure1_system_architecture.png": (
            "ddc5bc6e9b8bce2dd272fa8c195a364ebc5af8df32e3d42ffa3caaa28cc0d770"
        ),
        "docs/manuscript/figures_png/figure20_sovereign_experience_control_plane.png": (
            "b9a2f4490e0b863a4c2c5f09bc33ff005a14459effd06d754915efd0ebfb2d82"
        ),
        "docs/manuscript/figures_png/figure21_proofzero_planning_layer.png": (
            "c3bc1816a946f63fa84f86d2ab1a0a49d1a9e837cd357eda84fa3259876641bf"
        ),
        "docs/manuscript/figures_png/figure22_sovereign_evolutionary_agent_economy.png": (
            "d8c8b17405c66ed702d9deffbedede3c4a7ce78f35e1c27c9a060915e705446f"
        ),
        "docs/manuscript/figures_png/figure23_civilizational_value_to_energy_flywheel.png": (
            "efff7d856465cd191803a12c5d771cda3334eb2b6d51091be609e79683bfca98"
        ),
        "docs/manuscript/figures_png/figure24_agiet_institutional_stack.png": (
            "d43bb2df3dc0bc89af76d615370eb00e39583c8df562204c829fb9795de1e742"
        ),
        "docs/manuscript/figures_png/figure25_agiet_proof_settlement_chain.png": (
            "52cd355e03271b5985d217d9c909ed75fc068ce39d31931b1fb53a5c4709f0f3"
        ),
        "docs/manuscript/figures_png/figure26_agiet_namespace_layer.png": (
            "feaf0a9542325bff7f97bd50d6dc12815993279717c61eaecbe6824a141b69c4"
        ),
        "docs/manuscript/figures_png/figure27_proof_gated_aiga_work_engine.png": (
            "f1fa20e1cca3fde77cd395270a2a0779f0d9eff7361a41ccb0408db27066b070"
        ),
        "docs/manuscript/figures_png/figure28_montrealai_evidence_corpus.png": (
            "4bedb53d6359fa86866c2ce75f31422de0471893e447a136690c3ecf52967e60"
        ),
        "docs/manuscript/figures_png/figure29_market_governed_invention_foundry.png": (
            "abe03d17d45a1f507432b465c86308d839aea908e34de471de414554790ec673"
        ),
        "docs/manuscript/figures_png/figure2_inflow_dynamics.png": (
            "47856d03f59c54352bd27334d8244f367d1b5378bc2def4168f6ef3ed30cc952"
        ),
        "docs/manuscript/figures_png/figure30_rsi_control_plane.png": (
            "1fec5d0834f7adccb574c746cf6d9078a6466061f356dea6fe41be7efea9c422"
        ),
        "docs/manuscript/figures_png/figure31_evidence_factory_to_sovereign_organs.png": (
            "73ece92eb446cc570269490d8ff7fe7c278a89869cda2981b0ecbb230e43dc04"
        ),
        "docs/manuscript/figures_png/figure32_cybersecurity_sovereign_immune_organ.png": (
            "959c490adfc6a634b9eb6346bf1ea210b43540047c87a996edb292adb468ed00"
        ),
        "docs/manuscript/figures_png/figure3_free_energy_landscape.png": (
            "074cf7360821214afa7c851bd655f0f898ec1beee1403ce00ad67312657df5d6"
        ),
        "docs/manuscript/figures_png/figure4_entropy_band.png": (
            "1828f5c11a1e1172d143b87840cb9278e22d16d6462f6a07b1d5ab17986ef812"
        ),
        "docs/manuscript/figures_png/figure5_hamiltonian_matrix.png": (
            "3fe34968b1dd2cc2a8d0e9f48bf85fb0e0f4aec6347a2709ac018be5edcc1443"
        ),
        "docs/manuscript/figures_png/figure6_risk_frontier.png": (
            "df1abbdd368418c46bee8d6035dfeb3e43a5b28d5fb678ed0895cb064fb2c119"
        ),
        "docs/manuscript/figures_png/figure7_validator_loop.png": (
            "b9a67ac0f2a7c58aa7a4808b307b13a2ae9c44f023dc021f7866227eeff0d703"
        ),
        "docs/manuscript/figures_png/figure9_doctrine_lattice.png": (
            "49156e24a8148b4d5448a3899939f1e5a7bcc68474bf8b7da5331933b13a08af"
        ),
    }
)


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def _git_root() -> Path:
    result = _run("git", "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip())


def _load_event_base_sha() -> str | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None
    try:
        data = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    base = data.get("pull_request", {}).get("base", {}).get("sha")
    return base or None


def _ensure_origin_main() -> str | None:
    try:
        _run("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main")
        return "origin/main"
    except subprocess.CalledProcessError:
        pass
    try:
        remotes = _run("git", "remote").stdout.splitlines()
    except subprocess.CalledProcessError:
        return None
    if "origin" in remotes:
        try:
            _run("git", "fetch", "origin", "main", "--quiet")
        except subprocess.CalledProcessError:
            return None
        try:
            _run("git", "show-ref", "--verify", "--quiet", "refs/remotes/origin/main")
            return "origin/main"
        except subprocess.CalledProcessError:
            return None
    return None


def _verify_ref(ref: str) -> bool:
    try:
        _run("git", "rev-parse", "--verify", f"{ref}^{{commit}}")
        return True
    except subprocess.CalledProcessError:
        return False


def _base_ref() -> str:
    base_sha = _load_event_base_sha()
    if base_sha and _verify_ref(base_sha):
        return base_sha
    origin_main = _ensure_origin_main()
    if origin_main and _verify_ref(origin_main):
        return origin_main
    for candidate in ("main", "master"):
        if _verify_ref(candidate):
            return candidate
    return "HEAD"


def _iter_changed_paths(base_ref: str) -> list[str]:
    try:
        result = _run("git", "diff", "--name-status", f"{base_ref}...HEAD")
    except subprocess.CalledProcessError:
        result = _run("git", "diff", "--name-status", "HEAD")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            paths.extend(parts[1:])
        else:
            paths.extend(parts[1:])
    return [p for p in paths if p]


def _has_binary_diff(base_ref: str) -> list[str]:
    try:
        result = _run("git", "diff", "--numstat", f"{base_ref}...HEAD")
    except subprocess.CalledProcessError:
        result = _run("git", "diff", "--numstat", "HEAD")
    binaries = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0] == "-" and parts[1] == "-":
            binaries.append(parts[2])
    return binaries


def _matches_binary_extension(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in BINARY_EXTENSIONS


REPORT_PACK_SHA256 = "d29e9951bd2d04c05a4520d885e5ca8f716e280b715445dea6f6a193b537f27b"
AUTHORIZED_REPORT_PACK = {"docs/reports/computer-use-study/report-pack.zip": REPORT_PACK_SHA256}

# Owner-supplied flagship art; this exception admits only these exact optimized bytes.
AUTHORIZED_FLAGSHIP_ARTWORK = {
    "docs/assets/successor-alpha/institution.webp": "0e3829bf7615d3658bd8bd0c7e0f7b788d7e1fc383ac86019de5c6dea122ee06",
}


ENTERPRISE_MANIFEST = "scripts/data/autonomous_enterprise_evidence.json"
ENTERPRISE_MANIFEST_SHA256 = "cbb2744071352b4204500b43e849b9d8b6df7b1f522d26f7b4d5e48fc9d67118"
ENTERPRISE_PREFIX = "evidence/autonomous-enterprises-20261022/"


def _regular_path(root: Path, name: str) -> Path:
    path = root
    for part in PurePosixPath(name).parts:
        path /= part
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"Evidence symlink is not admitted: {name}")
    if not stat.S_ISREG(mode):
        raise ValueError(f"Evidence must be a regular file: {name}")
    return path


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate evidence manifest key: {key}")
        result[key] = value
    return result


def _load_enterprise_manifest(root: Path) -> dict[str, dict[str, Any]]:
    raw = _regular_path(root, ENTERPRISE_MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ENTERPRISE_MANIFEST_SHA256:
        raise ValueError("Enterprise evidence manifest differs from its reviewed bytes")
    data = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(data, dict) or set(data) != {"schema", "source_commit", "source_tree", "files"}:
        raise ValueError("Invalid enterprise evidence manifest schema")
    if (
        data["schema"] != "autonomous-enterprise-evidence/v1"
        or data["source_commit"] != "91298676775e2958f010906a96edfb176f5b1709"
        or data["source_tree"] != "8d1972503af365b9a70770ee7e1d8e711ba5330f"
        or not isinstance(data["files"], list)
        or len(data["files"]) != 16
    ):
        raise ValueError("Invalid enterprise evidence source or inventory")
    rows: dict[str, dict[str, Any]] = {}
    for row in data["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "size", "sha256", "git_blob", "media_type"}:
            raise ValueError("Invalid enterprise evidence record")
        name = row["path"]
        if (
            not isinstance(name, str)
            or not name.startswith(ENTERPRISE_PREFIX)
            or "\\" in name
            or "\x00" in name
            or PurePosixPath(name).as_posix() != name
            or ".." in PurePosixPath(name).parts
            or name in rows
            or not isinstance(row["size"], int)
            or isinstance(row["size"], bool)
            or row["size"] <= 0
            or not isinstance(row["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
            or not isinstance(row["git_blob"], str)
            or re.fullmatch(r"[0-9a-f]{40}", row["git_blob"]) is None
            or not isinstance(row["media_type"], str)
            or (PurePosixPath(name).suffix, row["media_type"])
            not in {(".png", "image/png"), (".zip", "application/zip")}
        ):
            raise ValueError("Invalid enterprise evidence path, identity or media type")
        rows[name] = row
    if sum(row["size"] for row in rows.values()) != 13_510_902:
        raise ValueError("Invalid enterprise evidence total byte length")
    return rows


def _valid_png(raw: bytes) -> bool:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset, chunks, image_data = 8, 0, False
    while offset + 12 <= len(raw):
        size = int.from_bytes(raw[offset : offset + 4], "big")
        kind = raw[offset + 4 : offset + 8]
        end = offset + 8 + size
        if end + 4 > len(raw) or not re.fullmatch(b"[A-Za-z]{4}", kind):
            return False
        body = raw[offset + 8 : end]
        if zlib.crc32(kind + body) != int.from_bytes(raw[end : end + 4], "big"):
            return False
        if chunks == 0:
            if kind != b"IHDR" or size != 13:
                return False
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if (
                not 0 < width < 2**31
                or not 0 < height < 2**31
                or depth not in depths.get(color, set())
                or compression != 0
                or filtering != 0
                or interlace not in {0, 1}
            ):
                return False
        elif kind == b"IHDR":
            return False
        if kind == b"IDAT":
            image_data = image_data or size > 0
        if kind == b"IEND":
            return size == 0 and image_data and end + 4 == len(raw)
        offset, chunks = end + 4, chunks + 1
    return False


def _valid_zip(path: Path, raw: bytes) -> bool:
    if not raw.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names: set[str] = set()
            for member in members:
                name = member.filename.rstrip("/")
                parts = PurePosixPath(name)
                if (
                    not name
                    or parts.is_absolute()
                    or parts.as_posix() != name
                    or ".." in parts.parts
                    or "\\" in name
                    or "\x00" in member.orig_filename
                    or name in names
                    or stat.S_ISLNK(member.external_attr >> 16)
                    or member.flag_bits & 1
                    or member.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                ):
                    return False
                names.add(name)
            return bool(members)
    except (OSError, ValueError, zipfile.BadZipFile):
        return False


def _enterprise_admissions(root: Path, paths: list[str]) -> set[str]:
    candidates = {name for name in paths if name.startswith(ENTERPRISE_PREFIX)}
    if not candidates:
        return set()
    manifest = _load_enterprise_manifest(root)
    admitted: set[str] = set()
    for name in candidates:
        row = manifest.get(name)
        if row is None:
            continue
        try:
            path = _regular_path(root, name)
            if path.stat().st_size != row["size"]:
                continue
            raw = path.read_bytes()
            if (
                len(raw) != row["size"]
                or hashlib.sha256(raw).hexdigest() != row["sha256"]
                or hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != row["git_blob"]
            ):
                continue
            valid_type = _valid_png(raw) if row["media_type"] == "image/png" else _valid_zip(path, raw)
            if valid_type:
                admitted.add(name)
        except (OSError, ValueError):
            continue
    return admitted


def main() -> int:
    root = _git_root()
    base_ref = _base_ref()
    changed_paths = _iter_changed_paths(base_ref)
    binary_paths = [path for path in changed_paths if _matches_binary_extension(path)]
    binary_paths.extend(_has_binary_diff(base_ref))
    authorized = AUTHORIZED_MANUSCRIPT | AUTHORIZED_REPORT_PACK | AUTHORIZED_FLAGSHIP_ARTWORK
    # Only exact validated catalog bytes qualify; this is not a PDF suffix exclusion.
    from scripts.research_papers import (
        CATALOG,
        asset_hashes,
        load_catalog,
        parse_catalog,
        preserve_catalog,
        verify_files,
    )

    catalog = load_catalog(Path.cwd())
    verify_files(Path.cwd(), catalog, pdf_checks=False)
    # Full/mixed qualification cannot silently rewrite previously catalogued originals.
    previous = _run("git", "show", f"{base_ref}:{CATALOG}", check=False)
    if previous.returncode == 0:
        preserve_catalog(parse_catalog(previous.stdout.encode()), catalog)
    authorized |= asset_hashes(catalog)
    try:
        admitted_evidence = _enterprise_admissions(root, binary_paths)
    except (OSError, ValueError) as exc:
        print(f"ERROR: Enterprise binary admission failed: {exc}")
        return 1
    binary_paths = sorted(
        {
            path
            for path in binary_paths
            if path not in admitted_evidence
            and (
                path not in authorized
                or not Path(path).is_file()
                or hashlib.sha256(Path(path).read_bytes()).hexdigest() != authorized[path]
            )
        }
    )
    if binary_paths:
        joined = "\n".join(f"  - {path}" for path in binary_paths)
        print("ERROR: Binary files changed in diff:")
        print(joined)
        return 1
    print("No binary changes detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
