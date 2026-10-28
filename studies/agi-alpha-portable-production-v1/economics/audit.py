# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
F = Fraction

def audit(output: Path) -> dict[str, Any]:
    config = json.loads((ROOT / "inputs.json").read_text())
    results = json.loads((output / "results.json").read_text())
    scenarios = {s["name"]: s for s in config["scenarios"]}
    cost = config["costs_cents"]
    sums: dict[tuple[str, str, str], dict[str, Fraction]] = defaultdict(lambda: defaultdict(F))
    checks = 0
    rows = 0
    with gzip.open(output / "histories.csv.gz", "rt", newline="") as stream:
        for row in csv.DictReader(stream):
            rows += 1
            key = (row["scenario"], row["arrangement"], row["policy"])
            p = F(row["probability"])
            price = int(row["price_cents"])
            capital = int(row["capital_cents"])
            observations = row["observations"].split("|") if row["observations"] else []
            accepted_events = [e for e in observations if e.startswith(("clean_", "corrected_"))]
            failed_events = [e for e in observations if e.startswith("failed_")]
            booked = len(accepted_events) + len(failed_events)
            accepted = len(accepted_events)
            corrected = sum(e.startswith("corrected_") for e in observations) + len(failed_events)
            defaults = sum("_default_" in e for e in accepted_events)
            leads = sum(e != "lead_financing_blocked" for e in observations)
            finance_blocks = sum(e.endswith("financing_blocked") for e in observations)
            setup = booked if row["arrangement"] == "separate_preparation" else int(booked > 0)
            for field, expected in (("booked",booked),("accepted",accepted),("corrected",corrected),
                                    ("defaults",defaults),("leads",leads),("finance_blocks",finance_blocks),
                                    ("setups",setup),("failures",len(failed_events))):
                assert int(row[field]) == expected, (key, field, row)
                checks += 1
            per_execution = (cost["source_intake"] + cost["construction"] + cost["independent_digital_validation"]
                             + cost["handoff"] + cost["compute_storage"] + cost["permissions_administration"])
            deposit = price // 2
            fees = deposit // 50 * (booked + accepted - defaults)
            complete_cost = (leads * cost["lead_acquisition"] + setup * cost["additional_commercial_setup"]
                             + booked * per_execution + corrected * cost["one_correction"]
                             + accepted * cost["accepted_support"] + len(failed_events) * cost["failed_refund_administration"]
                             + int(row["expanded"]) * cost["selective_continuation_coordination"] + fees)
            bad_debt = defaults * (price - deposit)
            revenue = accepted * price
            collections = accepted * price - bad_debt
            profit = collections - complete_cost
            values = scenarios[row["scenario"]]["outside_option_values_cents"]
            customer_value = sum(values[int(e.rsplit("t",1)[1])] for e in accepted_events)
            customer_net = (customer_value - revenue - accepted * config["labor_reference"]["buyer_integration_cents"]
                            - len(failed_events) * config["labor_reference"]["buyer_failed_attempt_loss_cents"])
            expected = {"revenue_cents":revenue,"cost_cents":complete_cost,"bad_debt_cents":bad_debt,
                        "net_collections_cents":collections,"refunds_cents":len(failed_events)*deposit,
                        "prospective_profit_cents":profit,"end_cash_cents":capital+profit,
                        "illustrative_full_history_profit_cents":profit-cost["illustrative_historical_build_once"],
                        "customer_reference_value_cents":customer_value,"customer_net_benefit_cents":customer_net}
            for field, value in expected.items():
                assert int(row[field]) == value, (key, field, row[field], value)
                sums[key][field] += p * value
                checks += 1
            assert int(row["min_unrestricted_cents"]) >= config["offer"]["minimum_unrestricted_reserve_cents"]
            sums[key]["probability"] += p
            sums[key]["loss_probability"] += p * (profit < 0)
            sums[key]["finance_probability"] += p * bool(finance_blocks)
            checks += 2
    indexed = {}
    mapping = {"revenue":"revenue_cents","cost":"cost_cents","bad_debt":"bad_debt_cents",
               "collected":"net_collections_cents","refunded":"refunds_cents","profit":"prospective_profit_cents",
               "customer_value":"customer_reference_value_cents","customer_benefit":"customer_net_benefit_cents",
               "illustrative_full_history_profit":"illustrative_full_history_profit_cents","expected_end_cash":"end_cash_cents"}
    for cell in results["results"]:
        key = (cell["scenario"],cell["arrangement"],cell["policy"])
        indexed[key] = cell
        assert sums[key]["probability"] == 1
        for name, source in mapping.items():
            assert F(cell["expected"][name]["exact_cents"]) == sums[key][source], (key, name)
            checks += 1
        assert F(cell["prospective_loss_probability"]["exact"]) == sums[key]["loss_probability"]
        assert F(cell["finance_refusal_probability"]["exact"]) == sums[key]["finance_probability"]
        checks += 3
    for scenario in scenarios:
        for policy in config["policies"]:
            shared = indexed[(scenario,"conventional_shared",policy)]
            proposed = indexed[(scenario,"proposed_shared",policy)]
            for field in ("expected","expected_counts","prospective_loss_probability","finance_refusal_probability",
                          "expansion_probability","minimum_prospective_profit","maximum_prospective_profit"):
                assert shared[field] == proposed[field], (scenario, policy, field)
                checks += 1
    for arrangement in config["arrangements"]:
        stop = indexed[("public_source_zero_value_control",arrangement,"stop_now")]
        assert F(stop["expected"]["profit"]["exact_cents"]) == 0
        for policy in ("deliver_first_only","deliver_selectively"):
            cell = indexed[("public_source_zero_value_control",arrangement,policy)]
            assert F(cell["expected_counts"]["accepted"]) == 0
            assert F(cell["expected"]["revenue"]["exact_cents"]) == 0
            assert F(cell["expected"]["profit"]["exact_cents"]) == -cost["lead_acquisition"]
            checks += 3
    x = config["expansion"]
    ramp = sum(map(F,x["annual_adoption_fractions"]))
    benefit = x["population"] * ramp * x["illustrative_jobs_per_active_shop_year"] * x["illustrative_net_value_per_accepted_outcome_cents"]
    assert F(results["scale_and_retention"]["illustrative_ramp_net_customer_benefit"]["exact_cents"]) == benefit
    assert F(results["scale_and_retention"]["retention_incremental_value_vs_same_library"]["exact_cents"]) == 0
    assert results["actual"]["collections_cents"] == 0 and results["actual"]["actual_profit_cents"] is None
    checks += 3
    for name, sha in results["frozen_sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha
        checks += 1
    receipt = {"status":"PASS","auditor":"separate arithmetic reconstruction; no model.py import",
               "finite_history_rows":rows,"arithmetic_and_scope_assertions":checks,
               "matched_shared_cells":len(scenarios)*len(config["policies"]),
               "limitations":"An accounting audit does not calibrate demand, hours, model costs, acceptance probabilities, insurance adequacy or customer value.",
               "results_sha256":hashlib.sha256((output/"results.json").read_bytes()).hexdigest(),
               "histories_sha256":hashlib.sha256((output/"histories.csv.gz").read_bytes()).hexdigest()}
    (output/"independent_audit.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt))
    return receipt

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True,type=Path)
    audit(parser.parse_args().output)

