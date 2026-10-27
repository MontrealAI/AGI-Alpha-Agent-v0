# SPDX-License-Identifier: Apache-2.0
"""Reconstruct named conditional mean branches from actual development sources."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "instrument"))
from evidence_engine import cell_value, read_jats, rounded_mean_model


def main() -> None:
    """Retain all-source inconsistency and separate source-conditional results."""
    packet = read_jats(ROOT / "data/development/development_article.xml",
                       "18acae39e5cfbb8832a6ab616f49de795af8130ef9b1be52e03028febb202cb2")
    table = "pone-0078976-t002"
    facts = {}

    def fact(row: int, col: int) -> float:
        result = cell_value(packet, table, row, col, "mean")
        facts[f"r{row}c{col}"] = result
        return result["value"]

    def count(row: int, col: int) -> int:
        result = cell_value(packet, table, row, col, "number")
        facts[f"r{row}c{col}"] = result
        value = result["value"]
        if value != int(value):
            raise ValueError("noninteger participant count")
        return int(value)

    nr, nc, nm = count(1, 5), count(3, 5), count(7, 2)
    nn = count(7, 3)
    if nr + nc != nm + nn:
        raise ValueError("row and column participant totals conflict")
    candidates = [[x, nr - x, nm - x, nc - nm + x] for x in range(1, nr)
                  if min(nm - x, nc - nm + x) > 0]
    means = [fact(r, c) for r, c in [(2, 2), (2, 3), (4, 2), (4, 3)]]
    aggregates = [{"id": key, "cells": cells, "mean": fact(r, c)} for key, cells, r, c in [
        ("nonretrieval-total", [2, 3], 4, 4), ("mindmaps-total", [0, 2], 6, 2),
        ("no-mindmaps-total", [1, 3], 6, 3), ("grand-total", [0, 1, 2, 3], 6, 4)]]
    base = {"scenario": "main-table-mean-branch", "rounding_half_width": .005,
            "cell_means": means, "count_candidates": candidates, "aggregates": aggregates,
            "contrast_positive_cells": [0, 1], "contrast_negative_cells": [2, 3],
            "assumptions": ["Four mutually exclusive groups, common complete-case population",
                            "Main-table row and column totals are correct",
                            "All listed cell and nonsuspect marginal means round to 0.01 percentage points",
                            "Descriptive mean contrast only; no adjusted, causal or clustered precision claim"],
            "excluded_claims": ["Reported retrieval five-week marginal54.07",
                                "S4 cell counts conflict with main-table column totals",
                                "SDs and other timepoints are not LP constraints"]}
    strict = dict(base)
    strict["scenario"] = "all-five-week-main-table-means"
    strict["aggregates"] = aggregates + [{"id": "retrieval-total", "cells": [0, 1], "mean": fact(2, 4)}]
    strict["excluded_claims"] = ["S4 counts not part of this main-table-only consistency check"]
    supplement = dict(base)
    supplement.update(scenario="supplement-counts-cell-means-branch", count_candidates=[[49, 50, 46, 41]],
                      aggregates=[], assumptions=["S4 cell counts are correct", "Table2 cell means are correct",
                                                  "Four mutually exclusive groups, common complete-case population",
                                                  "Descriptive contrast from rounded numbers only"],
                      excluded_claims=["Main-table marginal means and column totals conflict with S4",
                                       "No claim that this branch repairs the source"])
    outputs = []
    for spec in (strict, base, supplement):
        result = rounded_mean_model(spec)
        outputs.append(result)
        (ROOT / "data/development" / (spec["scenario"] + ".json")).write_text(json.dumps(spec, indent=2) + "\n")
    delivery = {"schema": "source-conditional-delivery/v1", "evidence": "OBSERVED_LOCAL_COMPUTATION",
                "source_facts": facts, "branches": outputs,
                "unconditional_corrected_mean": None, "exact_repaired_source_claim": "HOLD",
                "research_use": "Inspect source inconsistency and preserve explicitly conditional descriptive bounds",
                "commercial_acceptance": False, "source_author_validation": False}
    (ROOT / "results/development/constructed-delivery.json").write_text(json.dumps(delivery, indent=2) + "\n")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
