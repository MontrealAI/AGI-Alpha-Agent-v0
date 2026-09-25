# SPDX-License-Identifier: Apache-2.0
"""Exercise the white-paper journey in Chromium, including negative cases and recovery."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import time
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


class Handler(SimpleHTTPRequestHandler):
    """Serve under a GitHub Pages style project prefix."""

    def translate_path(self, path: str) -> str:
        return super().translate_path(path.removeprefix("/project"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def inspect(page: Page, expression: str) -> Any:
    """Inspect through DevTools without changing the shipped CSP."""
    session = page.context.new_cdp_session(page)
    try:
        result = session.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
                "allowUnsafeEvalBlockedByCSP": True,
            },
        )
        assert "exceptionDetails" not in result, result
        return result["result"].get("value")
    finally:
        session.detach()


def wait_for(page: Page, expression: str) -> None:
    """Wait for a specific browser state without evaluating against a weaker CSP."""
    deadline = time.monotonic() + 60
    while not inspect(page, expression):
        if time.monotonic() > deadline:
            raise TimeoutError(expression)
        page.wait_for_timeout(100)


def validate(site: Path, output: Path, public_url: str | None = None) -> dict[str, Any]:
    """Require the actual UI, crypto, funding gates, exports and offline recovery to work."""
    output.mkdir(parents=True, exist_ok=True)
    server = None
    thread = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public validation requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    errors: list[str] = []
    failures: list[str] = []
    report: dict[str, Any] = {"origin": public_url or "local project subpath", "scenarios": [], "checks": []}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "response",
                lambda response: failures.append(response.url)
                if response.status >= 400 and ("ascension" in response.url or "whitepaper" in response.url)
                else None,
            )
            page.goto(origin)
            expect(page.get_by_role("link", name="Launch Ascension")).to_be_visible()
            assert page.locator(".demo-card").count() == 26
            assert page.locator(".wheel-node").count() == 6
            page.screenshot(path=str(output / "home-desktop.png"))
            page.locator("#ascension").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "home-missions.png"))
            page.get_by_role("link", name="Launch Ascension").click()
            expect(page.locator("#insight-results")).to_be_visible()
            page.screenshot(path=str(output / "ascension-desktop.png"))
            for scenario_id, expected in [
                ("resilient-city", 210),
                ("research-foundry", 200),
                ("enterprise-frontier", 185),
            ]:
                page.locator(f'[data-case="{scenario_id}"]').click()
                expect(page.locator("#portfolio-metrics .metric strong").first).to_have_text(str(expected))
                assert page.locator("#frontier-chart circle").count() >= 6
                report["scenarios"].append({"id": scenario_id, "assumed_value": expected})
            page.locator('[data-case="resilient-city"]').click()
            expect(page.locator("#portfolio-metrics .metric strong").first).to_have_text("210")
            page.locator('[data-step="market"]').click()
            expect(page.locator("#buy-lots")).to_be_disabled()
            page.locator('[data-step="settlement"]').click()
            expect(page.locator("#settle-plan")).to_be_disabled()
            page.locator('[data-step="seed"]').click()
            # Public test phrase, not a user credential. It is never an artifact field.
            phrase = "public acceptance fixture passphrase 2026"
            page.locator("#seed-passphrase").fill(phrase)
            page.locator("#seal-seed").click()
            expect(page.locator("#download-seed")).to_be_enabled(timeout=30000)
            expect(page.locator("#seed-passphrase")).to_have_value("")
            with page.expect_download() as downloaded:
                page.locator("#download-seed").click()
            capsule_file = output / "test-nova-seed.sealed.json"
            downloaded.value.save_as(capsule_file)
            capsule = json.loads(capsule_file.read_text())
            assert capsule["cipher"] == "AES-256-GCM" and capsule["iterations"] == 600000
            assert "resilient-city" not in capsule_file.read_text() and phrase not in capsule_file.read_text()
            page.screenshot(path=str(output / "nova-seed-desktop.png"))
            page.get_by_text("Recover a saved Nova-Seed", exact=True).click()
            page.locator("#seed-import").set_input_files(capsule_file)
            page.locator("#recovery-passphrase").fill("incorrect fixture passphrase")
            page.get_by_role("button", name="Decrypt & inspect").click()
            expect(page.locator("#recovery-status")).to_contain_text("Could not open", timeout=30000)
            expect(page.locator("#recovered-genome")).to_be_hidden()
            altered = {**capsule, "commitment": "0" * 64}
            page.locator("#seed-import").set_input_files(
                {"name": "altered.json", "mimeType": "application/json", "buffer": json.dumps(altered).encode()}
            )
            page.locator("#recovery-passphrase").fill(phrase)
            page.get_by_role("button", name="Decrypt & inspect").click()
            expect(page.locator("#recovery-status")).to_contain_text("Could not open", timeout=30000)
            page.locator("#seed-import").set_input_files(capsule_file)
            page.locator("#recovery-passphrase").fill(phrase)
            page.get_by_role("button", name="Decrypt & inspect").click()
            expect(page.locator("#recovery-status")).to_contain_text("Authenticated and recovered", timeout=30000)
            recovered = json.loads(page.locator("#recovered-genome").inner_text())
            assert recovered["scenario"]["id"] == "resilient-city"
            assert len(recovered["fusion_plan"]["selected"]) == 4
            assert inspect(page, "localStorage.length") == 0
            page.locator("#restore-plan").click()
            expect(page.locator("#portfolio-metrics .metric strong").first).to_have_text("210")
            expect(page.locator("#download-seed")).to_be_disabled()
            page.locator('[data-step="seed"]').click()
            page.locator("#seed-passphrase").fill(phrase)
            page.locator("#seal-seed").click()
            expect(page.locator("#download-seed")).to_be_enabled(timeout=30000)
            report["checks"].append("authenticated encryption, wrong passphrase, altered capsule and recovery")
            page.locator('[data-step="market"]').click()
            page.locator("#market-lots").fill("1")
            page.locator("#buy-lots").click()
            expect(page.locator("#market-metrics .metric strong").first).to_have_text("1")
            page.locator('[data-step="settlement"]').click()
            expect(page.locator("#settle-plan")).to_be_disabled()
            page.locator('[data-step="market"]').click()
            page.locator("#market-lots").fill("2")
            page.locator("#sell-lots").click()
            expect(page.locator("#lab-status")).to_contain_text("Cannot redeem more lots")
            expect(page.locator("#market-metrics .metric strong").first).to_have_text("1")
            page.locator("#market-lots").fill("1")
            page.locator("#sell-lots").click()
            expect(page.locator("#market-metrics .metric strong").first).to_have_text("0")
            page.locator("#market-lots").fill("25")
            page.locator("#buy-lots").click()
            expect(page.locator("#market-metrics .metric strong").first).to_have_text("100")
            page.screenshot(path=str(output / "mark-desktop.png"))
            report["checks"].append("exact funding, inverse redemption, rejected oversell and underfunding gate")
            page.locator('[data-step="sovereign"]').click()
            assert page.locator("#gantt-chart rect").count() == 12
            for kind in ("allocation", "research", "schedule"):
                with page.expect_download() as downloaded:
                    page.locator(f'[data-mission="{kind}"]').click()
                path = output / f"native-{kind}.json"
                downloaded.value.save_as(path)
                native = json.loads(path.read_text())
                Mission.model_validate(native)
                assert native["work"]["kind"] == kind and native["goal"]
                assert native == recovered["fusion_plan"]["missions"][kind]
            page.locator('[data-panel="sovereign"]').scroll_into_view_if_needed()
            page.screenshot(path=str(output / "sovereign-desktop.png"))
            page.locator('[data-step="settlement"]').click()
            assert page.locator(".check-card:not(.fail)").count() == 2
            page.locator("#settle-plan").click()
            expect(page.locator("#settlement-results")).to_be_hidden()
            page.locator("#operator-approval").check()
            page.get_by_text("Explore the paper’s value-minting policy", exact=True).click()
            page.locator("#certified-value").fill("100")
            page.locator("#emission-cap").fill("3")
            page.locator("#settle-plan").click()
            expect(page.locator("#settlement-results")).to_be_visible()
            expect(page.locator("#settle-plan")).to_be_disabled()
            with page.expect_download() as downloaded:
                page.locator("#download-report").click()
            evidence_file = output / "ascension-evidence.json"
            downloaded.value.save_as(evidence_file)
            evidence = json.loads(evidence_file.read_text())
            ledger = evidence["settlement"]
            assert ledger["burned"] == "1" and ledger["minted"] == "3" and ledger["treasury"] == "1.5"
            assert ledger["workers"] == "100.5" and ledger["escrow"] == "0" and ledger["supply"] == "102"
            assert ledger["conservation"] and ledger["settled_jobs"] == 4
            with page.expect_download() as downloaded:
                page.locator("#download-brief").click()
            downloaded.value.save_as(output / "mission-brief.md")
            assert evidence["sha256"] in (output / "mission-brief.md").read_text()
            page.locator('[data-panel="settlement"]').scroll_into_view_if_needed()
            page.screenshot(path=str(output / "council-desktop.png"))
            page.locator('[data-step="market"]').click()
            expect(page.locator("#sell-lots")).to_be_disabled()
            expect(page.locator("#buy-lots")).to_be_disabled()
            report["checks"].append("explicit acceptance, exact settlement, capped emissions, conservation and exports")
            page.locator('[data-step="architect"]').click()
            page.locator("#run-architect").click()
            expect(page.locator("#policy-list .policy-card")).to_have_count(20)
            page.locator('[data-panel="architect"]').scroll_into_view_if_needed()
            page.screenshot(path=str(output / "architect-desktop.png"))
            page.locator("[data-policy]").first.click()
            expect(page.locator("#download-seed")).to_be_disabled()
            expect(page.locator("#settlement-results")).to_be_hidden()
            assert page.locator("#scenario-budget").input_value() == "60"
            report["checks"].append("20 policy variants and fresh-cycle invalidation")
            page.locator('[data-step="governance"]').click()
            expect(page.locator("#risk-conclusion")).to_contain_text("0.393045")
            expect(page.locator("#strategy-note")).to_contain_text("V/C = 50%")
            page.locator("#game-kind").select_option("rps")
            expect(page.locator("#strategy-note")).to_contain_text("cycles")
            page.locator("#game-kind").select_option("coordination")
            expect(page.locator("#strategy-note")).to_contain_text("Two attracting outcomes")
            page.locator("#game-kind").select_option("hawk")
            page.locator("#mitigation").fill("50")
            expect(page.locator("#risk-conclusion")).to_contain_text("within the modeled gate")
            page.locator("#proposal-votes").fill("11")
            expect(page.locator("#governance-result")).to_contain_text("121/100 credits: rejected")
            page.locator("#proposal-votes").fill("7")
            page.locator("#upgrade-days").fill("8")
            expect(page.locator("#governance-result")).to_contain_text("Upgrade blocked")
            page.locator("#governance-approved").check()
            expect(page.locator("#governance-result")).to_contain_text("All modeled gates pass")
            page.locator("#policy-valid").uncheck()
            expect(page.locator("#governance-result")).to_contain_text("Upgrade blocked")
            page.locator("#identity-attested").uncheck()
            expect(page.locator("#stake-result")).to_contain_text("Not eligible")
            page.locator("#mitigation").fill("0")
            page.locator('[data-panel="governance"]').scroll_into_view_if_needed()
            page.screenshot(path=str(output / "governance-desktop.png"))
            report["checks"].append("corrected risk/dynamics, stake, quadratic credits and complete eight-day gate")
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                for step in ("insight", "seed", "market", "sovereign", "settlement", "architect", "governance"):
                    page.locator(f'[data-step="{step}"]').click()
                    assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), (width, step)
                page.screenshot(path=str(output / f"governance-mobile-{width}.png"))
                page.goto(origin)
                page.screenshot(path=str(output / f"home-mobile-{width}.png"))
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), width
                page.goto(origin + "ascension/")
                expect(page.locator("#insight-results")).to_be_visible()
                page.screenshot(path=str(output / f"ascension-mobile-{width}.png"))
            report["checks"].append("desktop and 390/320 px mobile layouts without horizontal overflow")
            hostile = recovered["scenario"]
            hostile["title"] = '<img src=x onerror="window.injected=true">'
            hostile["opportunities"][0]["title"] = "<script>window.injected=true</script>"
            page.locator("#scenario-import").set_input_files(
                {"name": "scenario.json", "mimeType": "application/json", "buffer": json.dumps(hostile).encode()}
            )
            expect(page.locator("#case-context")).to_contain_text("<img")
            expect(page.locator("#insight-results")).to_be_visible()
            assert inspect(page, "window.injected === undefined && !document.querySelector('#case-context img')")
            page.locator("#scenario-budget").fill("1")
            expect(page.locator("#insight-results")).to_be_hidden()
            page.locator("#analyse").click()
            expect(page.locator("#lab-status")).to_contain_text("No project fits")
            expect(page.locator("#seal-seed")).to_be_disabled()
            report["checks"].append(
                "untrusted text remains text; changed and infeasible inputs invalidate stale success"
            )
            pdf = context.request.get(origin + "assets/whitepaper_v0.1.0-alphav15.pdf")
            assert pdf.ok
            paper_hash = hashlib.sha256(pdf.body()).hexdigest()
            assert paper_hash == "fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa"
            report["paper_sha256"] = paper_hash
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#insight-results")).to_be_visible()
            expect(page.locator("#portfolio-metrics .metric strong").first).to_have_text("210")
            page.locator('[data-case="research-foundry"]').click()
            expect(page.locator("#portfolio-metrics .metric strong").first).to_have_text("200")
            report["checks"].append("offline reload and fresh computation from cached modules/scenarios")
            assert not errors and not failures, {"errors": errors, "failed_http": failures}
            report["passed"] = True
            report["browser"] = browser.version
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=5)
    (output / "ascension.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url), indent=2))


if __name__ == "__main__":
    main()
