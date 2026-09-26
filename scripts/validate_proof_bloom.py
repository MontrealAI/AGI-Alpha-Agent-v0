# SPDX-License-Identifier: Apache-2.0
"""Exercise every Proof Bloom journey, native return, adversarial gate and recovery in Chromium."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.store import Journal, digest
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler, inspect, wait_for


def ready(page: Page) -> None:
    """Wait for an atomic UI action to finish."""
    wait_for(
        page,
        "document.documentElement.dataset.bloomReady === 'true' && "
        "document.querySelector('#bloom').getAttribute('aria-busy') === 'false'",
    )


def click(page: Page, selector: str) -> None:
    """Run a real user action and wait for completion."""
    page.locator(selector).click()
    ready(page)


def upload(page: Page, selector: str, value: dict[str, Any] | Path) -> None:
    """Import exact downloaded bytes or deliberately malformed evidence."""
    if isinstance(value, Path):
        page.locator(selector).set_input_files(str(value))
    else:
        page.locator(selector).set_input_files(
            {"name": "return.json", "mimeType": "application/json", "buffer": json.dumps(value).encode()}
        )
    ready(page)


def download(page: Page, selector: str, path: Path) -> dict[str, Any]:
    """Retain the actual browser download for unchanged round-trip acceptance."""
    with page.expect_download() as event:
        click(page, selector)
    event.value.save_as(path)
    assert path.stat().st_size <= 250000
    value: dict[str, Any] = json.loads(path.read_text())
    return value


def review_all(page: Page) -> None:
    """Record separate explicit decisions for every returned job."""
    page.locator('[data-view="docket"]').click()
    for job in ("source", "benchmark", "stress"):
        page.locator("#job-picker").select_option(job)
        page.locator("#reviewer").fill("Acceptance reviewer")
        page.locator("#review-decision").select_option("accept")
        page.locator("#review-note").fill(
            "Inspected exact inputs, baseline and replay. Accept bounded computation; visionary claims remain unproven."
        )
        click(page, "#save-review")
        expect(page.locator("#review-summary")).to_contain_text("ACCEPT")


def validate(site: Path, output: Path, public_url: str | None = None, axe_script: Path | None = None) -> dict[str, Any]:
    """Require complete browser and native journeys on canonical and mirrored project paths."""
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {
        "schema": "agialpha.bloom.acceptance.v1",
        "origin": public_url or "local project subpath",
        "experiences": [],
        "checks": [],
        "passed": False,
    }
    errors: list[str] = []
    audits: list[dict[str, Any]] = []

    def audit(page: Page, label: str) -> None:
        if axe_script is None:
            return
        inspect(page, axe_script.read_text() + ";true")
        result = inspect(
            page,
            "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
            ".then(r=>({violations:r.violations}))",
        )
        audits.append({"view": label, **result})
        assert not result["violations"], result["violations"]

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(origin, wait_until="networkidle")
            expect(page.locator(".demo-card")).to_have_count(26)
            expect(page.locator(".wheel-node")).to_have_count(6)
            expect(page.get_by_role("link", name="Enter the Proof Bloom")).to_be_visible()
            audit(page, "homepage-desktop")
            page.screenshot(path=str(output / "homepage.png"), full_page=True)
            page.get_by_role("link", name="Enter the Proof Bloom").click()
            ready(page)
            page.screenshot(path=str(output / "bloom-desktop.png"), full_page=True)
            page.locator("#guide-toggle").click()
            expect(page.locator("#guide")).to_be_visible()
            page.locator("#guide-toggle").click()
            for experience in ("nova", "sovereign", "omega", "invention", "proof"):
                page.locator(f'[data-experience="{experience}"]').focus()
                page.keyboard.press("Enter")
                expect(page.locator(f'[data-experience="{experience}"]')).to_be_focused()
                expect(page.locator("#run-all")).to_be_disabled()
                click(page, "#compile-seed")
                expect(page.locator(".job-card")).to_have_count(3)
                if experience == "nova":
                    audit(page, "seed-desktop")
                click(page, "#run-all")
                expect(page.locator("#promote")).to_be_disabled()
                page.locator("#job-picker").select_option("benchmark")
                mission = download(page, "#download-mission", output / f"{experience}-mission.json")
                Mission.model_validate(mission)
                spec_path = output / f"{experience}-job-spec.json"
                download(page, "#download-spec", spec_path)
                bundle_path = output / f"{experience}-bundle.json"
                bundle = download(page, "#download-bundle", bundle_path)
                returned = json.loads(bundle_path.read_text())
                returned["validator_verdict"] = "accepted"
                upload(page, "#bundle-import", returned)
                expect(page.locator("#bloom-status")).to_contain_text("unsupported fields")
                altered = json.loads(bundle_path.read_text())
                altered["result"]["summary"] = "Accepted without proof"
                upload(page, "#bundle-import", altered)
                expect(page.locator("#bloom-status")).to_contain_text("does not replay")
                upload(page, "#bundle-import", bundle_path)
                expect(page.locator("#bloom-status")).to_contain_text("Return verified")
                # Actual agent execution, explicit native review and signed return for all four Mission kinds.
                with tempfile.TemporaryDirectory(prefix="bloom-native-") as temporary:
                    journal = Journal.initialize(Path(temporary) / "agent")
                    engine = Engine(journal)
                    submitted = journal.submit(Mission.model_validate(mission))
                    record = engine.execute(submitted["id"])
                    assert record["state"] == "review", record
                    engine.review(
                        record["id"],
                        record["revision"],
                        digest(record["result"]),
                        True,
                        "Inspected the bounded result and its stated assumptions.",
                    )
                    signed = engine.export(record["id"])
                    page.locator("#result-view + .actions + details").locator("summary").click()
                    page.locator("#trusted-key").fill("a" * 64)
                    upload(page, "#native-import", signed)
                    expect(page.locator("#bloom-status")).to_contain_text("Pin")
                    page.locator("#trusted-key").fill(journal.public)
                    page.locator("#job-picker").select_option("stress")
                    upload(page, "#native-import", signed)
                    expect(page.locator("#bloom-status")).to_contain_text("different job input")
                    page.locator("#job-picker").select_option("benchmark")
                    broken = json.loads(json.dumps(signed))
                    broken["receipt"]["signature"] = "A" * 86 + "=="
                    upload(page, "#native-import", broken)
                    expect(page.locator("#bloom-status")).not_to_contain_text("Return verified")
                    upload(page, "#native-import", signed)
                    expect(page.locator("#bloom-status")).to_contain_text("Return verified")
                    expect(page.locator("#result-view")).to_contain_text("Native signed approval attached")
                    (output / f"{experience}-native-return.json").write_text(json.dumps(signed, indent=2) + "\n")
                    page.locator("#result-view + .actions + details").locator("summary").click()
                if experience == "nova":
                    audit(page, "docket-desktop")
                    page.screenshot(path=str(output / "docket-desktop.png"), full_page=True)
                review_all(page)
                expect(page.locator("#promote")).to_be_enabled()
                dossier = download(page, "#download-dossier", output / f"{experience}-dossier.json")
                spec_plan = next(item for item in dossier["jobSpecURI_plans"] if item["job_id"] == "benchmark")
                assert hashlib.sha256(spec_path.read_bytes()).hexdigest() == spec_plan["sha256"]
                assert dossier["docket"]["visionary_claim"]["status"] == "unproven"
                assert dossier["docket"]["visionary_claim"]["economic_value_verified"] == 0
                assert all(gate["passed"] for gate in dossier["docket"]["gates"])
                click(page, "#promote")
                expect(page.locator("#bloom-status")).to_contain_text("recorded in Chronicle")
                report["experiences"].append(
                    {"id": experience, "kind": mission["work"]["kind"], "job_hash": bundle["job_hash"]}
                )
            expect(page.locator("#memory-count")).to_have_text("5 active")
            recovery_path = output / "recovery.json"
            download(page, "#save-workspace", recovery_path)
            audit(page, "chronicle-desktop")
            page.screenshot(path=str(output / "chronicle-desktop.png"), full_page=True)
            # Reuse is an actual unchanged benchmark; all new probes and decisions remain mandatory.
            page.get_by_role("button", name="Seed the next mission").first.click()
            ready(page)
            click(page, "#run-all")
            expect(page.locator("#promote")).to_be_disabled()
            review_all(page)
            click(page, "#promote")
            expect(page.locator("#memory-count")).to_have_text("6 active")
            expect(page.locator("#reused-count")).to_have_text("1")
            page.locator("#revoke-reason-0").fill("The source input assumptions were superseded by new evidence.")
            page.get_by_role("button", name="Revoke capability & dependents").first.click()
            ready(page)
            expect(page.locator("#memory-count")).to_have_text("4 active")
            revoked_path = output / "revoked-recovery.json"
            revoked = download(page, "#save-workspace", revoked_path)
            upload(page, "#workspace-import", revoked_path)
            expect(page.locator("#memory-count")).to_have_text("4 active")
            tampered = json.loads(json.dumps(revoked))
            tampered["history"][0]["payload"]["reviews"]["source"]["decision"] = "reject"
            upload(page, "#workspace-import", tampered)
            expect(page.locator("#bloom-status")).to_contain_text("chain")
            expect(page.locator("#memory-count")).to_have_text("4 active")
            upload(page, "#workspace-import", recovery_path)
            expect(page.locator("#memory-count")).to_have_text("5 active")
            # Changed inputs cannot export or accept stale proof; text renders literally.
            page.locator('[data-view="seed"]').click()
            page.locator("#claim").fill('<img src=x onerror="alert(1)"> A changed claim remains unproven.')
            expect(page.locator("#run-all")).to_be_disabled()
            click(page, "#compile-seed")
            page.locator('[data-view="docket"]').click()
            upload(page, "#bundle-import", output / "proof-bundle.json")
            expect(page.locator("#bloom-status")).to_contain_text("does not replay")
            page.locator('[data-view="seed"]').click()
            click(page, "#run-all")
            assert page.locator("#result-view img").count() == 0
            # A reviewed failure must remain HOLD, even when every decision says accept.
            page.locator('[data-experience="nova"]').click()
            page.locator("#shock").fill("50")
            click(page, "#compile-seed")
            click(page, "#run-all")
            review_all(page)
            expect(page.locator("#promote")).to_be_disabled()
            expect(page.locator("#gate-grid")).to_contain_text("HOLD")
            page.locator('[data-view="chronicle"]').click()
            upload(page, "#workspace-import", recovery_path)
            report["checks"].extend(
                [
                    "all-five-experiences",
                    "original-gallery-preserved",
                    "baseline-and-stress-computed",
                    "native-missions-executed-and-signed-returns",
                    "signature-key-and-input-binding",
                    "self-declared-verdict-rejected",
                    "tampered-and-stale-return-rejected",
                    "reviewed-failure-remains-hold",
                    "exact-benchmark-reuse-needs-fresh-probes",
                    "transitive-revocation",
                    "unchanged-recovery-roundtrip",
                    "tampered-history-rejected-atomically",
                    "jobspec-download-sha256",
                    "keyboard-focus-preserved",
                    "input-text-escaped",
                ]
            )
            # Shared scripts resolve by import.meta.url under the historical mirrored route.
            page.goto(origin + "alpha_factory_v1/demos/bloom/", wait_until="networkidle")
            ready(page)
            expect(page.locator("#memory-count")).to_have_text("5 active")
            page.locator('[data-view="chronicle"]').click()
            report["checks"].append("mirrored-page")
            wait_for(page, "!!navigator.serviceWorker.controller")
            context.set_offline(True)
            page.reload(wait_until="domcontentloaded")
            ready(page)
            expect(page.locator("#memory-count")).to_have_text("5 active")
            page.locator('[data-view="docket"]').click()
            click(page, "#run-job")
            expect(page.locator("#bloom-status")).to_contain_text("Job executed and replayed")
            report["checks"].append("offline-recovery-and-execution")
            context.set_offline(False)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(origin + "bloom/", wait_until="networkidle")
            ready(page)
            for panel in ("seed", "docket", "chronicle"):
                page.locator(f'[data-view="{panel}"]').click()
                audit(page, f"{panel}-mobile")
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), panel
                page.screenshot(path=str(output / f"{panel}-mobile.png"), full_page=True)
            report["checks"].append("mobile-no-overflow")
            if axe_script:
                report["checks"].append("axe-wcag-a-aa-no-violations")
            # A bounded workspace can be rotated without losing the prior downloadable history.
            previous_path = output / "previous-workspace.json"
            previous = download(page, "#start-fresh", previous_path)
            assert len(previous["history"]) == 5
            expect(page.locator("#memory-count")).to_have_text("0 active")
            page.locator('[data-view="chronicle"]').click()
            upload(page, "#workspace-import", previous_path)
            expect(page.locator("#memory-count")).to_have_text("5 active")
            report["checks"].append("save-and-start-fresh-preserves-history")
            browser.close()
        assert not errors, errors
        report["passed"] = True
    finally:
        if server:
            server.shutdown()
            server.server_close()
        report["browser_errors"] = errors
        (output / "accessibility.json").write_text(json.dumps(audits, indent=2) + "\n")
        (output / "proof-bloom.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--output", type=Path, default=Path("evidence/proof-bloom"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script), indent=2))


if __name__ == "__main__":
    main()
