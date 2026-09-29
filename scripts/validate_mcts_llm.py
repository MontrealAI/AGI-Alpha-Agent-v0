# SPDX-License-Identifier: Apache-2.0
"""Exercise real training, health, browser interaction and mobile layout locally."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def validate(output: Path, url: str | None = None) -> None:
    """Use an isolated local server, not an SDK stub or prerecorded completion."""
    from playwright.sync_api import sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    child = None
    with tempfile.TemporaryFile(mode="w+") as log:
        try:
            if url is None:
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                url = f"http://127.0.0.1:{port}"
                env = os.environ.copy()
                for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
                    env.pop(key, None)
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "alpha_factory_v1.demos.muzeromctsllmagent_v0",
                        "--episodes",
                        "4",
                        "--port",
                        str(port),
                    ],
                    stdout=log,
                    stderr=log,
                    env=env,
                )
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(150):
                try:
                    with client.open(url + "/__live", timeout=1) as response:
                        assert json.load(response)["status"] == "ok"
                    break
                except OSError:
                    if child is not None and child.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    time.sleep(0.2)
            else:
                raise RuntimeError("MuZero health endpoint did not become ready")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                from playwright.sync_api import expect

                errors = []
                page.on("pageerror", lambda error: errors.append(error.stack))
                # Training and the interface must work even when external browser requests are blocked.
                context.route(
                    "**/*",
                    lambda route: (
                        route.continue_()
                        if urlsplit(route.request.url).netloc == urlsplit(url).netloc
                        else route.abort()
                    ),
                )
                page.goto(url, wait_until="networkidle")
                page.get_by_role("button", name="Retrieve, train & compare", exact=True).click()
                page.get_by_text("Complete · review required.", exact=False).wait_for(timeout=120000)
                assert page.get_by_text("trained_search", exact=False).count() > 0
                assert page.get_by_text("immediate · lexical overlap", exact=False).count() > 0
                assert page.get_by_text("First action 0 · observed total reward 0.3", exact=False).count() > 0
                download_button = page.get_by_role("button", name="Download JSON report", exact=True)
                with page.expect_download() as download_info:
                    download_button.click()
                download = download_info.value
                path = output / download.suggested_filename
                download.save_as(path)
                record = json.loads(path.read_text())
                assert record["status"] == "complete" and record["execution"] == "simulation_only"
                assert len(record["provenance"]["source_sha256"]) == 3
                assert record["experiment"]["config"]["episodes"] == 4
                page.screenshot(path=str(output / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(output / "mobile.png"), full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                # A failed run must replace the previous completion and disable stale exports.
                question = page.get_by_role("textbox", name="Question about MiniChoice", exact=True)
                question.fill("")
                page.get_by_role("button", name="Retrieve, train & compare", exact=True).click()
                page.get_by_text("Run failed.", exact=False).wait_for(timeout=15000)
                expect(download_button).to_be_disabled()
                assert page.get_by_text("Complete · review required.", exact=False).count() == 0
                question.fill("Which first action maximizes delayed reward?")
                page.get_by_role("button", name="Retrieve, train & compare", exact=True).click()
                page.get_by_text("Complete · review required.", exact=False).wait_for(timeout=120000)
                expect(download_button).to_be_enabled()
                page.get_by_role("button", name="Retrieve, train & compare", exact=True).click()
                page.get_by_role("button", name="Stop", exact=True).click()
                page.get_by_text("Stop requested.", exact=False).wait_for(timeout=15000)
                assert not errors, errors
                (output / "browser.json").write_text(
                    json.dumps(
                        {
                            "health": True,
                            "real_training": True,
                            "evaluation_visible": True,
                            "evidence_and_counterfactuals": True,
                            "mobile_no_overflow": True,
                            "stop": True,
                            "json_download": True,
                            "failure_clears_previous_report": True,
                            "retry_after_failure": True,
                            "external_browser_requests_blocked": True,
                            "page_errors": errors,
                        },
                        indent=2,
                    )
                    + "\n"
                )
                browser.close()
        finally:
            if child is not None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/mcts-llm-browser"))
    parser.add_argument("--url", help="Existing local Docker URL instead of starting a subprocess")
    args = parser.parse_args()
    validate(args.output, args.url)


if __name__ == "__main__":
    main()
