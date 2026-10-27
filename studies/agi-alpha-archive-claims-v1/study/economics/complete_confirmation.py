#!/usr/bin/env python3
"""Reporting-only completion for the frozen runner's missing zero-event counter.

Preserves runner.py, config.json, policy and raw confirmation outcomes unchanged.
On a clean reproduction it invokes frozen confirm; on the existing study it only
reads preserved results. No price selection or fresh random sampling occurs here.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("frozen_economics", HERE / "runner.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
policy = model.frozen_policy()
raw_path = model.RESULTS / "confirmation.json"

if not raw_path.exists():
    try:
        model.confirm()
    except KeyError as error:
        if str(error) != "'contracts'" or not raw_path.exists():
            raise

raw_bytes = raw_path.read_bytes()
raw = json.loads(raw_bytes)
rows = raw["rows"]
count_fields = ["contracts", "capacity_rejections", "willing_origins", "source_fit_origins",
                "unsupported_origins", "useful_accepted_deliveries", "open_contracts"]
normalized_rows = []
repairs = []
for row in rows:
    row = dict(row)
    for key in count_fields:
        if key not in row:
            row[key] = 0.0
            repairs.append({"scenario": row["scenario"], "field": key, "structural_zero": True})
    normalized_rows.append(row)


def new_json(name, data):
    p = model.RESULTS / name
    if not p.exists():
        model.write_json(p, data)


def new_csv(name, data):
    p = model.RESULTS / name
    if not p.exists():
        model.write_csv(p, data)


new_json("reporting_failure_record.json", {
    "failure": "KeyError('contracts') while formatting per-origin rows after all confirmation simulations and raw saves completed",
    "correction": "Supply structural zero event counters in a separate derived report; frozen model and raw outcomes unchanged",
    "repairs": repairs, "raw_confirmation_sha256": hashlib.sha256(raw_bytes).hexdigest(),
    "prices_changed": False, "parameters_changed": False, "random_draws_changed": False,
    "selection_or_outcome_tuning": False})
new_json("confirmation_reporting_normalized.json", {**raw, "rows": normalized_rows,
          "reporting_only_structural_zero_repairs": repairs,
          "raw_confirmation_sha256": hashlib.sha256(raw_bytes).hexdigest()})
per_origin = []
for row in normalized_rows:
    per_origin.append({"scenario": row["scenario"], "price": policy["price"],
                       **{k: row[k] / row["origins"] for k in ["contracts", "useful_accepted_deliveries",
                          "collected_modeled_cash", "earned_modeled_revenue",
                          "operating_expense_before_finance", "bad_debt", "financing_cost", "operating_profit"]}})
new_csv("expected_per_origin.csv", per_origin)
category_keys = sorted(set(k for row in normalized_rows for k in row if k.startswith("A_")))
new_csv("cost_categories.csv", [{"scenario": r["scenario"], **{k: r.get(k, 0) for k in category_keys},
        "bad_debt": r["bad_debt"], "financing_cost": r["financing_cost"]} for r in normalized_rows])
new_csv("attribution_null_and_library_parity.csv", [{"scenario": r["scenario"],
        "E_profit": r["operating_profit"], "U_profit": r["operating_profit"],
        "ordinary_library_profit": r["operating_profit"], "E_minus_U": 0,
        "E_minus_identical_content_library": 0,
        "basis": "declared identical economics; no measured operational advantage"} for r in normalized_rows])
if not (model.RESULTS / "first_confirmation_campaign_ledger.json").exists():
    summary, ledger = model.campaign(model.CFG["scenarios"]["baseline"], policy["price"],
                                    model.CFG["confirmation_seed"], retain_ledger=True)
    new_json("first_confirmation_campaign_ledger.json", {"summary": summary, "ledger": ledger,
             "not_selected_for_favorability": True, "deterministic_replay_of_first_preserved_seed": True})
assert raw_path.read_bytes() == raw_bytes
print(json.dumps({"reporting_completed": True, "structural_zero_repairs": repairs,
                  "frozen_model_unchanged": True, "raw_confirmation_unchanged": True}, indent=2))
