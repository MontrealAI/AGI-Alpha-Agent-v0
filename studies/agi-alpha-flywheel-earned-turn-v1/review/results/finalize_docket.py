"""Post-confirmation evidence mapping. Never runs a mission or edits frozen inputs."""
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
checks = []

def read(path):
    return json.loads((ROOT / path).read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(label, condition, detail=None):
    checks.append({"check": label, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError((label, detail))

def same(label, actual, expected):
    if isinstance(expected, dict):
        require(label + ": mapping", isinstance(actual, dict))
        for key, value in expected.items():
            require(label + ": key " + key, key in actual)
            same(label + "/" + key, actual[key], value)
    elif isinstance(expected, list):
        require(label + ": sequence", isinstance(actual, list) and len(actual) == len(expected))
        for i, value in enumerate(expected):
            same(label + "/" + str(i), actual[i], value)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        require(label, isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-9), {"actual": actual, "expected": expected})
    else:
        require(label, actual == expected, {"actual": actual, "expected": expected})

draft = read("EVIDENCE_DOCKET_DRAFT.json")
docket = copy.deepcopy(draft)
claims = {c["id"]: c for c in docket["claims"]}
audit = read("review/results/INDEPENDENT_RESULTS.json")
mechanism = read("review/results/MECHANISM_ATTRIBUTION.json")
storage = read("review/results/STORAGE_ACCOUNTING.json")
analysis = read("results/confirmation-v1/ANALYSIS.json")
execution = read("results/confirmation-v1/EXECUTION.json")
freeze = read("protocol/FREEZE.json")
protocol = read("protocol/CONFIRMATORY_PROTOCOL.json")
prior = read("audit/PRIOR_FAILURE_AUDIT.json")
first = "results/confirmation-v1/trials/00-recurring-flywheel/"
first_rows = {r["id"]: r for r in read(first + "rows.json")}
first_events = read(first + "events.json")
fly = analysis["arms"]["flywheel"]

require("Exact frozen independent audit PASS", audit["status"] == "PASS" and not audit["issues"])
require("Product gate HOLD remains a completed negative result", not audit["product_gate"]["passed"] and analysis["product_admission"] == "HOLD")
require("No paired input divergence", not audit["paired_input_divergences"])
for path, digest in freeze["files"].items():
    require("Frozen bytes: " + path, sha(ROOT / path) == digest)
require("Freeze identity matches audit and execution", freeze["freeze_sha256"] == audit["expected_source"] == execution["freeze_sha256"] == draft["freeze_sha256"])

# Verify every number and nested identity retained from the original draft.
same("ET-03/A", first_rows["A"], claims["ET-03"]["observed_outcome"]["first_registered_A"])
same("ET-03/B08", first_rows["B08"], claims["ET-03"]["observed_outcome"]["first_registered_B08"])
same("ET-04", {"qualified_fresh_parent_calls": fly["parent_using_qualified_fresh"], "qualified": fly["qualified"], "offered": fly["offered"], "streams": fly["trials"]}, claims["ET-04"]["observed_outcome"])
requirement = next(e for e in first_events if e["kind"] == "SUCCESSOR_REQUIREMENT")
same("ET-05", {"successors": fly["successors"], "requirement": requirement, "C": first_rows["C"], "D01": first_rows["D01"]}, claims["ET-05"]["observed_outcome"])
same("ET-06", {"primary_comparison": analysis["comparisons"]["native_refactor"], "conventional_comparison": analysis["comparisons"]["conventional_reuse"], "primary_gate": analysis["primary_gate"], "conventional_noninferiority_guard": analysis["conventional_noninferiority_guard"], "quality_resource_gate": analysis["quality_resource_gate"], "product_admission": analysis["product_admission"], "qualified_per_arm": {a: [r["qualified"], r["offered"]] for a, r in analysis["arms"].items()}}, claims["ET-06"]["observed_outcome"])
same("ET-08", {"released_service_quota_ms": fly["released_ms"], "actual_successor_debits_ms": fly["construction_debits_ms"], "origin": "EXTERNAL_ENDOWMENT"}, claims["ET-08"]["observed_outcome"])
same("ET-13", {"flywheel_whole_cpu_ms": fly["total_cpu_ms"], "flywheel_whole_wall_ms": fly["total_wall_ms"], "full_investment_recovery": analysis["full_investment_recovery"], "acceleration": analysis["acceleration"], "commercial_growth": analysis["commercial_growth"], "manual_intermediate_triggers": execution["manual_intermediate_triggers"], "confirmation_reruns": execution["confirmation_reruns"]}, claims["ET-13"]["observed_outcome"])

prior_arms = {a["arm"]: a for a in prior["primary_aggregates"]}
same("Prior user facts", [prior_arms[a]["qualified"] for a in ["flywheel", "learner", "portfolio"]], [517, 517, 591])
same("Prior primary denominator", prior_arms["flywheel"]["offered"], 864)
same("Prior primary assets", prior_arms["flywheel"]["assets"], 0)
same("Prior qualified repair using parent", prior["fresh_repair_use_summary"]["qualified_outputs_using_parent"], 0)
claims["ET-01"]["observed_outcome"] = {"prior_frozen_files_verified": prior["prior_frozen_files_verified"], "prior_frozen_files_unchanged": prior["all_prior_frozen_files_unchanged"], "flywheel_qualified": 517, "learner_qualified": 517, "portfolio_qualified": 591, "offered_each": 864, "primary_assets": 0, "fresh_qualified_parent_using_repair": 0, "qualification_reserved_work_units": prior["reservation"]["qualification_reserved"], "stage_cap_work_units": prior["reservation"]["stage_cap"], "scheduled_training_calls": prior["reservation"]["scheduled_training_calls_for_complete_race"], "qualification_evaluations_executed": prior["reservation"]["qualification_evaluations_executed"], "proximate_failure": prior["interpretation"]["proximate_failure"]}
charter = read("protocol/DEVELOPMENT_CHARTER.json")
screen = read("development/SCREEN_RESULTS.json")
same("Domain screen count", len(screen["rows"]), charter["maximum_screen_runs"])
claims["ET-02"]["observed_outcome"] = {"screened_families": len(charter["domains"]), "screen_runs": len(screen["rows"]), "selected_family": screen["selection"], "maximum_algorithm_variants": charter["maximum_selected_domain_algorithm_variants"], "maximum_full_development_campaigns": charter["maximum_full_development_campaigns"], "screen_cpu_ms": screen["screen_cpu_ms"], "selection_scope": "Development only; not selection on fresh confirmation outcomes"}

for cid in ["ET-03", "ET-04", "ET-05", "ET-06", "ET-08", "ET-13"]:
    claims[cid]["status"] = "INDEPENDENT_NUMERICAL_AUDIT_COMPLETE"
    claims[cid]["artifact_refs"].extend({"path": p} for p in ["review/results/INDEPENDENT_RESULTS.json", "review/results/INDEPENDENT_REVIEW.md", "review/results/EXECUTION_VERIFICATION.json"])
claims["ET-05"]["claim_or_question"] = "Eighteen scoped changed-operator successor instances were constructed from actual accepted predecessors"
claims["ET-05"]["scope_limit"] += " These are instances of the fixed Woodbury construction vocabulary, not eighteen discovered algorithm families."
claims["ET-06"]["observed_outcome"].update({"independent_primary": audit["primary_cpu_ratio"], "independent_conventional_guard": audit["conventional_noninferiority"], "interval_relation": "Independent RNG sampling layout gives a small Monte Carlo interval difference. Point estimate and gate decision agree; neither interval replaces the other."})

custody_tests = read("runtime/development_custody_tests.json")
same("Custody component tests", custody_tests["passed"], len(custody_tests["tests"]))
require("Custody test source binding", custody_tests["source_sha256"] == sha(ROOT / "runtime/custody.py"))
claims["ET-07"]["observed_outcome"] = {"development_component_tests_passed": custody_tests["passed"], "registered_budgets": protocol["budgets"], "confirmation_account_conservation": "PASS", "control_scope": "Reservations and observed native costs, not OS preemption"}
claims["ET-07"]["artifact_refs"].extend({"path": p} for p in ["protocol/CONFIRMATORY_PROTOCOL.json", "review/results/INDEPENDENT_RESULTS.json"])
fly_exec = [r for r in mechanism["execution_rows"] if r["arm"] == "flywheel"]
claims["ET-08"]["observed_outcome"].update({"released_per_stream_ms": 400.0, "streams": len(fly_exec), "construction_streams": sum(r["C_valid_parent_child"] for r in fly_exec), "earned_remaining_ms": sum(r["earned_remaining_ms"] for r in fly_exec), "service_debits_ms": sum(r["service_debit_ms"] for r in fly_exec), "external_maintenance_debits_ms": sum(r["external_improvement_debit_ms"] for r in fly_exec), "external_control_cpu_ms": sum(r["control_cpu_ms"] for r in fly_exec), "account_rounding": "Each action debit rounded upward to whole microseconds; unrounded CPU remains separate", "observed_whole_CPU_difference_vs_native_ms": analysis["arms"]["native_refactor"]["total_cpu_ms"] - fly["total_cpu_ms"]})
require("All release opportunities in flywheel equal 400ms", all(r["released_quota_ms"] == 400 for r in fly_exec))
same("Release conservation", sum(r["released_quota_ms"] for r in fly_exec), fly["released_ms"])
same("Actual C debit conservation", sum(r["earned_debit_ms"] for r in fly_exec), fly["construction_debits_ms"])

probe = read("runtime/development-process-recovery/PROCESS_RECOVERY.json")
probe_review = read("runtime/development-process-recovery/READ_ONLY_VERIFICATION.json")
require("Recorded process recovery checks", probe["status"] == probe_review["status"] == "PASS" and all(probe["checks"].values()))
claims["ET-09"]["observed_outcome"] = {"recorded_status": probe["status"], "checks": probe["checks"], "os_processes": len(probe["pids"]), "actual_execution_events": len(probe["actual_execution_events"]), "recorded_children_cpu_ms": probe["total_children_cpu_ms"], "source_identity_status": probe["source_identity_status"]}
bound_probe = read("operations/process-recovery/PROCESS_RECOVERY.json")
bound_probe_review = read("operations/process-recovery/READ_ONLY_VERIFICATION.json")
require("Frozen-source operational recovery probe PASS", bound_probe["status"] == bound_probe_review["status"] == "PASS" and all(bound_probe["checks"].values()))
require("Operational probe exact scientific source", bound_probe["source_hash"] == freeze["freeze_sha256"] and bound_probe["probe_source_sha256"] == sha(ROOT / "runtime/process_recovery.py"))
same("Operational probe CPU", bound_probe["total_children_cpu_ms"], 692.213)
claims["ET-09"]["observed_outcome"] = {"earlier_development_probe": claims["ET-09"]["observed_outcome"], "frozen_source_operational_probe": {"status": bound_probe["status"], "source_identity": bound_probe["source_hash"], "checks": bound_probe["checks"], "os_processes": len(bound_probe["pids"]), "pids": bound_probe["pids"], "actual_execution_events": len(bound_probe["actual_execution_events"]), "children_cpu_ms": bound_probe["total_children_cpu_ms"], "wall_ms": bound_probe["total_wall_ms"], "scope": bound_probe["scope"]}}
claims["ET-09"]["artifact_refs"].extend({"path": p} for p in ["operations/process-recovery/PROCESS_RECOVERY.json", "operations/process-recovery/READ_ONLY_VERIFICATION.json", "protocol/FREEZE.json"])
claims["ET-09"]["scope_limit"] = "Two distinct operational records: the earlier unfrozen development probe and the later exact-source probe on the same declared development network. Neither is an additional efficacy confirmation. Both differ from the confirmation's matched memory eviction."

lock = read("browser/BROWSER_EXECUTION_LOCK.json")
fresh = read("browser/qa/fresh-evidence.json")
browser_records = {k: read("browser/qa/" + k + ".json") for k in ["CHECKER_QA", "BROWSER_QA", "RECOVERY_QA", "RECORDED_QA", "RECORDED_VISUAL_REVIEW"]}
require("Browser recorded QA reports PASS", all(v["pass"] for v in browser_records.values()))
require("Browser execution identity", fresh["source_hash"] == lock["execution_source_hash"] == browser_records["RECORDED_QA"]["execution_source_hash"])
for path, digest in lock["execution_manifest"].items():
    require("Browser locked module: " + path, sha(ROOT / path) == digest)
require("Browser canonical/deliverable HTML same reviewed bytes", sha(ROOT / "browser/index.html") == sha(ROOT / "deliverables/AGI_ALPHA_Earned_Turn_Laboratory.html") == browser_records["RECORDED_QA"]["html_sha256"] == browser_records["RECORDED_VISUAL_REVIEW"]["html_sha256"])
require("Recorded JSON is QA-bound", sha(ROOT / "browser/recorded-summary.json") == browser_records["RECORDED_QA"]["recorded_sha256"])
same("Browser accepted mission count", len(fresh["accepted"]), 4)
require("Browser accepted scope", all(r["valid"] and r["network"]["nodes"] == 64 for r in fresh["accepted"]))
claims["ET-10"]["observed_outcome"] = {"accepted_missions": len(fresh["accepted"]), "nodes": 64, "status": fresh["status"], "browser_execution_hash": lock["execution_source_hash"], "checker_tests": len(browser_records["CHECKER_QA"]["checks"]), "ui_tests": len(browser_records["BROWSER_QA"]["results"]), "recovery_tests": len(browser_records["RECOVERY_QA"]["results"]), "recorded_presentation_tests": len(browser_records["RECORDED_QA"]["results"]), "live_executor": "DISCONNECTED"}

foundations = read("audit/foundations/FOUNDATIONS_MANIFEST.json")
for rec in foundations["records"]:
    path = ROOT / "audit/foundations" / rec["file"]
    require("Foundation file: " + rec["file"], path.is_file() and sha(path) == rec["sha256"] and path.stat().st_size == rec["bytes"])
neural = next(r for r in foundations["records"] if r["file"] == "neuralsymbolicsuccessoromegav0.pdf")
claims["ET-11"]["observed_outcome"] = {"exact_PDFs_in_manifest": len(foundations["records"]), "neural_symbolic_exact_file": neural["file"], "neural_symbolic_exact_url": neural["url"], "neural_symbolic_sha256": neural["sha256"], "edition_inspected": neural.get("edition_inspected"), "inherited_proof_status": "NONE"}
contracts = read("audit/CONTRACT_SOURCE_MANIFEST.json")
interfaces = read("audit/INTERFACE_SOURCE_MANIFEST.json")
vendor = read("runtime/vendor/WORKBENCH_MANIFEST.json")
for rec in contracts:
    path = ROOT / "audit/contracts" / rec["path"]
    require("Contract source: " + rec["path"], path.is_file() and sha(path) == rec["sha256"] and path.stat().st_size == rec["bytes"])
for rec in interfaces:
    path = ROOT / "audit/interfaces" / rec["key"] / rec["path"]
    require("Interface source: " + rec["key"], path.is_file() and sha(path) == rec["sha256"] and path.stat().st_size == rec["bytes"])
for rec in vendor["files"]:
    path = ROOT / "runtime/vendor" / rec["path"]
    require("Workbench vendor: " + rec["path"], path.is_file() and sha(path) == rec["sha256"] and path.stat().st_size == rec["bytes"])
claims["ET-12"]["observed_outcome"] = {"Alpha_contract_source_files": len(contracts), "interface_records": len(interfaces), "vendor_files": len(vendor["files"]), "runtime_release_inspected": vendor["release"], "local_EVM_executed": False, "live_financial_settlement": False, "new_credentials": False, "production_authority": False, "Manager_settlement_asset": "USDC path remains distinct"}

claims["ET-13"]["observed_outcome"].update({"independent_audit_cpu_ms": audit["audit_cpu_ms"], "independent_audit_wall_ms": audit["audit_wall_ms"], "descriptive_mechanism_analysis_cpu_ms": mechanism["analysis_cpu_ms"], "cost_boundary": audit["cost_boundary"]})
claims["ET-14"].update({"claim_or_question": "Canonical paper, clean rebuild and complete page inspection require final evidence", "status": "PENDING_FINAL_PDF_REBUILD_AND_PAGE_REVIEW", "observed_outcome": {"canonical_pdf_sha256": None, "clean_rebuild_record": None, "full_page_review_record": None, "passed": None}})
if (OUT / "MANUSCRIPT_SCIENTIFIC_REVIEW.json").is_file():
    content_review = read("review/results/MANUSCRIPT_SCIENTIFIC_REVIEW.json")
    require("Manuscript scientific content review", content_review["status"].startswith("PASS_SCIENTIFIC_CONTENT") and content_review["open_substantive_scientific_errors"] == 0)
    claims["ET-14"]["observed_outcome"]["scientific_content_review"] = content_review["status"]
    claims["ET-14"]["artifact_refs"].extend({"path": p} for p in ["review/results/MANUSCRIPT_SCIENTIFIC_REVIEW.json", "review/results/MANUSCRIPT_SCIENTIFIC_REVIEW.md"])
claims["ET-15"].update({"claim_or_question": "Additive archive and publication lifecycle require final owner and served-file bindings", "status": "PENDING_FINAL_ARCHIVE_AND_PUBLICATION_HANDOFF", "observed_outcome": {"complete_archive_sha256": None, "archive_contains_canonical_pdf": None, "archive_rebuild_verified": None, "owner_review": "PENDING", "merged": "PENDING_VERIFICATION", "released": "PENDING_VERIFICATION", "live_served_file": "PENDING_VERIFICATION"}})

def add(cid, statement, status, paths, result, limit):
    c = {"id": cid, "claim_or_question": statement, "status": status, "artifact_refs": [{"path": p} for p in paths], "observed_outcome": result, "scope_limit": limit}
    docket["claims"].append(c)
    claims[cid] = c

count_result = {"trials": len(audit["trials"]), "raw_numerical_records": len(audit["numeric_checks"]), "accepted_valid_records": sum(r["accepted"] and r["independently_valid"] for r in audit["numeric_checks"]), "useful_qualified_outputs": sum(r["qualified"] for r in audit["aggregates"]), "maintenance_restore_checks": sum(r["id"] == "RESTORE" for r in audit["numeric_checks"]), "correct_scope_refusals": sum(r["reason"] == "CONDUCTANCE_SCOPE" for r in audit["numeric_checks"]), "source_artifact_identities": len(audit["source_artifacts"]), "artifact_issues": len(audit["issues"]), "paired_input_divergences": len(audit["paired_input_divergences"]), "frozen_files_unchanged": len(freeze["files"])}
same("Independent audit counts", list(count_result.values()), [168, 3654, 3486, 3444, 42, 168, 5334, 0, 0, 32])
add("ET-16", "Exact frozen independent numerical and artifact audit completed with no detected issues", "INDEPENDENT_AUDIT_PASS", ["review/results/INDEPENDENT_RESULTS.json", "review/results/EXECUTION_VERIFICATION.json", "review/results/INDEPENDENT_REVIEW.md", "review/INDEPENDENCE_DISCLOSURE.md"], count_result, "Separate checker and aggregation; same commission and host. Reviewer also repaired executor validation before freeze. Producer totals were received before executing the frozen audit, so review was not blinded. Stored CPU telemetry and parent counters are not independently traced hardware evidence.")
construction = mechanism["construction_aggregates"]
require("Construction scope 18 matched streams", all(r["paired_streams"] == r["qualified"] == 18 for r in construction))
add("ET-17", "Retained parent reduces matched successor-construction work; conventional reuse obtains the same mechanism", "DESCRIPTIVE_SECONDARY_NO_NEW_CONFIRMATION", ["review/results/MECHANISM_ATTRIBUTION.json", "review/results/derive_mechanism.py", "review/results/INDEPENDENT_REVIEW.md", "companion/numerical.py", "companion/study.py"], {"matched_scoped_streams": 18, "construction_means": construction, "paired_descriptive_comparisons": mechanism["construction_paired_descriptive"], "actual_parent_block_solves": next(r for r in construction if r["arm"] == "flywheel")["construction_parent_block_calls"], "direction_rhs_columns": next(r for r in construction if r["arm"] == "flywheel")["direction_rhs_columns"]}, "C algorithm CPU includes construction, one solve and NPZ persistence. Native C includes generic full-input inspection absent from the low-rank path; both receive final independent checking. Exact-reconstruction contrast is the cleaner inheritance comparison. Posthoc descriptive intervals do not replace the registered whole-system gate.")
for arm in storage["aggregates"]:
    same("Storage producer whole-evidence total: " + arm["arm"], arm["reported_whole_trial_storage_bytes"], analysis["arms"][arm["arm"]]["storage_bytes"])
add("ET-18", "Retained storage counts unique physical asset paths rather than duplicated logical aliases", "DESCRIPTIVE_STORAGE_AUDIT_COMPLETE", ["review/results/STORAGE_ACCOUNTING.json", "review/results/EXECUTION_VERIFICATION.json", "results/confirmation-v1/SUMMARIES.json"], {"by_arm": storage["aggregates"], "counting_rule": "Deduplicate identical paths within a trial; do not deduplicate independent trial copies. Whole evidence storage remains separate.", "storage_analysis_cpu_ms": storage["analysis_cpu_ms"]}, "Asset count is not capability growth. Direct specialist has no NPZ factors but still has raw evidence storage. Lifelong retention costs and indefinite growth were not measured.")
add("ET-19", "Rare and maintenance workload means preserve cases favoring simpler conventional alternatives", "DESCRIPTIVE_REGIME_RESULTS", ["review/results/MECHANISM_ATTRIBUTION.json", "results/confirmation-v1/ANALYSIS.json", "protocol/CONFIRMATORY_PROTOCOL.json"], {"regime_aggregates": mechanism["regime_aggregates"], "rare": analysis["regimes"]["rare"], "maintenance": analysis["regimes"]["maintenance"]}, "Six streams per regime; no additional confirmatory subgroup superiority claim. Wide-change flywheel does not construct a low-rank successor, so differences there cannot be attributed to that construction.")
history_root = "audit/prior-strategy-lab/"
history = read(history_root + "HISTORICAL_EVIDENCE_STATUS.json")
history_provenance = read(history_root + "PROVENANCE.json")
projection_manifest = read("publication/PUBLIC_PROJECTIONS.json")
projection = next(p for p in projection_manifest["projections"] if p["original"]["path"] == history_root + "HISTORICAL_STRATEGY_LAB_AUDIT.md")
public_path = projection["public_projection"]["path"]
require("Explicit historical public projection", sha(ROOT / public_path) == projection["public_projection"]["sha256"] and (ROOT / public_path).stat().st_size == projection["public_projection"]["bytes"])
for rec in history_provenance["files"]:
    path = ROOT / history_root / rec["copied_path"]
    if rec["copied_path"] == "HISTORICAL_STRATEGY_LAB_AUDIT.md":
        require("Historical original is explicitly projected, not silently replaced", rec["sha256"] == projection["original"]["sha256"] and rec["bytes"] == projection["original"]["bytes"])
    else:
        require("Historical copied record: " + rec["copied_path"], path.is_file() and sha(path) == rec["sha256"] and path.stat().st_size == rec["bytes"])
for key in ["independent_artifact_audit", "fresh_frozen_policy_confirmation_replay"]:
    rec = history[key]
    require("Historical report binding: " + key, sha(ROOT / history_root / rec["record"]) == rec["sha256"] and rec["status"] == "PASS")
historical_replay = history["fresh_frozen_policy_confirmation_replay"]
require("Historical replay log binding", sha(ROOT / history_root / historical_replay["log"]) == historical_replay["log_sha256"])
require("Original recovered archive identity", history_provenance["original_zip"]["sha256"] == history["original_zip_sha256"])
add("ET-20", "Recovered Strategy Laboratory v0.1.0 was verified and replayed in the prior edition; its status is preserved separately", "HISTORICAL_RECORDS_REBOUND_NO_NEW_REPLAY", [history_root + p for p in ["PROVENANCE.json", "HISTORICAL_EVIDENCE_STATUS.json", "HISTORICAL_VERIFICATION.json", "HISTORICAL_STRATEGY_LAB_AUDIT.public.md", "original-identities.json", "current-exact-replay/EXECUTION.json", "current-exact-replay/replay.log"]] + ["publication/PUBLIC_PROJECTIONS.json"], {"original_archive_sha256": history["original_zip_sha256"], "prior_independent_artifact_audit": history["independent_artifact_audit"], "prior_exact_frozen_policy_replay": historical_replay, "prior_pilot_policy_replay": history["prior_pilot_policy_replay"], "public_projection": projection, "full_original_payload_location": "Prior Strategy Succession package; not duplicated or recreated by the new confirmation"}, "Original non-timing policies and judgments were replayed under CPython 3.13.5. Acquisition/development search was not freshly rerun. Equal exploration counts do not establish equal total computation, full-cost adoption or integrated production operation. The narrative is an explicitly named public projection; original content remains in prior-study custody. These historical records are not new Earned Turn observations.")

rebuild = read("publication/PDF_REBUILD_VERIFICATION.json")
paper_archive = read("publication/PAPER_ARCHIVE_IDENTITY.json")
pdf_path = "paper/AGI_ALPHA_FLYWHEEL_Earn_the_Next_Turn.pdf"
require("Canonical PDF exact identity", sha(ROOT / pdf_path) == rebuild["pdf_sha256"] and (ROOT / pdf_path).stat().st_size == rebuild["pdf_bytes"])
require("Clean packaged-paper rebuild", rebuild["status"] == "PASS" and rebuild["clean_rebuild_pdf"] == "BYTE_IDENTICAL" and rebuild["every_rebuild_render"] == "BYTE_IDENTICAL_TO_VISUALLY_REVIEWED_FINAL_PAGES")
require("Paper source archive identity record agrees", rebuild["source_archive"] == paper_archive)
paper_zip = ROOT / "deliverables" / paper_archive["file"]
require("Actual paper-only archive identity", sha(paper_zip) == paper_archive["sha256"] and paper_zip.stat().st_size == paper_archive["bytes"])
with zipfile.ZipFile(paper_zip) as packed:
    require("Canonical PDF inside paper source archive", hashlib.sha256(packed.read(pdf_path)).hexdigest() == rebuild["pdf_sha256"])
reviewed_pages = {}
for review_path in rebuild["visual_reviews"]:
    reviewed = read(review_path)
    require("Page review PDF binding: " + review_path, reviewed["pdf_sha256"] == rebuild["pdf_sha256"])
    for page in reviewed["pages"]:
        number = page["physical_page"]
        digest = page.get("image_sha256", page.get("png_sha256", page.get("render_sha256")))
        require("Page inspection pass: " + str(number), page["status"].startswith("PASS"))
        reviewed_pages[number] = digest
require("All 23 physical pages covered", set(reviewed_pages) == set(range(1, rebuild["pages"] + 1)) and rebuild["pages"] == 23)
for page in rebuild["page_records"]:
    number = page["physical_page"]
    require("Final inspected/rebuilt render: " + str(number), page["render_sha256"] == reviewed_pages[number] == sha(ROOT / f"paper/qa/publication-pages/page-{number:02}.png"))
claims["ET-14"].update({"claim_or_question": "Canonical paper rebuilt byte-identically from packaged LaTeX; all 23 final pages were visually reviewed", "status": "PDF_REBUILD_AND_ALL_PAGE_REVIEW_VERIFIED", "observed_outcome": {"canonical_pdf_sha256": rebuild["pdf_sha256"], "pdf_bytes": rebuild["pdf_bytes"], "pages": rebuild["pages"], "paper_source_archive": paper_archive, "clean_rebuild_pdf": rebuild["clean_rebuild_pdf"], "every_rebuild_render": rebuild["every_rebuild_render"], "scientific_content_review": content_review["status"], "visual_review_records": rebuild["visual_reviews"], "institutional_review": False}})
claims["ET-14"]["artifact_refs"].extend({"path": p} for p in [pdf_path, "publication/PDF_REBUILD_VERIFICATION.json", "publication/PAPER_ARCHIVE_IDENTITY.json"] + rebuild["visual_reviews"])
raw_identity = read("publication/RAW_ARCHIVE_IDENTITY.json")
extractor = read("publication/EXTRACTOR_VERIFICATION.json")
raw_manifest = read("publication/RAW_EVIDENCE_MANIFEST.json")["files"]
require("Extractor current source and tests", extractor["status"] == "PASS" and extractor["extractor"]["sha256"] == sha(ROOT / "unpack_evidence.py") and extractor["fixture_tests"]["passed"] == 20)
require("Actual archive byte verification", extractor["actual_archive_verification"]["status"] == "PASS" and extractor["actual_archive_verification"]["archive_sha256"] == raw_identity["sha256"] and extractor["actual_archive_verification"]["verified_members"] == raw_identity["members"])
for path, identity in audit["source_artifacts"].items():
    require("Archived raw audit reference: " + path, raw_manifest["results/confirmation-v1/" + path] == identity)
add("ET-21", "Pinned raw evidence is lossless and the extractor restores exact bytes without clobbering existing evidence", "PACKAGING_BYTE_AND_FIXTURE_VERIFICATION_PASS", ["unpack_evidence.py", "publication/RAW_ARCHIVE_IDENTITY.json", "publication/RAW_EVIDENCE_MANIFEST.json", "publication/RAW_ARCHIVE_VERIFICATION.json", "publication/EXTRACTOR_VERIFICATION.json", "review/results/test_unpack_evidence.py", "review/results/UNPACK_REVIEW.json", "review/results/UNPACK_INITIAL_TEST_RESULT.json"], {"archive_identity": raw_identity, "actual_verification": extractor["actual_archive_verification"], "fixture_tests_passed": extractor["fixture_tests"]["passed"], "audited_raw_artifacts_resolved": len(audit["source_artifacts"]), "raw_file_records": len(raw_manifest), "uncompressed_raw_file_bytes": sum(v["bytes"] for v in raw_manifest.values())}, "Per-file atomic no-replace installation, not one transaction over the entire archive. Verified prefixes may remain after interruption; an idempotent rerun preserves exact files. Symlink destinations/parents are refused. Byte verification does not rerun numerical experiments. Same-host integrity does not defeat a hostile administrator.")
components = read("VERIFICATION.json")
claims["ET-15"].update({"claim_or_question": "Source preparation is additive; outer archive and future publication states use separate detached receipts", "status": "PREPARED_FOR_ADDITIVE_DRAFT_REVIEW", "observed_outcome": {"paper_source_archive": paper_archive, "raw_evidence_archive": raw_identity, "publication": components["publication"], "outer_archive_identity": components["outer_archive_identity"], "earlier_editions": "PRESERVED"}})
claims["ET-15"]["artifact_refs"].extend({"path": p} for p in ["VERIFICATION.json", "publication/PREFERRED_EDITION02_READBACK.json", "publication/PUBLIC_PROJECTIONS.json"])

# Every supplied path must exist. Draft presentation hashes may change only by observation,
# not by pretending that final publication review or a new scientific freeze occurred.
artifact_index = {}
for c in docket["claims"]:
    unique = []
    seen = set()
    for ref in c["artifact_refs"]:
        path = ref["path"]
        if path in seen:
            continue
        seen.add(path)
        p = ROOT / path
        require("Docket artifact exists: " + path, p.is_file())
        digest = sha(p)
        record = {"path": path, "exists": True, "sha256": digest, "bytes": p.stat().st_size, "binding": "OBSERVED_ARTIFACT_IDENTITY_NOT_PUBLICATION_APPROVAL"}
        if "sha256_at_draft" in ref:
            record["draft_sha256"] = ref["sha256_at_draft"]
            record["matches_draft_hash"] = digest == ref["sha256_at_draft"]
        if path in freeze["files"]:
            record["binding"] = "FROZEN_SCIENTIFIC_SOURCE"
            require("Docket frozen reference: " + path, digest == freeze["files"][path])
        unique.append(record)
        artifact_index[path] = {"sha256": digest, "bytes": p.stat().st_size}
    c["artifact_refs"] = unique

now = datetime.datetime.now(datetime.timezone.utc).isoformat()
docket.update({"schema": "earned-turn-evidence-docket/v1", "updated_utc": now, "status": "SCIENTIFIC_EVIDENCE_AUDIT_COMPLETE_FINAL_PUBLICATION_BINDINGS_PENDING", "instructions": "Final scientific claim mapping. All observed artifact paths and numerical fields were reconciled; independent numerical audit is complete. PDF/rebuild/render/archive/publication must receive their own final evidence, not inferred PASS. Observational hashes are not a new scientific freeze.", "docket_source_sha256": sha(Path(__file__)), "artifact_index": artifact_index, "verification": {"checks": len(checks), "all_passed": all(c["passed"] for c in checks), "distinct_artifact_paths": len(artifact_index), "frozen_files_unchanged": len(freeze["files"]), "numeric_audit": "COMPLETE_PASS", "product_gate": "HOLD", "no_mission_rerun": True, "no_frozen_source_or_result_edits": True}, "completion_status": {"independent_numerical_audit": "COMPLETE_PASS", "canonical_PDF": "PENDING_FINAL_HASH", "clean_rebuild": "PENDING_FINAL_RECORD", "every_page_visual_review": "PENDING_FINAL_RECORD", "complete_source_archive": "PENDING_FINAL_HASH_AND_REBUILD", "publication_owner_review": "PENDING", "merge": "PENDING_VERIFICATION", "release": "PENDING_VERIFICATION", "live_served_file": "PENDING_VERIFICATION"}, "accounting_limits": ["Transferred quota originated from external endowment; it is not cash or independently established incremental savings.", "Correctness qualification, whole-system product admission and full-investment recovery are separate decisions.", "Full-cost participant CPU includes dispatch/checking/persistence/maintenance/control; independent audit and development remain additional research investment.", "Unknown human/model/monetary costs are not zero; CPU, elapsed time and abstract work are distinct measures.", "Construction phase includes one solve and persistence, and native/low-rank validation paths differ.", "Storage deduplicates logical aliases to the same file and keeps executable asset bytes separate from full evidence bytes.", "A fixed algorithm vocabulary and one successor depth do not establish discovery improvement or acceleration."], "independence": audit["independence"]})
docket["status"] = "COMPONENTS_VERIFIED_PRODUCT_HOLD_PUBLICATION_PREPARED"
docket["instructions"] = "Final scientific and component claim mapping. Independent numerical audit, canonical PDF, packaged-paper rebuild, all-page review, raw archive and extractor checks are complete. Source preparation is additive; owner review, merge, public release and new served-file status are not claimed. The complete outer archive has a detached final identity to avoid self-hashing."
docket["completion_status"] = {"independent_numerical_audit": "COMPLETE_PASS", "canonical_PDF": "VERIFIED_EXACT_SHA256", "paper_source_archive": "VERIFIED_WITH_CANONICAL_PDF", "clean_packaged_LaTeX_rebuild": "BYTE_IDENTICAL", "every_page_visual_review": "ALL_23_FINAL_PAGES_REVIEWED", "raw_evidence_archive": "ALL_6985_MEMBERS_BYTE_VERIFIED", "extractor": "20_FIXTURE_TESTS_AND_ACTUAL_ARCHIVE_PASS", "complete_outer_archive": "DETACHED_FINAL_IDENTITY_REQUIRED_OUTSIDE_ITS_OWN_PAYLOAD", "publication_source": "PREPARED_FOR_ADDITIVE_DRAFT_REVIEW", "publication_owner_review": "NOT_CLAIMED", "merge": "NOT_PERFORMED", "release": "NOT_PERFORMED", "new_live_served_file": "NOT_PERFORMED"}
docket["path_resolution"] = "Paths are relative to the research companion root. Restore losslessly compressed raw records with unpack_evidence.py before resolving their paths. The raw archive and packaged-LaTeX rebuild have completed verification records. The complete outer archive's final identity is detached from its payload; future publication observations do not retroactively grant authority."
(ROOT / "EVIDENCE_DOCKET.json").write_text(json.dumps(docket, indent=2) + "\n")

lines = ["# Evidence docket — audited scientific record", "", "**Independent numerical audit: PASS. Registered product admission: HOLD.** This is the final claim-to-artifact mapping for the completed study. Canonical PDF, clean rebuild, complete page review, source archive and publication lifecycle bindings remain pending until their final records are supplied.", "", "Scientific freeze: `" + freeze["freeze_sha256"] + "`. All 32 frozen source/protocol files remain unchanged. This docket adds observations and interpretation; it does not create a new scientific freeze or rerun confirmation.", "", "## Claim map", "", "| ID | Claim or recorded outcome | Evidence status |", "|---|---|---|"]
for c in docket["claims"]:
    lines.append("| " + c["id"] + " | " + c["claim_or_question"] + " | " + c["status"] + " |")
lines += ["", "## Decisive results", "", "The frozen auditor checked **168 trials, 3,654 numerical records and 5,334 source-artifact identities**. It accepted 3,486 valid records: 3,444 useful outputs plus 42 restore checks. All 168 negative-conductance requests were correctly refused. There were no detected artifact issues or paired-input divergences. Every arm qualified **492/492** offered useful outputs. See ET-16 and [the exact auditor output](review/results/INDEPENDENT_RESULTS.json).", "", "The registered producer CPU ratio is **0.993302513**, 95% interval **[0.966884058, 1.026457374]**, versus native refactor. The independent implementation recovers the same point, with Monte Carlo interval **[0.967210479, 1.027136356]**. Both fail the required upper bound below 0.95. The conventional-reuse noninferiority guard passes; superiority is not established. Product admission remains **HOLD**. See ET-06.", "", "The actual accepted B08 result determines C's changed requirements. Across 18 scoped streams, construction used 18 parent block solves and 36 direction RHS columns; 156 fresh D outputs then qualified while using the parent. These are instances of a declared numerical construction method, not eighteen independently invented algorithm families. See ET-03–05 and ET-17.", "", "## Matched successor-construction phase", "", "All seven rows use the same 18 scoped streams; every C output qualified. Units are CPU milliseconds.", "", "| Arm | Algorithm + solve + persistence | Whole dispatched C |", "|---|---:|---:|"]
for r in construction:
    lines.append(f"| `{r['arm']}` | {r['mean_algorithm_solve_persistence_cpu_ms']:.3f} | {r['mean_whole_dispatched_cpu_ms']:.3f} |")
lines += ["", "The exact reconstruction comparison follows the same low-rank path plus rebuilding a parent; it is the cleaner attribution contrast. Native C also performs generic full-input inspection, so native-versus-low-rank timing includes a validation-path difference. Every method receives final independent checking. The phase includes a changed-system solve and NPZ persistence; it is not pure construction time. These descriptive secondary results do not override the whole-system gate.", "", "## Conserved allowance and complete cost boundaries", "", "The flywheel released **9,600.000 ms** of unused externally supplied service allowance, debited **1,034.057 ms** for construction and retained **8,565.943 ms**. Each of 24 streams released 400 ms; 18 performed low-rank construction, while six wide-change streams deferred it. Separate externally funded maintenance consumed **912.143 ms**. The observed whole-study CPU difference versus native refactor was only **280.073 ms**, with uncertainty including no gain. Released quota is not a measure of capability-created savings or money. See ET-08.", "", "Whole flywheel CPU was **41,537.568 ms**. The independent audit added **98,521.918 ms CPU** outside the trial boundary. Development, failed candidates, review and unknown human/model/monetary costs remain research investment. Upward whole-microsecond action debit rounding is separate from unrounded CPU. Full investment recovery is unresolved; acceleration is untested; commercial growth is unmeasured. See ET-13.", "", "## Storage: unique files, not aliases", "", "Logical labels such as `native-current` and `parent` can refer to one immutable NPZ. The following totals deduplicate those paths within each trial. Independent trials remain separate copies. Raw evidence storage is a different quantity.", "", "| Arm | Unique asset files | Unique asset bytes | Whole trial evidence bytes |", "|---|---:|---:|---:|"]
for r in storage["aggregates"]:
    lines.append(f"| `{r['arm']}` | {r['unique_asset_files']:,} | {r['unique_asset_bytes']:,} | {r['reported_whole_trial_storage_bytes']:,} |")
lines += ["", "Direct specialist retains no NPZ factors but still has evidence storage. Asset counts do not establish capability growth, and indefinite retention was not evaluated. See ET-18 and [the storage reconciliation](review/results/STORAGE_ACCOUNTING.json).", "", "## Preserved negative boundaries", "", "At the rare-workload mean, native refactor costs 1,086.199 ms versus flywheel 1,088.842 ms. At the maintenance mean, direct specialist costs 2,470.167 ms versus flywheel 2,569.456 ms. These are descriptive six-stream subgroup means, not additional confirmatory superiority tests. Low-rank construction was not used by the flywheel in the wide-change regime. See ET-19.", "", "The prior study remains unchanged: 517/864 flywheel and equally funded learner outcomes, 591/864 portfolio outcomes, no primary admitted asset and no qualified fresh parent-using repair output. Its reserve/search schedule stopped before the primary economic gate was reached. The new study does not relabel or repair those old confirmation observations. See ET-01.", "", "## Scope and independence", "", "The native independent checker and aggregation are separate implementations on the same host and commission. Reviewer corrections to executor validation occurred before freeze; the reviewer received preliminary producer totals before executing the frozen auditor. This is not blinded institutional replication. Parent calls are producer instrumentation attributed to independently checked outputs, not a separate hardware trace.", "", "The two-process restart/lost-acknowledgement probe is development evidence. Matched array reload in native confirmation is a different test. Browser mode is a separate 64-node, four-mission JavaScript demonstration; its recorded panel is replay and the approved executor remains disconnected. Foundation/contract mappings are source inspections. No local EVM execution, live settlement or production authority is established by those diagrams or inspected interfaces. Manager's USDC path remains distinct. See ET-09–12.", "", "## Final package and publication bindings", "", "| Completion item | Status |", "|---|---|"]
for k, v in docket["completion_status"].items():
    lines.append("| " + k.replace("_", " ") + " | " + v + " |")
lines += ["", "ET-14 and ET-15 have no preassigned pass or fabricated final hash. Earlier editions and historical URLs remain intact. A prepared artifact, an owner review, a merged change, a release and a verified served file are distinct states.", "", "## Artifact access", "", "[EVIDENCE_DOCKET.json](EVIDENCE_DOCKET.json) contains each claim's exact artifact paths, byte counts, SHA-256 observations, numerical fields and limits. [The independent review](review/results/INDEPENDENT_REVIEW.md) supplies the reasoning and disclosure. [Docket verification](review/results/DOCKET_VERIFICATION.json) records all path, hash, source-binding and numerical reconciliation checks. Presentation hashes are observations at this docket's timestamp, not authority to publish.", ""]
lines[2] = "**Independent numerical audit: PASS. Registered product admission: HOLD.** This final docket binds the completed scientific results, canonical PDF, byte-identical packaged-LaTeX rebuild, all 23 final page reviews, browser presentation, lossless raw archive and exact extractor. Source preparation is additive. Owner review, merge, public release and new served-file status are not claimed; the complete outer archive receives a detached final identity."
insert_at = lines.index("## Scope and independence")
lines[insert_at:insert_at] = ["## Recovered Strategy Lab: preserve the exact historical status", "", "The prior edition recovered **SUCCESSOR Ω—Strategy Laboratory v0.1.0**, archive SHA-256 `c0df2ac39ddcb32de672db93d05df77b8d8f683966cb92469ab00bf2060284a1`. Its unchanged frozen policies were replayed under CPython 3.13.5 across six attempts and 27,648 cases; non-timing outputs and judgments matched. A separate artifact audit checked 193,536 policy/control artifacts. Acquisition search was not rerun, and equal exploration counts did not establish equal total computation or full-cost productive value.", "", "Byte-identical copies of the prior status, audit and replay records are preserved under `audit/prior-strategy-lab/` with provenance. The original ZIP and full historical payload remain in the preceding Strategy Succession package. Copying these records is not another replay or an observation in the new confirmation. See ET-20.", ""]
lines = [line.replace("Byte-identical copies of the prior status, audit and replay records are preserved under `audit/prior-strategy-lab/` with provenance.", "The prior status, numerical-audit JSON and replay records are preserved byte-for-byte under `audit/prior-strategy-lab/`. The historical narrative is an explicitly named `.public.md` projection omitting two private transport identifiers, with both original and projection identities recorded.").replace("ET-14 and ET-15 have no preassigned pass or fabricated final hash.", "ET-14 binds the actual canonical PDF, packaged-source rebuild and complete page reviews. ET-21 binds all 6,985 raw archive members and 20 extractor fixture tests. ET-15 records source preparation and the need for a detached outer-archive identity; it assigns no owner review or deployment approval.") for line in lines]
lines += ["Raw artifact paths are relative to the companion root. Run `unpack_evidence.py` to restore the verified lossless raw archive before resolving those paths. The complete outer archive cannot contain its own final hash; consult the detached delivered identity and payload manifest. Later publication receipts remain separate from this prepared-source snapshot.", ""]
(ROOT / "EVIDENCE_DOCKET.md").write_text("\n".join(lines))
verification = {"schema": "earned-turn-docket-verification/v1", "recorded_utc": now, "status": "PASS", "scope": "Scientific artifact and numerical claim reconciliation; not final publication QA", "source_sha256": sha(Path(__file__)), "checks": checks, "distinct_artifact_paths": len(artifact_index), "docket_json_sha256": sha(ROOT / "EVIDENCE_DOCKET.json"), "docket_markdown_sha256": sha(ROOT / "EVIDENCE_DOCKET.md"), "pending": docket["completion_status"], "no_mission_rerun": True, "no_frozen_source_or_result_edits": True}
(OUT / "DOCKET_VERIFICATION.json").write_text(json.dumps(verification, indent=2) + "\n")
print(json.dumps({"status": "PASS", "claims": len(docket["claims"]), "checks": len(checks), "distinct_artifact_paths": len(artifact_index), "docket_json_sha256": verification["docket_json_sha256"], "docket_markdown_sha256": verification["docket_markdown_sha256"], "verification_sha256": sha(OUT / "DOCKET_VERIFICATION.json")}, indent=2))
