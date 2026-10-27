# SPDX-License-Identifier: Apache-2.0
"""Verify preserved originals and exact HOLD/control relations after confirmation."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "value_results"


def main():
    rows = json.loads((OUT / "confirmation.json").read_text())
    frozen = json.loads((OUT / "VALUE_FREEZE.json").read_text())
    keyed = {(row["profile"], row["seed"], row["policy"], row["controller"]): row for row in rows}
    omitted = {"policy", "requested_policy", "operative_policy", "controller_mode"}
    held = parity = controls = 0
    for row in rows:
        assert row["cash_cents"] == row["seed_capital_cents"] + row["profit_cents"]
        assert row["profit_cents"] == row["net_collections_cents"] - row["total_cost_cents"]
        assert row["accepted"] + row["failed"] == row["attempted"]
        assert row["actual_profit_cents"] is None and row["actual_complete_cost_cents"] is None
        if row["controller"] != "value_selected":
            continue
        if row["policy"] in ("private_retention", "shared_retention", "library_retention"):
            expert = keyed[row["profile"], row["seed"], "expert_E", "value_selected"]
            assert {k: v for k, v in row.items() if k not in omitted} == {
                k: v for k, v in expert.items() if k not in omitted
            }
            held += 1
        if row["policy"] == "shared_retention":
            library = keyed[row["profile"], row["seed"], "library_retention", "value_selected"]
            assert {k: v for k, v in row.items() if k not in omitted} == {
                k: v for k, v in library.items() if k not in omitted
            }
            parity += 1
        if row["policy"] in ("ordinary_U", "expert_E", "enhanced_Eplus"):
            previous = keyed[row["profile"], row["seed"], row["policy"], "original_selected"]
            assert {k: v for k, v in row.items() if k != "controller"} == {
                k: v for k, v in previous.items() if k != "controller"
            }
            controls += 1
    boundaries = {
        name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest
        for name, digest in frozen["bindings"].items()
    }
    assert all(boundaries.values())
    report = {
        "histories": len(rows),
        "accounting_identities_checked": len(rows),
        "held_histories_exact_E": held,
        "graph_library_equal_pairs": parity,
        "control_histories_unchanged": controls,
        "original_confirmation_unchanged": True,
        "source_boundaries_unchanged": boundaries,
        "freeze_sha256": hashlib.sha256((OUT / "VALUE_FREEZE.json").read_bytes()).hexdigest(),
        "limitation": "Summary/accounting identities and immutable-source checks; not independent market validation.",
    }
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
