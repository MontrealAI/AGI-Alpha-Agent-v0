# SPDX-License-Identifier: Apache-2.0
"""Build the offline bilingual demonstration from preserved study outputs."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "origin": "evaluation/origin-check/reference.json",
    "origin_mission": "data/origin.json",
    "economics": "results/economics/economic_results.json",
    "economic_summary": "results/economics/summary.json",
    "confirmation": "evaluation/confirmation-v1/summary.json",
    "fresh_economics": "results/economics/confirmation_summary.json",
    "campaign": "results/economics/campaign_summary.json",
    "transfer": "evidence/recipient-transfer-v1_0_1/summary.json",
    "recipient": "evidence/recipient-transfer-v1_0_1/recipient/result.json",
    "native_ledger": "evidence/native-economics-v1/reconciliation.json",
}


def main() -> None:
    data = {}
    manifest = []
    for key, relative in SOURCES.items():
        raw = (ROOT / relative).read_bytes()
        data[key] = json.loads(raw)
        manifest.append({"key": key, "path": relative, "sha256": sha256(raw).hexdigest()})
    data["sources"] = manifest
    data["evidence_boundary"] = {
        "executed": "Local finite Bayesian computation over synthetic probabilities",
        "economics": "Conditional simulation; customer decisions and collections modeled",
        "actual_customer_collections_usd": 0,
        "actual_total_research_cost_usd": None,
        "production_authority": False,
    }
    assert len(data["economics"]["sensitivity"]) == 25
    assert data["confirmation"]["conforms_count"] == 48
    assert data["fresh_economics"]["cases_with_positive_launch_probability"] == 0
    template = (ROOT / "docs/demo.template.html").read_text()
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    output = template.replace("__STUDY_DATA__", encoded)
    target = ROOT / "docs/English_French_Demonstration.html"
    target.write_text(output)
    print(f"Built {target.relative_to(ROOT)} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
