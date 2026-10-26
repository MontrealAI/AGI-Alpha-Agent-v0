#!/usr/bin/env python3
"""Index saved research resource evidence; never execute an experiment or price unknown labor."""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTED = "2026-10-26T18:37:09+00:00"
REOPENED = "2026-10-26T18:46:38+00:00"


def main() -> None:
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    destination = ROOT / "costs"
    destination.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []

    def read(path: str):
        return json.loads((ROOT / path).read_text())

    def source(path: str) -> dict:
        p = ROOT / path
        return {"path": path, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}

    def add(key, phase, action, paths=(), *, actor="assistant research team", count=None,
            unit=None, wall=None, cpu=None, cpu_scope=None, window=None, started=None,
            ended=None, status="recorded", parent=None, note="", kind="saved_evidence",
            subtotal=False):
        records.append({
            "id": key, "phase": phase, "action": action, "actor": actor,
            "status": status, "evidence_kind": kind, "count": count, "count_unit": unit,
            "started_at": started, "ended_at": ended, "wall_seconds": wall,
            "cpu_seconds": cpu, "cpu_scope": cpu_scope,
            "authoring_or_review_window_seconds": window,
            "active_human_minutes": None, "authoring_model_invoice_usd": None,
            "actual_all_in_expense_usd": None,
            "parent_or_overlapping_record": parent,
            "included_in_partial_root_command_subtotal": subtotal,
            "sources": [source(p) for p in paths], "note": note,
        })

    failures = {
        "schema": "agi-alpha-root-reported-publication-failures/v1",
        "recorded_at": now, "provenance": "Parent researcher task message to accounting reviewer; not a timed command receipt",
        "actions": [
            {"id": "latex-moving-argument", "action": "First LaTeX attempt", "status": "failed",
             "reason": "Moving-argument path macro failure", "correction": "Robust text macro"},
            {"id": "latex-table-bottomrule", "action": "Second LaTeX attempt", "status": "failed",
             "reason": "Input-derived table bottomrule failure", "correction": "Inline derived table rows"},
            {"id": "latex-later-success", "action": "Later PDF compile", "status": "parent_reports_pass_15_pages",
             "reason": "Subsequent publication work continues; final PDF identity belongs to final delivery", "correction": None},
            {"id": "latex-intermediate-success", "action": "Subsequent intermediate PDF compile", "status": "parent_reports_pass_16_pages",
             "reason": "Parent reported 16-page compile before subsequent layout refinements", "correction": None},
            {"id": "publication-relative-path-failure", "action": "Publication patch command from wrong work directory", "status": "failed_no_source_change",
             "reason": "FileNotFoundError from wrong relative path under publication working directory; command corrected", "correction": "Correct path then compile"},
            {"id": "latex-final-success", "action": "Final layout compile and PDF inspection", "status": "parent_reports_pass_15_pages_323855_bytes",
             "reason": "Robustness figure restored to float and bibliography spacing tightened; parent inspected all 15 rendered pages via contact sheet plus full pages 1, 6, 7, 10, 14; no LaTeX warnings, overfull or underfull boxes reported", "correction": None},
            {"id": "chromium-download", "action": "Bundled Chromium 151 download", "status": "failed",
             "reason": "Invalid ZIP; CLI made five internal retries", "internal_retries_reported": 5},
            {"id": "chromium-old-head", "action": "Archived Chromium revision 1200 HEAD probe", "status": "failed",
             "reason": "Returned HTML,195 bytes; no usable browser"},
        ],
        "wall_seconds_each": None, "cpu_seconds_each": None, "model_billing_usd": None,
        "active_human_minutes": None, "working_browser_established_by_these_failed_attempts": False,
        "html_visual_layout_verified_by_these_failed_attempts": False,
        "pdf_layout_inspection": "Parent reports all 15 pages inspected as contact sheet and selected full-size pages; distinct from unavailable HTML browser inspection",
        "note": "The separately metered Playwright missing-executable attempt is indexed from its original receipt, not duplicated here. PDF compilation alone is not page-layout inspection."
    }
    report_path = "costs/root-reported-publication-failures.json"
    (ROOT / report_path).write_text(json.dumps(failures, indent=2) + "\n")

    prior = read("heritage/review/second-capability-gate.json")
    add("prior-second-screen", "historical discovery", "Earlier three-candidate NO_GO screen", ["heritage/review/second-capability-gate.json"],
        count=3, unit="rejected or research-only candidates", window=prior["elapsed_review_window_seconds"],
        started=prior["started_at"], ended=prior["ended_at"],
        note="321.809514 seconds is a review window, not active labor. Historical compute examples inside the gate are earlier evidence, not newly incurred cash outflows.")
    add("historical-initial-asset", "inherited history", "Preserve initial asset construction, acceptance and earlier economic custody", ["heritage/production/OFFERING_AND_CAPABILITY.md", "heritage/protocol/source-freeze.json", "heritage/prior-market-results/CUSTODY.json", "protocol/inherited-identities.json"],
        note="Actual all-in first-asset expense remains unidentified. Modeled opening history 361.52 and first adoption 32.69 USD are scenario amounts, not invoices; historical spending is never repeatedly charged as new cash.")
    add("ecosystem-source-audit", "discovery", "Read-only ownership, runtime and economic source audit", ["heritage/ecosystem-audit/coordination_audit.json", "heritage/ecosystem-audit/economics_audit.json", "heritage/ecosystem-audit/runtime_sources/SOURCES.json"],
        note="No complete time or billing receipt. Unknown read/tool/orchestration cost remains.")
    screen = read("heritage/ecosystem-audit/candidate-screen/native-lock-screen.json")
    add("native-lock-feasibility-screen", "discovery", "Read-only 41-pin metadata opportunity screen", ["heritage/ecosystem-audit/candidate-screen/native-lock-screen.json"],
        count=1, unit="candidate feasibility screen", window=screen["screen_timing"]["elapsed_agent_wall_seconds"],
        note="80.08938511399901-second agent window; snapshot CPU is only a nested final-write measurement, not total screen compute.")
    add("new-portfolio", "discovery", "Four-choice bounded screen and one prototype selection", ["protocol/research-envelope.json", "protocol/candidate-selection.json", "review/candidate-portfolio-accounting.json"],
        count=4, unit="choices: incumbent, pip adoption, custom resolver, full application",
        note="One prototype selected, two construction directions rejected, incumbent retained as alternative. Unknown rejected/search expense is not zero; no monetary qualification assumed.")
    add("B-authoring", "construction", "B pip adapter and native Workbench integration; A study recorder", ["resources/authoring-events.jsonl", "protocol/asset-B.json", "history/development/retained-initial.py"],
        actor="root assistant", count=1, unit="selected B asset construction episode",
        note="Assistant-authored ordinary-tool adoption. Source writing, model inference and active attention unmetered. A recorder and common checker are supplied study work, not costless commercial construction.")
    construction = read("resources/conventional/CONSTRUCTION_RECEIPT.json")
    add("C-authoring", "construction", "Independent C wrapper construction including portable-path correction", ["resources/conventional/CONSTRUCTION_RECEIPT.json", "resources/conventional/CONSTRUCTION_RECEIPT.v1.json", "resources/conventional/failed-development-v1-source.py", "protocol/asset-C.json"],
        actor="runtime_audit assistant", count=1, unit="C asset; initial and corrected development versions",
        window=construction["elapsed_wall_seconds"], started=construction["started_utc"], ended=construction["ended_utc"],
        note="Final 259.268458003-second window contains the earlier 188.08505785-second window; never sum them. No B source or fresh outcomes seen before construction.")
    add("verifier-authoring", "verification construction", "Separate acceptance contract and metadata verifier", ["review/independent-acceptance-prefreeze.json", "production/verify.py", "production/test_verify.py", "protocol/acceptance-contract.json"],
        actor="coordination_audit assistant", count=1, unit="shared independently authored checker",
        note="Same-session role independence; one validator shared by A/B/C. Authoring and review billing/attention unobserved.")
    controls = read("resources/verifier-controls/run-001/summary.json")
    add("verifier-controls", "development verification", "Finite synthetic acceptance controls", ["resources/verifier-controls/run-001/summary.json"],
        count=controls["total"], unit="synthetic controls", wall=controls["wall_seconds"],
        note="24/24; zero fresh production/customer jobs. Unknown process CPU is not filled with zero.")
    add("B-F01-correction", "prefreeze correction", "Correct native headline to preserve incomplete verification", ["review/independent-acceptance-prefreeze.json", "review/F01-resolution.json"],
        count=1, unit="material B correction", parent="B-authoring", note="Three truth-table checks are nested verification, not three new customer outcomes. F02 conservative-negative limitation was disclosed, not invented as a correction.")
    add("C-path-correction", "prefreeze correction", "Reject original absolute-path job and preserve portable correction", ["resources/conventional/development-original/independent-certificate.json", "resources/conventional/CONSTRUCTION_RECEIPT.json"],
        count=1, unit="material C correction", parent="C-authoring", note="Original producer looked consistent but independent acceptance was INCOMPLETE; failed attempt and its costs retained.")
    add("selection-driver-corrections", "prefreeze correction", "S01-S03 and D01-D02 freeze, selection and partial-output corrections", ["review/selection-driver-prefreeze.json", "review/production-independent-review.json", "history/development/production-freeze-01.json", "history/development/production-freeze-02.json"],
        count=5, unit="reported protocol/driver findings", note="Earlier development freezes retained; corrections precede fresh metadata. No primary replacement cohort.")

    descriptions = {
        "baseline-wheel-acquisition": ("development preparation", "Acquire 41 baseline public wheel artifacts"),
        "development-pip-preflight": ("development baseline", "Strong direct pip development preflight"),
        "retained-development-01": ("development construction", "B raw retained-adapter development invocation"),
        "incumbent-development-01": ("development baseline", "A measured incumbent development invocation"),
        "retained-native-development-01": ("development construction", "B first native Workbench development invocation"),
        "retained-native-development-02": ("development construction", "B subsequent native Workbench development invocation"),
        "fresh-identity-selection": ("fresh input selection", "Select six predecessor identities before metadata acquisition"),
        "fresh-wheel-acquisition": ("fresh input acquisition", "Acquire six registered predecessor wheels and jobs"),
        "primary-confirmation": ("primary production", "Single frozen six-question A/B/C confirmation"),
        "market-primary": ("primary simulation", "Single frozen 1920-world market campaign"),
    }
    top_receipts = []
    for p in sorted((ROOT / "resources").glob("*/receipt.json")):
        d = json.loads(p.read_text())
        if d.get("schema") != "second-investment-resource-receipt/v1":
            continue
        name = p.parent.name
        phase, description = descriptions[name]
        count, unit = (18, "arm evaluations on six research questions") if name == "primary-confirmation" else ((1920, "paired worlds; 5760 enterprise histories") if name == "market-primary" else (1, "top-level command"))
        add("root-" + name, phase, description, [str(p.relative_to(ROOT))], actor="root assistant command", count=count, unit=unit,
            wall=d["wall_seconds"], cpu=d["self_cpu_seconds"] + d["child_cpu_seconds"],
            cpu_scope="wrapper self plus all child CPU; inclusive", started=d["started_at"], ended=d["finished_at"],
            status="exit_" + str(d["exit_code"]), subtotal=True,
            note="One selected nonoverlapping root command. Nested producer/verifier/campaign resources are not added again. This is machine resource use, not a dollar bill.")
        top_receipts.append(d)

    for suffix, output in [("original", "development-original"), ("portable", "development-portable")]:
        p = f"resources/conventional/{output}/result.json"
        d = read(p)
        add("C-baseline-" + suffix, "development construction", "C " + suffix + " baseline execution", [p], actor="runtime_audit assistant",
            count=1, unit="development invocation", wall=d["elapsed_wall_seconds"], cpu=d["cpu_seconds"],
            cpu_scope="producer-recorded inclusive CPU", parent="C-authoring", note="Not added to construction elapsed window or to the partial root-command subtotal.")
    for suffix, name in [("original", "development-checks-absolute-attempt.json"), ("portable", "development-checks.json")]:
        p = "resources/conventional/" + name
        d = read(p)
        add("C-controls-" + suffix, "development verification", "C " + suffix + " four-case control suite", [p], count=len(d["results"]), unit="synthetic development checks",
            wall=d["wall_seconds"], cpu=d["cpu_seconds"], cpu_scope="suite-inclusive CPU", parent="C-authoring", note="Do not add contained per-case result timing to the suite total.")
    add("C-independent-certificates", "development verification", "Independent C baseline/negative acceptance", [str(p.relative_to(ROOT)) for p in sorted((ROOT / "resources/conventional").glob("*/independent-certificate.json"))], count=4, unit="preserved development certificates", parent="C-authoring", note="Includes refused original absolute-path packet; elapsed resources not captured.")

    campaign = read("results/confirmation-01/campaign.json")
    for row in campaign["rows"]:
        p = f"results/confirmation-01/{row['family']}/{row['arm']}/service-receipt.json"
        d = read(p)
        add("primary-service-" + row["family"] + "-" + row["arm"], "primary production detail", "Complete service " + row["family"] + " arm " + row["arm"], [p, row["result_path"], row["verification_path"]],
            count=1, unit="arm evaluation; not a separate mission", wall=d["complete_service_wall_seconds"], cpu=d["inclusive_cpu_seconds"], cpu_scope="whole service including verification; inclusive", parent="root-primary-confirmation",
            note="Nested primary measurement for comparing branches. Excluded from aggregate root command subtotal; six questions overall, not 18 independent customers.")

    for key, path in [("market-development-16", "market/development/receipt.json"), ("market-development-17", "market/development/receipt-02.json")]:
        d = read(path)
        add(key, "simulation construction", "Continuation development regression suite", [path], count=d["software_checks"], unit="synthetic software checks", wall=d["wall_seconds"], cpu=d["child_cpu_seconds"], cpu_scope="child process CPU", note="No fresh market campaign. Repeated control sets are development cost, not additional empirical evidence.")
    add("market-earlier-development", "simulation construction", "Earlier 10/10/13-control iterations and wrong-directory failure", ["market/development/receipt.json"], count=4, unit="earlier reported invocations: three suites and one module-not-found", note="Receipt lists earlier 10, 10, 13 passing suites and one wrong-cwd command; unmetered resources retained as unknown. Its 16-check final pass is the separately metered row, not a fifth extra event.")
    d = read("review/market-review-execution.json")
    for i, trial in enumerate(d["tests"]):
        add("market-independent-check-" + str(i + 1), "simulation review", "Independent synthetic invariant execution", ["review/market-review-execution.json"], count=1, unit="review command", wall=trial["elapsed_wall_seconds"], cpu=trial["child_cpu_seconds"], cpu_scope="child process CPU", note="The seven-probe report is nested in the second command; do not add its process timing again.")
    for key, path, action in [
        ("market-static-review", "review/market-independent-review.json", "Continuation source and economics invariant review"),
        ("runner-prefreeze-review", "review/campaign-driver-review.json", "Frozen campaign design and driver review"),
        ("runner-design-check", "review/campaign-validation-only.json", "Validation-only frozen design arithmetic"),
        ("runner-statistics-check", "review/market-runner-reporting-review.json", "Synthetic distribution/null/quantile reporting checks"),
        ("production-archive-review", "review/production-independent-review.json", "Read-only 18-output production custody audit"),
        ("native-archive-review", "review/native-pack-review.json", "Native pack/artifact custody inspection"),
        ("freshness-identity-review", "review/prior-cohort-identity-review.json", "Disjoint cohort identity review"),
        ("packet-interpretation-review", "review/packet-interpretation-review.json", "User-facing packet interpretation check"),
        ("manuscript-review", "review/manuscript-review.json", "Manuscript factual review and corrected reviewer false alarm"),
        ("portable-static-review", "review/companion-static-review.json", "Read-only companion source review"),
    ]:
        d = read(path)
        add(key, "verification and review", action, [path],
            wall=d.get("audit_wall_seconds", d.get("elapsedWallSeconds")), cpu=d.get("cpuSeconds"),
            cpu_scope="reported process CPU only" if d.get("cpuSeconds") is not None else None,
            note="No new primary production or market execution. Detailed assertions are audit checks, never additional independent observations.")
    for key, path in [("ledger-audit-first-failure", "review/history/market-results-registration-assumption-failure.json"), ("ledger-audit-corrected", "review/market-results-independent-review.json")]:
        d = read(path)
        add(key, "saved ledger audit", "Read full saved 1920-world ledgers and reconcile aggregates", [path], count=1920, unit="saved worlds inspected; zero newly simulated", wall=d["audit_wall_seconds"], cpu=d["audit_cpu_seconds"], cpu_scope="auditor process CPU", status=d.get("status", "recorded"),
            note="First pass had a wrong reviewer registration predicate; corrected using actual public-comment receipt. Both executions count as research work. Nested first-pass timing repeated in final review must not be counted twice.")
    add("saved-market-analysis", "analysis", "Explain selected cash path, thresholds and two positive path perturbations", ["review/seed8001-hand-reconciliation.json", "analysis/market-findings.json", "analysis/market-findings.md"], count=1, unit="analysis episode", note="Reads saved outcomes only. Complete execution/authoring resources unmetered; not a new simulation.")

    presentation = read("resources/rendering/CONTRIBUTION_RECEIPT.json")
    add("presentation-authoring", "post-confirmation presentation", "Common English/French six-packet renderer and index", ["resources/rendering/CONTRIBUTION_RECEIPT.json"], window=presentation["authoring_window_elapsed_seconds"], started=presentation["started_utc"], ended=presentation["finished_utc"], count=7, unit="HTML outputs; not new customer jobs", note="Common post-evaluation contribution, not measured productivity benefit. Window overlaps nested execution and other team work.")
    for key, path, label in [("render-first", "resources/rendering/render-execution-01.json", "First packet rendering"), ("render-final", "resources/rendering/render-execution.json", "Subsequent packet rendering"), ("browser-missing", "resources/rendering/visual-execution.json", "Playwright layout attempt;missing Chromium executable")]:
        d = read(path)
        add(key, "post-confirmation presentation", label, [path], count=1, unit="command", wall=d["elapsed_wall_seconds"], cpu=d.get("render_child_cpu_seconds", d.get("child_cpu_seconds")), cpu_scope="child process CPU", parent="presentation-authoring", status="exit_" + str(d["exit_code"]), note="This failed browser attempt is metered. Separate root browser-download attempts remain unmetered and unsuccessful.")
    add("publication-data-build", "publication", "Construct figures/tables from saved primary results", ["publication/publication-build-receipt.json"], count=1, unit="derived-data build receipt", note="No new simulated worlds; process resources unavailable in this receipt.")
    for action in failures["actions"]:
        paths = [report_path] + (["publication/paper.pdf", "publication/compile-log.txt"] if action["id"] == "latex-final-success" else [])
        add(action["id"], "publication and layout attempts", action["action"], paths, count=1, unit="parent-reported action", status=action["status"], kind="parent_researcher_report", note=action["reason"] + ". CPU/wall and active attention unmeasured, not zero.")

    portable = read("resources/portable-companion/CONTRIBUTION_RECEIPT.json")
    add("portable-authoring", "reproducibility construction", "Archive verifier/builder and provenance construction", ["resources/portable-companion/CONTRIBUTION_RECEIPT.json"], count=1, unit="portable companion tooling contribution", window=portable["authoring_window_elapsed_seconds"], started=portable["started_utc"], ended=portable["finished_utc"], note="658.292897827-second authoring window includes nested support executions; do not convert it to labor or add those execution spans to it.")
    add("portable-source-verification", "reproducibility verification", "Full source and raw-ledger verification", ["resources/portable-companion/CONTRIBUTION_RECEIPT.json"], wall=portable["source_verification_wall_seconds"], cpu=portable["source_verification_child_cpu_seconds"], cpu_scope="child process CPU", parent="portable-authoring")
    portable_rows = [
        ("portable-tool-download", "tool-acquisition.json", "Acquire two exact official execution-tool wheels", "self_cpu_seconds"),
        ("portable-url-provenance", "wheel-url-provenance.json", "Save 41 public metadata responses for existing wheel URLs", "self_cpu_seconds"),
        ("portable-full-stage", "stage-receipt.json", "Create and verify disposable full companion stage", "child_cpu_seconds"),
        ("portable-relocation-replay", "REPRODUCTION_RECEIPT.json", "One relocation replay of existing six questions", "child_cpu_seconds"),
        ("portable-github-stage", "github-edition-check.json", "GitHub stage with negative tamper/no-network checks", "stage_child_cpu_seconds"),
    ]
    for key, filename, label, cpu_key in portable_rows:
        path = "resources/portable-companion/" + filename
        d = read(path)
        add(key, "post-confirmation reproducibility", label, [path], wall=d["elapsed_wall_seconds"], cpu=d.get(cpu_key), cpu_scope=cpu_key, parent="portable-authoring", count=18 if "replay" in key else 1, unit="reproduction arm evaluations; zero fresh missions" if "replay" in key else "support command or receipt", note="Post-confirmation support. No fresh target selection or additional primary evidence. Stage CPU may cover a narrower interval than its receipt's full check window; retain the source metric name.")
    p = "resources/portable-companion/candidate-screen-custody.json"
    add("screen-custody-copy", "post-confirmation custody", "Copy unchanged earlier feasibility screen into companion", [p], wall=read(p)["elapsed_copy_seconds"], note="Outside main portable authoring window; not a new candidate search.")
    add("portable-documentation-amendment", "post-confirmation documentation", "Clarify frozen-market replay label and immutable-copy boundary", ["resources/portable-companion/CONTRIBUTION_RECEIPT.json", "tools/COMPANION.md"], note="Later post-review amendment has no measured duration; no additional market execution.")
    for path, label in [("resources/demo/started.json", "Interactive financial demonstration authoring"), ("review/demo-review-start.json", "Independent demonstration review")]:
        add("demo-" + ("authoring" if path.startswith("resources") else "review"), "post-confirmation demonstration", label, [path], status="started_at_snapshot", note="Final receipt if available is separately indexed; unfinished/post-snapshot work remains in the closing delivery supplement. No value credited to production.")
    for path in ["resources/demo/CONTRIBUTION_RECEIPT.json", "resources/demo/contribution-receipt.json", "review/demo-review.json"]:
        if (ROOT / path).is_file():
            d = read(path)
            window = d.get("resources", {}).get("review_window_elapsed_seconds")
            add("demo-final-" + Path(path).stem.lower(), "post-confirmation demonstration", "Completed demonstration support receipt", [path], window=window,
                started=d.get("resources", {}).get("started_utc", d.get("first_recorded_at")), ended=d.get("completed_utc", d.get("completed_at")),
                note="Post-outcome presentation/review, never a fresh economic observation. Review window contains measured executions and unmetered authoring; its reported execution subtotal is not added again to individual command receipts.")
    for path in sorted((ROOT / "resources/demo").glob("build-*.json")):
        d = json.loads(path.read_text())
        add("demo-" + path.stem, "post-confirmation demonstration", "Preserved demonstration presentation build", [str(path.relative_to(ROOT))],
            count=1, unit="presentation build", wall=d.get("buildWallSeconds"), cpu=d.get("buildCPUSeconds"), cpu_scope="builder process CPU if exposed",
            note="Distinct build receipts only; BUILD_RECEIPT is latest-copy evidence, not an additional execution. The first build's original full receipt was overwritten and its retrospective provenance remains explicit.")
    mobile_patch = "resources/demo/history/mobile-wrap-fix.patch"
    if (ROOT / mobile_patch).is_file():
        browser_result = read("review/demo-browser-results.json") if (ROOT / "review/demo-browser-results.json").is_file() else {}
        current_demo_hash = source("publication/AGI_ALPHA_Second_Investment_Demo.html")["sha256"]
        final_browser_passed = browser_result.get("passed") and browser_result.get("htmlSHA256") == current_demo_hash
        if (ROOT / "review/demo-review.json").is_file():
            latest_review = read("review/demo-review.json")
            final_browser_passed = final_browser_passed or (latest_review.get("disposition", "").startswith("PASS") and latest_review.get("artifact", {}).get("sha256") == current_demo_hash)
        add("demo-mobile-wrap-correction", "post-confirmation presentation correction", "Repair independently observed French calculator overflow at 360px", [mobile_patch, "resources/demo/history/demo-before-mobile-wrap-fix.html", "review/demo-browser-french-overflow.json", "review/demo-browser-french-overflow-diagnostic.json"],
            count=1, unit="observed presentation defect and CSS correction", status="corrected_and_final_browser_passed" if final_browser_passed else "corrected_pending_final_QA_report", note="Browser found 398px page width at 360px viewport. Corrected nowrap badge/min-content grid using CSS wrapping/min-width; prior HTML and exact patch retained. Data, JavaScript, embedded PDF and primary outcomes unchanged. Build cost is a separate numbered presentation receipt; do not count it twice.")
    currency_patch = "resources/demo/history/mobile-currency-fit.patch"
    if (ROOT / currency_patch).is_file():
        add("demo-currency-typography-correction", "post-confirmation presentation correction", "Keep French mobile market currency token on one line", [currency_patch, "resources/demo/history/demo-before-currency-fit.html", "resources/demo/CONTRIBUTION_RECEIPT.json"],
            count=1, unit="root visual-review correction", note="Seventh build applies responsive market-value font sizing only. Previous HTML and exact patch retained. Inline JavaScript, embedded data and PDF unchanged; final affected-section capture and source-equivalence review are separate QA evidence.")
    seen_functional_receipts = set()
    for source_path in sorted((ROOT / "review").glob("demo-functional-*.json")):
        raw = source_path.read_bytes()
        d = json.loads(raw)
        if d.get("schema") != "agi-alpha-demo-functional-qa/v1" or raw in seen_functional_receipts:
            continue
        seen_functional_receipts.add(raw)
        path = str(source_path.relative_to(ROOT))
        add("qa-" + source_path.stem, "post-confirmation demonstration QA", "Distinct functional JavaScript review execution", [path],
            count=1, unit="functional review command", wall=d.get("elapsed_wall_seconds"), cpu=d.get("child_cpu_seconds"),
            cpu_scope="child process CPU", status="passed" if d.get("passed") else "failed_preserved",
            note="Minimal-DOM functional checks are not browser rendering. Preserve earlier harness failures and the earlier-HTML pass as distinct review work; byte-identical receipt aliases are not additional executions.")
    browser_receipts = sorted((ROOT / "resources/demo-qa").glob("browser-execution-*.json"))
    latest_browser = ROOT / "resources/demo-qa/browser-execution.json"
    prior_bytes = {p.read_bytes() for p in browser_receipts}
    if latest_browser.is_file() and latest_browser.read_bytes() not in prior_bytes:
        browser_receipts.append(latest_browser)
    for path in browser_receipts:
        d = json.loads(path.read_text())
        add("qa-" + path.stem, "post-confirmation browser QA", "Distinct local browser review execution", [str(path.relative_to(ROOT))],
            count=1, unit="local browser command", wall=d.get("elapsed_wall_seconds"), cpu=d.get("child_cpu_seconds"),
            cpu_scope="child process CPU", status="exit_" + str(d.get("exit_code")),
            note="Includes unsuccessful sandbox/selector attempts where preserved. Latest-copy aliases with identical bytes are not counted as additional executions. No new market, production or customer mission.")
    for filename in ["demo-browser-initial-launch-failure.json", "demo-browser-closed-details-harness.json", "demo-browser-pdf-selection-harness.json", "demo-browser-french-overflow.json", "demo-browser-french-overflow-diagnostic.json", "demo-browser-results.json", "demo-currency-fit-results.json", "final-paper-layout-review.json"]:
        path = "review/" + filename
        if (ROOT / path).is_file():
            d = read(path)
            add("evidence-" + Path(filename).stem, "post-confirmation visual QA evidence", "Saved browser/PDF visual-review report", [path],
                status="passed" if d.get("passed") else "see_source_report", parent="corresponding browser or PDF execution; do not count twice",
                note="Evidence report is not an additional execution. Source report determines success, scope and artifact identity; unavailable resource measurements remain unknown.")
    history_path = "costs/history/accounting-01/PRESERVATION.json"
    if (ROOT / history_path).is_file():
        preserved = read(history_path)
        add("accounting01-preservation", "accounting snapshot preservation", "Retain prior 95-row/294-source accounting package unchanged", [history_path],
            count=1, unit="earlier snapshot preserved", wall=preserved["copy_wall_seconds"], cpu=preserved["copy_self_cpu_seconds"], cpu_scope="copy process only",
            note="Some previously bound presentation files subsequently changed. The earlier index is historical; its 294 identities are not asserted to match the current tree. Only preservation receipt is indexed, with no recursive traversal of earlier ledgers.")
        path = "costs/history/accounting-01/accounting-validation.json"
        d = read(path)
        add("accounting01-validation", "accounting snapshot verification", "Earlier accounting snapshot's post-write validation", [path],
            wall=d["validation_wall_seconds"], cpu=d["validation_self_cpu_seconds"], cpu_scope="validation process CPU", note="Validates the earlier snapshot as it existed then. Does not imply all earlier presentation identities remain current.")
        add("resource-index-reopening", "accounting and publication", "Reopen accounting after final demo and visual QA", ["tools/build_resource_accounting.py"],
            actor="coordination_audit assistant", window=(datetime.now(timezone.utc) - datetime.fromisoformat(REOPENED)).total_seconds(), started=REOPENED, ended=now,
            parent="resource-index-authoring", note="Overlaps the encompassing assignment-to-final-snapshot window; do not add these windows. Actual inference/labor unknown. Prior snapshot and stale-identity boundary remain preserved.")
    add("accounting-generator-lookup-failures", "accounting and publication", "First two resource-index invocations failed before ledger emission", ["tools/build_resource_accounting.py"], count=2, unit="failed indexing invocations", status="failed_then_corrected", kind="reviewer_observed_command_failure",
        note="FileNotFoundError from first deriving service receipt under A/delivery, then under B/native. Corrected to the registered family/arm service path. No experiment source or results changed; failed invocation CPU/wall not separately measured.")
    add("resource-index-authoring", "accounting and publication", "Assemble this source-bound resource and cost index", ["tools/build_resource_accounting.py"], actor="coordination_audit assistant", window=(datetime.now(timezone.utc) - datetime.fromisoformat(STARTED)).total_seconds(), started=STARTED, ended=now, note="Elapsed task window includes reading, thought and tool latency; active labor/model billing remain unknown. The generator's tiny self timing below covers only one serialization run, not this full contribution.")

    ordered = sorted(top_receipts, key=lambda x: x["started_at"])
    disjoint = all(datetime.fromisoformat(a["finished_at"]) <= datetime.fromisoformat(b["started_at"]) for a, b in zip(ordered, ordered[1:]))
    if not disjoint:
        raise ValueError("Selected root-command intervals overlap; do not form subtotal")
    subtotal = {
        "label": "PARTIAL_OBSERVED_COMPUTE_ONLY_NOT_TOTAL_RESEARCH_COST",
        "records": [x["id"] for x in records if x["included_in_partial_root_command_subtotal"]],
        "commands": len(ordered), "nonoverlapping_root_intervals_checked": disjoint,
        "wall_seconds_sum": sum(d["wall_seconds"] for d in ordered),
        "wrapper_plus_child_cpu_seconds_sum": sum(d["self_cpu_seconds"] + d["child_cpu_seconds"] for d in ordered),
        "monetary_value_usd": None,
        "excludes": "Other agents, source reading, model inference, human attention, research writing, all other listed development/review/publication/tooling work and closing delivery. Nested timings are never added again. Wall sum is selected command occupancy, not total team elapsed time.",
    }
    cost_inputs = ["market/cost-profiles.json", "market/effect-profile.json", "market/campaign-protocol.json", "market/campaign-freeze.json", "market/upstream/canonical/automated-costs.mjs", "market/upstream/canonical/shadow-ledger.mjs", "market/upstream/protocol/protocol.json", "market/upstream/protocol/external-sources.json", "market/upstream/deployment-robustness/protocol.json", "heritage/market/protocol/parameter-manifest.json", "heritage/calibration/source-manifest.json", "protocol/asset-B.json", "protocol/asset-C.json"]
    cost_inputs += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "heritage/prior-market-results").rglob("protocol.json"))]
    inventory = set(cost_inputs)
    for record in records:
        inventory.update(s["path"] for s in record["sources"])
    for base in ["resources", "review"]:
        for p in (ROOT / base).rglob("*"):
            if p.is_file() and p.suffix in {".json", ".jsonl"} and "selected-wheels" not in p.parts:
                inventory.add(str(p.relative_to(ROOT)))
    inventory.update(["results/confirmation-01/campaign.json", "results/production-summary.json", "market/results/primary-01/completion.json", "market/results/primary-01/summary.json", "publication/AGI_ALPHA_Second_Investment_Demo.html"])
    profiles = read("market/cost-profiles.json")["profiles"]
    ledger = {
        "schema": "agi-alpha-research-resource-accounting/v1", "snapshot_at_utc": now,
        "snapshot_id": "accounting-02" if (ROOT / history_path).is_file() else "accounting-01",
        "status": "OBSERVED_RESOURCE_REFERENCE_INDEX_WITH_UNKNOWN_ACTUAL_TOTAL_COST",
        "scope": "Historical context plus this bounded discovery, construction, confirmation, simulation, failed attempts, review and post-presentation work. Source receipts are immutable evidence snapshots; future changes require a supplement.",
        "actual_money": {"observed_customer_collections_usd": 0, "observed_new_paid_commitments_usd": 0, "complete_starting_research_capital_usd": None, "complete_research_expense_usd": None, "model_inference_and_tool_service_invoice_usd": None, "active_human_minutes": None, "ongoing_upkeep_usd": None, "note": "Zero observed customer receipts and no new paid commitment do not mean supplied compute, software work, inference or research was free. No actual enterprise surplus or actual monetary return is established."},
        "model_money_separate": {"classification": "SIMULATED_SCENARIO_NOT_ACTUAL_PAYMENT", "seed_usd": 1000, "reserve_usd": 200, "historical_opening_cost_usd": 361.52, "first_asset_adoption_usd": 32.69, "second_oneoff_cents": {k: v["totalOneoffCents"] for k, v in profiles.items()}, "source_identities": [source(p) for p in cost_inputs], "note": "The complete-category low/reference/high allocations were frozen before fresh economic outcomes; actual unknown profile stays unidentified. This accounting index does not recalibrate or change frozen costs after results."},
        "distinct_action_counts": {"earlier_screen_choices": 3, "current_portfolio_choices": 4, "new_selected_prototype_B": 1, "independent_C_asset": 1, "new_directions_rejected_before_construction": 2, "no_investment_alternative": 1, "B_explicit_development_invocations": 3, "A_explicit_development_invocations_excluding_initial_pip_preflight": 1, "C_baseline_invocations": 2, "C_synthetic_case_executions": 8, "C_independent_development_certificates": 4, "acceptance_synthetic_controls": 24, "material_prefreeze_findings_corrected": 7, "fresh_primary_questions": 6, "fresh_primary_arm_evaluations": 18, "fresh_market_campaigns": 1, "fresh_market_paired_worlds": 1920, "modeled_enterprise_histories": 5760, "archived_market_audit_passes_including_failed_predicate": 2, "post_confirmation_relocation_replays": 1, "replay_arm_evaluations": 18, "new_customer_jobs": 0, "warning": "These counts have different units and overlapping scopes. Do not sum them into a workload or independent sample count."},
        "partial_observed_compute_subtotal": subtotal,
        "post_confirmation_counts": {"numbered_demo_builds": len(list((ROOT / "resources/demo").glob("build-*.json"))), "distinct_browser_command_receipts": len(browser_receipts), "functional_command_receipts": sum(x["phase"] == "post-confirmation demonstration QA" for x in records), "new_scientific_confirmations": 0, "note": "Presentation commands and nested evidence reports are different units; do not add reports as extra executions."},
        "accounting_rules": ["Unknown money or labor is null, not zero.", "Do not monetize elapsed authoring/review windows as active human attention.", "Do not sum overlapping team authoring windows.", "Do not add a command's nested producer, verifier, suite or archive timing to its inclusive outer receipt.", "Repeated receipt versions describe overlapping history; original and corrected execution attempts count separately only when distinct executions are evidenced.", "Keep historical cost recovery, prospective deployment, available modeled operating funds and next-investment repayment separate.", "Scenario wages/compute tariffs price assumptions, not actual bills.", "Post-outcome publication/tooling/reproduction never increases measured capability benefits or creates new customer demand.", "Final archive creation, integrity checking, persistence, publication and communication after this snapshot belong to a dated outside-archive closing supplement."],
        "records": records, "source_inventory": [source(p) for p in sorted(inventory)],
        "unmetered_residual": ["Complete original first-asset research history beyond preserved custody", "All assistant inference/token charges and provider infrastructure not exposed", "Active researcher/customer attention", "Unrecorded reading, coordination, source writing, tool orchestration and failed commands", "Prior rejected discovery and later unfunded attempts in actual dollars", "Future maintenance and support", "Publication/browser attempts without receipts", "Final closing delivery after snapshot"],
        "index_generation": {"new_experiment_runs": 0, "wall_seconds_before_serialization": time.perf_counter() - wall_start, "self_cpu_seconds_before_serialization": time.process_time() - cpu_start, "not_full_authoring_cost": True},
    }
    (destination / "research-resource-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    columns = ["id", "phase", "action", "actor", "status", "evidence_kind", "count", "count_unit", "started_at", "ended_at", "wall_seconds", "cpu_seconds", "cpu_scope", "authoring_or_review_window_seconds", "active_human_minutes", "authoring_model_invoice_usd", "actual_all_in_expense_usd", "parent_or_overlapping_record", "included_in_partial_root_command_subtotal", "sources", "note"]
    with (destination / "research-resource-ledger.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in records:
            printable = dict(row)
            printable["sources"] = " | ".join(x["path"] + "#sha256=" + x["sha256"] for x in row["sources"])
            writer.writerow({k: "UNKNOWN" if v is None else v for k, v in printable.items()})
    print(json.dumps({"records": len(records), "source_files": len(inventory), "partial_compute": subtotal, "actual_total_expense_usd": None}))


if __name__ == "__main__":
    main()
