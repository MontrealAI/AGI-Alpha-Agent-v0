# SPDX-License-Identifier: Apache-2.0
"""Actual Chromium UI against the disposable exact-source EVM and local artifact HTTP service."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    config = json.loads(Path(sys.argv[1]).read_text())
    output = Path(config["output"])
    fixture = "window.__novaActors=" + json.dumps(config["actors"]) + ";\n"
    fixture += Path(__file__).with_name("browser-provider.js").read_text()
    errors: list[str] = []
    checks: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True)
        context.add_init_script(script=fixture)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(config["url"])
        expect(page.locator("#status")).to_contain_text("Start locally")
        assert page.evaluate("window.__nova.calls.length") == 0
        page.locator("#example").click()
        page.locator("#compile").click()
        expect(page.locator("#compile-summary")).to_contain_text("1 jobs")
        page.locator('[data-step="protect"]').click()
        page.locator("#passphrase").fill("browser capsule passphrase")
        page.locator("#passphrase-again").fill("browser capsule passphrase")
        page.locator("#seal-package").click()
        expect(page.locator("#recovery-result")).to_contain_text("successfully", timeout=30000)
        assert page.locator("#passphrase").input_value() == ""
        with page.expect_download() as download:
            page.locator("#export-kit").click()
        download.value.save_as(output / "browser-initial-kit.json")
        assert page.evaluate("window.__nova.calls.length") == 0
        checks.append("No-wallet creation, compilation, encryption, recovery and export")
        page.screenshot(path=str(output / "studio-desktop.png"), full_page=True)
        page.locator('[data-step="publish"]').click()
        page.locator("#public-consent").check()
        page.locator("#storage-token").fill("synthetic-local-storage-token")
        page.locator("#publish-artifacts").click()
        expect(page.locator("#status")).to_contain_text("three published", timeout=30000)
        assert page.locator("#storage-token").input_value() == ""
        page.locator("#verify-publication").click()
        expect(page.locator("#status")).to_contain_text("both configured gateways")
        page.locator('[data-step="protect"]').click()
        with page.expect_download() as download:
            page.locator("#export-kit").click()
        kit_path = output / "browser-published-kit.json"
        download.value.save_as(kit_path)
        checks.append("Production multipart storage adapter over real local HTTP with exact retrieved bytes")

        def connect(actor: int) -> None:
            page.locator('[data-step="mint"]').click()
            page.evaluate("i=>window.__chooseNovaActor(i)", actor)
            page.locator("#discover").click()
            page.locator("#wallet-choice").select_option("0")
            page.locator("#connect").click()
            expect(page.locator("#account")).to_contain_text(config["actors"][actor])
            page.locator("#journal-consent").check()

        def finish() -> None:
            expect(page.locator("#preview-panel:not([hidden]), #status.error")).to_have_count(1, timeout=30000)
            assert not page.locator("#status").evaluate("el=>el.classList.contains('error')"), page.locator(
                "#status"
            ).inner_text()
            expect(page.locator("#preview-panel")).to_be_visible()
            page.locator("#transaction-ack").check()
            page.locator("#confirm").click()
            expect(page.locator("#status")).to_contain_text("Submitted, not confirmed", timeout=30000)
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("finalized", timeout=30000)

        connect(0)
        page.locator("#check-identity").click()
        expect(page.locator("#identity-summary")).to_contain_text("Eligible business")
        page.locator("#mint").click()
        expect(page.locator("#preview-panel")).to_be_visible(timeout=30000)
        page.evaluate("window.__nova.loseNext=true")
        page.locator("#transaction-ack").check()
        page.locator("#confirm").click()
        expect(page.locator("#status")).to_contain_text("unknown", timeout=30000)
        mint_hash = page.evaluate("window.__nova.lastHash")
        assert page.evaluate("window.__nova.sends") == 1
        page.reload()
        expect(page.locator("#status")).to_contain_text("Start locally")
        assert page.evaluate("window.__nova.sends") == 0
        page.locator('[data-step="resume"]').click()
        page.locator("#kit-file").set_input_files(kit_path)
        page.locator("#restore-passphrase").fill("browser capsule passphrase")
        page.locator("#restore-kit").click()
        expect(page.locator("#status")).to_contain_text("recovered locally", timeout=30000)
        connect(0)
        page.locator('[data-step="resume"]').click()
        page.locator("#reconcile-hash").fill(mint_hash)
        page.locator("#reconcile").click()
        expect(page.locator("#status")).to_contain_text("finalized", timeout=30000)
        assert page.locator("#seed-summary").inner_text() == "2"
        assert page.evaluate("window.__nova.sends") == 0
        checks.append("Real mint with lost response, reload, kit import and canonical reconciliation without resend")
        page.locator('[data-step="review"]').click()
        page.locator("#open-review").click()
        finish()
        for actor in [3, 4]:
            connect(actor)
            page.locator('[data-step="review"]').click()
            page.locator("#review-findings").locator("xpath=ancestor::details").evaluate("el=>el.open=true")
            page.locator("#review-findings").fill(
                "Synthetic local UI acceptance. Exact package inspected by a fixture actor; not independent humans."
            )
            page.locator("#review-decision").select_option("true")
            page.locator("#review-ack").check()
            page.locator("#attest").click()
            finish()
        connect(0)
        page.locator('[data-step="fund"]').click()
        page.locator("#open-campaign").click()
        finish()
        connect(1)
        page.locator('[data-step="fund"]').click()
        page.locator("#approve-funding").click()
        finish()
        page.locator('[data-step="fund"]').click()
        page.locator("#buy").click()
        finish()
        connect(0)
        page.locator('[data-step="fund"]').click()
        page.locator("#bloom-ack").check()
        page.locator("#bloom").click()
        finish()
        page.locator('[data-step="launch"]').click()
        for index, address in enumerate(config["committee"], 1):
            page.locator(f"#reviewer-{index}").fill(address)
        page.locator("#route").click()
        finish()
        assert page.locator("#onchain-job").input_value() == "2"
        page.locator('[data-step="launch"]').click()
        page.locator("#inspect-job").click()
        expect(page.locator("#status")).to_contain_text("Job posted")
        assert "No runtime connected" in page.locator("#runtime-state").inner_text()
        with page.expect_download() as download:
            page.locator("#work-package").click()
        download.value.save_as(output / "browser-work-package.json")
        checks.append("Actual browser mint, separate fixture review, funding, activation, route and work handoff")
        connect(2)
        page.locator('[data-step="launch"]').click()
        page.locator("#bid").locator("xpath=ancestor::details").evaluate("el=>el.open=true")
        page.locator("#bid").click()
        finish()
        origin = config["url"].split("/ascension/")[0]
        assert context.request.post(origin + "/advance-auction").ok
        page.locator('[data-step="launch"]').click()
        page.locator("#award").click()
        finish()
        page.locator('[data-step="launch"]').click()
        page.locator("#inspect-job").click()
        expect(page.locator("#status")).to_contain_text("Worker awarded")
        result_bytes = b'{"result":"synthetic local UI acceptance result"}\n'
        result_path = output / "browser-result.json"
        result_path.write_bytes(result_bytes)
        uploaded = context.request.post(
            origin + "/upload",
            multipart={
                "network": "public",
                "file": {"name": "result.json", "mimeType": "application/json", "buffer": result_bytes},
            },
        ).json()
        page.locator('[data-step="launch"]').click()
        page.locator("#result-file").set_input_files(result_path)
        expect(page.locator("#result-hash")).to_contain_text("0x")
        page.locator("#result-uri").fill("ipfs://" + uploaded["data"]["cid"])
        page.locator("#submit-result").click()
        finish()
        for actor in [3, 4]:
            connect(actor)
            page.locator('[data-step="launch"]').click()
            page.locator("#result-decision").select_option("true")
            page.locator("#result-findings").fill(
                "Synthetic local result meets the fixture criteria; not a human review."
            )
            page.locator("#result-review-ack").check()
            page.locator("#validate-result").click()
            finish()
        page.locator('[data-step="launch"]').click()
        page.locator("#inspect-job").click()
        expect(page.locator("#status")).to_contain_text("Settlement paid")
        connect(0)
        page.locator('[data-step="resume"]').click()
        page.locator("#collect").locator("xpath=ancestor::details").evaluate("el=>el.open=true")
        page.locator("#collect").click()
        finish()
        page.locator("#close-campaign").click()
        finish()
        connect(1)
        page.locator('[data-step="resume"]').click()
        page.locator("#reclaim").click()
        finish()
        checks.append("Browser bid, award, result delivery, distinct votes, payment, collection, closure and reclaim")
        axe = (Path(__file__).parents[1] / "browser/node_modules/axe-core/axe.min.js").read_text()
        audits = []
        for width in [1440, 390, 320]:
            page.set_viewport_size({"width": width, "height": 1000})
            for step in ["project", "protect", "publish", "mint", "review", "fund", "launch", "resume"]:
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
                page.screenshot(path=str(output / "studio-mobile-fr.png"), full_page=True)
                page.locator("#language").click()
        page.locator('[data-step="project"]').focus()
        page.keyboard.press("Enter")
        expect(page.locator("#step-project")).to_be_visible()
        checks.append("EN/FR, keyboard, 1440/390/320 px and axe WCAG A/AA across all steps")
        assert not errors, errors
        (output / "browser-report.json").write_text(
            json.dumps(
                {
                    "classification": (
                        "Chromium, synthetic wallet, actual disposable contracts; no physical wallet trial"
                    ),
                    "checks": checks,
                    "audits": audits,
                    "pageErrors": errors,
                    "mainnetTransactions": 0,
                },
                indent=2,
            )
            + "\n"
        )
        context.close()
        browser.close()
    print("Nova-Seed Chromium acceptance passed")


if __name__ == "__main__":
    main()
