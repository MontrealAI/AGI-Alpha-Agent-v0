# SPDX-License-Identifier: Apache-2.0
"""Build the wallet's pinned runtime digest profile without network access or signing."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

NAMES = {"Access": "AscensionAccess", "Seed": "NovaSeed", "Oracle": "AscensionRiskOracle", "Jobs": "AscensionJobMarket", "Mark": "AscensionMark"}
ADDRESSES = {"Access": "0x36f8C079fEEBC81c5AF30D71be5017037246a32e", "Seed": "0xFA4737Ba7cF111EBb0840aA300BC61D84d303449", "Oracle": "0x06cb4D684628846B048d88CCf8C03c4Cfb74f149", "Jobs": "0x86f84E173A7a1a4588f4e757552F20f7C58e61E8", "Mark": "0xa28dA507f7F9AFF8910f1F7cB5d5b8238F5Db625"}


def build(root: Path, docs: Path | None = None) -> Path:
    archive = root / "deployments/ethereum-mainnet/2026-10-11"
    manifest_bytes = (archive / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    runtimes = json.loads((archive / "runtime-code.json").read_text(encoding="utf-8"))
    if manifest["chainId"] != 1 or manifest["profile"] != "ascension-2026-10-11-solc-0.8.24":
        raise ValueError("Wrong deployment profile; do not substitute current-source artifacts")
    contracts = {}
    for alias, name in NAMES.items():
        record = manifest["contracts"][name]
        if record["address"].lower() != ADDRESSES[alias].lower():
            raise ValueError(f"{name}: changed deployment address")
        encoded = runtimes[name]
        if not isinstance(encoded, str) or not encoded.startswith("0x"):
            raise ValueError(f"{name}: invalid archived runtime")
        runtime = bytes.fromhex(encoded[2:])
        if not runtime or len(runtime) > 100000:
            raise ValueError(f"{name}: empty or oversized runtime")
        contracts[alias] = {"address": record["address"], "sha256": hashlib.sha256(runtime).hexdigest(), "archivedKeccak256": record["runtimeCodeHash"]}
    output = {"schema": "agialpha.mark-wallet-profile.v1", "chainId": 1, "profile": manifest["profile"],
              "sourceManifestSHA256": hashlib.sha256(manifest_bytes).hexdigest(), "contracts": contracts,
              "newExposureEnabled": False,
              "reason": "Archived deployment predates newer settlement safeguards; funding commissioning remains unresolved. No runtime override is accepted."}
    destination = (docs or root / "docs") / "assets/ascension-wallet/profile.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--docs-dir", type=Path)
    args = parser.parse_args()
    print(build(args.root, args.docs_dir))
