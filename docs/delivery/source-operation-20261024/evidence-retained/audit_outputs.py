# SPDX-License-Identifier: Apache-2.0
"""Reconstruct archived terminal outputs without importing the candidate runtime.

Run with Python 3.11+: python audit_outputs.py PATH_TO_EVIDENCE_DIRECTORY.
This is a separate same-operator computational audit, not independent custody.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import sys


def commitment(domain: str, value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(b"successor-omega/v1:" + domain.encode() + b"\0" + data).hexdigest()


def score(document: dict, selected: list[str], limit: int) -> dict:
    claims = document["claims"]
    indexed = {claim["id"]: claim for claim in claims}
    chosen = set(selected)
    assert len(chosen) == len(selected) <= limit and chosen <= indexed.keys()

    def supported(name: str, visiting: frozenset[str] = frozenset()) -> bool:
        assert name not in visiting, "cyclic input"
        return name in chosen and all(
            supported(parent, visiting | {name}) for parent in indexed[name]["depends_on"]
        )

    valid = [c["id"] for c in claims if c["id"] in chosen and supported(c["id"])]
    covered = sum(indexed[name]["weight"] for name in valid)
    total = sum(c["weight"] for c in claims)
    return {
        "selected": selected,
        "supported_claims": valid,
        "unsupported_claims": sorted(chosen - set(valid)),
        "covered_weight": covered,
        "total_weight": total,
        "score_millionths": covered * 1_000_000 // total,
        "text": "\n".join(c["text"] for c in claims if c["id"] in chosen),
        "references": [{"id": c["id"], "provenance": c["provenance"]} for c in claims if c["id"] in chosen],
        "source_digest": commitment("ti-source", document),
    }


def audit(directory: Path) -> dict:
    cases = []
    for path in sorted(directory.glob("*-history.json")):
        data = json.loads(path.read_text())
        assert data["active_authority"] == []
        submitted = data["submitted_inputs"]["spec"]
        limit = submitted["study"]["charter"]["max_clauses"]
        counts = {"attached_records": 0, "pending_records": 0, "attached_outputs": 0, "pending_outputs": 0}
        for kind, records in [("attached", data["evidence"]["campaigns"]),
                              ("pending", data["evidence"]["pending_campaigns"])]:
            for campaign in records.values():
                result = campaign.get("result")
                if not result:
                    continue
                counts[f"{kind}_records"] += 1
                sources = result["fresh_sources"]
                for method, outputs in result["results"].items():
                    # Incomplete attempts cannot become accepted evidence.
                    if len(outputs) != len(sources):
                        assert result.get("failure") or not outputs
                        continue
                    for source, output in zip(sources, outputs, strict=True):
                        actual = score(source, output["selected"], limit)
                        assert all(output[k] == v for k, v in actual.items()), (path.name, method, output)
                        if method == "unrestricted-exact-search":
                            names = [c["id"] for c in source["claims"]]
                            best = max(score(source, list(choice), limit)["score_millionths"]
                                       for n in range(limit + 1) for choice in itertools.combinations(names, n))
                            assert output["score_millionths"] == best, "conventional baseline missed optimum"
                        counts[f"{kind}_outputs"] += 1
        cases.append({"case": path.name.removesuffix("-history.json"), **counts})
    assert cases, "no histories found"
    return {"schema": "separate-terminal-output-audit/v1", "runtime_imported": False,
            "independence": "same operator; separate standard-library reconstruction; no external custody",
            "checks": ["exact text and references", "selection identity and clause limit", "recursive prerequisite support",
                       "weighted coverage", "domain-separated source commitment", "exhaustive conventional optimum",
                       "inert exported authority", "pending completed children counted separately"],
            "cases": cases, "totals": {k: sum(c[k] for c in cases) for k in counts}}


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1])), indent=2))
