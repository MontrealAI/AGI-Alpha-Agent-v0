# SPDX-License-Identifier: Apache-2.0
"""Render a read-only, source-bound deployment directory; never a wallet profile."""
from __future__ import annotations

import html
import json
from pathlib import Path


def build(root: Path) -> None:
    record = root / "deployments/ethereum-mainnet/2026-10-18/manifest.json"
    raw = record.read_bytes()
    manifest = json.loads(raw)
    destination = root / "docs/deployments/2026-10-18"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "manifest.json").write_bytes(raw)
    rows = "\n".join(
        f'<li><h2>{html.escape(item["name"])}</h2>'
        f'<p><a href="{html.escape(item["addressUrl"], quote=True)}"><code>{item["address"]}</code></a></p>'
        f'<p><a href="{item["creationUrl"]}">Finalized creation transaction</a> · Explorer exact match</p></li>'
        for item in manifest["contracts"]
    )
    source_url = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/" + manifest["source"]["commit"]
    guide_url = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/agent/CURRENT_MAINNET_DEPLOYMENT.md"
    notice_url = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md"
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy"
content="default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'">
<title>New Mainnet contracts · AGIALPHA</title><link rel="stylesheet" href="directory.css"></head>
<body><main><a href="../../">AGIALPHA home</a><h1>New Mainnet deployment</h1>
<p>October 18, 2026 · Ethereum Mainnet (chain ID 1)</p>
<p>Five deployed contracts, exact explorer matches and finalized graph bindings are recorded
in owner-provided verification reports.
Scoped graph authority was verified at block {manifest['authorityBlock']['number']}.</p>
<p><strong>Deployment record only. No public funding or activation approval.</strong> There is no global pause.
External dependency qualification, security assurance and off-chain commissioning remain separate.</p>
<ul>{rows}</ul>
<h2>Provenance and operating limits</h2>
<p>Deployed source: <a href="{source_url}"><code>{manifest['source']['commit']}</code></a>.</p>
<p>External authority closeout completed at 2026-10-18 15:24:15.848 UTC; both original actor leases were released.
The original session remains historically incomplete at sequence 20 with its journal unchanged.
Closeout performed no signing and broadcast no transactions.
Manual bindings were verified post hoc; that does not recreate missing pre-sign intent.
Existing applications retain their selected historical profiles; this page does not connect a wallet
or change a contract configuration.</p>
<p><a href="manifest.json">Machine-readable record</a> ·
<a href="{guide_url}">Complete evidence scope and deviations</a></p>
<p><a href="{notice_url}">Research-prototype disclaimer</a></p>
<p><a href="../../index.html">⬅️ Back to Gallery</a></p>
</main></body></html>
"""
    (destination / "index.html").write_text(page, encoding="utf-8")
    (destination / "directory.css").write_text(
        "body{font:1rem/1.6 system-ui,sans-serif;background:#faf8f3;color:#202020;margin:0}"
        "main{max-width:58rem;margin:auto;padding:2rem 1.25rem}a{color:#164ba0}"
        "code{overflow-wrap:anywhere}li{margin-block:1.5rem}h2{font-size:1.2rem}",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
