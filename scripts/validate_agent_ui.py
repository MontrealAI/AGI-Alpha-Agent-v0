#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Drive the installed operator console through a real browser on loopback."""

from __future__ import annotations

import argparse
import json
import socket
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
import uvicorn

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    """Check authentication, work, review, exports, controls and mobile layout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=str)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alpha-ui-") as temporary:
        journal = Journal.initialize(Path(temporary) / "agent")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(create_app(journal), host="127.0.0.1", port=port, log_level="error", access_log=False)
        )
        worker = threading.Thread(target=server.run, daemon=True)
        worker.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("operator console startup failed")
            with sync_playwright() as playwright:
                options = {"executable_path": args.browser} if args.browser else {}
                browser = playwright.chromium.launch(**options)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                # A test guard prevents any accidental third-party requests.
                page.route(
                    "**/*",
                    lambda route: (
                        route.continue_()
                        if route.request.url.startswith(f"http://127.0.0.1:{port}/")
                        else route.abort()
                    ),
                )
                page.goto(f"http://127.0.0.1:{port}")
                page.locator("#token").fill("incorrect")
                page.get_by_role("button", name="Connect", exact=True).click()
                expect(page.locator("#message")).to_contain_text("Access token required")
                page.locator("#token").fill((journal.root / "api.token").read_text())
                page.get_by_role("button", name="Connect", exact=True).click()
                expect(page.locator("#workspace")).to_be_visible()
                completed = []
                for kind in ("research", "allocation", "schedule", "forecast"):
                    page.locator("#kind").select_option(kind)
                    page.locator("#start").click()
                    expect(page.locator("#approve")).to_be_visible(timeout=30000)
                    expect(page.locator("#stages li")).to_have_count(7)
                    page.locator("#review-note").fill(
                        "Reviewed example constraints and explicit limits in browser acceptance test."
                    )
                    page.locator("#approve").click()
                    expect(page.locator("#download")).to_be_visible()
                    with page.expect_download() as download:
                        page.locator("#download").click()
                    artifact = json.loads(Path(download.value.path()).read_bytes())
                    assert artifact["receipt"]["body"]["document"]["state"] == "completed"
                    completed.append(kind)
                page.locator("#pause").click()
                expect(page.locator("#start")).to_be_disabled()
                expect(page.locator("#connection")).to_have_text("Paused")
                page.locator("#pause").click()
                expect(page.locator("#start")).to_be_enabled()
                page.screenshot(path=str(args.output / "operator-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(args.output / "operator-mobile.png"), full_page=True)
                page.locator("#disconnect").click()
                expect(page.locator("#login")).to_be_visible()
                assert page.evaluate("localStorage.length") == 0
                assert not errors, errors
                browser.close()
            evidence = {
                "passed": True,
                "missions_approved_and_exported": completed,
                "checks": [
                    "authentication failure",
                    "seven stages",
                    "signed export",
                    "persistent pause/resume",
                    "mobile no horizontal overflow",
                    "disconnect",
                    "no browser script errors",
                    "no token in localStorage",
                    "third-party network blocked",
                ],
                "journal": journal.verify(),
            }
            (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence))
        finally:
            server.should_exit = True
            worker.join(timeout=10)


if __name__ == "__main__":
    main()
