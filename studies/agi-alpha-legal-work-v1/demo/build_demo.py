# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained bilingual replay from the sealed research artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Embed observed packets and explicitly assumed economic thresholds."""
    primary = json.loads((ROOT / "evidence/production-summary.json").read_text())
    reconciliation = json.loads((ROOT / "evidence/reconciliation-independent-audit.json").read_text())
    secondary = json.loads((ROOT / "economics/results/reconciliation/unit-thresholds.json").read_text())
    packets = [
        json.loads(path.read_text()) for path in sorted((ROOT / "evidence/reconciliation").glob("*/*/packet.json"))
    ]
    payload = {
        "primary": primary["acceptance"]["primary"],
        "reconciliation": reconciliation,
        "packets": packets,
        "thresholds": secondary["demandThresholds"],
        "assumptions": secondary["assumptions"],
    }
    template = (ROOT / "demo/template.html").read_text()
    serialized = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    output = template.replace("__EVIDENCE_JSON__", serialized)
    destination = ROOT / "demo/AGI_ALPHA_Legal_Work_Demo.html"
    destination.write_text(output)
    print(json.dumps({"file": str(destination), "packets": len(packets), "bytes": destination.stat().st_size}))


if __name__ == "__main__":
    main()
