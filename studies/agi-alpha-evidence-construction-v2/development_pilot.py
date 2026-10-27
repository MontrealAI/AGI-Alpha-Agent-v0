# SPDX-License-Identifier: Apache-2.0
"""Minimal source-to-purpose experiment, before retained instrument construction."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def run() -> dict[str, object]:
    """Check the supplied primary report without repairing or replacing its facts."""
    root = Path(__file__).resolve().parent
    source = root / "data/development/development_article.xml"
    article = ET.parse(source).getroot()
    tables = {}
    for wrap in article.findall(".//table-wrap"):
        tables[wrap.attrib["id"]] = [
            [" ".join("".join(cell.itertext()).split()) for cell in row if cell.tag in {"td", "th"}]
            for row in wrap.findall(".//tr")
        ]

    def msd(text: str) -> tuple[float, float]:
        values = re.fullmatch(r"([\d.]+)\s*\(([\d.]+)\)", text)
        if values is None:
            raise ValueError(text)
        return float(values[1]), float(values[2])

    t1, t2 = tables["pone-0078976-t001"], tables["pone-0078976-t002"]
    outputs = []
    for label, table, rows, column, ns in [
        ("Experiment 1, four-day recall", t1, (1, 2), 3, (52, 56)),
        ("Experiment 2, one-week recall", t2, (1, 3), 4, (99, 87)),
    ]:
        (m1, s1), (m0, s0) = (msd(table[r][column]) for r in rows)
        difference = m1 - m0
        se = math.sqrt(s1 * s1 / ns[0] + s0 * s0 / ns[1])
        outputs.append({"endpoint": label, "mean_difference_percentage_points": difference,
                        "se_independent_group_summary_assumption": se,
                        "n": list(ns), "purpose": "unadjusted descriptive contrast, not the reported ANCOVA"})
    submeans = [msd(t2[2][i])[0] for i in (2, 3)]
    reported = msd(t2[2][4])[0]
    conflict = reported - 0.005 > max(submeans) + 0.005
    return {"schema": "minimal-source-pilot/v1", "evidence": "OBSERVED_LOCAL_COMPUTATION_ON_PUBLIC_REPORT",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "reported_tables": tables, "bounded_outputs": outputs,
            "five_week_retrieval": {"reported_mean": reported, "subgroup_means": submeans,
                                    "two_decimal_rounding_margin": 0.005,
                                    "aggregate_outside_subgroup_convex_hull": conflict,
                                    "status": "HOLD_REPORTED_AGGREGATE" if conflict else "CONSISTENT"},
            "commercial_customer_acceptance": False, "all_required_context_independently_validated": False}


if __name__ == "__main__":
    result = run()
    target = Path(__file__).resolve().parent / "results/development/minimal-pilot.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "reported_tables"}, indent=2))
