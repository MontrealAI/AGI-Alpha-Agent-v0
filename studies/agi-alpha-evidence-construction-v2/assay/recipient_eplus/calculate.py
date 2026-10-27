# SPDX-License-Identifier: Apache-2.0
"""Reconstruct requested contrasts from printed summaries; no outcome reanalysis."""
from pathlib import Path
import json
import math
import re
import sys
import numpy
import scipy
from scipy.stats import t

HERE = Path(__file__).resolve().parent
PACKET = Path("/workspace/scratch/9738c9c6b885/connected-fresh-curation/source_packet")
sys.path.insert(0, str(HERE / "recovered_capability"))
import evidence_engine as engine


def run() -> dict:
    """Read authoritative tables, qualify units, and return derived results."""
    a = engine.read_jats(PACKET / "pone.0272427.xml",
                         "f014df30f2f5c6190dbd10160b037621c886dc574d7b6f4534678b804b4275de")
    b = engine.read_jats(PACKET / "pone.0143177.xml")
    cells = a["tables"]["pone.0272427.t003"]["rows"][3]
    moments = []
    for column in (1, 2):
        match = re.fullmatch(r"\s*([\d.]+)\s*±\s*([\d.]+)\s*", cells[column])
        if match is None:
            raise ValueError("Unexpected Table 3 cell format")
        moments.append({"mean": float(match[1]), "sd": float(match[2]), "n": 30})
    ad = engine.mean_difference(moments[0], moments[1], design="independent_groups")
    v1, v2 = [g["sd"] ** 2 / g["n"] for g in moments]
    se = math.sqrt(v1 + v2)
    assert math.isclose(se, ad["se"])
    df = (v1 + v2) ** 2 / (v1 ** 2 / 29 + v2 ** 2 / 29)
    critical = float(t.ppf(0.975, df))
    ci = [ad["difference"] - critical * se, ad["difference"] + critical * se]
    short = engine.cell_value(b, "pone.0143177.t001", 1, 1, "mean")
    long = engine.cell_value(b, "pone.0143177.t001", 2, 1, "mean")
    ss = engine.cell_value(b, "pone.0143177.t001", 1, 1, "dispersion")
    ls = engine.cell_value(b, "pone.0143177.t001", 2, 1, "dispersion")
    # Point-only mode for dependent estimates; does not assert complete pairing.
    bd = engine.mean_difference({"mean": long["value"]}, {"mean": short["value"]},
                                design="paired_unknown_covariance")
    result = {
        "versions": {"python": sys.version, "numpy": numpy.__version__, "scipy": scipy.__version__},
        "source_sha256": {"A": a["source_sha256"], "B": b["source_sha256"]},
        "artifact_functions_invoked": ["read_jats", "cell_value", "mean_difference"],
        "A": {"moments": moments, "difference": ad["difference"], "se": se, "welch_df": df,
              "critical_t": critical, "ci95": ci, "mean_rounding_difference_bounds": [0.210, 0.230],
              "conditions": "Independent randomized participant groups; participant proportion SDs; fixed item set"},
        "B": {"short": short, "long": long, "short_uncertainty": {**ss, "qualified_kind": "SE"},
              "long_uncertainty": {**ls, "qualified_kind": "SE"}, "contrast": bd,
              "mean_rounding_difference_bounds": [0.006, 0.008],
              "variance_formula": "SE_L^2 + SE_S^2 - 2 Cov(L,S)",
              "covariance_identified": False, "ci95": None,
              "hold": "Missing joint covariance of dependent estimators and outcome overlap; marginal SEs insufficient"},
        "mission_rechecks": ["Public primary-source provenance and fixed target",
                              "A Experiment 1 correct responses, Feedback row only; SD footnote",
                              "A randomization between participants, 30 per cell; no actual yoking",
                              "B standardized within-student effects and matched crossover design",
                              "B outcome-specific missingness and common cohort",
                              "Semantic acceptance and production authority not conferred by engine flags"],
    }
    (HERE / "calculation_results.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
