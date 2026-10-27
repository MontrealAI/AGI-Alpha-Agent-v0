# SPDX-License-Identifier: Apache-2.0
"""Independently enumerate exact rounded-mean scenarios; not a publication correction."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from fractions import Fraction
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent


def q(value: str | int) -> Fraction:
    """Convert a printed decimal or integer to an exact rational."""
    return Fraction(str(value))


def enc(value: Fraction) -> dict[str, str | float]:
    """Preserve the exact value and a convenient approximate display."""
    return {"rational": str(value), "decimal": float(value)}


def interval(value: str) -> tuple[Fraction, Fraction]:
    """Use closed half-unit intervals conservatively for hundredth rounding."""
    return q(value) - q("0.005"), q(value) + q("0.005")


def weighted_box(values: list[str], counts: list[int]) -> tuple[Fraction, Fraction]:
    """Bound a weighted average using source-cell rounding intervals."""
    total = sum(counts)
    return tuple(sum(n * interval(v)[j] for n, v in zip(counts, values)) / total for j in (0, 1))


def overlap(left: tuple[Fraction, Fraction], right: tuple[Fraction, Fraction]) -> bool:
    """Return whether two closed intervals intersect."""
    return max(left[0], right[0]) <= min(left[1], right[1])


def solve(matrix: list[list[int]], rhs: list[Fraction]) -> list[Fraction] | None:
    """Solve four simultaneous equations exactly or reject singular rows."""
    rows = [[q(v) for v in row] + [b] for row, b in zip(matrix, rhs)]
    for column in range(4):
        pivot = next((i for i in range(column, 4) if rows[i][column]), None)
        if pivot is None:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [v / scale for v in rows[column]]
        for i in range(4):
            if i != column:
                scale = rows[i][column]
                rows[i] = [a - scale * b for a, b in zip(rows[i], rows[column])]
    return [row[4] for row in rows]


def exact_vertices(
    means: list[str], counts: list[int], aggregates: list[tuple[list[int], str]]
) -> list[list[Fraction]]:
    """Enumerate vertices of a bounded four-cell rounded-mean polytope."""
    inequalities: list[tuple[list[int], Fraction]] = []
    for index, (mean, count) in enumerate(zip(means, counts)):
        low, high = interval(mean)
        row = [int(i == index) for i in range(4)]
        inequalities.append((row, count * high))
        inequalities.append(([-x for x in row], -count * low))
    for members, reported in aggregates:
        total = sum(counts[i] for i in members)
        low, high = interval(reported)
        row = [int(i in members) for i in range(4)]
        inequalities.append((row, total * high))
        inequalities.append(([-x for x in row], -total * low))
    vertices: dict[tuple[Fraction, ...], list[Fraction]] = {}
    for selected in itertools.combinations(inequalities, 4):
        point = solve([row for row, _ in selected], [bound for _, bound in selected])
        if point is not None and all(sum(a * b for a, b in zip(row, point)) <= bound for row, bound in inequalities):
            vertices[tuple(point)] = point
    return list(vertices.values())


def pooled_summary(means: list[str], sds: list[str], counts: list[int]) -> dict[str, Any]:
    """Calculate descriptive pooled moments from printed cell centers."""
    total = sum(counts)
    mean = sum(n * q(m) for n, m in zip(counts, means)) / total
    variance = sum((n - 1) * q(sd) ** 2 + n * (q(m) - mean) ** 2 for n, m, sd in zip(counts, means, sds)) / (total - 1)
    bounds = weighted_box(means, counts)
    return {
        "n": total,
        "mean": enc(mean),
        "sd_from_printed_centers": math.sqrt(float(variance)),
        "mean_rounding_box": [enc(v) for v in bounds],
    }


def main() -> None:
    """Build source-bound exact evidence for competing, conditional reconstructions."""
    table = (
        ElementTree.parse(ROOT / "development_article.xml")
        .getroot()
        .find(".//table-wrap[@id='pone-0078976-t002']/alternatives/table")
    )
    if table is None:
        raise ValueError("Table 2 not found")
    raw_rows = [["".join(td.itertext()).strip() for td in tr] for tr in table.findall(".//tr")]
    cells = [
        re.findall(r"[0-9]+\.[0-9]+", raw_rows[i][j])
        for i, j in ((1, 2), (1, 3), (3, 2), (3, 3), (2, 2), (2, 3), (4, 2), (4, 3))
    ]
    means1, means5 = [v[0] for v in cells[:4]], [v[0] for v in cells[4:]]
    sds1, sds5 = [v[1] for v in cells[:4]], [v[1] for v in cells[4:]]
    agg1 = [([0, 1], "61.82"), ([2, 3], "54.07"), ([0, 2], "56.98"), ([1, 3], "59.60"), ([0, 1, 2, 3], "58.19")]
    agg5 = [([2, 3], "45.39"), ([0, 2], "47.73"), ([1, 3], "51.48"), ([0, 1, 2, 3], "49.47")]
    candidates: list[dict[str, Any]] = []
    rejected: list[int] = []
    for first in range(14, 99):
        counts = [first, 99 - first, 100 - first, first - 13]
        consistent = all(
            overlap(weighted_box([means[i] for i in ids], [counts[i] for i in ids]), interval(reported))
            for means, aggregates in ((means1, agg1), (means5, agg5))
            for ids, reported in aggregates
        )
        if not consistent:
            rejected.append(first)
            continue
        vertices1 = exact_vertices(means1, counts, agg1)
        vertices5 = exact_vertices(means5, counts, agg5)
        if not vertices1 or not vertices5:
            rejected.append(first)
            continue
        effects = [(v[0] + v[1]) / 99 - (v[2] + v[3]) / 87 for v in vertices5]
        retrieval = [(v[0] + v[1]) / 99 for v in vertices5]
        candidates.append(
            {
                "counts_R_mind_R_no_NR_mind_NR_no": counts,
                "feasible_vertex_counts_week1_week5": [len(vertices1), len(vertices5)],
                "week5_unadjusted_difference_interval": [enc(min(effects)), enc(max(effects))],
                "week5_retrieval_mean_interval": [enc(min(retrieval)), enc(max(retrieval))],
                "exact_feasible_witness_weighted_cell_sums_week1": [str(v) for v in vertices1[0]],
                "exact_feasible_witness_weighted_cell_sums_week5": [str(v) for v in vertices5[0]],
            }
        )
    scenarios = []
    for label, counts in [
        ("Table2_count_and_other_mean_constraints", [52, 47, 48, 39]),
        ("Supplement_S4_cell_count_sums", [49, 50, 46, 41]),
    ]:
        r = pooled_summary(means5[:2], sds5[:2], counts[:2])
        nr = pooled_summary(means5[2:], sds5[2:], counts[2:])
        bounds_r, bounds_nr = weighted_box(means5[:2], counts[:2]), weighted_box(means5[2:], counts[2:])
        delta = q(r["mean"]["rational"]) - q(nr["mean"]["rational"])
        scenarios.append(
            {
                "scenario": label,
                "conditional_not_corrected": True,
                "counts": counts,
                "retrieval": r,
                "nonretrieval": nr,
                "difference_center": enc(delta),
                "difference_cell_only_rounding_interval": [
                    enc(bounds_r[0] - bounds_nr[1]),
                    enc(bounds_r[1] - bounds_nr[0]),
                ],
            }
        )
    sd_mind = pooled_summary([means1[0], means1[2]], [sds1[0], sds1[2]], [52, 48])
    sd_min = math.sqrt(
        float(sum((n - 1) * (q(sd) - q("0.005")) ** 2 for n, sd in zip([52, 48], [sds1[0], sds1[2]])) / 99)
    )
    sources = {
        name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), "bytes": (ROOT / name).stat().st_size}
        for name in ["development_article.xml", "development_article.pdf", "development_table_s4.doc"]
    }
    result = {
        "schema": "independent-source-diagnosis/v1",
        "evidence_type": "executed exact rational arithmetic and visual source inspection",
        "doi": "10.1371/journal.pone.0078976",
        "sources": sources,
        "visual_inspection": ["Original article PDF page 5 Table 2", "Original S4 DOC rendered to PDF page 1"],
        "purpose": "unadjusted descriptive five-week retrieval-minus-nonretrieval difference among reported complete cases",
        "not_estimated": [
            "covariate-adjusted ANCOVA effect",
            "causal intervention effect",
            "repeated-measures interaction",
            "statistical confidence interval",
            "authoritative correction",
            "true original participant data",
        ],
        "raw_table2_rows": raw_rows,
        "rounding_policy": "Closed +/-0.005 intervals at printed hundredths, exact rational calculations; these are rounding envelopes, not statistical confidence intervals.",
        "all_source_assertions_jointly_consistent": False,
        "strict_authoritative_point_result": "HOLD",
        "convexity_conflict": {
            "cell_envelope": [enc(q("52.815")), enc(q("53.305"))],
            "reported_total_interval": [enc(q("54.065")), enc(q("54.075"))],
            "minimum_gap": enc(q("0.760")),
            "scope": "Any positively weighted average of the two reported same-row cells; independent of subgroup counts",
        },
        "count_enumeration": {
            "count_equations": ["a+b=99", "c+d=87", "a+c=100", "b+d=86", "a,b,c,d positive integers"],
            "all_possible_first_cells": [14, 98],
            "enumerated_count": 85,
            "rejected_first_cells": rejected,
            "excluded_assertion": "Table2 week5 retrieval aggregate mean54.07 conflicts with its cells; all SD constraints excluded from mean-only enumeration and audited separately",
            "admissible_scenarios": candidates,
        },
        "competing_source_scenarios": scenarios,
        "supplement_conflicts": {
            "experiment2_cells": [49, 50, 46, 41],
            "experiment2_column_totals": [95, 91],
            "table2_column_totals": [100, 86],
            "experiment1_primary5_total_printed": 38,
            "experiment1_primary5_subgroup_sum": 58,
        },
        "additional_sd_conflict": {
            "source": "Table2 week1 mind-map aggregate SD23.04",
            "conditional_counts": [52, 48],
            "pooled_from_centers": sd_mind["sd_from_printed_centers"],
            "conservative_minimum_sd_ignoring_between_cell_mean_difference": sd_min,
            "maximum_printed_sd_after_rounding": 23.045,
            "interpretation": "Even omitting nonnegative between-cell mean variance, the cell SDs cannot generate23.04 under these counts.",
        },
        "publication_reported_difference": {
            "center": enc(q("54.07") - q("45.39")),
            "rounding_interval": [enc(q("8.67")), enc(q("8.69"))],
            "status": "Faithful transcription only; conflicts with subgroup-cell implication",
        },
        "limits": "No original participant data or author adjudication; source inconsistencies do not identify which cell or total is wrong. Positive conditional intervals do not validate every possible correction or the reported ANCOVA.",
    }
    (ROOT / "development-independent-golden.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "exact_admissible_scenarios": candidates,
                "scenario_differences": [s["difference_center"] for s in scenarios],
                "strict_result": result["strict_authoritative_point_result"],
                "minimum_convexity_gap": result["convexity_conflict"]["minimum_gap"],
                "sd_lower_bound": sd_min,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
