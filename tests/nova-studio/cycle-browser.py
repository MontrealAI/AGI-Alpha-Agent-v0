# SPDX-License-Identifier: Apache-2.0
"""Production browser controls, actual bounded runtime and two disposable EVM settlements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any, cast
from uuid import uuid4

from playwright.sync_api import Route, expect, sync_playwright


def main() -> None:
    config = json.loads(Path(sys.argv[1]).read_text())
    output = Path(config["output"])
    origin = config["url"].split("/ascension/")[0]
    errors: list[str] = []
    checks: list[str] = []
    transaction_history: list[str] = []
    financial_evidence: dict[str, Any] = {}
    expected_nodes = [
        "Insight",
        "Nova-Seeds",
        "MARK",
        "Sovereign",
        "Business",
        "Marketplace",
        "Jobs",
        "Agents",
        "Nodes",
        "Council",
        "Value Reservoir",
        "Architect",
    ]
    expected_edges = [
        "Insight → Nova-Seeds",
        "Nova-Seeds → MARK",
        "MARK → Sovereign",
        "Sovereign → Business",
        "Business → Marketplace",
        "Marketplace → Jobs",
        "Jobs → Agents",
        "Agents → Value Reservoir",
        "Jobs → Value Reservoir",
        "Value Reservoir → Nova-Seeds",
        "Value Reservoir → Marketplace",
        "Agents → Nodes",
        "Nodes → Agents",
        "Architect → Sovereign",
        "Sovereign → Architect",
        "Architect → Insight",
        "Insight → Architect",
        "Council → Sovereign",
    ]
    fixture = "window.__novaActors=" + json.dumps(config["actors"]) + ";\n"
    fixture += Path(__file__).with_name("browser-provider.js").read_text()
    capsule_passphrase = "browser complete cycle capsule"
    project_passphrase = "browser encrypted project history"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True)
        context.add_init_script(script=fixture)

        def artifact_request(route: Route) -> None:
            # Keep the browser's native fetch receiver intact while every
            # synthetic artifact request stays on the disposable local server.
            request = route.request
            cors = {
                "access-control-allow-origin": origin,
                "access-control-allow-methods": "GET, POST, OPTIONS",
                "access-control-allow-headers": "authorization, content-type",
            }
            if request.method == "OPTIONS":
                route.fulfill(status=204, headers=cors)
                return
            target = origin + ("/upload" if request.method == "POST" else "/ipfs/" + request.url.split("/")[-1])
            response = route.fetch(url=target)
            route.fulfill(response=response, headers={**response.headers, **cors})

        context.route("https://uploads.pinata.cloud/v3/files", artifact_request)
        context.route("https://gateway.pinata.cloud/ipfs/*", artifact_request)
        context.route("https://ipfs.io/ipfs/*", artifact_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(config["url"])
        expect(page.locator("#status")).to_contain_text("Start locally")
        assert page.evaluate("Function.prototype.toString.call(window.fetch).includes('[native code]')")

        def show(control: str) -> None:
            step = page.locator("#" + control).evaluate("el=>el.closest('.step')?.id.slice(5)")
            if step:
                page.locator(f'[data-step="{step}"]').click()
            page.locator("#" + control).evaluate(
                "el=>{for(let p=el.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true}"
            )

        def healthy() -> None:
            assert not page.locator("#status").evaluate("el=>el.classList.contains('error')"), page.locator(
                "#status"
            ).inner_text()

        def assert_graph() -> None:
            show("cycle-graph")
            expect(page.locator("#cycle-graph")).to_be_visible()
            assert page.locator("#cycle-graph tbody th").all_text_contents() == expected_nodes
            assert [
                text.split(" · ")[0] for text in page.locator("#cycle-graph li").all_text_contents()
            ] == expected_edges

        def download(control: str, filename: str) -> Path:
            show(control)
            with page.expect_download(timeout=30000) as waiting:
                page.locator("#" + control).click()
            destination = output / filename
            waiting.value.save_as(destination)
            healthy()
            return destination

        def connect(actor: int) -> None:
            show("discover")
            page.evaluate("i=>window.__chooseNovaActor(i)", actor)
            page.locator("#discover").click()
            page.locator("#wallet-choice").select_option("0")
            page.locator("#connect").click()
            expect(page.locator("#account")).to_contain_text(config["actors"][actor])
            page.locator("#journal-consent").check()

        def finish() -> str:
            expect(page.locator("#preview-panel:not([hidden]), #status.error")).to_have_count(1, timeout=30000)
            healthy()
            expect(page.locator("#preview-panel")).to_be_visible()
            page.locator("#transaction-ack").check()
            page.locator("#confirm").click()
            expect(page.locator("#status")).to_contain_text("Submitted, not confirmed", timeout=30000)
            transaction = str(page.evaluate("window.__nova.lastHash"))
            show("reconcile")
            page.locator("#reconcile-hash").fill(transaction)
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("finalized", timeout=30000)
            page.locator("#reconcile-hash").fill("")
            transaction_history.append(transaction)
            return transaction

        def action(control: str) -> str:
            show(control)
            page.locator("#" + control).click()
            return finish()

        def operator(payload: dict[str, Any]) -> dict[str, Any]:
            response = context.request.post(origin + "/operator", data=payload, timeout=120000)
            result = response.json()
            assert response.ok, result
            return cast(dict[str, Any], result)

        def retain(filename: str, value: dict[str, Any]) -> Path:
            destination = output / filename
            destination.write_text(json.dumps(value, indent=2) + "\n")
            return destination

        def import_record(file_control: str, button: str, filename: str, record: dict[str, Any], expected: str) -> None:
            show(file_control)
            page.locator("#" + file_control).set_input_files(retain(filename, record))
            page.locator("#" + button).click()
            expect(page.locator("#status")).to_contain_text(expected, timeout=30000)
            healthy()

        def ledger(label: str, count: int) -> dict[str, Any]:
            before = page.evaluate("window.__nova.sends")
            show("refresh-ledger")
            page.locator("#refresh-ledger").click()
            expect(page.locator("#ledger-status")).to_contain_text(f"{count} reconciled settlements", timeout=30000)
            healthy()
            value = json.loads(page.locator("#ledger-details").inner_text())
            assert len(value["settlements"]) == count
            assert sum(int(row["grossPayout"]) for row in value["recipients"]) == count * 80 * 10**18
            assert sum(int(row["burned"]) for row in value["recipients"]) == count * 8 * 10**17
            assert value["profit"] is None and value["spendableIncrease"] is None
            assert all(row["spendable"] is False for row in value["refunds"])
            assert page.evaluate("window.__nova.sends") == before
            financial_evidence[label] = value
            retain(f"browser-financial-{label}.json", value)
            return cast(dict[str, Any], value)

        def cycle(ordinal: int, numerical: dict[str, Any], plan_index: int = 0) -> dict[str, Any]:
            download("export-kit", f"browser-cycle-{ordinal}-prepublication-kit.json")
            show("public-consent")
            page.locator("#public-consent").check()
            page.locator("#storage-token").fill("synthetic-local-storage-token")
            page.locator("#publish-artifacts").click()
            expect(page.locator("#status")).to_contain_text("three published", timeout=30000)
            connect(0)
            action("mint")
            seed_id = page.locator("#seed-summary").inner_text()
            action("open-review")
            for actor in [3, 4]:
                connect(actor)
                show("review-findings")
                page.locator("#review-findings").fill(
                    "Exact synthetic package inspected by a distinct fixture address "
                    "controlled by this acceptance test."
                )
                page.locator("#review-decision").select_option("true")
                page.locator("#review-ack").check()
                action("attest")
            connect(0)
            action("open-campaign")
            connect(1)
            show("lot-count")
            funding = page.locator("#funding-target").input_value()
            if ordinal == 3:
                show("reinvestment-amount")
                page.locator("#reinvestment-amount").fill(funding)
                page.locator("#reinvestment-lots").fill(funding)
                page.locator("#reinvestment-rationale").fill(
                    "Use currently owned wallet funds for the fresh successor after the rightful first-cycle exit."
                )
                page.locator("#reinvestment-risk").fill(
                    "Returned principal is not profit. External costs and other devices remain unreconciled."
                )
                before = page.evaluate("window.__nova.sends")
                page.locator("#review-reinvestment").click()
                expect(page.locator("#status")).to_contain_text("owned balance and destination quote checked")
                proposal = json.loads(page.locator("#reinvestment-details").inner_text())
                assert proposal["sourceOwner"] == config["actors"][1]
                assert proposal["amount"] == str(int(funding) * 10**18)
                assert proposal["status"] == "proposal-only" and proposal["exactCalls"] is None
                assert proposal["destination"]["seedId"] == seed_id
                assert proposal["quote"]["baseUnits"] == proposal["amount"]
                page.locator("#use-reinvestment").click()
                expect(page.locator("#status")).to_contain_text("funding form filled")
                assert page.evaluate("window.__nova.sends") == before
                assert page.locator("#lot-count").input_value() == funding
                assert page.locator("#max-cost").input_value() == funding
                financial_evidence["successorProposal"] = proposal
                retain("browser-financial-successor-proposal.json", proposal)
            else:
                page.locator("#lot-count").fill(funding)
                page.locator("#max-cost").fill(funding)
            action("approve-funding")
            action("buy")
            connect(0)
            show("bloom-ack")
            page.locator("#bloom-ack").check()
            action("bloom")
            return job(ordinal, seed_id, numerical, plan_index)

        def job(
            ordinal: int, seed_id: str, numerical: dict[str, Any], plan_index: int, frozen: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            connect(0)
            show("job-choice")
            page.locator("#job-choice").select_option(str(plan_index))
            show("runtime-family")
            page.locator("#runtime-family").select_option("numerical")
            page.locator("#numerical-coefficients").fill(",".join(map(str, numerical["coefficients"])))
            for key in ["lower", "upper", "steps"]:
                page.locator("#numerical-" + key).fill(str(numerical[key]))
            page.locator("#numerical-tolerance").fill(str(numerical["tolerancePpm"]))
            request = json.loads(
                download("export-runtime-request", f"browser-cycle-{ordinal}-request.json").read_text()
            )
            assert request["work_spec"]["inputs"] == numerical
            if frozen is not None:
                frozen["request"] = request
                frozen["freeze"] = operator(
                    {
                        "operation": "freeze-evaluation",
                        "seed_id": seed_id,
                        "request": request,
                        "baseline_request": frozen["baseline"]["request"],
                        "baseline_result": frozen["baseline"]["result"],
                        "evaluation_id": str(uuid4()),
                    }
                )
                show("runtime-observer-key")
                page.locator("#runtime-observer-key").fill(frozen["baseline"]["source_key"])
                import_record(
                    "evaluation-freeze-file",
                    "import-evaluation-freeze",
                    "browser-evaluation-freeze.json",
                    frozen["freeze"],
                    "Frozen comparison retained",
                )
            sealed = operator({"operation": "seal", "seed_id": seed_id, "request": request})
            show("runtime-observer-key")
            page.locator("#runtime-observer-key").fill(sealed["source_public_key"])
            import_record(
                "terms-file", "import-runtime-terms", f"browser-cycle-{ordinal}-terms.json", sealed["seal"], "verified"
            )
            show("route")
            page.locator("#auction").fill("60")
            for index, reviewer in enumerate(config["committee"], 1):
                page.locator(f"#reviewer-{index}").fill(reviewer)
            posting_tx = action("route")
            job_id = page.locator("#onchain-job").input_value()
            connect(2)
            action("bid")
            assert context.request.post(origin + "/clock", data={"job_id": job_id}).ok
            assignment_tx = action("award")
            show("inspect-job")
            page.locator("#inspect-job").click()
            expect(page.locator("#status")).to_contain_text("Worker awarded")
            job = json.loads(page.locator("#job-state").inner_text())
            bound = operator(
                {
                    "operation": "bind",
                    "seed_id": seed_id,
                    "request": request,
                    "seal": sealed["seal"],
                    "job_id": job_id,
                    "posting_tx": posting_tx,
                    "assignment_tx": assignment_tx,
                    "expires_at": datetime.fromtimestamp(int(job["due"]), timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )
            result = operator(
                {"operation": "execute", "seed_id": seed_id, "request": request, "seal": sealed["seal"], **bound}
            )
            if ordinal == 1:
                show("result-format")
                page.locator("#result-format").select_option("native-signed")
                expect(page.locator("#result-algorithm")).to_have_value("keccak256")
                expect(page.locator("#result-algorithm")).to_be_disabled()
                page.locator("#result-file").set_input_files(
                    retain(f"browser-cycle-{ordinal}-runtime-result.json", result)
                )
                page.locator("#native-signer").fill(sealed["source_public_key"])
                assert page.locator("#result-file").evaluate("el=>el.files.length") == 1
            show("runtime-observer-key")
            page.locator("#runtime-observer-key").fill(sealed["source_public_key"])
            import_record(
                "runtime-result-file",
                "import-runtime-result",
                f"browser-cycle-{ordinal}-runtime-result.json",
                result,
                "verified",
            )
            expect(page.locator("#result-format")).to_have_value("cycle-artifact")
            expect(page.locator("#result-algorithm")).to_have_value("keccak256")
            expect(page.locator("#result-algorithm")).to_be_disabled()
            expect(page.locator("#result-file")).to_be_disabled()
            expect(page.locator("#native-signer")).to_have_value("")
            assert page.locator("#result-file").evaluate("el=>el.files.length") == 0
            expect(page.locator("#result-digest")).to_have_value(result["artifact_keccak256"])
            expect(page.locator("#result-hash")).to_contain_text(result["artifact_keccak256"])
            artifact_file = download("export-native-artifact", f"browser-cycle-{ordinal}-exact-artifact.json")
            assert artifact_file.read_bytes() == result["artifact_utf8"].encode()
            show("runtime-public-consent")
            page.locator("#runtime-public-consent").check()
            page.locator("#runtime-storage-token").fill("synthetic-local-storage-token")
            page.locator("#publish-native-artifact").click()
            expect(page.locator("#status")).to_contain_text("Exact public result verified", timeout=30000)
            assert page.locator("#runtime-storage-token").input_value() == ""
            action("submit-result")
            settlement_tx = ""
            for actor in [3, 4]:
                connect(actor)
                show("result-findings")
                page.locator("#result-decision").select_option("true")
                page.locator("#result-findings").fill(
                    "Reviewed the exact rational report and original synthetic input. "
                    "Its negative/positive decision is accurate."
                )
                page.locator("#result-review-ack").check()
                settlement_tx = action("validate-result")
            imported = operator(
                {
                    "operation": "settle",
                    "seed_id": seed_id,
                    "request": request,
                    "result": result,
                    "settlement_tx": settlement_tx,
                }
            )
            show("runtime-observer-key")
            page.locator("#runtime-observer-key").fill(sealed["source_public_key"])
            import_record(
                "settlement-file",
                "import-runtime-settlement",
                f"browser-cycle-{ordinal}-settlement.json",
                imported["record"],
                "settlement",
            )
            accepted = operator({"operation": "accept", "seed_id": seed_id, "request": request, "result": result})
            assert accepted["before"]["reserved"]["calls"] == 1
            assert accepted["after"]["reserved"]["calls"] == 0
            assert accepted["after"]["spent"]["calls"] == 1
            return {
                "request": request,
                "seed_id": seed_id,
                "job_id": job_id,
                "result": result,
                "settlement": imported["settlement"],
                "settlement_record": imported["record"],
                "settlement_tx": settlement_tx,
                "source_key": sealed["source_public_key"],
                "native_acceptance": accepted,
            }

        assert page.evaluate("window.__nova.calls.length") == 0
        page.locator("#example").click()
        page.locator("#title").fill("Two inspectable numerical missions")
        page.locator('[data-field="goal"]').fill(
            "Produce an exact rational report on the declared synthetic polynomial."
        )
        page.locator('[data-field="successMetric"]').fill(
            "Report the analytical integral and exact residuals. "
            "Accept truthful negative findings independently of candidate adoption."
        )
        page.locator("#evidence").fill(
            "Synthetic polynomial input; Apache-2.0 maintained quadrature adapter; exact rational checks."
        )
        page.locator("#add-job").click()
        page.locator('[data-field="goal"]').nth(1).fill(
            "Produce an exact rational report on the declared synthetic polynomial."
        )
        page.locator('[data-field="successMetric"]').nth(1).fill(
            "Report the analytical integral and exact residuals. "
            "Accept truthful negative findings independently of candidate adoption."
        )
        page.locator("#compile").click()
        expect(page.locator("#compile-summary")).to_contain_text("2 jobs")
        show("passphrase")
        page.locator("#passphrase").fill(capsule_passphrase)
        page.locator("#passphrase-again").fill(capsule_passphrase)
        page.locator("#seal-package").click()
        expect(page.locator("#recovery-result")).to_contain_text("successfully", timeout=30000)
        assert page.evaluate("window.__nova.calls.length") == 0
        assert_graph()
        first = cycle(1, {"coefficients": [0, 0, 0, 0, 1], "lower": 0, "upper": 3, "steps": 2, "tolerancePpm": 10}, 1)
        assert first["result"]["candidate_verdict"] == "FAIL"
        assert first["settlement"]["settlement_status"] == "paid"
        assert first["settlement"]["authority_status"] == "not_granted"
        first_ledger = ledger("first-output-before-collect", 1)
        assert first_ledger["refunds"][0]["status"] == "collectible-by-mark"
        checks.append(
            "Browser-created seed, native sealed terms before route, controller grant, "
            "genuine FAIL report accepted and paid"
        )
        comparison_state = {"baseline": first}
        evaluated = job(
            2,
            first["seed_id"],
            {"coefficients": [1, 0, 1], "lower": 0, "upper": 5, "steps": 12, "tolerancePpm": 10},
            0,
            comparison_state,
        )
        comparison = operator(
            {
                "operation": "evaluate-comparison",
                "seed_id": first["seed_id"],
                "request": evaluated["request"],
                "result": evaluated["result"],
                "baseline_request": first["request"],
                "baseline_result": first["result"],
                "freeze": comparison_state["freeze"],
            }
        )
        assert comparison["body"]["outcome"] == "PASS"
        assert comparison["body"]["admission"] == "HOLD"
        assert comparison["body"]["authority_status"] == "not_granted"
        assert comparison["body"]["compute_cost"] is None
        assert comparison["body"]["human_cost"] is None
        show("evaluation-freeze-file")
        page.locator("#evaluation-freeze-file").set_input_files(
            retain("browser-evaluation-freeze.json", comparison_state["freeze"])
        )
        page.locator("#evaluation-report-file").set_input_files(retain("browser-evaluation-report.json", comparison))
        page.locator("#import-evaluation").click()
        expect(page.locator("#status")).to_contain_text("comparison verified", timeout=30000)
        healthy()
        page.locator("#evaluation-reviewer").fill("Fixture operator; no independent-person claim")
        page.locator("#evaluation-rationale").fill(
            "Same fresh polynomial, equal step budget, exact rational error criterion passed. "
            "Costs remain unknown; no profit or independent holdout claim."
        )
        page.locator("#improvement-decision").select_option("adopt")
        page.locator("#adopt-candidate").click()
        expect(page.locator("#status")).to_contain_text("Reviewed decision preserved", timeout=30000)
        healthy()
        connect(0)
        show("onchain-job")
        page.locator("#onchain-job").fill(first["job_id"])
        action("collect")
        show("onchain-job")
        page.locator("#onchain-job").fill(evaluated["job_id"])
        action("collect")
        action("close-campaign")
        connect(1)
        action("reclaim")
        first_exit_ledger = ledger("first-cycle-after-reclaim", 2)
        assert first_exit_ledger["ownerTotals"]["netPayout"] == "0"
        assert all(row["status"] == "collected-into-campaign" for row in first_exit_ledger["refunds"])
        assert all(row["reserve"] == "0" for row in first_exit_ledger["campaigns"])
        checks.append(
            "Preregistered same-input real method comparison settled in first cycle, "
            "with deliberate adoption before successor"
        )
        show("project-passphrase")
        page.locator("#project-passphrase").fill(project_passphrase)
        recovery = download("export-project", "browser-first-cycle-private-recovery.json")
        recovered_receipts = transaction_history.copy()
        before_reload_sends = page.evaluate("window.__nova.sends")
        assert before_reload_sends > 0
        page.reload()
        expect(page.locator("#status")).to_contain_text("Start locally")
        assert page.evaluate("window.__nova.sends") == 0
        show("journal-consent")
        page.locator("#journal-consent").check()
        show("project-file")
        page.locator("#project-file").set_input_files(recovery)
        page.locator("#project-restore-passphrase").fill(project_passphrase)
        page.locator("#project-capsule-passphrase").fill(capsule_passphrase)
        page.locator("#restore-project").click()
        expect(page.locator("#status")).to_contain_text("restored", timeout=30000)
        assert page.evaluate("window.__nova.sends") == 0
        assert page.evaluate("window.__nova.calls.length") == 0
        assert_graph()
        checks.append("Rendered 12 named components and all 18 original directions persist through fresh recovery")
        checks.append("Fresh page restores encrypted runtime/settlement history without wallet traffic or execution")
        connect(0)
        show("reconcile-hash")
        for transaction in recovered_receipts:
            page.locator("#reconcile-hash").fill(transaction)
            page.locator("#reconcile").click()
            page.wait_for_function(
                "hash=>JSON.parse(document.querySelector('#journal').textContent).transactions"
                ".find(row=>row.hash===hash)?.status==='finalized'",
                arg=transaction,
            )
            expect(page.locator("#deployment-choice")).to_be_enabled()
            expect(page.locator("#status")).to_contain_text("finalized", timeout=30000)
        page.locator("#reconcile-hash").fill("")
        assert page.evaluate("window.__nova.sends") == 0
        checks.append("Every recovered receipt is independently reconciled before any new cycle authorization")
        show("runtime-observer-key")
        page.locator("#runtime-observer-key").fill(evaluated["source_key"])
        import_record(
            "runtime-result-file",
            "import-runtime-result",
            "browser-reverified-evaluation-result.json",
            evaluated["result"],
            "verified",
        )
        import_record(
            "settlement-file",
            "import-runtime-settlement",
            "browser-reverified-evaluation-settlement.json",
            evaluated["settlement_record"],
            "settlement",
        )
        show("evaluation-freeze-file")
        page.locator("#evaluation-freeze-file").set_input_files(output / "browser-evaluation-freeze.json")
        page.locator("#evaluation-report-file").set_input_files(output / "browser-evaluation-report.json")
        page.locator("#import-evaluation").click()
        expect(page.locator("#status")).to_contain_text("comparison verified", timeout=30000)
        healthy()
        show("reuse-reviewer")
        page.locator("#reuse-source").select_option(evaluated["result"]["artifact_keccak256"])
        page.locator("#reuse-reviewer").fill("Fixture operator; explicit local rights review")
        page.locator("#reuse-rationale").fill(
            "Reviewed the exact accepted calculation-input.json and its declared synthetic source. "
            "Reuse its bounds, steps and absolute tolerance with fresh polynomial coefficients."
        )
        page.locator("#reuse-license").fill(evaluated["request"]["work_spec"]["rights"]["license"])
        page.locator("#reuse-valid-until").fill(
            (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        )
        page.locator("#authorize-artifact-reuse").click()
        expect(page.locator("#status")).to_contain_text("next request will inherit", timeout=30000)
        healthy()
        reuse_selection = json.loads(page.locator("#reuse-details").inner_text())
        show("next-cycle-title")
        page.locator("#next-cycle-title").fill("Fresh polynomial successor")
        page.locator("#next-cycle-goal").fill(
            "Check fresh polynomial coefficients using the exact retained calculation-input procedure."
        )
        page.locator("#next-cycle-evidence").fill(
            "Fresh coefficients; reviewed calculation-input bounds, steps and tolerance inherited; "
            "new review and authority required."
        )
        page.locator("#next-cycle-passphrase").fill(capsule_passphrase)
        page.locator("#reuse-ack").check()
        page.locator("#next-cycle").click()
        expect(page.locator("#status")).to_contain_text("cycle prepared", timeout=30000)
        healthy()
        second = cycle(3, {"coefficients": [2, -1, 1], "lower": 0, "upper": 5, "steps": 12, "tolerancePpm": 10})
        assert second["request"]["project_id"] == first["request"]["project_id"]
        assert second["request"]["cycle_id"] != first["request"]["cycle_id"]
        assert second["request"]["work_spec"]["inputs"] != first["request"]["work_spec"]["inputs"]
        assert second["result"]["artifact_sha256"] != first["result"]["artifact_sha256"]
        assert second["settlement"]["chain"] != first["settlement"]["chain"]
        assert second["result"]["candidate_verdict"] == "PASS"
        assert "reused calculation-input.json SHA-256" in second["request"]["work_spec"]["rights"]["source"]
        for field in ["lower", "upper", "steps", "tolerancePpm"]:
            assert second["request"]["work_spec"]["inputs"][field] == evaluated["request"]["work_spec"]["inputs"][field]
        checks.append(
            "Explicit successor with fresh input, risk review, funding, assignment, grant, run, output and settlement"
        )
        connect(0)
        action("collect")
        action("close-campaign")
        connect(1)
        action("reclaim")
        final_ledger = ledger("second-cycle-after-reclaim", 3)
        assert final_ledger["ownerTotals"]["netPayout"] == "0"
        assert all(row["reserve"] == "0" for row in final_ledger["campaigns"])
        checks.append(
            "Canonical payout/refund ledger and owner-specific proposal precede separate funding confirmations"
        )
        show("project-passphrase")
        page.locator("#project-passphrase").fill(project_passphrase)
        download("export-project", "browser-two-cycle-private-recovery.json")
        page.screenshot(path=str(output / "cycle-desktop.png"), full_page=True)
        axe = (Path(__file__).parents[1] / "browser/node_modules/axe-core/axe.min.js").read_text()
        audits = []
        for width in [1440, 390, 320]:
            page.set_viewport_size({"width": width, "height": 1080})
            for step in page.locator("[data-step]").evaluate_all("els=>els.map(el=>el.dataset.step)"):
                page.locator(f'[data-step="{step}"]').click()
                page.evaluate(axe)
                audit = page.evaluate(
                    "async()=>await axe.run(document,{runOnly:{type:'tag',"
                    "values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
                )
                audits.append({"width": width, "step": step, "violations": audit["violations"]})
                assert not audit["violations"], audits[-1]
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), (width, step)
            if width == 390:
                page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", "fr")
                page.screenshot(path=str(output / "cycle-mobile-fr.png"), full_page=True)
                page.locator("#language").click()
        assert not errors, errors
        retain(
            "cycle-browser-report.json",
            {
                "schema": "agialpha.ascension.complete-cycle.browser-acceptance.v1",
                "classification": "Actual production UI, synthetic EIP-1193 wallet, genuine native worker, "
                "disposable exact-source EVM",
                "profile": config["profile"],
                "fixtureModifications": config.get("fixtureModifications", []),
                "sourceHashes": config["sourceHashes"],
                "environment": config["environment"],
                "browserVersion": browser.version,
                "checks": checks,
                "reconciledRecoveredTransactions": recovered_receipts,
                "audits": audits,
                "pageErrors": errors,
                "cycles": [first, second],
                "evaluationJob": evaluated,
                "comparison": comparison,
                "reuseSelection": reuse_selection,
                "financialEvidence": financial_evidence,
                "renderedGraph": {"nodes": expected_nodes, "directedEdges": expected_edges},
                "mainnetTransactions": 0,
                "externalIndependentReview": False,
                "physicalWallet": False,
                "liveModel": False,
                "realStorageAccount": False,
                "operatorTransport": "Test-only loopback transport invokes maintained native APIs; "
                "fixture principals were explicitly preconfigured by one operator.",
                "manualScreenReaderTrial": "not performed",
                "realizedCommercialValue": None,
            },
        )
        context.close()
        browser.close()
    print("Ascension complete-cycle Chromium acceptance passed")


if __name__ == "__main__":
    main()
