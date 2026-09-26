# SPDX-License-Identifier: Apache-2.0
"""Exercise Insight Atlas calculations, proof controls, exports and recovery in Chromium."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.engine import Engine, verify_export
from alpha_factory_v1.core.runtime.store import Journal, digest
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler, inspect, wait_for


def downloaded(page: Page, selector: str, output: Path) -> dict[str, Any]:
    """Retain the actual user download, rather than synthesizing an export."""
    with page.expect_download() as event:
        page.locator(selector).click()
    event.value.save_as(output)
    assert output.stat().st_size <= 250000, "Downloaded JSON must fit the browser's unchanged import limit"
    result: dict[str, Any] = json.loads(output.read_text())
    return result


def upload(page: Page, selector: str, value: dict[str, Any] | Path) -> None:
    """Exercise the file input with a bounded JSON document."""
    if isinstance(value, Path):
        page.locator(selector).set_input_files(str(value))
    else:
        page.locator(selector).set_input_files(
            {"name": "validation.json", "mimeType": "application/json", "buffer": json.dumps(value).encode()}
        )
    wait_for(page, "!document.querySelector('#atlas').hasAttribute('aria-busy')")


def validate(site: Path, output: Path, public_url: str | None = None, axe_script: Path | None = None) -> dict[str, Any]:
    """Test canonical and mirrored pages under a project prefix, including offline use."""
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
        "schema": "agialpha.insight.acceptance.v1",
        "origin": public_url or "local project subpath",
        "scenarios": [],
        "checks": [],
        "passed": False,
    }
    errors: list[str] = []
    accessibility: list[dict[str, Any]] = []

    def audit(page: Page, label: str) -> None:
        if axe_script is None:
            return
        inspect(page, axe_script.read_text() + ";true")
        result = inspect(
            page,
            "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
            ".then(r=>({violations:r.violations,"
            "incomplete:r.incomplete.map(i=>({id:i.id,nodes:i.nodes.map(n=>n.target)}))}))",
        )
        accessibility.append({"view": label, **result})
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
            expect(page.get_by_role("link", name="Enter the Insight Atlas")).to_be_visible()
            audit(page, "homepage-desktop")
            page.screenshot(path=str(output / "homepage.png"), full_page=True)
            page.get_by_role("link", name="Enter the Insight Atlas").click()
            wait_for(page, "document.documentElement.dataset.atlasReady === 'true'")
            expect(page.locator(".sector-node")).to_have_count(12)
            page.get_by_role("button", name="Explore Science", exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("button", name="Explore Science", exact=True)).to_be_focused()
            expect(page.locator("#sector-title")).to_have_text("Science")
            audit(page, "atlas-map-desktop")
            page.get_by_role("button", name="A 3-minute field guide").click()
            expect(page.locator("#field-notes")).to_be_visible()
            page.get_by_role("button", name="A 3-minute field guide").click()
            expect(page.locator("#field-notes")).to_be_hidden()
            page.screenshot(path=str(output / "atlas-desktop.png"), full_page=True)
            for scenario in ("energy", "science", "enterprise"):
                page.locator("#scenario-picker").select_option(scenario)
                page.get_by_role("button", name="02 Second-order agency").click()
                if scenario == "energy":
                    audit(page, "atlas-agency-desktop")
                page.locator("#build-proof").click()
                expect(page.locator("#review-panel")).to_be_visible()
                proof = downloaded(page, "#download-proof", output / f"{scenario}-evidence.json")
                assert all(gate["passed"] for gate in proof["gates"])
                page.locator("#review-note").fill(
                    "Checked all holdout results and distinct validator groups; real-world claims remain unverified."
                )
                page.locator("#promote").click()
                expect(page.locator("#atlas-status")).to_contain_text("Modeled capability recorded")
                page.locator("#promote").click()
                expect(page.locator("#atlas-status")).to_contain_text("Duplicate capability")
                page.get_by_role("button", name="03 Alpha under trial").click()
                if scenario == "energy":
                    page.locator(".claim-card").nth(1).focus()
                    page.keyboard.press("Enter")
                    expect(page.locator('.claim-card[aria-pressed="true"]')).to_be_focused()
                    audit(page, "atlas-ontology-desktop")
                dossier = downloaded(page, "#download-dossier", output / f"{scenario}-dossier.json")
                for mission in dossier["missions"]:
                    Mission.model_validate(mission)
                mission = downloaded(page, "#download-mission", output / f"{scenario}-mission.json")
                Mission.model_validate(mission)
                with tempfile.TemporaryDirectory(prefix="atlas-native-") as temporary:
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
                        "Inspected the exported Atlas source excerpts and bounded research result.",
                    )
                    signed = engine.export(record["id"])
                    assert verify_export(signed, journal.public)["valid"]
                    (output / f"{scenario}-native-signed.json").write_text(json.dumps(signed, indent=2) + "\n")
                assert dossier["economic_value_verified_usd"] == "0"
                report["scenarios"].append(
                    {
                        "id": scenario,
                        "digest": proof["digest"],
                        "holdout_useful": proof["comparison"]["holdout"]["candidate"]["metrics"]["useful"],
                        "native_missions": len(dossier["missions"]),
                    }
                )
            expect(page.locator("#chronicle-count")).to_have_text("3 active modeled capabilities")
            recovery = downloaded(page, "#save-workspace", output / "recovery.json")
            page.get_by_role("button", name="02 Second-order agency").click()
            page.locator("#budget").fill("1500")
            page.locator("#agents").fill("7")
            page.get_by_role("button", name="Reuse reviewed design").first.click()
            expect(page.locator("#agents")).to_have_value("4")
            expect(page.locator("#budget")).to_have_value("1500")
            expect(page.locator("#review-panel")).to_be_hidden()
            expect(page.locator("#download-proof")).to_be_disabled()
            upload(page, "#workspace-import", output / "recovery.json")
            report["checks"].extend(
                [
                    "all-three-scenarios",
                    "native-mission-schema",
                    "native-research-execution-and-signed-export",
                    "duplicate-promotion-rejected",
                    "reviewed-design-reuse-requires-fresh-evidence",
                    "downloaded-recovery-bytes-reimported",
                    "existing-flywheel-and-26-entries-preserved",
                ]
            )

            page.get_by_role("button", name="02 Second-order agency").click()
            page.locator("#agents").fill("5")
            expect(page.locator("#review-panel")).to_be_hidden()
            expect(page.locator("#build-proof")).to_be_disabled()
            page.get_by_role("button", name="Run the comparison").click()
            upload(page, "#proof-import", proof)
            expect(page.locator("#atlas-status")).to_contain_text("stale")
            tampered = json.loads(json.dumps(proof))
            tampered["comparison"]["holdout"]["candidate"]["metrics"]["useful"] = 999
            upload(page, "#proof-import", tampered)
            expect(page.locator("#atlas-status")).to_contain_text("replay differs")
            page.locator("#quorum").fill("1")
            page.get_by_role("button", name="Run the comparison").click()
            page.locator("#build-proof").click()
            expect(page.locator("#atlas-status")).to_contain_text("model gates failed")
            expect(page.locator("#review-panel")).to_be_hidden()
            expect(page.locator('.proof-gate[data-passed="false"]')).not_to_have_count(0)
            page.locator("#search-architectures").click()
            expect(page.locator("#search-table tbody tr")).to_have_count(18)
            page.locator("#apply-search").click()
            page.locator("#build-proof").click()
            expect(page.locator("#review-panel")).to_be_visible()
            page.screenshot(path=str(output / "agency-desktop.png"), full_page=True)
            report["checks"].extend(
                ["stale-proof-rejected", "tampered-proof-rejected", "unsafe-quorum-blocked", "18-architecture-search"]
            )

            page.get_by_role("button", name="01 Living treasure map").click()
            page.locator("#envelope").fill("15.001")
            page.get_by_role("button", name="Reallocate").click()
            expect(page.locator("#allocation-table tbody tr").last).to_contain_text("$15,001,000,000,000,000")
            page.locator("#envelope").fill("-1")
            page.get_by_role("button", name="Reallocate").click()
            expect(page.locator("#atlas-status")).to_contain_text("Enter 0")
            expect(page.locator("#allocation-table tbody tr").last).to_contain_text("$15,001,000,000,000,000")
            upload(page, "#workspace-import", output / "recovery.json")
            expect(page.locator("#atlas-status")).to_contain_text("Expedition restored")
            expect(page.locator("#chronicle-count")).to_have_text("3 active modeled capabilities")
            bad_recovery = json.loads(json.dumps(recovery))
            bad_recovery["chronicle"]["events"][0]["note"] = "Altered operator review note."
            upload(page, "#workspace-import", bad_recovery)
            expect(page.locator("#atlas-status")).to_contain_text("hash mismatch")
            expect(page.locator("#chronicle-count")).to_have_text("3 active modeled capabilities")
            page.get_by_role("button", name="Revoke capability").first.click()
            expect(page.locator("#chronicle-count")).to_have_text("2 active modeled capabilities")
            downloaded(page, "#save-workspace", output / "recovery-revoked.json")
            upload(page, "#workspace-import", output / "recovery-revoked.json")
            expect(page.locator("#chronicle-count")).to_have_text("2 active modeled capabilities")
            page.locator("#scenario-picker").select_option("science")
            page.locator("#scenario-picker").select_option("restored")
            expect(page.locator("#scenario-question")).to_have_text(recovery["scenario"]["question"])
            custom = json.loads(json.dumps(recovery["scenario"]))
            custom["title"] = "Imported operator scenario"
            custom["question"] = "Can this imported scenario be selected again without losing its inputs?"
            upload(page, "#scenario-import", custom)
            page.locator("#scenario-picker").select_option("science")
            page.locator("#scenario-picker").select_option("imported")
            expect(page.locator("#scenario-question")).to_have_text(custom["question"])
            report["checks"].extend(
                [
                    "exact-envelope-ledger",
                    "invalid-input-atomicity",
                    "recovery-replays-promotions",
                    "tampered-history-rejected",
                    "revocation-survives-recovery",
                    "custom-expedition-reselection",
                ]
            )

            page.get_by_role("button", name="03 Alpha under trial").click()
            page.locator("#claim-search").fill("no-such-hypothesis-845")
            expect(page.locator("#claim-list")).to_contain_text("No claims match")
            page.locator("#claim-search").fill("")
            page.locator("#new-claim").click()
            form = page.locator("#claim-form")
            form.locator('[name="title"]').fill('<img src=x onerror="alert(1)">')
            form.locator('[name="hypothesis"]').fill("A changed review process reduces missing-evidence errors.")
            form.locator('[name="metric"]').fill("Missing-evidence error rate")
            form.locator('[name="target"]').fill("Improve over a matched baseline.")
            form.locator('[name="evidence_needed"]').fill(
                "Independent controlled review with all errors and raw decisions."
            )
            form.get_by_role("button", name="Add the claim").click()
            expect(page.locator("#claim-dossier h3")).to_have_text('<img src=x onerror="alert(1)">')
            expect(page.locator("#claim-dossier img")).to_have_count(0)
            bad_scenario = json.loads(json.dumps(recovery["scenario"]))
            bad_scenario["sources"][0]["url"] = "javascript:alert(1)"
            upload(page, "#scenario-import", bad_scenario)
            expect(page.locator("#atlas-status")).to_contain_text("HTTP(S)")
            page.screenshot(path=str(output / "ontology-desktop.png"), full_page=True)
            report["checks"].extend(
                [
                    "custom-hypothesis",
                    "safe-text-rendering",
                    "unsafe-source-url-rejected",
                    "claim-search-and-empty-state",
                ]
            )
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for view in ("map", "agency", "ontology"):
                    page.locator(f'[data-view="{view}"]').click()
                    assert not inspect(page, "document.documentElement.scrollWidth > innerWidth"), (width, view)
                    if width == 390:
                        audit(page, f"atlas-{view}-mobile")
                        page.screenshot(path=str(output / f"{view}-mobile.png"), full_page=True)
            page.goto(origin + "alpha_factory_v1/demos/insight/", wait_until="networkidle")
            wait_for(page, "document.documentElement.dataset.atlasReady === 'true'")
            expect(page.locator(".sector-node")).to_have_count(12)
            page.get_by_role("button", name="02 Second-order agency").click()
            page.locator("#build-proof").click()
            expect(page.locator("#review-panel")).to_be_visible()
            page.goto(origin + "insight/", wait_until="networkidle")
            wait_for(
                page,
                "document.documentElement.dataset.atlasReady === 'true' && Boolean(navigator.serviceWorker.controller)",
            )
            wait_for(page, "caches.keys().then(names => names.some(n => n.startsWith('agialpha-gallery-')))")
            context.set_offline(True)
            page.reload(wait_until="networkidle")
            wait_for(page, "document.documentElement.dataset.atlasReady === 'true'")
            upload(page, "#workspace-import", output / "recovery-revoked.json")
            expect(page.locator("#chronicle-count")).to_have_text("2 active modeled capabilities")
            page.get_by_role("button", name="02 Second-order agency").click()
            page.locator("#build-proof").click()
            expect(page.locator("#review-panel")).to_be_visible()
            context.set_offline(False)
            report["checks"].extend(
                ["320-390-768-1440-responsive", "mirrored-page", "offline-reload-recovery-and-replay"]
            )
            report["checks"].append("keyboard-selection-retains-focus")
            if axe_script is not None:
                report["checks"].append("axe-wcag-a-aa-no-violations")
                report["accessibility"] = {
                    "tool": "axe-core 4.10.3",
                    "scans": len(accessibility),
                    "scope": "Automated WCAG A/AA checks; incomplete items need human review. Not full certification.",
                }
            assert not errors, errors
            browser.close()
        report["passed"] = True
        return report
    finally:
        report["browser_errors"] = errors
        (output / "insight-atlas.json").write_text(json.dumps(report, indent=2) + "\n")
        if accessibility:
            (output / "accessibility.json").write_text(json.dumps(accessibility, indent=2) + "\n")
        if server:
            server.shutdown()
            server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--output", type=Path, default=Path("evidence/insight-atlas"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script), indent=2))


if __name__ == "__main__":
    main()
