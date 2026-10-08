# SPDX-License-Identifier: Apache-2.0
"""Exercise the SUCCESSOR browser lifecycle, real CLI transport and offline upgrade."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from alpha_factory_v1.core.runtime.store import Journal
from scripts.validate_ascension import Handler, inspect, wait_for


def upload(page: Page, selector: str, value: dict[str, Any] | str | Path) -> None:
    """Upload actual JSON or deliberately malformed bytes through the file picker."""
    if isinstance(value, Path):
        page.locator(selector).set_input_files(str(value))
    else:
        raw = value if isinstance(value, str) else json.dumps(value)
        page.locator(selector).set_input_files(
            {"name": "evidence.json", "mimeType": "application/json", "buffer": raw.encode()}
        )


def lifecycle(page: Page) -> None:
    """Execute every bounded phase through real UI controls."""
    page.locator("#underwrite").click()
    expect(page.locator("#discover")).to_be_enabled()
    page.locator("#discover").click()
    expect(page.locator("#freeze")).to_be_enabled(timeout=60000)
    page.locator("#freeze").click()
    expect(page.locator("#evaluate")).to_be_enabled(timeout=60000)
    page.locator("#evaluate").click()
    expect(page.locator("#record")).to_be_enabled(timeout=60000)
    page.locator("#record").click()
    expect(page.locator("#renew")).to_be_enabled()
    page.locator("#renew").click()
    expect(page.locator("#status")).to_contain_text("complete", timeout=60000)
    expect(page.locator("#export")).to_be_enabled()


def validate(
    site: Path,
    output: Path,
    public_url: str | None = None,
    axe_script: Path | None = None,
    browser_executable: str | None = None,
) -> dict[str, Any]:
    """Retain evidence of actual computation and reject unearned qualification."""
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
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    errors: list[str] = []
    report: dict[str, Any] = {
        "schema": "agialpha.successor.acceptance.v1",
        "origin": public_url or "local project subpath",
        "commit": commit,
        "version": None,
        "passed": False,
        "checks": [],
        "browser_errors": errors,
        "accessibility": [],
        "browser_executable_override": browser_executable is not None,
        "platform": sys.platform,
        "python": sys.version.split()[0],
    }
    try:
        with sync_playwright() as playwright, tempfile.TemporaryDirectory() as tmp:
            browser = playwright.chromium.launch(executable_path=browser_executable)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "successor/", wait_until="networkidle")
            report["version"] = page.locator('meta[name="application-version"]').get_attribute("content")
            wait_for(page, "navigator.serviceWorker.controller !== null")
            # Two actual shipped-worker registrations exercise update/activation across pinned browser versions.
            # The query URL and old-cache sentinel are explicit test fixtures, not historical execution evidence.
            inspect(
                page,
                "navigator.serviceWorker.register(new URL("
                "'../service-worker.js?successor-previous-fixture=1',location.href),"
                "{scope:new URL('./',location.href).pathname}).then(()=>true)",
            )
            wait_for(page, "navigator.serviceWorker.controller.scriptURL.includes('successor-previous-fixture=1')")
            inspect(
                page,
                "Promise.all([caches.open('agialpha-gallery-successor-upgrade-fixture'),"
                "caches.open('successor-unrelated-user-cache')]).then(()=>true)",
            )
            wait_for(page, "caches.keys().then(k=>k.includes('agialpha-gallery-successor-upgrade-fixture'))")
            inspect(
                page,
                "navigator.serviceWorker.register(new URL('../service-worker.js',location.href),"
                "{scope:new URL('./',location.href).pathname}).then(()=>true)",
            )
            wait_for(page, "!navigator.serviceWorker.controller.scriptURL.includes('successor-previous-fixture=1')")
            wait_for(
                page,
                "caches.keys().then(k=>!k.includes('agialpha-gallery-successor-upgrade-fixture') && "
                "k.some(n=>n.startsWith('agialpha-gallery-')) && k.includes('successor-unrelated-user-cache'))",
            )
            report["checks"].append("cache-upgrade")
            page.reload(wait_until="networkidle")
            expect(page.locator("#status")).to_contain_text("Choose")
            page.locator("#events").fill("128")
            page.locator("#candidates").fill("4")
            page.locator("#trials").fill("1")
            lifecycle(page)
            with page.expect_download() as exported:
                page.locator("#export").click()
            browser_evidence = output / "browser-evidence.json"
            exported.value.save_as(browser_evidence)
            evidence = json.loads(browser_evidence.read_text())["evidence"]
            assert evidence["scope"] == "browser-rehearsal"
            assert evidence["evaluation"]["correctness"] is True
            assert evidence["evaluation"]["institutional_verdict"] == "HOLD"
            assert len(evidence["discovery"]["attempts"]) == 4
            assert evidence["renewal"]["authority"] == []
            assert evidence["renewal"]["active_proof"] == []
            report["checks"].append("lifecycle")
            page.screenshot(path=str(output / "successor-desktop.png"), full_page=True)
            if axe_script:
                inspect(page, axe_script.read_text() + ";true")
                audit = inspect(
                    page,
                    "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
                    ".then(r=>({violations:r.violations}))",
                )
                report["accessibility"].append(audit)
                assert not audit["violations"], audit["violations"]
            with page.expect_download() as downloaded:
                page.locator("#request-export").click()
            request_path = output / "request.json"
            downloaded.value.save_as(request_path)
            result_path = Path(tmp) / "native-result.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.core.runtime.cli",
                    "--home",
                    str(Path(tmp) / "native-home"),
                    "successor-run",
                    str(request_path.resolve()),
                    "--output",
                    str(result_path.resolve()),
                ],
                check=True,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=180,
            )
            (output / "native-result.json").write_bytes(result_path.read_bytes())
            upload(page, "#result-import", result_path)
            expect(page.locator("#native-status")).to_contain_text("Original request and evidence digests match")
            expect(page.locator("#native-status")).to_contain_text("Authenticity unverified")
            trusted_key = Journal(Path(tmp) / "native-home").public
            page.locator("#trust-key").fill(trusted_key)
            page.locator("#trust-key").dispatch_event("change")
            expect(page.locator("#native-status")).to_contain_text("separately supplied key; local signer only")
            page.locator("#trust-key").fill("")
            page.locator("#trust-key").dispatch_event("change")
            expect(page.locator("#native-status")).to_contain_text("Authenticity unverified")
            corrupt = json.loads(result_path.read_text())
            corrupt["evidence_hash"] = "0" * 64
            upload(page, "#result-import", corrupt)
            expect(page.locator("#status")).to_contain_text("digest mismatch")
            upload(page, "#result-import", result_path)
            expect(page.locator("#native-status")).to_contain_text("Original request and evidence digests match")
            report["checks"].append("native-roundtrip")
            upload(page, "#request-import", '{"schema_version":1,"schema_version":1}')
            expect(page.locator("#status")).to_contain_text("Duplicate JSON key")
            upload(page, "#request-import", "[" * 34 + "0" + "]" * 34)
            expect(page.locator("#status")).to_contain_text("complexity")
            report["checks"].append("malformed-import")
            page.locator("#seed").fill("91")
            expect(page.locator("#status")).to_contain_text("stale")
            expect(page.locator("#export")).to_be_disabled()
            expect(page.locator("#evaluate")).to_be_disabled()
            report["checks"].append("changed-input-stale")
            page.locator("#events").fill("20000")
            page.locator("#candidates").fill("8")
            page.locator("#underwrite").click()
            # Cancel through the real button after one measured candidate. An observer avoids racing
            # browser actionability/scrolling against fast bounded work; no production delay is added.
            inspect(
                page,
                "(()=>{const progress=document.querySelector('#progress');"
                "const observer=new MutationObserver(()=>{if(progress.value>=1){"
                "observer.disconnect();document.querySelector('#cancel').click();}});"
                "observer.observe(progress,{attributes:true,attributeFilter:['value']});return true;})()",
            )
            page.locator("#discover").click()
            expect(page.locator("#status")).to_contain_text("cancelled")
            expect(page.locator("#discover")).to_be_enabled()
            expect(page.locator("#freeze")).to_be_disabled()
            page.locator("#events").fill("128")
            page.locator("#underwrite").click()
            page.locator("#discover").click()
            expect(page.locator("#freeze")).to_be_enabled(timeout=60000)
            report["checks"].append("cancel-retry")
            page.locator("#language").select_option("fr")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#status")).to_contain_text("périmés")
            expect(page.locator("#underwrite")).to_have_text("Consigner l’engagement borné")
            page.locator("#underwrite").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#discover")).to_be_enabled()
            report["checks"].append("bilingual")
            page.set_viewport_size({"width": 375, "height": 812})
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "successor-mobile-fr.png"), full_page=True)
            if axe_script:
                audit = inspect(
                    page,
                    "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
                    ".then(r=>({violations:r.violations}))",
                )
                report["accessibility"].append(audit)
                assert not audit["violations"], audit["violations"]
            report["checks"].append("narrow-mobile")
            page.locator("#language").select_option("en")
            with page.expect_download():
                page.locator("#request-export").click()
            page.goto(origin + "alpha_factory_v1/demos/successor/", wait_until="networkidle")
            expect(page.locator("#underwrite")).to_be_visible()
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth")
            report["checks"].append("mirrored-route")
            page.goto(origin + "successor/", wait_until="networkidle")
            page.locator("#request-export").click()
            context.set_offline(True)
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#underwrite")).to_be_visible()
            lifecycle(page)
            report["checks"].append("offline-cached")
            context.set_offline(False)
            assert not errors, errors
            report["passed"] = True
            browser.close()
    except subprocess.CalledProcessError as exc:
        report["native_failure"] = {"returncode": exc.returncode, "stdout": exc.stdout, "stderr": exc.stderr}
        report["failure"] = "Native request execution failed"
        raise
    except Exception as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (output / "successor.json").write_text(json.dumps(report, indent=2) + "\n")
        if server:
            server.shutdown()
    return report


def main() -> None:
    """Run local or public acceptance without weakening the shipped CSP."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, default=Path("artifacts/successor-browser"))
    parser.add_argument("--axe-script", type=Path)
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script, args.browser_executable), indent=2))


if __name__ == "__main__":
    main()
