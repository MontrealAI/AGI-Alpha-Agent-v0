# SPDX-License-Identifier: Apache-2.0
"""Post-confirmation row-order repair, preserving the exact conventional DP."""

import gc
import hashlib
import itertools
import json
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from ordering_reference import orbit_count

ROOT = Path(__file__).resolve().parent
PER_ORDER_SECONDS = 3.5
TOTAL_SECONDS = 89.0


class OrderTimeout(Exception):
    """This permutation exhausted its fixed execution budget."""


def alarm_handler(signum, frame):
    raise OrderTimeout("fixed per-permutation execution budget exhausted")


def run():
    case = json.loads((ROOT / "ordering_input.json").read_text())
    problem = case["problem"]
    orders = list(itertools.permutations(range(len(problem["rows"]))))
    protocol = {
        "declared_at": datetime.now(timezone.utc).isoformat(),
        "status": "post-confirmation diagnostic; neither held-out nor a new algorithm",
        "case": problem["name"], "orders": orders,
        "per_order_wall_seconds": PER_ORDER_SECONDS,
        "total_challenge_wall_seconds": TOTAL_SECONDS,
        "selection": "Exhaustively try all 24 row permutations in lexicographic order with equal execution budgets.",
        "fair_cost": "Order-search cost is the sum of all attempts, not the best successful attempt.",
        "max_states": 1000000,
        "reference_source_sha256": hashlib.sha256((ROOT / "ordering_reference.py").read_bytes()).hexdigest(),
        "harness_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (ROOT / "ordering_protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    started = time.perf_counter()
    signal.signal(signal.SIGALRM, alarm_handler)
    rows = []
    for order in orders:
        remaining = TOTAL_SECONDS - (time.perf_counter() - started)
        if remaining < PER_ORDER_SECONDS:
            rows.append({"order": order, "status": "not_run_total_budget"})
            continue
        began = time.perf_counter()
        try:
            signal.setitimer(signal.ITIMER_REAL, PER_ORDER_SECONDS)
            result = orbit_count(problem["rows"], problem["cols"], problem["caps"], row_order=order)
            result["count"] = str(result["count"])
            result["status"] = "complete"
            result["agrees_with_compiler"] = result["count"] == case["methods"]["compiler"]["count"]
        except OrderTimeout:
            result = {"status": "timeout"}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        result["order"] = order
        result["wall_seconds"] = time.perf_counter() - began
        rows.append(result)
        print(json.dumps(result), flush=True)
        gc.collect()
    completed = [r for r in rows if r["status"] == "complete"]
    summary = {
        "completed": len(completed),
        "timeouts": sum(r["status"] == "timeout" for r in rows),
        "not_run": sum(r["status"] == "not_run_total_budget" for r in rows),
        "all_completed_counts_agree": all(r["agrees_with_compiler"] for r in completed) if completed else None,
        "independent_corroboration_count": completed[0]["count"] if completed else None,
        "best_execution": min(completed, key=lambda r: r["wall_seconds"]) if completed else None,
        "same_input_order_execution": rows[0],
        "total_search_wall_seconds": time.perf_counter() - started,
        "compiler_confirmation_seconds": case["methods"]["compiler"]["seconds"],
        "original_conventional_confirmation_status": case["methods"]["orbit"],
        "fixed_general_heuristic_selected": False,
        "fresh_cases_required": False,
        "limits": "This adaptive all-order diagnostic measures order sensitivity on the already observed failure; it establishes no held-out speedup or general heuristic.",
    }
    result = {"protocol": protocol, "summary": summary, "attempts": rows}
    (ROOT / "ordering_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"summary": summary}, indent=2), flush=True)


if __name__ == "__main__":
    run()
