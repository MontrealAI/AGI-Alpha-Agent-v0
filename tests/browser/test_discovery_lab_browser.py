# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual Discovery Lab controls and existing portable history."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


def download_request(page: Page, destination: Path, route: str) -> dict[str, Any]:
    """Inspect the actual emitted review draft, not a reconstructed request."""
    page.locator("#lab-route").select_option(route)
    with page.expect_download() as pending:
        page.locator("#lab-export-request").click()
    pending.value.save_as(destination)
    request: dict[str, Any] = json.loads(destination.read_text())
    assert request["schema"] == "successor-discovery-work-request/v1"
    assert request["commission"]["capBaseUnits"] == "0"
    assert request["commission"]["status"] == "DRAFT_NOT_SUBMITTED"
    assert request["executionMode"] == "synthetic-local"
    return request


def main() -> None:
    """Retain negative, successful, edited and successor evidence in one actual history."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/index.html"
    errors: list[str] = []
    requests: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="discovery-lab-browser-") as temporary, sync_playwright() as playwright:
            executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            browser = playwright.chromium.launch(executable_path=executable)
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            context.on("request", lambda request: requests.append(request.url))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
            response = page.goto(url)
            assert response is not None
            loaded_page_hash = hashlib.sha256(response.body()).hexdigest()
            assert manifest["sourceHash"] in response.text()
            source_receipt = {
                "source": manifest,
                "pageSha256": loaded_page_hash,
                "browser": browser.version,
                "scope": "Actual generated page bytes loaded by this local browser attempt; no hosted or release acceptance.",
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
            audit(page, "accepted")
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-accepted.png"))
            manager = download_request(page, Path(temporary) / "manager.json", "USDC")
            jobs = download_request(page, Path(temporary) / "jobs.json", "AGIALPHA")
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

            page.locator("#lab-successor").click()
            idle(page)
            assert campaign_count(page) == 4
            expect(page.locator("#lab-controls")).to_have_value("4")
            expect(page.locator("#lab-bindings")).to_contain_text('"controls": 4')
            retained = page.locator("#lab-events").text_content()
            assert retained and "inconclusive" in retained and "accepted" in retained and "rejected" in retained
            page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "desktop-successor.png"))
            reloaded = page.reload()
            assert reloaded is not None
            assert (
                hashlib.sha256(reloaded.body()).hexdigest() == loaded_page_hash
            ), "Generated source changed during browser evidence."
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
            assert all(request.startswith(f"http://127.0.0.1:{server.server_port}/") for request in requests), requests
            (OUTPUT / "journey.json").write_text(
                json.dumps(
                    {
                        "campaigns": 4,
                        "requests": requests,
                        "pageErrors": errors,
                        "sourceHash": manifest["sourceHash"],
                        "pageSha256": loaded_page_hash,
                    },
                    indent=2,
                )
            )
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
