# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual Discovery Lab controls and existing portable history."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Page, expect, sync_playwright

if TYPE_CHECKING:
    from tests.browser import test_successor_capability_accessibility as accessibility
else:
    import test_successor_capability_accessibility as accessibility

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("DISCOVERY_LAB_EVIDENCE", "/tmp/discovery-lab-browser-evidence"))
AXE = Path(os.environ.get("AXE_SCRIPT", str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js")))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        """Keep the retained test log focused on acceptance."""


def idle(page: Page) -> None:
    """Wait for the actual workspace operation to finish."""
    expect(page.locator("#lab-form")).to_have_attribute("aria-busy", "false", timeout=120000)
    expect(page.locator("#lab-construct")).to_be_enabled(timeout=120000)


def campaign_count(page: Page) -> int:
    """Count retained campaign records rendered from the existing history bridge."""
    return int(page.locator("#lab-events > li h4").count())


def audit(page: Page, label: str) -> None:
    """Resolve every Axe incomplete through the preserved conservative contrast reviewer."""
    assert AXE.is_file(), "The pinned accessibility script is required."
    accessibility.OUTPUT = OUTPUT / "contrast-review"
    accessibility.OUTPUT.mkdir(parents=True, exist_ok=True)
    accessibility.AXE = AXE
    result = accessibility.inspect(page, label)
    (OUTPUT / f"accessibility-{label}.json").write_text(json.dumps(result, indent=2))


def download_json(page: Page, selector: str, destination: Path) -> dict[str, Any]:
    """Retain the exact bytes emitted by an actual page download."""
    with page.expect_download() as pending:
        page.locator(selector).click()
    pending.value.save_as(destination)
    result: dict[str, Any] = json.loads(destination.read_text())
    return result


def download_request(page: Page, destination: Path, route: str) -> dict[str, Any]:
    """Inspect the actual emitted review draft, not a reconstructed request."""
    page.locator("#lab-route").select_option(route)
    request = download_json(page, "#lab-export-request", destination)
    assert request["schema"] == "successor-discovery-work-request/v1"
    assert request["commission"]["capBaseUnits"] == "0"
    assert request["commission"]["status"] == "DRAFT_NOT_SUBMITTED"
    assert request["executionMode"] == "synthetic-local"
    return request


def run_acceptance(entry: str, output: Path, *, expected_page_sha256: str | None = None) -> dict[str, Any]:
    """Use the same complete finite journey for an exact packaged file or public HTTPS page."""
    if not __debug__:
        raise RuntimeError("Discovery Lab browser acceptance requires Python assertion checks enabled")
    global OUTPUT
    OUTPUT = output.resolve()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    parsed = urlsplit(entry)
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("Browser acceptance requires an entry without credentials, query or fragment")
    server = None
    if parsed.scheme == "file" and not parsed.netloc:
        destination = Path(unquote(parsed.path)).resolve()
        if not destination.is_file():
            raise ValueError("The exact packaged browser page is missing")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(destination.parent)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/{destination.name}"
        mode = "packaged-local"
    elif parsed.scheme == "https" and parsed.netloc:
        url, mode = entry, "public-https"
    else:
        raise ValueError("Browser acceptance supports an exact local file or public HTTPS entry")
    location = urlsplit(url)
    allowed_root = f"{location.scheme}://{location.netloc}{location.path.rsplit('/', 1)[0]}/"
    expected_hash = (
        expected_page_sha256
        or hashlib.sha256((ROOT / "docs/successor/capabilities/index.html").read_bytes()).hexdigest()
    )
    errors: list[str] = []
    requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            browser = playwright.chromium.launch(executable_path=executable)
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            context.on("request", lambda request: requests.append(request.url))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
            response = page.goto(url)
            assert response is not None and response.status == 200 and response.url == url
            loaded_page_hash = hashlib.sha256(response.body()).hexdigest()
            assert loaded_page_hash == expected_hash, "Browser page differs from exact packaged/generated bytes."
            assert manifest["sourceHash"] in response.text()
            source_receipt = {
                "source": manifest,
                "pageSha256": loaded_page_hash,
                "browser": browser.version,
                "scope": "Exact "
                + mode
                + (
                    " generated-page browser journey; synthetic software evidence, "
                    "not release or external-execution qualification."
                ),
                "entryUrl": entry,
                "browserEntryUrl": url,
            }
            (OUTPUT / "source-receipt.json").write_text(json.dumps(source_receipt, indent=2))
            page.locator("#lab-public-confirmation").check()
            idle(page)
            assert campaign_count(page) == 0
            audit(page, "ready")
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-ready.png"))

            page.locator("#lab-form details").filter(has=page.locator("#lab-budget-search")).locator("summary").click()
            page.locator("#lab-budget-search").fill("0")
            page.locator("#lab-construct").click()
            idle(page)
            expect(page.locator("#lab-outcome-summary")).to_contain_text("INCONCLUSIVE")
            assert campaign_count(page) == 1
            first = page.locator("#lab-events > li").first.text_content()

            page.locator("#lab-defaults").click()
            page.locator("#lab-construct").click()
            idle(page)
            expect(page.locator("#lab-outcome-summary")).to_contain_text("ACCEPTED")
            assert campaign_count(page) == 2
            assert page.locator("#lab-events > li").first.text_content() == first
            assert page.locator("#lab-stages > li").count() == 6
            assert page.locator("#lab-stages > li[data-state=accepted]").count() == 6
            accepted_selector = (
                page.locator("#lab-events > li").nth(1).get_by_role("button", name="Show campaign 2 · accepted")
            )
            accepted_digest = accepted_selector.get_attribute("data-campaign-digest")
            assert accepted_digest is not None and len(accepted_digest) == 64
            audit(page, "accepted")
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-accepted.png"))
            manager = download_request(page, OUTPUT / "manager-initial-review-draft.json", "USDC")
            jobs = download_request(page, OUTPUT / "jobs-initial-review-draft.json", "AGIALPHA")
            assert manager["commission"]["route"] == "manager-usdc"
            assert manager["commission"]["currency"] == "USDC6"
            assert jobs["commission"]["route"] == "jobs-agialpha"
            assert jobs["commission"]["currency"] == "AGIALPHA18"
            assert manager["commission"]["id"] == jobs["commission"]["id"]
            assert manager["commission"]["branch"] != jobs["commission"]["branch"]
            assert manager["payloadDigest"] == jobs["payloadDigest"]

            page.locator("#lab-memory").fill("1")
            expect(page.locator("#lab-charter-badge")).to_contain_text("needs qualification")
            expect(page.locator("#lab-status")).to_contain_text("earlier frozen scope")
            page.locator("#lab-construct").click()
            idle(page)
            expect(page.locator("#lab-outcome-summary")).to_contain_text("REJECTED")
            assert campaign_count(page) == 3
            assert page.locator("#lab-events > li").first.text_content() == first
            expect(page.locator("#lab-export-request")).to_be_disabled()

            # A later failure must not make its retained accepted predecessor unreachable.
            accepted_selector = page.locator(f'button[data-campaign-digest="{accepted_digest}"]')
            accepted_selector.focus()
            page.keyboard.press("Enter")
            expect(page.locator("#lab-result-heading")).to_be_focused()
            expect(page.locator("#lab-outcome-summary")).to_contain_text("ACCEPTED")
            expect(accepted_selector).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#lab-selection-status")).to_contain_text("Showing campaign 2 · accepted")
            expect(page.locator("#lab-memory")).to_have_value("1")
            assert campaign_count(page) == 3
            assert download_request(page, OUTPUT / "manager-retained-review-draft.json", "USDC") == manager
            assert download_request(page, OUTPUT / "jobs-retained-review-draft.json", "AGIALPHA") == jobs
            expect(accepted_selector).to_have_attribute("aria-pressed", "true")
            assert campaign_count(page) == 3
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-retained-selection.png"))

            # Selection is view-only: reload clearly resets to the latest retained result.
            selection_reload = page.reload()
            assert selection_reload is not None and selection_reload.status == 200 and selection_reload.url == url
            assert hashlib.sha256(selection_reload.body()).hexdigest() == loaded_page_hash
            page.locator("#lab-public-confirmation").check()
            idle(page)
            assert campaign_count(page) == 3
            expect(page.locator("#lab-outcome-summary")).to_contain_text("REJECTED")
            expect(page.locator("#lab-selection-status")).to_contain_text("Showing campaign 3 · rejected")
            expect(page.locator("#lab-selection-status")).to_contain_text("Reload shows the latest retained result")
            expect(page.locator("#lab-export-request")).to_be_disabled()

            page.locator("#lab-successor").click()
            idle(page)
            assert campaign_count(page) == 4
            expect(page.locator("#lab-controls")).to_have_value("4")
            expect(page.locator("#lab-bindings")).to_contain_text('"controls": 4')
            retained = page.locator("#lab-events").text_content()
            assert retained and "inconclusive" in retained and "accepted" in retained and "rejected" in retained
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-successor.png"))
            manager_successor = download_request(page, OUTPUT / "manager-review-draft.json", "USDC")
            jobs_successor = download_request(page, OUTPUT / "jobs-review-draft.json", "AGIALPHA")
            assert manager_successor["payloadDigest"] == jobs_successor["payloadDigest"]
            assert manager_successor["commission"]["id"] == jobs_successor["commission"]["id"]
            assert manager_successor["commission"]["branch"] != jobs_successor["commission"]["branch"]
            workspace = download_json(page, "#export", OUTPUT / "browser-workspace.json")
            assert workspace["missionId"] == manager_successor["missionId"]
            resource_panel = page.locator("#lab-resource-panel")
            resource_panel.locator("summary").click()
            account = download_json(page, "#lab-export-account", OUTPUT / "browser-account.json")
            assert account["schema"] == "discovery-lab-account-receipt/v1"
            assert account["workspaceId"] == workspace["missionId"]
            resource_panel.locator("summary").click()
            reloaded = page.reload()
            assert reloaded is not None and reloaded.status == 200 and reloaded.url == url
            reloaded_hash = hashlib.sha256(reloaded.body()).hexdigest()
            assert reloaded_hash == loaded_page_hash, "Generated source changed during browser evidence."
            page.locator("#lab-public-confirmation").check()
            idle(page)
            assert campaign_count(page) == 4
            expect(page.locator("#lab-controls")).to_have_value("4")
            assert page.locator("#lab-events").text_content() == retained
            expect(page.locator("#lab-form")).to_have_attribute("aria-busy", "false")

            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
                audit(page, f"mobile-{width}")
                page.locator("#discovery-lab").screenshot(path=str(OUTPUT / f"mobile-{width}.png"))
            page.locator("#lab-accuracy").focus()
            expect(page.locator("#lab-accuracy")).to_be_focused()
            page.keyboard.press("Tab")
            expect(page.locator("#lab-uses")).to_be_focused()
            assert not errors, errors
            assert all(request.startswith(allowed_root) for request in requests), requests
            artifacts = {}
            for name in (
                "manager-initial-review-draft.json",
                "jobs-initial-review-draft.json",
                "manager-retained-review-draft.json",
                "jobs-retained-review-draft.json",
                "manager-review-draft.json",
                "jobs-review-draft.json",
                "browser-workspace.json",
                "browser-account.json",
            ):
                raw = (OUTPUT / name).read_bytes()
                artifacts[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "utf8Bytes": len(raw)}
            (OUTPUT / "journey.json").write_text(
                json.dumps(
                    {
                        "passed": True,
                        "entryUrl": entry,
                        "browserEntryUrl": url,
                        "mode": mode,
                        "campaigns": 4,
                        "checks": [
                            "budget-inconclusive",
                            "six-stage-accepted",
                            "both-zero-cap-drafts",
                            "edited-constraint-rejected",
                            "retained-campaign-selection",
                            "stronger-successor",
                            "history-reload",
                            "resolved-accessibility",
                            "responsive-390-320",
                            "keyboard",
                            "no-external-requests",
                            "exact-page-before-and-after",
                        ],
                        "requests": requests,
                        "pageErrors": errors,
                        "sourceHash": manifest["sourceHash"],
                        "pageSha256": loaded_page_hash,
                        "artifacts": artifacts,
                    },
                    indent=2,
                )
            )
            browser.close()
            result: dict[str, Any] = json.loads((OUTPUT / "journey.json").read_text())
            return result
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


def main() -> None:
    """Run the complete journey against the generated checkout page."""
    result = run_acceptance((ROOT / "docs/successor/capabilities/index.html").as_uri(), OUTPUT)
    print(
        json.dumps(
            {"passed": result["passed"], "sourceHash": result["sourceHash"], "checks": len(result["checks"])},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
