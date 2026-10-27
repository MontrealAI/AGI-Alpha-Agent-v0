#!/usr/bin/env python3
"""Independent, read-only audit of retained Beyond Beta v2 outputs.

Never imports or executes the simulator. No new economic seeds are run. Input
files are not modified. The optional report is a small postfreeze analysis file.
All financial quantities concern simulated counterfactual enterprises.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

EXPECTED_PROTOCOL = "7cb1683c08090d68cef5e847438446dda8032b67163c5368c2cbdaddce180dcb"
B = {"retention_evaluation", "retention_extract_validate_package", "retention_creator_bounty",
     "skill_maintenance", "skill_distribution", "skill_revalidation", "moving_beta_alpha_reassessment",
     "network_access_overhead"}
C = {"investment_evaluation", "capability_search_build_confirm_migrate", "investment_creator_bounty"}
COMMON = {"setup", "infrastructure_access_storage"}
A = {"automated_intake", "production", "validation", "revalidation", "correction", "packaging",
     "failed_job_recovery", "refund_and_recovery"}
PAIRS = (("network", "beta"), ("network", "isolated"), ("network", "network_no_invest"), ("isolated", "beta"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cents(x):
    return round(float(x) * 100)


def read_json(path):
    return json.loads(Path(path).read_text())


def json_rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.endswith("\n"):
                raise ValueError(f"Incomplete JSONL line: {path}:{line_number}")
            yield json.loads(line)


def ci(xs):
    n = len(xs)
    mean = statistics.fmean(xs) if n else 0.0
    width = 1.96 * statistics.stdev(xs) / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": mean, "lower": mean - width, "upper": mean + width,
            "median": statistics.median(xs) if n else None,
            "min": min(xs) if n else None, "max": max(xs) if n else None}


class Checks:
    def __init__(self):
        self.counts = Counter()
        self.failures = []
        self.failed_count = 0

    def check(self, name, condition, context, expected=None, actual=None):
        self.counts[name] += 1
        if not condition:
            self.failed_count += 1
            if len(self.failures) < 250:
                self.failures.append({"check": name, "context": context, "expected": expected, "actual": actual})

    def eq(self, name, actual, expected, context):
        self.check(name, actual == expected, context, expected, actual)

    def near(self, name, actual, expected, context, tolerance=1e-7):
        self.check(name, math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=1e-10),
                   context, expected, actual)

    def result(self):
        return {"passed": self.failed_count == 0, "check_count": sum(self.counts.values()),
                "checks_by_type": dict(self.counts), "failure_count": self.failed_count,
                "failure_examples": self.failures, "failure_examples_truncated": self.failed_count > len(self.failures)}


def key(row):
    return row["scenario"], row["arm"], row["seed"]


def classification(category):
    if category in B:
        return "retention"
    if category in C:
        return "investment"
    if category in COMMON:
        return "common"
    if category in A:
        return "job"
    return "UNCLASSIFIED"


def work_cost(w, s):
    # Independently implement the declared billing convention from the catalog.
    if s["cache_enabled"]:
        tokens = (12.5*w["astra_input"] + w["astra_cache"] + 50*w["astra_output"]
                  + 1.25*w["terra_input"] + .05*w["terra_cache"] + 5*w["terra_output"])
    else:
        tokens = (10*(w["astra_input"]+w["astra_cache"]) + 50*w["astra_output"]
                  + w["terra_input"]+w["terra_cache"] + 5*w["terra_output"])
    return tokens*s["token_cost_factor"] + w["tools"]*s["tool_cost_factor"]


def audit_ledger(full, slim, scenario, catalog, checks):
    label = list(key(full))
    by_week = defaultdict(list)
    for row in full["ledger"]:
        by_week[row["week"]].append(row)
    weeks = [r["week"] for r in full["ledger"]]
    checks.eq("ledger_chronology", weeks, sorted(weeks), label)
    weekly = {r["week"]: r for r in full["weekly"]}
    cash = seed = collections = paid_total = accrued = unpaid = 0
    committed, warranty, reserves = {}, {}, {}
    books, categories = Counter(), Counter()
    job_expenses, source_collections = defaultdict(list), defaultdict(list)
    min_cash = None
    final_week = max([0, *by_week, *weekly])
    for week in range(final_week + 1):
        warranty = {k: v for k, v in warranty.items() if v[1] > week}
        for row_index, row in enumerate(by_week[week]):
            context = [*label, week, row_index]
            kind, amount = row["kind"], row["amount_cents"]
            checks.check("nonnegative_amount", isinstance(amount, int) and amount >= 0, context, actual=amount)
            if kind == "seed":
                checks.eq("one_seed", seed, 0, context)
                seed = amount
                cash += amount
            elif kind == "reserve":
                identifier = row["key"]
                reserved_before = sum(committed.values()) + sum(v[0] for v in warranty.values())
                checks.check("cash_before_commitment", amount <= cash-reserved_before-unpaid, context,
                             cash-reserved_before-unpaid, amount)
                checks.check("no_duplicate_commitment", identifier not in committed, context)
                reserves[identifier] = {"week": week, "amount": amount, "cash": cash,
                                        "reserved_before": reserved_before, "unpaid": unpaid,
                                        "earned_cash": collections-paid_total}
                committed[identifier] = amount
            elif kind == "release":
                checks.eq("release_amount", amount, committed.pop(row["key"], 0), context)
            elif kind == "expense":
                category, identifier = row["category"], row.get("key", "")
                if category == "refund_and_recovery":
                    warranty.pop(identifier.removeprefix("refund-"), None)
                if identifier in committed:
                    checks.check("expense_within_commitment", amount <= committed[identifier], context,
                                 committed[identifier], amount)
                    committed[identifier] -= amount
                payment = row["paid_cents"]
                checks.check("payment_within_expense", 0 <= payment <= amount, context, amount, payment)
                protected = sum(committed.values()) + sum(v[0] for v in warranty.values())
                checks.check("payment_respects_protected_cash", payment <= max(0, cash-protected), context,
                             max(0, cash-protected), payment)
                cash -= payment
                paid_total += payment
                accrued += amount
                unpaid += amount-payment
                book = classification(category)
                checks.check("known_expense_category", book != "UNCLASSIFIED", context, actual=category)
                checks.eq("expense_book_once", row.get("book"), book, context)
                books[book] += amount
                categories[category] += amount
                if identifier.startswith("job-"):
                    job_expenses[int(identifier[4:])].append(row)
            elif kind == "collection":
                cash += amount
                collections += amount
                source_collections[int(row["key"])].append({"week": week, "amount_cents": amount})
                if scenario["warranty_weeks"]:
                    warranty[row["key"]] = (round(amount*.15), week+scenario["warranty_weeks"])
            else:
                checks.check("known_transaction_kind", False, context, actual=kind)
            checks.eq("transaction_cash", row["cash_cents"], cash, context)
            checks.check("nonnegative_cash", cash >= 0, context, actual=cash)
            if "reserved_cents" in row:
                checks.eq("transaction_reserved", row["reserved_cents"],
                          sum(committed.values())+sum(v[0] for v in warranty.values()), context)
        if week in weekly:
            w = weekly[week]
            reserve = sum(committed.values())+sum(v[0] for v in warranty.values())
            checks.eq("weekly_cash", cents(w["cash"]), cash, [*label, week])
            checks.eq("weekly_commitment_and_warranty", cents(w["committed"]), reserve, [*label, week])
            checks.eq("weekly_available", cents(w["available"]), max(0, cash-reserve-unpaid), [*label, week])
            checks.check("input_quota", w["input_m"] <= scenario["quota_input_m"]+1e-5, [*label, week])
            checks.check("output_quota", w["output_m"] <= scenario["quota_output_m"]+1e-5, [*label, week])
            min_cash = cash if min_cash is None else min(min_cash, cash)
    checks.eq("seed_total", seed, cents(slim["seed_capital"]), label)
    checks.eq("cash_identity", cash, seed+collections-paid_total, label)
    checks.eq("reported_cash", cents(slim["cash"]), cash, label)
    checks.eq("reported_collections", cents(slim["collections"]), collections, label)
    checks.eq("reported_accrued_expenses", cents(slim["expenses"]), accrued, label)
    checks.eq("expense_books_partition", sum(books.values()), accrued, label)
    for book in ("job", "retention", "investment", "common"):
        checks.eq("reported_book_total", cents(slim["cost_books"][book]), books[book], [*label, book])
    checks.eq("reported_categories", {k:cents(v) for k,v in slim["costs"].items()}, dict(categories), label)
    outstanding = sum(committed.values())
    inferred_refunds = cents(slim["closing_obligations"])-unpaid-outstanding
    checks.check("closing_refunds_nonnegative", inferred_refunds >= 0, label, actual=inferred_refunds)
    checks.eq("profit_cash_obligations_identity", cents(slim["profit"]),
              cash-seed-cents(slim["closing_obligations"]), label)
    checks.eq("profit_accrual_identity", cents(slim["profit"]),
              collections-accrued-outstanding-inferred_refunds, label)
    checks.eq("reported_available_cash", cents(slim["available_cash"]),
              max(0, cash-outstanding-sum(v[0] for v in warranty.values())-unpaid), label)
    checks.eq("reported_min_cash", cents(slim["min_cash"]), min_cash, label)

    outcomes = {r["job"]: r for r in full["outcomes"]}
    checks.eq("unique_outcome_ids", len(outcomes), len(full["outcomes"]), label)
    counts = {"completed": len(outcomes), "accepted_useful": sum(bool(r["useful"]) for r in outcomes.values()),
              "false_passes": sum(bool(r["delivered"] and not r["true_correct"]) for r in outcomes.values()),
              "late": sum(bool(r["late"]) for r in outcomes.values()),
              "abstentions": sum(not r["delivered"] for r in outcomes.values()),
              "recipient_useful": sum(bool(r["useful"] and r["transferred"] > 0) for r in outcomes.values())}
    for name, number in counts.items():
        checks.eq("reported_outcome_count", slim["stats"].get(name, 0), number, [*label, name])
    learning_memo = 0
    for job, outcome in outcomes.items():
        context = [*label, "job", job]
        direct = sum(r["amount_cents"] for r in job_expenses[job] if r["category"] != "failed_job_recovery")
        checks.eq("outcome_direct_accrued_cost", cents(outcome["job_direct_cost"]), direct, context)
        memo = cents(outcome["learning_cost_already_in_job"])
        checks.check("learning_subset_not_extra_expense", 0 <= memo <= direct, context, direct, memo)
        learning_memo += memo
        for receipt in source_collections[job]:
            checks.check("collection_after_delivery", outcome["delivered"] and receipt["week"] >= outcome["week"], context)
            checks.eq("collection_delay", receipt["week"], outcome["week"]+scenario["collection_delay"], context)
            checks.eq("collection_matches_price", receipt["amount_cents"], cents(outcome["price"]), context)
    checks.eq("reported_learning_memo", cents(slim["paid_job_learning_cost_memo"]), learning_memo, label)

    campaign_counts = Counter()
    fixed = 105+30*scenario["validator_slots"]+40*scenario["agents"]
    fixed += (35 if slim["arm"] in {"isolated", "beta", "no_retention"}
              else scenario["distribution_fixed"]+scenario["membership_count"]*scenario["member_overhead"])
    source_ids = set()
    for book, records in (("retention", slim["retention_records"]), ("investment", slim["investments"])):
        checks.eq("campaign_count", slim[book+"_count"], len(records), [*label, book])
        for record in records:
            context = [*label, book, record["id"]]
            ids = set(record["source_jobs"])
            source_ids.update(ids)
            checks.eq("no_A_recharge", record["paid_job_cost_recharged"], 0, context)
            memo = sum(sum(r["amount_cents"] for r in job_expenses[j]) for j in ids)
            checks.eq("source_cost_memo_is_accrued", cents(record["source_job_paid_cost"]), memo, context)
            packet = "RETENTION" if book == "retention" else "CONSTRUCTION"
            factor = scenario["retention_cost_factor" if book == "retention" else "construction_cost_factor"]
            expected = sum(work_cost(catalog[packet][k[1]], scenario) for k in record["skills"])*factor
            expected += len(record["skills"])*scenario["sharing_bounty"]
            checks.check("campaign_budget_prices_only_correct_packet", abs(cents(record["cost"])-cents(expected)) <= 1,
                         context, cents(expected), cents(record["cost"]))
            checks.eq("prospective_retention_amount", cents(record["prospective_incremental_retention"]),
                      cents(record["cost"]) if book == "retention" else 0, context)
            reserve = reserves.get(record["id"])
            checks.check("campaign_was_prefunded", reserve is not None, context)
            if reserve:
                checks.eq("campaign_reserve_amount", reserve["amount"], cents(record["cost"]), context)
                checks.eq("campaign_reserve_time", reserve["week"], record["week"], context)
                checks.eq("campaign_earned_cash_before", cents(record["earned_cash_before"]), reserve["earned_cash"], context)
                available = max(0, reserve["cash"]-reserve["reserved_before"]-reserve["unpaid"]
                                -cents(fixed*slim["policy"]["reserve_weeks"]))
                checks.eq("campaign_available_before", cents(record["available_before"]), available, context)
                checks.check("campaign_share_of_available_cash", reserve["amount"] <= available*slim["policy"]["max_investment_share"]+1, context)
                funding = "operating-surplus" if reserve["earned_cash"] >= reserve["amount"] else "seed-or-mixed"
                checks.eq("campaign_funding_label", record["funding_basis"], funding, context)
            source_states = []
            for job in ids:
                outcome = outcomes.get(job)
                checks.check("campaign_has_prior_delivered_source", bool(outcome and outcome["delivered"] and outcome["week"] <= record["week"]), [*context, job])
                receipts = source_collections.get(job, [])
                state = ("collected_before_or_at_retention" if any(r["week"] <= record["week"] for r in receipts)
                         else "collected_after_retention" if receipts else "not_collected_by_close")
                source_states.append(state)
                campaign_counts[book+"_source_links_"+state] += 1
            campaign_counts[book+"_campaigns"] += 1
            campaign_counts[book+"_funding_"+record["funding_basis"]] += 1
            if all(s == "collected_before_or_at_retention" for s in source_states):
                campaign_counts[book+"_all_sources_collected_at_decision"] += 1
    return {"scenario": slim["scenario"], "arm": slim["arm"], "seed": slim["seed"],
            "cash_identity_residual_cents": cash-seed-collections+paid_total,
            "unpaid_accrued_cents": unpaid, "closing_commitments_cents": outstanding,
            "inferred_unexpensed_future_refunds_cents": inferred_refunds,
            "cost_books_cents": dict(books), "learning_memo_cents_not_added": learning_memo,
            "unique_source_jobs_in_authorized_campaigns": len(source_ids),
            "source_job_timing_counts": dict(campaign_counts),
            "outcomes": counts}


def training_audit(results, manifest, selected, checks):
    grouped, seen = defaultdict(list), set()
    policies = {p["name"]: p for p in manifest["policy_candidates"]}
    expected = {(s,p,seed) for s in manifest["scenarios"] for p in policies for seed in manifest["training_seeds"]}
    for r in json_rows(results/"training_runs.jsonl"):
        identity = (r["scenario"], r["policy"]["name"], r["seed"])
        checks.check("unique_training_world_policy", identity not in seen, list(identity))
        seen.add(identity)
        checks.eq("training_policy_frozen", r["policy"], policies.get(r["policy"]["name"]), list(identity))
        checks.eq("training_arm", r["arm"], "network", list(identity))
        grouped[identity[:2]].append((r["profit"], bool(r["stats"].get("cash_shortfall"))))
    checks.eq("complete_training_set", sorted(seen), sorted(expected), "training")
    reselected = {}
    for scenario in manifest["scenarios"]:
        candidates = []
        for name, p in policies.items():
            rows = grouped[scenario, name]
            if rows and sum(x[1] for x in rows)/len(rows) <= .05:
                candidates.append((statistics.fmean(x[0] for x in rows), p))
        checks.check("some_training_policy_feasible", bool(candidates), scenario)
        if not candidates:
            continue
        best = max(x[0] for x in candidates)
        winner = min((p for mean,p in candidates if best-mean <= 1),
                     key=lambda p:(p["invest"],p["retain_skills"],p["name"]))
        reselected[scenario] = winner
        checks.eq("selection_independently_reproduced", selected["policies"][scenario], winner, scenario)
    checks.eq("selection_training_hash", selected["training_results_sha256"], sha(results/"training_runs.jsonl"), "training")
    checks.eq("selection_protocol_hash", selected["protocol_sha256"], sha(results/"protocol_freeze.json"), "training")
    return {"rows":len(seen), "reselected_policies":reselected}


def recovery_audit(results, checks, study_root):
    receipt_path = results/"training_interruption.json"
    if not receipt_path.exists():
        return {"present":False}
    receipt = read_json(receipt_path)
    original_path = results/"interrupted_training_runs.jsonl"
    if not original_path.exists():
        original_path = study_root/"evidence/development/infrastructure-v2/interrupted_training_runs.jsonl"
    original = original_path.read_bytes()
    checks.eq("interruption_original_hash", sha(original_path), receipt["interrupted_sha256"], "recovery")
    offset = 0
    rows = []
    for line in original.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            break
        rows.append(json.loads(line))
        offset += len(line)
    checks.eq("interruption_complete_rows", len(rows), receipt["complete_prefix_rows"], "recovery")
    checks.eq("interruption_prefix_bytes", offset, receipt["complete_prefix_bytes"], "recovery")
    checks.eq("interruption_tail_bytes", len(original)-offset, receipt["incomplete_tail_bytes"], "recovery")
    checks.eq("interruption_tail_hash", hashlib.sha256(original[offset:]).hexdigest(), receipt["incomplete_tail_sha256"], "recovery")
    with (results/"training_runs.jsonl").open("rb") as stream:
        resumed_prefix = stream.read(offset)
    checks.eq("recovered_prefix_byte_identical", hashlib.sha256(resumed_prefix).hexdigest(),
              hashlib.sha256(original[:offset]).hexdigest(), "recovery")
    checks.eq("recovery_no_source_change_claim", receipt["frozen_source_modified"], False, "recovery")
    checks.eq("recovery_no_selection_change_claim", receipt["selection_or_seed_changes"], False, "recovery")
    checks.eq("recovery_finished_hash", receipt.get("resumed_training_sha256"), sha(results/"training_runs.jsonl"), "recovery")
    return {**receipt, "audited_interrupted_file":str(original_path),
            "audited_interrupted_file_sha256":sha(original_path)}


def audit(results, study_root):
    checks = Checks()
    manifest = read_json(results/"protocol_freeze.json")
    checks.eq("expected_protocol_identity", sha(results/"protocol_freeze.json"), EXPECTED_PROTOCOL, "protocol")
    for relative, digest in manifest["source_hashes"].items():
        checks.eq("frozen_source_identity", sha(study_root/relative), digest, relative)
    selected = read_json(results/"selected_policies.json")
    training = training_audit(results, manifest, selected, checks)
    recovery = recovery_audit(results, checks, study_root)
    summary = read_json(results/"summary.json")
    catalog = read_json(study_root/"sources/workload_catalog.json")["values"]
    slim_rows, index = [], {}
    for row in json_rows(results/"confirmation_runs.jsonl"):
        checks.check("unique_confirmation_identity", key(row) not in index, list(key(row)))
        index[key(row)] = row
        slim_rows.append(row)
        checks.eq("confirmation_uses_selected_policy", row["policy"], selected["policies"][row["scenario"]], list(key(row)))
    expected = {(s,a,n) for s in manifest["scenarios"] for a in manifest["arms"] for n in manifest["confirmation_seeds"]}
    checks.eq("complete_confirmation_set", sorted(index), sorted(expected), "confirmation")
    audited, seen = [], set()
    for full in json_rows(results/"confirmation_ledgers.jsonl.gz"):
        identity = key(full)
        checks.check("unique_ledger_identity", identity not in seen, list(identity))
        seen.add(identity)
        checks.check("ledger_has_summary", identity in index, list(identity))
        if identity in index:
            audited.append(audit_ledger(full,index[identity],manifest["scenarios"][identity[0]],catalog,checks))
    checks.eq("all_confirmation_ledgers_present", sorted(seen), sorted(expected), "ledgers")
    pairs, groups = {}, {}
    for scenario in manifest["scenarios"]:
        pairs[scenario], groups[scenario] = {}, {}
        for arm in manifest["arms"]:
            rows = [r for r in slim_rows if r["scenario"] == scenario and r["arm"] == arm]
            result = {}
            for metric in ("profit","cash","collections","expenses","closing_obligations","available_cash",
                           "retention_count","retention_cost","investment_count","investment_cost","paid_useful_source_jobs",
                           "recipient_exposed_valid_skills","skills_used_on_useful_recipient_jobs","reused_skills"):
                result[metric] = ci([r.get(metric,0) for r in rows])
                official = summary["scenarios"][scenario][arm].get(metric)
                if official:
                    for field in ("n","mean","lower","upper"):
                        checks.near("summary_numeric_reproduction",official[field],result[metric][field],[scenario,arm,metric,field])
            result["accepted_useful"] = ci([r["stats"].get("accepted_useful",0) for r in rows])
            result["recipient_useful"] = ci([r["stats"].get("recipient_useful",0) for r in rows])
            result["cash_shortfall_runs"] = sum(bool(r["stats"].get("cash_shortfall")) for r in rows)
            result["books"] = {b:ci([r["cost_books"][b] for r in rows]) for b in ("job","retention","investment","common")}
            result["source_timing_counts_across_counterfactual_runs"] = dict(sum((Counter(r["source_job_timing_counts"]) for r in audited if r["scenario"]==scenario and r["arm"]==arm),Counter()))
            groups[scenario][arm] = result
        for treatment,control in PAIRS:
            name = treatment+"-minus-"+control
            pair = {}
            for metric in ("profit","accepted_useful","recipient_useful"):
                values = []
                for seed in manifest["confirmation_seeds"]:
                    t,c = index[scenario,treatment,seed],index[scenario,control,seed]
                    values.append(t[metric]-c[metric] if metric=="profit" else t["stats"].get(metric,0)-c["stats"].get(metric,0))
                pair[metric] = ci(values)
                if metric in summary["paired"][scenario][name]:
                    for field in ("n","mean","lower","upper"):
                        checks.near("paired_summary_reproduction",summary["paired"][scenario][name][metric][field],pair[metric][field],[scenario,name,metric,field])
            pairs[scenario][name] = pair
    # The 12 full sample traces permit extra admission/source checks; the full
    # 768-run ledger archive alone does not retain the skill list or events.
    sample_checks = []
    for path in sorted((results/"samples").glob("*.json")):
        r = read_json(path)
        ids = {s["source_job"] for s in r["skills"]}
        outcomes = {x["job"]:x for x in r["outcomes"]}
        collected = {int(x["key"]) for x in r["ledger"] if x["kind"]=="collection"}
        paid_useful = sum(bool(outcomes.get(j,{}).get("useful") and j in collected) for j in ids)
        checks.eq("sample_paid_useful_source_jobs",r["paid_useful_source_jobs"],paid_useful,list(key(r)))
        sample_checks.append({"file":str(path.relative_to(results)),"admitted_source_jobs":len(ids),
                              "useful_collected_source_jobs":paid_useful})
    required = ["protocol_freeze.json","selected_policies.json","training_runs.jsonl","confirmation_runs.jsonl",
                "confirmation_ledgers.jsonl.gz","summary.json"]
    optional = ["training_interruption.json","interrupted_training_runs.jsonl","policy_search.json"]
    consumed = [results/p for p in required+optional if (results/p).exists()]+sorted((results/"samples").glob("*.json"))
    file_manifest = {str(p.relative_to(results)):{"bytes":p.stat().st_size,"sha256":sha(p)} for p in consumed}
    return {"schema":"beyond-beta.postfreeze-output-audit/1","source_kind":"independent-analysis-of-simulated-records",
            "created_utc":datetime.now(timezone.utc).isoformat(),"audit_source_sha256":sha(Path(__file__)),
            "protocol_sha256":sha(results/"protocol_freeze.json"),"checks":checks.result(),
            "training":training,"interruption":recovery,"confirmation_rows":len(slim_rows),
            "audited_full_ledgers":len(audited),"groups":groups,"paired":pairs,
            "ledger_reconciliation":audited,"sample_admission_checks":sample_checks,"consumed_result_manifest":file_manifest,
            "limitations":[
                "All dollars, jobs, collections, retention and admissions describe simulations, not realized activity.",
                "The audit runs no new economic seeds and imports no simulator code; it checks retained outputs and frozen source identities.",
                "Future unexpensed refunds are inferred from closing obligations; the complete future receipt/refund schedule is not retained in every ledger record.",
                "Source-job direct cost excludes shared overhead and is not proof of full job profitability; paid_cost labels are accrued-cost memos.",
                "Source timing is audited for authorized campaigns in every run; admitted-skill/source collection joins are independently reconstructed only for the 12 complete sample traces.",
                "Counts summed across counterfactual worlds are audit totals, not a combined operating enterprise or independent customer observations.",
                "Monte Carlo intervals concern seed sampling within the assumed model; the audit does not establish real demand, quality or scope-equivalent human prices."]}


def self_test():
    c = Checks()
    c.eq("normal_identity",1000+200-100,1100,"fixture")
    c.eq("deliberately_tampered_identity",1000+200-101,1100,"fixture")
    assert c.failed_count == 1 and c.failures[0]["check"] == "deliberately_tampered_identity"
    assert classification("retention_extract_validate_package")=="retention"
    assert classification("production")=="job" and classification("capability_search_build_confirm_migrate")=="investment"
    assert classification("unknown") == "UNCLASSIFIED"
    assert ci([1,2,3])["mean"] == 2
    return {"passed":True,"scope":"audit arithmetic/error detection only; no simulated world executed"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results",type=Path)
    parser.add_argument("--study-root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test()))
        return
    if args.results is None or args.out is None:
        parser.error("--results and --out are required unless --self-test is used")
    if args.out.exists():
        raise FileExistsError("Refusing to overwrite a retained audit report")
    report=audit(args.results,args.study_root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"report":str(args.out),"passed":report["checks"]["passed"],
                      "checks":report["checks"]["check_count"],"failures":report["checks"]["failure_count"],
                      "full_ledgers":report["audited_full_ledgers"]}))
    if not report["checks"]["passed"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
