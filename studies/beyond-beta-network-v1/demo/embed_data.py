# SPDX-License-Identifier: Apache-2.0
"""Embed verified publication data in the standalone offline demonstration."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=BASE / "demo_data.json")
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text())
    if not args.allow_draft:
        assert data.get("status") == "bound_to_frozen_results", "Final demo requires executed frozen results."
        assert {s["id"] for s in data["scenarios"]} == {"conservative", "central", "favorable"}
        for scenario in data["scenarios"]:
            assert scenario["worlds"] > 0
            assert scenario["policies"]
            for policy in scenario["policies"]:
                assert policy["profit"]["p05"] <= policy["profit"]["p50"] <= policy["profit"]["p95"]
                assert policy["human_review_hours"] == 0, "Primary demo must not silently add human review."
                accounting = policy["accounting"]
                names = ("a_paid_work", "b_retention", "c_optional_research", "common_business", "total_resource_cost", "net_collections", "a_recharged")
                assert all(isinstance(accounting[k], (int, float)) and math.isfinite(accounting[k]) for k in names)
                assert accounting["a_recharged"] == 0, "Paid-job development must not be charged again at retention."
                partition = sum(accounting[k] for k in names[:4])
                assert abs(partition - accounting["total_resource_cost"]) < 0.031, "A/B/C/common expense must reconcile."
                assert all(accounting["note"].get(lang) for lang in ("en", "fr"))
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    html = (BASE / "index.html").read_text()
    pattern = r'(<script id="study-data" type="application/json">).*?(</script>)'
    html, count = re.subn(pattern, lambda m: m.group(1) + encoded + m.group(2), html, count=1, flags=re.S)
    assert count == 1, "Embedded data block missing."
    (BASE / "index.html").write_text(html)
    print("Embedded", len(encoded), "characters from", args.data)


if __name__ == "__main__":
    main()
