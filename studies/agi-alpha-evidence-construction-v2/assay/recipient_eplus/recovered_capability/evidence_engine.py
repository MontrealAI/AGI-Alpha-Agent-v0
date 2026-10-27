# SPDX-License-Identifier: Apache-2.0
"""Source-bound table reading and conventional rounded-mean reconstruction.

This engine checks declared arithmetic. A reviewer must qualify source semantics,
design, units, missingness and the useful purpose for every new mission.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import linprog

VERSION = "1.0.0"


def digest(path: str | Path) -> str:
    """Return the identity of actual source bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value: Any) -> float:
    """Reject nonnumeric, nonfinite and Boolean values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


def read_jats(path: str | Path, expected_sha256: str | None = None) -> dict[str, Any]:
    """Expose table cells and context without inferring missing labels or sample sizes."""
    path = Path(path)
    if expected_sha256 is not None and digest(path) != expected_sha256:
        raise ValueError("source digest mismatch")
    raw = path.read_bytes()
    if len(raw) > 8_000_000 or b"<!ENTITY" in raw.upper():
        raise ValueError("source outside bounded XML scope")
    root = ET.fromstring(raw)
    text = lambda e: " ".join("".join(e.itertext()).split())
    tables = {}
    for wrap in root.findall(".//table-wrap"):
        table_id = wrap.attrib.get("id")
        if not table_id or table_id in tables:
            raise ValueError("table identity missing or duplicate")
        rows = []
        occupied: dict[tuple[int, int], str] = {}
        for ri, row in enumerate(wrap.findall(".//tr")):
            ci = 0
            for cell in row:
                if cell.tag not in {"td", "th"}:
                    continue
                while (ri, ci) in occupied:
                    ci += 1
                rs, cs = int(cell.attrib.get("rowspan", "1")), int(cell.attrib.get("colspan", "1"))
                if min(rs, cs) < 1 or max(rs, cs) > 100:
                    raise ValueError("unsupported table span")
                for dr in range(rs):
                    for dc in range(cs):
                        if (ri + dr, ci + dc) in occupied:
                            raise ValueError("overlapping cells")
                        occupied[ri + dr, ci + dc] = text(cell)
                ci += cs
            rows.append([])
        if occupied:
            height = max(r for r, _ in occupied) + 1
            width = max(c for _, c in occupied) + 1
            rows = [[occupied.get((r, c), "") for c in range(width)] for r in range(height)]
        tables[table_id] = {"caption": " ".join(text(e) for e in wrap.findall("caption")), "rows": rows}
    paragraphs = [{"id": e.attrib.get("id"), "text": text(e)} for e in root.findall(".//body//p")]
    return {"schema": "jats-evidence/v1", "source_sha256": digest(path), "tables": tables,
            "paragraphs": paragraphs, "semantic_acceptance": False}


def cell_value(packet: dict[str, Any], table_id: str, row: int, column: int, part: str) -> dict[str, Any]:
    """Read a zero-based cell with a replayable source locator."""
    if isinstance(row, bool) or isinstance(column, bool) or min(row, column) < 0:
        raise ValueError("nonnegative cell index required")
    raw = packet["tables"][table_id]["rows"][row][column]
    if part in {"mean", "dispersion"}:
        m = re.fullmatch(r"\s*([+-]?[\d.]+)\s*\(\s*([\d.]+)\s*\)\s*", raw)
        if m is None:
            raise ValueError("cell is not an unambiguous value (dispersion)")
        value = float(m[1 if part == "mean" else 2])
    elif part == "number":
        value = float(raw.strip())
    else:
        raise ValueError("unknown cell component")
    finite(value)
    return {"value": value, "source_sha256": packet["source_sha256"], "table": table_id,
            "row": row, "column": column, "part": part, "raw": raw,
            "dispersion_kind": "UNQUALIFIED" if part == "dispersion" else None}


def pool(groups: list[dict[str, Any]], *, mutually_exclusive: bool, same_endpoint: bool) -> dict[str, Any]:
    """Combine sample moments only after explicit group/endpoint qualification."""
    if mutually_exclusive is not True or same_endpoint is not True or not groups:
        raise ValueError("disjoint groups with one endpoint must be qualified")
    normalized = []
    for group in groups:
        if set(group) != {"n", "mean", "dispersion", "dispersion_kind"}:
            raise ValueError("unknown or missing moment fields")
        n = finite(group["n"])
        mean, spread = finite(group["mean"]), finite(group["dispersion"])
        if n < 2 or n != int(n) or spread < 0:
            raise ValueError("invalid sample moments")
        if group["dispersion_kind"] == "SE":
            spread *= math.sqrt(n)
        elif group["dispersion_kind"] != "SD":
            raise ValueError("dispersion meaning requires qualification")
        normalized.append((int(n), mean, spread))
    total = sum(n for n, _, _ in normalized)
    mean = sum(n * m for n, m, _ in normalized) / total
    variance = sum((n - 1) * s * s + n * (m - mean) ** 2 for n, m, s in normalized) / (total - 1)
    return {"n": total, "mean": mean, "sd": math.sqrt(variance),
            "precision": "nominal calculation from rounded source moments"}


def mean_difference(a: dict[str, Any], b: dict[str, Any], *, design: str) -> dict[str, Any]:
    """Compute a descriptive difference; require independent groups for its SE."""
    if design not in {"independent_groups", "paired_unknown_covariance"}:
        raise ValueError("unqualified design")
    difference = finite(a["mean"]) - finite(b["mean"])
    if design == "paired_unknown_covariance":
        return {"difference": difference, "se": None, "status": "POINT_ONLY_COVARIANCE_MISSING"}
    for group in (a, b):
        n, sd = finite(group["n"]), finite(group["sd"])
        if n < 2 or n != int(n) or sd < 0:
            raise ValueError("invalid independent group")
    se = math.sqrt(a["sd"] ** 2 / a["n"] + b["sd"] ** 2 / b["n"])
    return {"difference": difference, "se": se, "status": "DESCRIPTIVE_ONLY",
            "limit": "Not a covariate-adjusted, cluster-adjusted or causal estimate."}


def rounded_mean_model(spec: dict[str, Any]) -> dict[str, Any]:
    """Enumerate count candidates and solve conventional LP bounds for rounded means.

    The caller supplies and owns named source hypotheses. This function never
    discards a conflicting observation or searches for a favorable subset.
    """
    required = {"scenario", "rounding_half_width", "cell_means", "count_candidates", "aggregates",
                "contrast_positive_cells", "contrast_negative_cells", "assumptions", "excluded_claims"}
    if set(spec) != required:
        raise ValueError("unknown or missing specification field")
    half = finite(spec["rounding_half_width"])
    means = [finite(x) for x in spec["cell_means"]]
    if half < 0 or len(means) != 4 or len(spec["count_candidates"]) > 1000:
        raise ValueError("outside four-cell bounded reconstruction scope")
    positive, negative = spec["contrast_positive_cells"], spec["contrast_negative_cells"]
    for indexes in (positive, negative):
        if not indexes or len(set(indexes)) != len(indexes) or any(type(i) is not int or i not in range(4) for i in indexes):
            raise ValueError("invalid contrast indexes")
    if set(positive) & set(negative):
        raise ValueError("contrast groups overlap")
    feasible = []
    for candidate in spec["count_candidates"]:
        if len(candidate) != 4 or any(type(n) is not int or n < 1 for n in candidate):
            raise ValueError("positive integer cell counts required")
        counts = np.array(candidate, dtype=float)
        upper, limits = [], []
        for aggregate in spec["aggregates"]:
            if set(aggregate) != {"id", "cells", "mean"}:
                raise ValueError("unknown aggregate field")
            cells = aggregate["cells"]
            if not cells or len(set(cells)) != len(cells) or any(type(i) is not int or i not in range(4) for i in cells):
                raise ValueError("invalid aggregate indexes")
            weights = np.zeros(4)
            weights[cells] = counts[cells] / sum(counts[cells])
            target = finite(aggregate["mean"])
            upper.extend([weights, -weights])
            limits.extend([target + half, -target + half])
        objective = np.zeros(4)
        objective[positive] = counts[positive] / sum(counts[positive])
        objective[negative] = -counts[negative] / sum(counts[negative])
        args = {"A_ub": np.array(upper) if upper else None, "b_ub": np.array(limits) if limits else None,
                "bounds": [(m - half, m + half) for m in means], "method": "highs"}
        lo = linprog(objective, **args)
        hi = linprog(-objective, **args)
        if lo.status == 2 and hi.status == 2:
            continue
        if not lo.success or not hi.success:
            raise RuntimeError("LP solver did not establish bounds")
        feasible.append({"counts": candidate, "lower": float(lo.fun), "upper": float(-hi.fun)})
    return {"schema": "rounded-mean-reconstruction/v1", "version": VERSION, "scenario": spec["scenario"],
            "status": "CONDITIONAL_BOUNDS" if feasible else "INCONSISTENT_HOLD", "feasible": feasible,
            "lower": min((x["lower"] for x in feasible), default=None),
            "upper": max((x["upper"] for x in feasible), default=None),
            "assumptions": spec["assumptions"], "excluded_claims": spec["excluded_claims"],
            "source_truth_established": False, "semantic_acceptance": False,
            "production_authority": False}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "bounds"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    result = read_jats(options.input) if options.action == "inspect" else rounded_mean_model(json.loads(options.input.read_text()))
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if options.output:
        options.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
