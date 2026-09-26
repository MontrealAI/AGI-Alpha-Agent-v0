# SPDX-License-Identifier: Apache-2.0
"""Verify the owner-supplied publication against immutable upstream commitments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

EXPECTED = {
    "AGI_ALPHA_Unified_Publication_Final.pdf": "4b290d5a8232364b8808c0af8a96e7c9b152afd7ac3f5ba05668a538e073791a",
    "AGI_ALPHA_Unified_Publication_Final.md": "4217bd4041c4fa066a5a77d38404c3f5963feb79a7e0730d27467432be50c99f",
}
EXPECTED.update(
    {
        "figures_png/figure10_frontier_synthesis_lattice.png": "b929e1186bbeeb3cf2e4b3ed2ef78b8b5401aefb1007785709c23e9d9bf7d1a0",
        "figures_png/figure11_sovereign_invention_stack.png": "5be3a36cc41df60d3d73919d3951c636b553873c6fcf435eff3840a6e52a6c55",
        "figures_png/figure12_build_test_compression_loop.png": "c578d12b42450a8a8d56811c2f33ad06239891313ebc711a74db71770a8cbc11",
        "figures_png/figure13_distributional_safety_envelope.png": "2b04acd0663fa94f7f60989397a8ffa3bea3b8ff740606a8ff87c2ae7cd5b56b",
        "figures_png/figure14_model_vs_organization_substrate.png": "f6dba956e7fcf5ced793f5fb3086e6420a1a349add9bb06de534d4e32ed66302",
        "figures_png/figure15_real_task_demonstration_harness.png": "f249fe0437b1d4ed5f24d14deb634f319dd056194b4f71fcb98df01c5958c585",
        "figures_png/figure16_mvp_reference_stack.png": "526cbb07222e748ea0924f0c1eae59f703328b73987efd637ce3b13835c21d52",
        "figures_png/figure17_generalized_validated_search.png": "fdf3723080a431ae66374d7e84c64e9a3d41c927462959bc67957086a540f7ee",
        "figures_png/figure18_learned_coordination_substrates.png": "e261ad436e17e660c69de84ed163edef6307b86ac836cd4ebb4ed6176c0c1b02",
        "figures_png/figure19_experience_grounded_machine_labor.png": "2a1fceca43ca4aa420b9d697212e3bcd10c78aad53f27da04a5d485c00706b9e",
        "figures_png/figure1_system_architecture.png": "ddc5bc6e9b8bce2dd272fa8c195a364ebc5af8df32e3d42ffa3caaa28cc0d770",
        "figures_png/figure20_sovereign_experience_control_plane.png": "b9a2f4490e0b863a4c2c5f09bc33ff005a14459effd06d754915efd0ebfb2d82",
        "figures_png/figure21_proofzero_planning_layer.png": "c3bc1816a946f63fa84f86d2ab1a0a49d1a9e837cd357eda84fa3259876641bf",
        "figures_png/figure22_sovereign_evolutionary_agent_economy.png": "d8c8b17405c66ed702d9deffbedede3c4a7ce78f35e1c27c9a060915e705446f",
        "figures_png/figure23_civilizational_value_to_energy_flywheel.png": "efff7d856465cd191803a12c5d771cda3334eb2b6d51091be609e79683bfca98",
        "figures_png/figure24_agiet_institutional_stack.png": "d43bb2df3dc0bc89af76d615370eb00e39583c8df562204c829fb9795de1e742",
        "figures_png/figure25_agiet_proof_settlement_chain.png": "52cd355e03271b5985d217d9c909ed75fc068ce39d31931b1fb53a5c4709f0f3",
        "figures_png/figure26_agiet_namespace_layer.png": "feaf0a9542325bff7f97bd50d6dc12815993279717c61eaecbe6824a141b69c4",
        "figures_png/figure27_proof_gated_aiga_work_engine.png": "f1fa20e1cca3fde77cd395270a2a0779f0d9eff7361a41ccb0408db27066b070",
        "figures_png/figure28_montrealai_evidence_corpus.png": "4bedb53d6359fa86866c2ce75f31422de0471893e447a136690c3ecf52967e60",
        "figures_png/figure29_market_governed_invention_foundry.png": "abe03d17d45a1f507432b465c86308d839aea908e34de471de414554790ec673",
        "figures_png/figure2_inflow_dynamics.png": "47856d03f59c54352bd27334d8244f367d1b5378bc2def4168f6ef3ed30cc952",
        "figures_png/figure30_rsi_control_plane.png": "1fec5d0834f7adccb574c746cf6d9078a6466061f356dea6fe41be7efea9c422",
        "figures_png/figure31_evidence_factory_to_sovereign_organs.png": "73ece92eb446cc570269490d8ff7fe7c278a89869cda2981b0ecbb230e43dc04",
        "figures_png/figure32_cybersecurity_sovereign_immune_organ.png": "959c490adfc6a634b9eb6346bf1ea210b43540047c87a996edb292adb468ed00",
        "figures_png/figure3_free_energy_landscape.png": "074cf7360821214afa7c851bd655f0f898ec1beee1403ce00ad67312657df5d6",
        "figures_png/figure4_entropy_band.png": "1828f5c11a1e1172d143b87840cb9278e22d16d6462f6a07b1d5ab17986ef812",
        "figures_png/figure5_hamiltonian_matrix.png": "3fe34968b1dd2cc2a8d0e9f48bf85fb0e0f4aec6347a2709ac018be5edcc1443",
        "figures_png/figure6_risk_frontier.png": "df1abbdd368418c46bee8d6035dfeb3e43a5b28d5fb678ed0895cb064fb2c119",
        "figures_png/figure7_validator_loop.png": "b9a67ac0f2a7c58aa7a4808b307b13a2ae9c44f023dc021f7866227eeff0d703",
        "figures_png/figure9_doctrine_lattice.png": "49156e24a8148b4d5448a3899939f1e5a7bcc68474bf8b7da5331933b13a08af",
    }
)
SOURCE_COMMIT = "bd920a6c52d820a087116bf59f2a4236d0494ac0"


def verify(folder: Path = Path("docs/manuscript")) -> dict[str, str]:
    """Reject source replacement, manifest drift and symlink substitution."""
    manifest = json.loads((folder / "source-manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT or manifest["pdf_pages"] != 198:
        raise ValueError("Manuscript identity differs from the supplied publication")
    if set(manifest["files"]) != set(EXPECTED):
        raise ValueError("Unexpected manuscript files")
    for name, expected in EXPECTED.items():
        path = folder / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Manuscript must be a regular file")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected or manifest["files"][name] != {
            "sha256": expected,
            "bytes": len(data),
        }:
            raise ValueError(f"Manuscript checksum differs: {name}")
    return EXPECTED


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
