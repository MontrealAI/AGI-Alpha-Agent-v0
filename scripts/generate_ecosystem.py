# SPDX-License-Identifier: Apache-2.0
"""Render the bilingual paired-system guide from a dated public contract inventory."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def contract_rows(contracts: list[dict[str, Any]], language: str) -> str:
    """Render selectable full addresses without a browser fetch or wallet connection."""
    rows = []
    for contract in contracts:
        name = html.escape(contract["name"])
        address = html.escape(contract["address"])
        purpose = html.escape(contract["purpose"][language])
        label = "View on Etherscan" if language == "en" else "Voir sur Etherscan"
        rows.append(
            f'<tr><th scope="row">{name}</th><td>{purpose}</td><td>'
            f'<a href="https://etherscan.io/address/{address}#code" '
            f'aria-label="{name}: {label}, {address}"><code>{address}</code></a></td></tr>'
        )
    return "\n".join(rows)


def build(root: Path = ROOT) -> None:
    """Generate both static languages and keep their addresses bound to source records."""
    directory = root / "docs/assets/ecosystem/contracts.json"
    data = json.loads(directory.read_text(encoding="utf-8"))
    alpha_record = json.loads(
        (root / "deployments/ethereum-mainnet/2026-10-11/manifest.json").read_text(encoding="utf-8")
    )
    if data["chainId"] != 1 or data["token"]["decimals"] != 18:
        raise ValueError("The guide must identify the recorded Ethereum mainnet token")
    if data["token"]["address"].lower() != "0xa61a3b3a130a9c20768eebf97e21515a6046a1fa":
        raise ValueError("Shared token differs from the deployment records")
    if len(data["alpha"]["contracts"]) != 5 or len(data["jobs"]["contracts"]) != 24:
        raise ValueError("The dated directory must retain all 29 deployed instances")
    contracts = data["alpha"]["contracts"] + data["jobs"]["contracts"]
    addresses = [contract["address"].lower() for contract in contracts]
    if len(set(addresses)) != len(addresses) or not all(re.fullmatch(r"0x[0-9a-f]{40}", x) for x in addresses):
        raise ValueError("Contract addresses must be complete and distinct")
    for contract in data["alpha"]["contracts"]:
        if contract["address"] != alpha_record["contracts"][contract["name"]]["address"]:
            raise ValueError("Alpha guide differs from its immutable deployment archive")
    version = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text(encoding="utf-8"))["release"]
    for language, relative_root in (("en", "../"), ("fr", "../../")):
        template = root / "scripts/templates" / f"ecosystem-{language}.html"
        page = template.read_text(encoding="utf-8")
        replacements = {
            "ROOT": relative_root,
            "VERSION": version,
            "TOKEN": data["token"]["address"],
            "ALPHA_SOURCE": data["alpha"]["source"],
            "JOBS_SOURCE": data["jobs"]["source"],
            "ALPHA_ROWS": contract_rows(data["alpha"]["contracts"], language),
            "JOBS_ROWS": contract_rows([c for c in data["jobs"]["contracts"] if not c["implementation"]], language),
            "IMPLEMENTATION_ROWS": contract_rows(
                [c for c in data["jobs"]["contracts"] if c["implementation"]], language
            ),
        }
        for key, value in replacements.items():
            page = page.replace("{{" + key + "}}", value)
        if "{{" in page:
            raise ValueError("Unexpanded ecosystem page placeholder")
        destination = root / "docs/ecosystem" / ("fr/index.html" if language == "fr" else "index.html")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()
