#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail if the Git diff includes binary file changes."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path


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
    "docs/manuscript/AGI_ALPHA_Unified_Publication_Final.pdf": "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a",
}

AUTHORIZED_MANUSCRIPT.update(
    {
        "docs/manuscript/figures_png/figure10_frontier_synthesis_lattice.png": "b929e1186bbeeb3cf2e4b3ed2ef78b8b5401aefb1007785709c23e9d9bf7d1a0",
        "docs/manuscript/figures_png/figure11_sovereign_invention_stack.png": "5be3a36cc41df60d3d73919d3951c636b553873c6fcf435eff3840a6e52a6c55",
        "docs/manuscript/figures_png/figure12_build_test_compression_loop.png": "c578d12b42450a8a8d56811c2f33ad06239891313ebc711a74db71770a8cbc11",
        "docs/manuscript/figures_png/figure13_distributional_safety_envelope.png": "2b04acd0663fa94f7f60989397a8ffa3bea3b8ff740606a8ff87c2ae7cd5b56b",
        "docs/manuscript/figures_png/figure14_model_vs_organization_substrate.png": "f6dba956e7fcf5ced793f5fb3086e6420a1a349add9bb06de534d4e32ed66302",
        "docs/manuscript/figures_png/figure15_real_task_demonstration_harness.png": "f249fe0437b1d4ed5f24d14deb634f319dd056194b4f71fcb98df01c5958c585",
        "docs/manuscript/figures_png/figure16_mvp_reference_stack.png": "526cbb07222e748ea0924f0c1eae59f703328b73987efd637ce3b13835c21d52",
        "docs/manuscript/figures_png/figure17_generalized_validated_search.png": "fdf3723080a431ae66374d7e84c64e9a3d41c927462959bc67957086a540f7ee",
        "docs/manuscript/figures_png/figure18_learned_coordination_substrates.png": "e261ad436e17e660c69de84ed163edef6307b86ac836cd4ebb4ed6176c0c1b02",
        "docs/manuscript/figures_png/figure19_experience_grounded_machine_labor.png": "2a1fceca43ca4aa420b9d697212e3bcd10c78aad53f27da04a5d485c00706b9e",
        "docs/manuscript/figures_png/figure1_system_architecture.png": "ddc5bc6e9b8bce2dd272fa8c195a364ebc5af8df32e3d42ffa3caaa28cc0d770",
        "docs/manuscript/figures_png/figure20_sovereign_experience_control_plane.png": "b9a2f4490e0b863a4c2c5f09bc33ff005a14459effd06d754915efd0ebfb2d82",
        "docs/manuscript/figures_png/figure21_proofzero_planning_layer.png": "c3bc1816a946f63fa84f86d2ab1a0a49d1a9e837cd357eda84fa3259876641bf",
        "docs/manuscript/figures_png/figure22_sovereign_evolutionary_agent_economy.png": "d8c8b17405c66ed702d9deffbedede3c4a7ce78f35e1c27c9a060915e705446f",
        "docs/manuscript/figures_png/figure23_civilizational_value_to_energy_flywheel.png": "efff7d856465cd191803a12c5d771cda3334eb2b6d51091be609e79683bfca98",
        "docs/manuscript/figures_png/figure24_agiet_institutional_stack.png": "d43bb2df3dc0bc89af76d615370eb00e39583c8df562204c829fb9795de1e742",
        "docs/manuscript/figures_png/figure25_agiet_proof_settlement_chain.png": "52cd355e03271b5985d217d9c909ed75fc068ce39d31931b1fb53a5c4709f0f3",
        "docs/manuscript/figures_png/figure26_agiet_namespace_layer.png": "feaf0a9542325bff7f97bd50d6dc12815993279717c61eaecbe6824a141b69c4",
        "docs/manuscript/figures_png/figure27_proof_gated_aiga_work_engine.png": "f1fa20e1cca3fde77cd395270a2a0779f0d9eff7361a41ccb0408db27066b070",
        "docs/manuscript/figures_png/figure28_montrealai_evidence_corpus.png": "4bedb53d6359fa86866c2ce75f31422de0471893e447a136690c3ecf52967e60",
        "docs/manuscript/figures_png/figure29_market_governed_invention_foundry.png": "abe03d17d45a1f507432b465c86308d839aea908e34de471de414554790ec673",
        "docs/manuscript/figures_png/figure2_inflow_dynamics.png": "47856d03f59c54352bd27334d8244f367d1b5378bc2def4168f6ef3ed30cc952",
        "docs/manuscript/figures_png/figure30_rsi_control_plane.png": "1fec5d0834f7adccb574c746cf6d9078a6466061f356dea6fe41be7efea9c422",
        "docs/manuscript/figures_png/figure31_evidence_factory_to_sovereign_organs.png": "73ece92eb446cc570269490d8ff7fe7c278a89869cda2981b0ecbb230e43dc04",
        "docs/manuscript/figures_png/figure32_cybersecurity_sovereign_immune_organ.png": "959c490adfc6a634b9eb6346bf1ea210b43540047c87a996edb292adb468ed00",
        "docs/manuscript/figures_png/figure3_free_energy_landscape.png": "074cf7360821214afa7c851bd655f0f898ec1beee1403ce00ad67312657df5d6",
        "docs/manuscript/figures_png/figure4_entropy_band.png": "1828f5c11a1e1172d143b87840cb9278e22d16d6462f6a07b1d5ab17986ef812",
        "docs/manuscript/figures_png/figure5_hamiltonian_matrix.png": "3fe34968b1dd2cc2a8d0e9f48bf85fb0e0f4aec6347a2709ac018be5edcc1443",
        "docs/manuscript/figures_png/figure6_risk_frontier.png": "df1abbdd368418c46bee8d6035dfeb3e43a5b28d5fb678ed0895cb064fb2c119",
        "docs/manuscript/figures_png/figure7_validator_loop.png": "b9a67ac0f2a7c58aa7a4808b307b13a2ae9c44f023dc021f7866227eeff0d703",
        "docs/manuscript/figures_png/figure9_doctrine_lattice.png": "49156e24a8148b4d5448a3899939f1e5a7bcc68474bf8b7da5331933b13a08af",
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


def main() -> int:
    _git_root()
    base_ref = _base_ref()
    changed_paths = _iter_changed_paths(base_ref)
    binary_paths = [path for path in changed_paths if _matches_binary_extension(path)]
    binary_paths.extend(_has_binary_diff(base_ref))
    binary_paths = sorted(
        {
            path
            for path in binary_paths
            if path not in AUTHORIZED_MANUSCRIPT
            or not Path(path).is_file()
            or hashlib.sha256(Path(path).read_bytes()).hexdigest() != AUTHORIZED_MANUSCRIPT[path]
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
