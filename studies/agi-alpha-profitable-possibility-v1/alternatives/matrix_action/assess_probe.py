# SPDX-License-Identifier: Apache-2.0
"""Record the stronger historical disk comparator after primary-source review.

The C=2 disk program is identical to general_crouzeix_2 in the raw probe:
the theorem justifying that bound predates 2026. No benchmark is rerun or
silently relabeled; this separate assessment preserves the original record.
"""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
raw_path = root / "matrix_probe_results.json"
raw = json.loads(raw_path.read_text())
rows = raw["rows"]
candidate = [r["methods"]["general_crouzeix_2"]["degree_matvecs"] for r in rows]
conventional = [min(r["methods"]["general_crouzeix_2"]["degree_matvecs"],
                    r["methods"]["conventional_norm_or_special"]["degree_matvecs"])
                for r in rows]
assessment = {
    "raw_results_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    "decision": "REJECT_AS_FLAGSHIP_INVENTION",
    "reason": "The produced C=2 disk Taylor action already follows from classical complete disk bounds; scalar Crouzeix 2 was also public in August 2026.",
    "classical_disk_comparator": {
        "operation": "Exactly the same select_degree(radius, shift, tolerance, 2.0) and polynomial_action call as the candidate.",
        "source": "https://www.math.uwaterloo.ca/~krdavids/Preprints/DPWnum_range.pdf",
        "location": "Introduction, printed pages 3-4, reviewing Berger and Okubo-Ando.",
        "same_program_production_cost": True,
    },
    "strong_conventional_portfolio": {
        "methods": ["Classical numerical-radius disk bound C=2", "Operator norm Taylor C=1", "Normal-matrix C=1", "Jordan nilpotency"],
        "candidate_degree_wins": sum(x < y for x, y in zip(candidate, conventional)),
        "candidate_degree_ties": sum(x == y for x, y in zip(candidate, conventional)),
        "candidate_degree_losses": sum(x > y for x, y in zip(candidate, conventional)),
        "selection_overhead": "Portfolio minimum is a degree comparison, not a claimed measured optimal end-to-end runtime. Identical classical disk program alone establishes candidate parity.",
    },
    "new_complete_scope_unused": True,
    "total_roundoff_certificate_implemented": False,
    "prior_scalar_proof": "https://arxiv.org/html/2608.03841v2",
    "future_reopen_condition": "A concrete matrix-valued non-disk production task using the new complete scope, with a useful execution gain over current specialized methods and total error accounting.",
}
(root / "matrix_probe_assessment.json").write_text(json.dumps(assessment, indent=2) + "\n")
print(json.dumps(assessment, indent=2))
