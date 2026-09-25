# SPDX-License-Identifier: Apache-2.0
"""Exercise legacy gallery interactions under a project subpath in real Chromium."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


class Handler(SimpleHTTPRequestHandler):
    """Serve the site exactly one directory below the origin, like GitHub Pages."""

    def translate_path(self, path: str) -> str:
        return super().translate_path(path.removeprefix("/project"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def validate(site: Path, output: Path) -> dict[str, object]:
    """Require chart data, controls, correct resource URLs and offline recovery."""
    output.mkdir(parents=True, exist_ok=True)
    pages = sorted(
        page
        for page in site.rglob("index.html")
        if "alpha_agi_insight_v1" not in page.parts
        and 'id="chart"' in page.read_text(encoding="utf-8")
        and (page.parent / "assets" / "logs.json").is_file()
    )
    if len(pages) < 40:
        raise AssertionError("Both canonical and mirrored legacy demos must be exercised")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}/project/"
    records = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(service_workers="block", viewport={"width": 390, "height": 844})
            context.route("https://**", lambda route: route.abort())
            for file in pages:
                page = context.new_page()
                errors: list[str] = []
                failed: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: failed.append(response.url) if response.status >= 400 else None)
                page.goto(origin + file.relative_to(site).as_posix())
                page.get_by_role("status").filter(has_text="Bundled sample replay").wait_for(timeout=15000)
                page.get_by_role("button", name="Replay bundled sample offline").click()
                assert page.locator("table tbody tr").count() > 0
                assert page.locator("#logs-panel").inner_text().strip()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert not errors and not failed, {"page": str(file), "errors": errors, "http": failed}
                records.append(
                    {"page": file.relative_to(site).as_posix(), "rows": page.locator("table tbody tr").count()}
                )
                page.close()

            page = context.new_page()
            page.goto(origin + "index.html")
            count = page.locator(".demo-card").count()
            assert count >= 26
            assert page.locator("a button").count() == 0
            page.get_by_role("searchbox", name="Search demos").fill("no-matching-demo-987654")
            assert page.locator(".demo-card:visible").count() == 0
            assert page.locator("#no-results").is_visible()
            page.get_by_role("searchbox", name="Search demos").fill("governance")
            assert page.locator(".demo-card:visible").count() == 1
            page.screenshot(path=str(output / "gallery-mobile.png"), full_page=True)

            # Explicit provider error must remain visible, without a silent offline fallback.
            page.goto(origin + "macro_sentinel/index.html")
            page.locator("#demo-status").filter(has_text="Bundled sample replay").wait_for()
            replies = iter(["test-model", "test-key-not-a-secret"])
            page.on("dialog", lambda dialog: dialog.accept(next(replies)))
            page.route("https://api.openai.com/**", lambda route: route.fulfill(status=401, body='{"error":"test"}'))
            page.get_by_role("button", name="Generate synthetic data with a paid OpenAI API").click()
            page.locator("#demo-status").filter(has_text="HTTP 401").wait_for()
            assert page.get_by_role("button", name="Replay bundled sample offline").is_enabled()
            assert page.evaluate("localStorage.length") == 0
            page.screenshot(path=str(output / "demo-error-mobile.png"), full_page=True)
            page.get_by_role("button", name="Python example (runtime download)").click()
            page.locator("#demo-status").filter(has_text="Seeded Python example complete").wait_for(timeout=60000)
            assert page.locator("table tbody tr").count() == 10

            legacy = context.new_page()
            legacy.emulate_media(reduced_motion="reduce")
            legacy_errors = []
            legacy.on("pageerror", lambda error: legacy_errors.append(str(error)))
            legacy.goto(origin + "alpha_factory_v1/demos/alpha_agi_insight_v1/")
            legacy.locator("#legacy-status").filter(has_text="Bundled synthetic scenario").wait_for(timeout=30000)
            assert legacy.locator(".js-plotly-plot").count() == 3
            legacy.wait_for_function("document.querySelectorAll('#tree-container .node').length > 10")
            legacy.get_by_role("button", name="Show/Hide Logs").click()
            assert legacy.locator("#toggle-logs").get_attribute("aria-expanded") == "true"
            legacy.get_by_role("button", name="Replay bundled sample", exact=True).click()
            legacy.locator("#legacy-status").filter(has_text="Bundled synthetic scenario").wait_for()
            assert legacy.locator("#tree-container svg").count() == 1
            assert legacy.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            legacy.wait_for_timeout(1000)
            assert not legacy_errors, legacy_errors
            legacy.screenshot(path=str(output / "preserved-insight-mobile.png"), full_page=True)
            legacy.close()
            context.close()

            offline = browser.new_context()
            offline.route("https://**", lambda route: route.abort())
            page = offline.new_page()
            page.goto(origin + "macro_sentinel/index.html")
            page.evaluate("() => navigator.serviceWorker.ready")
            page.evaluate(
                "() => caches.open('unrelated-operator-cache').then(c => c.put('/sentinel', new Response('keep')))"
            )
            await_cache = "() => caches.keys().then(keys => keys.some(k => k.startsWith('agialpha-gallery-')))"
            page.wait_for_function(await_cache)
            # ready resolves only after successful install; reload is then controlled.
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            offline.set_offline(True)
            page.reload()
            page.locator("#demo-status").filter(has_text="Bundled sample replay").wait_for()
            page.get_by_role("button", name="Replay bundled sample offline").click()
            assert page.locator("table tbody tr").count() > 0
            assert page.evaluate("() => caches.has('unrelated-operator-cache')")
            offline.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    report = {
        "pages": records,
        "search": True,
        "mobile": True,
        "explicit_api_error": True,
        "same_origin_python_runtime": True,
        "preserved_insight_charts_tree_and_replay": True,
        "offline_reload": True,
        "unrelated_cache_preserved": True,
        "external_api_calls": 0,
    }
    (output / "gallery-catalog.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/gallery-catalog"))
    args = parser.parse_args()
    report = validate(args.site, args.output)
    count = len(report["pages"])  # type: ignore[arg-type]
    print(f"Validated {count} canonical/mirrored demo pages and offline gallery behavior")


if __name__ == "__main__":
    main()
