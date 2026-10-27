# SPDX-License-Identifier: Apache-2.0
"""Build the publication claim map from existing study evidence; no network or models.

Run again after the final publication/evidence refresh. This script validates paths
and records hashes; it does not manufacture missing validation or buyer evidence.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def ref(name):
    p = ROOT / name
    assert p.is_file() and p.resolve().is_relative_to(ROOT), name
    return {"path": name, "sha256": sha(p)}


def references(names):
    return [ref(n) for n in dict.fromkeys(names)]


def existing(names):
    return [n for n in names if (ROOT / n).is_file()]


def main():
    now = datetime.now(timezone.utc).isoformat()
    protocol = read("protocol.json")
    econ = read("economics/results/summary.json")
    central = next(s for s in econ["scenarios"] if s["scenario"] == "central")
    repeat = read("evidence/independent-repeatability.json")
    native = read("evidence/native_execution.json")
    bindings = read("evidence/native_inputs.json")["bindings"]
    numerical_checker = sha(ROOT / "scripts/independent_checks.py")
    assert numerical_checker == "ef7f5bcec0fd21aaca812ca0ea1149791fc755a0cbf4bf81f779ddac2665f715"
    assert sha(ROOT / "economics/inputs.json") == econ["input_sha256"]
    cases = [p[:-6] for p in protocol["selection"]["confirmation"]]
    case_refs, case_rows = [], []
    for case in cases:
        notebook = f"deliveries/{case}/recovered.ipynb"
        pair = [f"evidence/independent-{run}-{case}.json" for run in ["first", "second"]]
        reports = [read(p) for p in pair]
        for r in reports:
            assert r["sha256"] == sha(ROOT / notebook)
            assert r["checker_sha256"] == numerical_checker
            assert r["accepted"] and r["all_cells_completed"]
            assert all(c["pass"] for c in r["checks"])
        assert reports[0]["checks"] == reports[1]["checks"]
        case_refs.extend([notebook, f"deliveries/{case}/identity.json", *pair])
        case_rows.append({"case": case, "code_cells": reports[0]["executed_code_cells"],
                          "distinct_checks": len(reports[0]["checks"]), "fresh_runs": 2,
                          "notebook_sha256": sha(ROOT / notebook)})
    assert sum(c["code_cells"] for c in case_rows) == 133
    assert sum(c["distinct_checks"] for c in case_rows) == 38
    assert repeat["accepted"] and len(cases) == 4

    graphical_path = "evidence/independent-plot-visual-review.json"
    graphical = read(graphical_path) if (ROOT / graphical_path).exists() else {}
    graphical_ok = graphical.get("all16_pass") is True
    if graphical_ok:
        assert len(graphical["images"]) == 16
        for row in graphical["images"]:
            assert row["status"] == "pass" and sha(ROOT / row["path"]) == row["sha256"]
    stale_native = []
    for row in bindings["cases"]:
        for item in row["delivery_files"] + row["before_records"] + row["after_records"]:
            if not (ROOT / item["path"]).exists() or sha(ROOT / item["path"]) != item["sha256"]:
                stale_native.append(item["path"])
    for key, filename in [("protocol_sha256", "protocol.json"), ("economics_input_sha256", "economics/inputs.json"),
                          ("economic_summary_sha256", "economics/results/summary.json")]:
        if bindings[key] != sha(ROOT / filename):
            stale_native.append(filename)

    claims = []
    def claim(identifier, text, level, status, files, limits, quantities=None):
        row = {"id": identifier, "claim": text, "evidence_level": level, "status": status,
               "evidence": references(files), "limits": limits}
        if quantities is not None:
            row["quantities"] = quantities
        claims.append(row)

    ec = ["economics/inputs.json", "economics/run_economics.py", "economics/results/summary.json",
          "economics/verification.json", "evidence/economics_adversarial_review.json"]
    claim("C01", "The bounded USD900 recovery offer has a positive conditional twelve-month commercial foundation: USD36,309.008 after additional development.",
          "modeled", "conditional", ec,
          ["Eight attempted orders monthly and 85% final customer acceptance are unobserved assumptions.",
           "Price, acquisition, labor, token use and eventual collection are not validated by the four technical cases.",
           "Before income tax; this is not earned revenue or demonstrated enterprise profit."],
          {k: central[k] for k in ["price", "attempted_orders_annual", "final_accepted_orders_annual", "accepted_revenue", "direct_delivery_cost", "payment_fees", "direct_contribution", "acquisition_cost", "fixed_operating_cost", "operating_profit", "additional_development", "full_project_return"]})
    claim("C02", "The study has zero customers, zero orders and zero actual collections; complete actual study cost remains unknown.",
          "measured", "supported_with_unknown_cost", ["economics/inputs.json", "economics/results/summary.json", "evidence/model_record.json", "evidence/native_execution.json"],
          ["No complete token ledger or allocated platform invoice is available.", "Zero new external cash spending is not zero allocated resource expense."], econ["actual"])
    claim("C03", "Four prospective confirmation notebooks complete 133 code cells and pass 38 distinct independent numerical/semantic checks on two fresh-process runs.",
          "executed_and_measured", "supported", [*case_refs, "scripts/independent_checks.py", "evidence/independent_expectations.json", "evidence/independent-repeatability.json", "evidence/independent_review.txt"],
          ["Four purposive public educational analogues, not representative customer jobs.", "The checker is independently authored within the same team/model family, not an external certification.", "Repeated runs are not extra cases, distinct cells or distinct checks."],
          {"confirmation_cases": 4, "unique_code_cells": 133, "distinct_numerical_semantic_checks": 38, "fresh_runs_per_case": 2, "cases": case_rows})
    claim("C04", "Original input identity, code-cell scope and declared migrations are preserved and independently checked.",
          "executed_and_measured", "supported", ["inputs/confirmation/source_manifest.json", "evidence/independent-identity-final.json", "scripts/independent_audit.py", "inputs/iris-provenance.json", *[f"deliveries/{c}/changes.json" for c in cases], *[f"deliveries/{c}/migration.diff" for c in cases]],
          ["Current pinned Iris data are a same-source snapshot, not proven identical to the unpinned historical download.", "Seeded illustrative outputs and current numerical libraries need not reproduce historical random draws bitwise.", "Bounded historical normalization adapter is not the complete sklearn estimator API."])
    plot_files = existing(["evidence/plot-lifecycle-before-correction/failure.json", "evidence/pre-plot-correction-independent/manifest.json", "evidence/plot-acceptance-addendum.json", graphical_path, "evidence/development-plot-visual-qa.json", "evidence/independent-plot-adverse/independent-plot-adverse-control.json"])
    claim("C05", "A discovered plot-lifecycle defect was preserved and corrected; current confirmation output contains nine and seven separate cell plots, with visual and adverse verification.",
          "executed_and_measured", "supported" if graphical_ok else "pending_final_graphical_review", plot_files,
          ["Graphical acceptance was strengthened after visual discovery; it is a later addendum, not part of the originally frozen 38 numerical checks.", "The forced-Agg adverse case still executes all 32 cells and passes all 10 numerical checks but fails graphical acceptance.", "Valid image structure and visual review do not certify underlying scientific truth."],
          {"confirmation_plots": 16, "development_plots": 3, "final_confirmation_visual_check_pass": graphical_ok, "frozen_numeric_checker_sha256": numerical_checker, "graphical_addendum_frozen_at": read("evidence/plot-acceptance-addendum.json")["frozen_at"]})
    claim("C06", "The offer and confirmation queue were frozen before case-specific confirmation repair, following two development cases.",
          "executed", "supported", ["protocol.json", "evidence/protocol-freeze.txt", "evidence/development-freeze.json", "evidence/independent_acceptance_plan.json", "evidence/independent_expectations.json", "evidence/plot-acceptance-addendum.json"],
          ["Prospective by filename/topic, not blinded or random.", "Case-specific expert repair remains allowed; no frozen autonomous repair-policy claim.", "Later plotting corrections and added checks are dated separately; historical frozen runner hashes intentionally differ from corrected current runners."],
          {"protocol_created_utc": protocol["created_utc"], "development_freeze_utc": read("evidence/development-freeze.json")["created_utc"], "development_cases": 2, "confirmation_cases": 4})
    claim("C07", "The handoff is bounded to one authorized notebook and includes runtime instructions, environment, identity, original failures, repaired runs, checks and migration rationale.",
          "executed_and_proposed", "supported_scope_with_proposed_service_terms", ["protocol.json", "README.md", "requirements.txt", "environment.json", *[f"deliveries/{c}/README.md" for c in cases]],
          ["Two-business-day SLA and 14-day correction/refund contract are proposed, not observed commercial service performance.", "Scientific validation, inaccessible data, GPUs, production hosting and professional certification are excluded.", "At most 100 code cells, 5 MB inputs and 120-second case execution envelope; arbitrary user code is not safely contained by the runner alone."])
    claim("C08", "A recorded diverse shortlist selected bounded custom analytical recovery on useful deliverability and complete economics.",
          "executed_research_and_proposed_opportunity", "supported_bounded_selection", ["evidence/selection_review.json", "protocol.json", "publication/body.tex", "publication/references.bib"],
          ["Three investigated candidates; no exhaustive market search, beyond-human-foresight claim or exclusive discovery.", "Accessible diagrams and legacy instrument data were deferred for missing decisive validation inputs.", "The executed teaching notebooks have a free maintained alternative; they are not evidence anyone should buy recovery of those examples."])
    claim("C09", "Expert tool-assisted frontier work executed in the authorized session; a separate documented API model is used only for prospective costing.",
          "executed_with_unmeasured_configuration", "supported_boundary", ["evidence/model_record.json", "economics/inputs.json", "publication/references.bib"],
          ["Session-reported GPT-6 Astra Pro is not an independently exported API snapshot.", "Actual sampling configuration, reasoning usage, billed tokens and complete invoice are unknown.", "Proposed gpt-6-astra/high reasoning deployment and documented prices are not an execution trace."])
    claim("C10", "The deployment cost envelope is explicitly partitioned into bounded calls, with output including reasoning and no assumed cache discounts.",
          "modeled", "conditional", ["economics/inputs.json", "economics/results/api_token_budget_partitions.json", "economics/verification.json", "evidence/model_record.json"],
          ["Central initial budget of two million input and 0.4 million output tokens costs USD40 at documented rates; retries change expected expense to USD53.80 per attempt.", "44 scenario/outcome allocations obey short-context input/output caps; budgets are assumptions, not metered calibration.", "Access, approved credentials, quota and expenditure authorization would be needed before future paid deployment."])
    claim("C11", "The central equivalent human reference is an explicit eight-hour complete-handoff estimate times a documented USD149 external hourly rate: USD1,192.",
          "modeled_from_documented_rate", "conditional_resource_reference", ["economics/inputs.json", "economics/README.md", "economics/results/summary.json", "evidence/economics_adversarial_review.json", "publication/references.bib"],
          ["Hours are phase estimates, not measured human experiments or a quotation for this exact service.", "Low reference is four hours at USD84 (USD336), which can beat the proposed offer.", "USD249 is an unloaded specialized rate; the loaded sixteen-hour reference at USD412.97 is USD6,607.52.", "No assumed automatic sale follows from a price discount."], {"hours_estimated": 8, "documented_rate_usd_hour": 149, "central_resource_reference_usd": 1192, "standard_offer_usd": 900})
    claim("C12", "Customer participation is conditional on alternatives, trust, switching effort and complete responsibility; willingness to pay is unmeasured.",
          "modeled_and_unestablished", "conditional", ["economics/results/participation_thresholds.csv", "economics/inputs.json", "evidence/selection_review.json", "publication/body.tex"],
          ["At central acceptance the gross participation allowance versus USD1,192 is USD248.20 before buyer setup/delay/trust costs.", "Free adequate replacements or USD336 provision can eliminate participation.", "USD500–1,500 price scenarios, premium and discount tiers are not demand evidence or validated rush-service terms."])
    claim("C13", "Complete modeled costs charge attempts, retries, failed corrections, refunds, packaging, support, acquisition, maintenance and additional development once.",
          "modeled_and_verified_arithmetic", "conditional", ec + ["economics/README.md"],
          ["No arbitrary mandatory manual-review charge; support and exception allowances are identified but unmeasured.", "Additional development is forty hours at USD95 plus USD200, separate from learning incidental to paid work.", "The USD95 resource proxy is assumed cash-paid fractional labor in financing scenarios.", "Model assumes complete eventual collection of final accepted invoices; bad-debt and chargeback sensitivities are separate."])
    claim("C14", "Central price, volume, acceptance and acquisition thresholds define how far the conditional surplus can deteriorate before break-even.",
          "modeled", "conditional", ec + ["economics/results/threshold_grid.csv", "economics/results/sensitivities.csv"],
          ["Thresholds hold stated other assumptions and jointly change correction/rejection costs with acceptance.", "Price-dependent payment fees explain why break-even price differs from cost per accepted job at USD900.", "Proportional acquisition and fixed-inquiry campaign thresholds are different arrangements."],
          {k: central[k] for k in ["operating_break_even_price", "project_break_even_price", "project_break_even_attempts_monthly", "project_break_even_accepted_monthly", "project_break_even_acceptance", "fixed_inquiry_campaign_project_break_even_conversion", "maximum_cac_per_attempt_at_operating_break_even"]})
    claim("C15", "Material negative scenarios are retained: joint downside, weak uptake, a funded campaign with no sales, and broad-corpus-inspired acceptance challenges.",
          "modeled", "supported_conditional_failures", ec + ["economics/results/scenario_summary.csv", "economics/results/sensitivities.csv"],
          ["External 40.1%/44.9% mechanical recovery rates are not estimates of screened service or final buyer acceptance.", "Challenge scenarios are not reasons to replace demand and quality assumptions with optimistic measured claims."],
          {s["scenario"]: {"full_project_return_usd": s["full_project_return"], "final_acceptance_rate": s["final_acceptance_rate"]} for s in econ["scenarios"] if s["scenario"] in ["downside", "low_uptake", "funded_campaign_no_sales", "acceptance_challenge_401", "acceptance_challenge_449", "acceptance_challenge_450", "price_pressure"]})
    claim("C16", "Profit and financing differ: expected opening equity is USD6,760.92 while warranty-exposed receipts remain fully restricted.",
          "modeled", "conditional", ec + ["economics/results/central_cash_ledger.csv", "economics/results/central_first_cohort_all_refunded_ledger.csv", "economics/results/central_35_day_collection_delay_ledger.csv", "economics/results/central_restricted_deposit_ledger.csv", "economics/results/central_after_warranty_ledger.csv"],
          ["First cohort fully refunded requires USD10,298.12 assuming later recovery; 35-day collection delay requires USD9,003.82.", "Mean event schedules are not solvency guarantees, calibrated tail reserves or financing commitments.", "Equity with no debt interest is assumed; capital injection is financing rather than a duplicate expense.", "Five calendar days is a cash-timing buffer, not a measured change to the proposed two-business-day offer."])
    claim("C17", "All selected volume scenarios fit a stated fractional-operation capacity envelope.",
          "modeled", "conditional", ["economics/inputs.json", "economics/results/summary.json", "economics/README.md"],
          ["Central 14.42 human hours monthly includes sales, administration, support and exceptions.", "39.88 attempted jobs/month is a planning capacity under 40 human/160 agent available hours.", "No throughput, API rate-limit, duration-tail or service-level study establishes this capacity."])
    claim("C18", "A 1,001-cell deterministic grid and 1,000 conditional stochastic histories explore uncertainty jointly.",
          "modeled", "conditional_not_probability_forecast", ["economics/inputs.json", "economics/run_economics.py", "economics/results/threshold_grid.csv", "economics/results/summary.json"],
          ["Common-incident frequency and its volume/quality/cost impacts are deliberately assumed, not empirically fitted.", "Grid-positive fractions and simulated quantiles are not real-world profitability probabilities or forecast confidence intervals."])
    claim("C19", "Ordinary shared coordination is tested against both human and frontier-assisted standalone work without exclusive technical attribution.",
          "modeled", "conditional", ["economics/results/coordination_comparison.csv", "economics/coordination_before_correction.csv", "economics/inputs.json", "economics/README.md"],
          ["Same 15% reuse benefit, setup, coordination and common-rework assumptions apply to both arrangements.", "Four-job coordination worsens both; human sharing can save at sixteen jobs while modeled AI sharing still fails to repay incremental coordination.", "Early auxiliary provider-selling-price/internal-resource confusion is preserved and corrected; headline economics unchanged.", "Reuse requires participant permission and compatible rights; no retained-skill benefit measured."])
    claim("C20", "Twenty-six byte-exact upstream files support executed local Charge, Nova-Seed, FusionPlan and Insight paths.",
          "executed", "supported_current_bindings" if not stale_native else "executed_but_bindings_need_refresh", ["upstream/manifest.json", "scripts/native_evidence_demo.py", "scripts/native_evidence_demo.mjs", "scripts/NATIVE_REUSE.md", "evidence/native_execution.json", "evidence/native_inputs.json", "evidence/native_nova_seed.json", "evidence/native_fusion_plan.json", "evidence/native_insight.json"],
          ["Cryptographic equality, encryption and Merkle proofs establish integrity, not scientific truth, paid demand or value.", "Fifty-four native Charge records keep accrual unknown; unknown-to-zero mutation is rejected.", "No signed cost ledger or complete-cost-profit seal is admitted.", "Insight evidence-needed is a native admission boundary and does not erase a separately labeled conditional calculation."],
          {"source_commit": native["source_commit"], "upstream_file_count": 26, "charge_records": 54, "fusion_jobs": 6, "binding_sha256": native["binding_sha256"], "stale_binding_paths": sorted(set(stale_native))})
    claim("C21", "No live ENS authentication, MARK admission, protected service, token settlement or customer contact is represented as executed.",
          "executed_boundary", "not_executed", ["protocol.json", "evidence/native_execution.json", "evidence/native_inputs.json"],
          ["Local identity authority is none; Nova passphrase is a public reproducibility fixture, not a live credential.", "Nominal AGIALPHA job fields are not USDC, earned revenue, funded bounties, issuance or treasury profit."])
    claim("C22", "Operational Alpha remains unestablished; useful delivery does not require an incremental ordinary-versus-expert model advantage.",
          "unestablished", "no_claim", ["evidence/model_record.json", "protocol.json", "publication/body.tex"],
          ["No matched ordinary/expert frontier experiment with equal tasks, budgets and tools was conducted.", "Unchanged legacy source is an engineering baseline, not an ordinary model operator baseline."])
    claim("C23", "Retained Alpha, Gym/self-acceleration and exclusive transformational technical novelty are not claimed.",
          "unestablished", "no_claim", ["economics/results/coordination_comparison.csv", "evidence/selection_review.json", "publication/body.tex"],
          ["No fresh-recipient comparison against both competent baseline and an ordinary library containing the asset.", "Reproducibility assets are retained without claiming measured learned capability transfer.", "Existing modernization, human services and free alternatives limit novelty and price; they do not automatically veto a conditional custom service."])
    claim("C24", "First useful delivery can conditionally expand into recurring maintenance and adjacent recoveries when paid repeatability and capacity are earned.",
          "proposed", "conditional_future_path", ["publication/body.tex", "protocol.json", "economics/inputs.json"],
          ["Requires authorized target-customer inputs, purchase decisions, metered costs, collection evidence, reliability and working capital.", "No valuation, market size or economy-wide transformation follows from one modeled margin."])
    failure_files = existing(["evidence/failed-checker-harness-03.06-Concat-And-Append.json", "evidence/failed-checker-harness-05.04-Feature-Engineering.json", "evidence/initial-readonly-cache-05.02.json", "evidence/independent-controls-reproduced/independent-adverse-controls.json", "evidence/independent-controls-final/independent-adverse-controls.json", "evidence/full-reproduction-final/adverse/independent-adverse-controls.json", "evidence/plot-lifecycle-before-correction/failure.json", "economics/prior/economic-v1-before-review-amendments.zip", "economics/coordination_before_correction.csv"])
    claim("C25", "Original failures, checker defects, graphical failures and economic amendments are preserved with corrected successors.",
          "executed", "supported", failure_files,
          ["Earlier false control summary reflected socket refusal occurring before the hook; later controls name the blocking layer.", "Failures are not silently removed or counted as accepted deliveries.", "Prior economic archive preserves the original assumptions/results before reviewed corrections."])
    reproduction_files = existing(["README.md", "requirements.txt", "environment.json", "scripts/reproduce.py", "evidence/full-reproduction-final/report.json", "evidence/native-output-isolation-verification.json"])
    claim("C26", "The supplied study replays in fresh processes on the recorded installed runtime; a focused native-output check preserves original evidence during reproduction.",
          "executed", "supported_tested_runtime", reproduction_files,
          ["Python 3.12.14, pinned packages including Pydantic 2.11.7 and matplotlib-inline 0.1.7, and Node 24.22.1 are recorded.", "Clean dependency installation, wheelhouse, other operating systems and arbitrary-upload sandboxing are not tested.", "The complete study replay preceded the output-routing-only wrapper amendment; the narrow follow-up verifies all five native files are redirected without altering original evidence."])
    publication_files = existing(["publication/paper.tex", "publication/body.tex", "publication/references.bib", "publication/paper.pdf", "publication/executive-brief.pdf", "publication/linkedin_draft.txt", "publication/browser-edition.html", "PUBLICATION_STATUS.json", "evidence/pdf_visual_qa_pages14_26_final.json", "evidence/pdf_visual_qa_final_first13.json"])
    missing_publication = [p for p in ["publication/browser-edition.html", "scripts/build_browser.py", "PUBLICATION_STATUS.json"] if not (ROOT/p).is_file()]
    claim("C27", "Publication outputs are a research review edition; final visual qualification and public-link status follow their explicit records.",
          "executed_and_proposed", "pending_packaging_checks" if missing_publication else "check_final_qa_and_publication_record", publication_files,
          ["LinkedIn text is a draft for approval, not posted.", "An additive pinned review edition is distinct from a merged canonical release or deployed customer service.", "A local PDF or HTML file does not establish a live public URL.", "Only matching-PDF-hash page-review records qualify the final PDF; earlier revisions remain historical."])

    limitations = [
        ("L01", "Commercial conditionality", "Price, paid demand, 85% buyer acceptance, acquisition and service-level performance remain unobserved; four technical successes do not calibrate them.", ["economics/inputs.json", "evidence/selection_review.json"]),
        ("L02", "Actual accounting", "Customers and actual collections are zero; actual complete study cost, model tokens and allocated invoices are unknown.", ["evidence/model_record.json", "economics/results/summary.json"]),
        ("L03", "Public analogue sample", "Four purposive teaching notebooks from one author are easier and more available than many orphaned analyses; a free updated edition exists. Paying target is customer-specific material without an equivalent substitute.", ["protocol.json", "inputs/confirmation/source_manifest.json"]),
        ("L04", "Independent checking boundary", "Different same-team checker authorship reduces some errors but leaves shared model blind spots; no third-party scientific certification. Exact historical random outputs are not guaranteed.", ["evidence/independent_acceptance_plan.json", "evidence/independent_review.txt"]),
        ("L05", "Chronology", "Numeric checker was frozen before repaired confirmation inspection. Graphical checks were added after the Agg lifecycle defect was discovered; headline 38 remains unchanged.", ["evidence/development-freeze.json", "evidence/plot-acceptance-addendum.json", "evidence/pre-plot-correction-independent/manifest.json"]),
        ("L06", "Scope and data", "Only authorized bounded CPU notebooks in the stated stack; current same-source Iris snapshot, narrow normalization adapter and deterministic illustrative seeds have explicit limits.", ["protocol.json", "inputs/iris-provenance.json", "evidence/independent_review.txt"]),
        ("L07", "Human and API references", "Human hours, support, exceptions and token envelopes are estimates. Published rates do not constitute an exact service quote, measured speed advantage or metered model bill.", ["economics/inputs.json", "evidence/economics_adversarial_review.json"]),
        ("L08", "Cash and tail risk", "Equity, cash-paid fractional labor, complete eventual collections and modeled reserve runoff are assumptions. Refund/late-collection stresses are not tail-risk calibration or financing commitments.", ["economics/README.md", "economics/results/summary.json"]),
        ("L09", "Optional Alpha", "No matched ordinary/expert model uplift, recipient-vs-library retention test, Gym development, exclusive technical invention or general intelligence achievement is established.", ["evidence/model_record.json", "economics/results/coordination_comparison.csv", "publication/body.tex"]),
        ("L10", "Native integrity", "Exact-source native paths execute locally with public fixtures; they do not provide live authority, truth, paid acceptance or complete accounting. MARK and live ENS/services remain unexecuted.", ["evidence/native_execution.json", "scripts/NATIVE_REUSE.md"]),
        ("L11", "Runtime and security", "Fresh-process replay uses the already installed environment. No clean install/cross-platform guarantee; the notebook runner alone is not a universal security boundary for arbitrary uploads.", ["README.md", "environment.json", "requirements.txt"]),
        ("L12", "Expansion", "Recurring service and shared productive infrastructure require new customers, metering, rights, reliability and capital. No enormous valuation or self-accelerating economic result is inferred.", ["publication/body.tex"]),
    ]
    limitation_rows = [{"id": i, "topic": topic, "limitation": text, "evidence": references(files)} for i, topic, text, files in limitations]
    gaps = []
    if not graphical_ok:
        gaps.append({"id": "G01", "status": "pending", "action": "Complete final graphical inspection against matching rendered image hashes."})
    if stale_native:
        gaps.append({"id": "G02", "status": "pending", "action": "Refresh native bindings after final artifact changes.", "affected_relative_paths": sorted(set(stale_native))})
    if missing_publication:
        gaps.append({"id": "G03", "status": "pending", "action": "Complete browser build and explicit publication-status record.", "expected_artifacts_not_evidence": missing_publication})
    paper_sha = sha(ROOT / "publication/paper.pdf")
    qa_records, passed_pages = [], set()
    for p in (ROOT / "evidence").glob("pdf_visual_qa*.json"):
        d = json.loads(p.read_text())
        if d.get("pdf_sha256") == paper_sha:
            status = "PASS" if d.get("all_reviewed_pages_pass") is True else d.get("overall", d.get("status"))
            covered = d.get("physical_pages", d.get("reviewed_physical_pages", []))
            qa_records.append({"path": str(p.relative_to(ROOT)), "status": status, "physical_pages": covered})
            if status == "PASS":
                passed_pages.update(covered)
    if not set(range(1,27)).issubset(passed_pages) or any(q["status"] in ["CHANGE_REQUIRED", "FAIL"] for q in qa_records):
        gaps.append({"id": "G04", "status": "pending", "action": "Bind passing page-by-page final visual review to the current paper PDF SHA-256; historical revisions do not qualify a new PDF.", "current_pdf_sha256": paper_sha, "matching_records": qa_records})
    total_refs = {item["path"] for row in claims for item in row["evidence"]}
    mapping = {"schema": "agi-alpha-claim-to-evidence/v1", "generated_at_utc": now,
               "path_base": "study root; every evidence path is relative and was verified to be an existing file at generation",
               "evidence_vocabulary": {"executed": "Operation actually performed; inspect scope and authority boundary.", "measured": "Recorded observation, not necessarily complete billing or representative population data.", "modeled": "Reproducible conditional calculation; assumptions remain unobserved unless separately stated.", "proposed": "Offer term, deployment or expansion not yet observed.", "unestablished": "No affirmative achievement claim."},
               "headline": {"commercial": "Positive conditional full-project result of USD36,309.008 over twelve months", "technical": "4 confirmation cases; 133 code cells; 38 distinct numerical/semantic checks; two runs", "actual_customers": 0, "actual_collections_usd": 0, "actual_complete_study_cost_usd": None},
               "frozen_economic_inputs_sha256": econ["input_sha256"], "frozen_numeric_checker_sha256": numerical_checker,
               "manuscript_snapshot": references(["publication/body.tex", "publication/references.bib"]),
               "claims": claims, "packaging_gaps_at_generation": gaps,
               "final_pdf_qa": {"pdf_sha256": paper_sha, "passed_physical_pages": sorted(passed_pages), "all_26_pages_pass": set(range(1,27)).issubset(passed_pages), "matching_records": qa_records},
               "reference_validation": {"all_evidence_paths_exist": True, "distinct_evidence_files": len(total_refs), "no_self_hash_cycle": True},
               "refresh_command": "python scripts/build_evidence_map.py"}
    lim = {"schema": "agi-alpha-limitations/v1", "generated_at_utc": now,
           "headline_boundary": "Useful delivery is executed; commercial surplus is conditional. No actual sales or complete actual-cost result.",
           "limitations": limitation_rows, "packaging_gaps_at_generation": gaps,
           "graphical_review": {"complete": graphical_ok, "numeric_checker_unchanged": True, "additional_checks_post_discovery": True},
           "refresh_command": "python scripts/build_evidence_map.py"}
    for name, content in [("claim_to_evidence.json", mapping), ("limitations.json", lim)]:
        (ROOT / "evidence" / name).write_text(json.dumps(content, indent=2) + "\n")
    print(json.dumps({"claims": len(claims), "distinct_evidence_files": len(total_refs), "all_paths_exist": True,
                      "graphical_review_complete": graphical_ok, "native_stale_paths": len(stale_native), "packaging_gaps": gaps}, indent=2))


if __name__ == "__main__":
    main()
