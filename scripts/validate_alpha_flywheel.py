# SPDX-License-Identifier: Apache-2.0
"""Verify exact Flywheel source bytes and its public, simulated browser journey."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_PAGE_BYTES = 2_000_000
MAX_MANIFEST_BYTES = 100_000
HASH = re.compile(r"[0-9a-f]{64}\Z")
CANONICAL_SOURCES = (
    "examples/alpha-flywheel/engine.mjs",
    "examples/alpha-flywheel/README.md",
    "examples/successor-alpha/project.mjs",
    "examples/successor-alpha/engine.mjs",
    "docs/assets/successor/engine.mjs",
    "scripts/generate_alpha_flywheel.py",
    "scripts/templates/alpha-flywheel/index.html",
    "scripts/templates/alpha-flywheel/app.js",
    "scripts/templates/alpha-flywheel/general-evidence.json",
    "scripts/templates/alpha-flywheel/specialist-evidence.json",
    "scripts/templates/alpha-flywheel/enterprise-evidence.json",
    "scripts/templates/alpha-flywheel/discovery-evidence.json",
    "scripts/templates/alpha-flywheel/opportunity-evidence.json",
    "scripts/templates/alpha-flywheel/style.css",
    "LICENSE",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def flagship_url(value: str) -> str:
    """Resolve only a credential-free HTTPS public route."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Public qualification requires HTTPS without credentials, query or fragment")
    if parsed.path.endswith("/flywheel/index.html"):
        return value.removesuffix("index.html")
    if parsed.path.endswith("/flywheel/"):
        return value
    if parsed.path.endswith("/flywheel"):
        return value + "/"
    return urljoin(value.rstrip("/") + "/", "flywheel/")


def manifest_data(raw: bytes) -> dict[str, Any]:
    """Reject malformed, escaping or unbound source inventories."""
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Flywheel manifest exceeds its byte budget")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != {"schema", "sourceHash", "sources", "pageSha256"}:
        raise ValueError("Unsupported Flywheel source manifest")
    if value["schema"] != "alpha-flywheel-source/v1":
        raise ValueError("Unsupported Flywheel source manifest")
    if not HASH.fullmatch(str(value["sourceHash"])) or not HASH.fullmatch(str(value["pageSha256"])):
        raise ValueError("Flywheel manifest lacks exact identities")
    sources = value["sources"]
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Flywheel source inventory is empty")
    for name, digest in sources.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("Invalid Flywheel source entry")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or str(path) != name:
            raise ValueError("Flywheel source paths must remain inside the repository")
    expected = sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode())
    if expected != value["sourceHash"]:
        raise ValueError("Flywheel source inventory hash differs")
    return value


class InlineBlocks(HTMLParser):
    """Inspect HTML elements without interpreting inert JavaScript strings as markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.policy: str | None = None
        self.blocks: list[tuple[str, dict[str, str | None], str]] = []
        self.active: tuple[str, dict[str, str | None]] | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "content-security-policy":
            self.policy = attributes.get("content")
        if tag in {"script", "style"}:
            self.active = tag, attributes
            self.text = []

    def handle_data(self, data: str) -> None:
        if self.active:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.active and self.active[0] == tag:
            self.blocks.append((*self.active, "".join(self.text)))
            self.active = None


def verify_csp(page: bytes) -> None:
    """Require every executable inline block to match the document's CSP hashes."""
    document = InlineBlocks()
    document.feed(page.decode("utf-8"))
    if document.policy is None:
        raise ValueError("Flywheel CSP is missing")
    directives = {
        row.strip().split(" ", 1)[0]: row.strip().split(" ", 1)[1]
        for row in document.policy.split(";")
        if " " in row.strip()
    }
    if directives.get("connect-src") != "'none'" or directives.get("form-action") != "'none'":
        raise ValueError("Flywheel public page must not enable external operation")
    for tag, directive in (("script", "script-src"), ("style", "style-src")):
        blocks = [(attrs, code) for found_tag, attrs, code in document.blocks if found_tag == tag]
        if not blocks:
            raise ValueError("Flywheel executable blocks are missing")
        for attributes, block in blocks:
            if "src" in attributes or "href" in attributes:
                raise ValueError("Flywheel bundle must be self-contained")
            if tag == "script" and attributes.get("type") == "application/json":
                continue
            digest = base64.b64encode(hashlib.sha256(block.encode()).digest()).decode()
            if directives.get(directive) != "'sha256-" + digest + "'":
                raise ValueError("Flywheel inline block differs from its CSP hash")


def verify_packaged(site: Path, source_root: Path = ROOT) -> dict[str, Any]:
    """Bind the packaged document to its exact canonical source closure."""
    destination = site.resolve() / "flywheel"
    page = (destination / "index.html").read_bytes()
    raw_manifest = (destination / "sources.json").read_bytes()
    manifest = manifest_data(raw_manifest)
    if set(manifest["sources"]) != set(CANONICAL_SOURCES):
        raise ValueError("Flywheel manifest must contain the complete canonical source closure")
    if len(page) > MAX_PAGE_BYTES or sha256(page) != manifest["pageSha256"]:
        raise ValueError("Packaged Flywheel differs from its source manifest")
    root = source_root.resolve()
    for name, digest in manifest["sources"].items():
        path = root / name
        if any((root / Path(*Path(name).parts[:index])).is_symlink() for index in range(1, len(Path(name).parts) + 1)):
            raise ValueError("Flywheel source cannot be a symlink")
        if not path.resolve().is_relative_to(root) or not path.is_file() or sha256(path.read_bytes()) != digest:
            raise ValueError("Flywheel source identity differs from checkout: " + name)
    verify_csp(page)
    from scripts.generate_alpha_flywheel import build

    with tempfile.TemporaryDirectory(prefix="alpha-flywheel-qualification-") as directory:
        temporary_root = Path(directory)
        for name in CANONICAL_SOURCES:
            destination = temporary_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, destination)
        build(temporary_root)
        rebuilt = temporary_root / "docs/flywheel"
        if (rebuilt / "index.html").read_bytes() != page or (rebuilt / "sources.json").read_bytes() != raw_manifest:
            raise ValueError("Packaged Flywheel differs from a trusted canonical rebuild")
    return {
        "page": page,
        "manifest": raw_manifest,
        "pageSha256": sha256(page),
        "manifestSha256": sha256(raw_manifest),
        "sourceHash": manifest["sourceHash"],
        "sourcesChecked": len(manifest["sources"]),
    }


def verify_received(page: bytes, manifest: bytes, expected: dict[str, Any]) -> None:
    """A self-consistent historical page cannot qualify the current release."""
    observed = manifest_data(manifest)
    if len(page) > MAX_PAGE_BYTES or sha256(page) != observed["pageSha256"]:
        raise ValueError("Public Flywheel differs from its advertised identity")
    if page != expected["page"] or manifest != expected["manifest"]:
        raise ValueError("Public Flywheel differs from the exact packaged release bytes")
    verify_csp(page)


def verify_public(url: str, expected: dict[str, Any]) -> None:
    """Read certificate-verified HTTPS bodies without accepting redirects or stale editions."""
    received = []
    for destination, limit in ((url, MAX_PAGE_BYTES), (urljoin(url, "sources.json"), MAX_MANIFEST_BYTES)):
        with urlopen(Request(destination, headers={"Cache-Control": "no-cache"}), timeout=60) as response:
            if response.status != 200 or response.geturl() != destination:
                raise ValueError("Public Flywheel response is not the exact requested route")
            body = response.read(limit + 1)
            if len(body) > limit:
                raise ValueError("Public Flywheel response exceeds its byte budget")
            received.append(body)
    verify_received(received[0], received[1], expected)


def browser_acceptance(
    entry: str,
    output: Path,
    *,
    axe_script: Path | None = None,
    browser_executable: Path | None = None,
    alpha_entry: str | None = None,
    expected_page_sha256: str | None = None,
) -> dict[str, Any]:
    """Exercise real browser calculations and downloads; no commercial or live authority claim."""
    from playwright.sync_api import expect, sync_playwright

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    checks: list[str] = []
    errors: list[str] = []
    requests: list[str] = []
    report: dict[str, Any] = {
        "passed": False,
        "origin": entry,
        "checks": checks,
        "errors": errors,
        "scope": "Public simulation and project preparation only",
        "accessibility": [],
    }
    try:
        with sync_playwright() as playwright:
            launch = {"executable_path": str(browser_executable)} if browser_executable else {}
            browser = playwright.chromium.launch(**launch)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1050}, reduced_motion="reduce", accept_downloads=True
            )
            context.add_init_script(
                "document.addEventListener('securitypolicyviolation',e=>console.error('CSP:'+e.violatedDirective))"
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            if expected_page_sha256 and entry.startswith("https:"):

                def check_document(response: Any) -> None:
                    if (
                        response.request.resource_type == "document"
                        and urlsplit(response.url).path == urlsplit(entry).path
                    ):
                        if response.status != 200 or sha256(response.body()) != expected_page_sha256:
                            errors.append("Browser received a different public Flywheel document")

                page.on("response", check_document)
            page.goto(entry, wait_until="load")
            page.on(
                "request", lambda request: requests.append(request.url) if request.resource_type != "document" else None
            )
            expect(page.locator("#intro-state")).to_be_visible()
            expect(page.locator("#results")).to_be_hidden()
            page.locator("#explore-button").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#results")).to_be_visible()
            expect(page.locator("#explore-title")).to_be_focused()
            expect(page.locator("#mission-title")).not_to_be_empty()
            expect(page.locator("#sample-schedule")).to_be_visible()
            expect(page.locator("#sample-schedule tr")).not_to_have_count(0)
            expect(page.locator("#economics-list")).to_contain_text(re.compile("profit", re.IGNORECASE))
            expect(page.locator("#quality-metrics")).not_to_be_empty()
            expect(page.locator("#execute")).to_contain_text("unqualified")
            baseline = json.loads(page.locator("#result-receipt").text_content() or "{}")
            assert baseline["input"]["preset"] == "baseline"
            page.locator("#replay").click()
            assert json.loads(page.locator("#result-receipt").text_content() or "{}") == baseline
            checks += [
                "first-keyboard-interaction-complete-example",
                "finite-engineering-sample",
                "deterministic-replay",
            ]
            page.locator("#policy").select_option("beta")
            beta = json.loads(page.locator("#result-receipt").text_content() or "{}")
            assert beta["input"]["policy"] == "beta"
            assert beta["summary"]["profit"] > 0
            assert beta["summary"]["costsB"] == beta["summary"]["costsC"] == 0
            assert beta["authority"] == [] and beta["modelsExecuted"] == []
            expect(page.locator("#retention-title")).not_to_be_empty()
            checks.append("profitable-beta-only-without-required-retention")
            for preset in ("stress", "frontier", "baseline"):
                page.locator("#preset").select_option(preset)
                assert json.loads(page.locator("#result-receipt").text_content() or "{}")["input"]["preset"] == preset
            checks.append("demand-quality-and-model-change-scenarios")
            before_error = page.locator("#result-receipt").text_content()
            page.locator("#seed").fill("0")
            page.locator("#replay").click()
            expect(page.locator("#input-error")).to_be_visible()
            assert page.locator("#result-receipt").text_content() == before_error
            page.locator("#seed").fill("42")
            page.locator("#replay").click()
            expect(page.locator("#input-error")).to_be_hidden()
            checks.append("invalid-input-preserves-result-and-recovers")
            page.locator("#evidence").evaluate("element=>element.open=true")
            with page.expect_download() as pending:
                page.locator("#export-replay").click()
            replay_file = output / "flywheel-replay.json"
            pending.value.save_as(replay_file)
            replay = json.loads(replay_file.read_text())
            assert replay["schema"] == "alpha-flywheel.replay/v1"
            page.locator("#preset").select_option("stress")
            page.locator("#import-replay").set_input_files(str(replay_file))
            expect(page.locator("#preset")).to_have_value("baseline")
            assert json.loads(page.locator("#result-receipt").text_content() or "{}")["input"] == replay["input"]
            good_receipt = page.locator("#result-receipt").text_content()
            page.locator("#import-replay").set_input_files(
                {"name": "bad.json", "mimeType": "application/json", "buffer": b'{"schema":"untrusted"}'}
            )
            expect(page.locator("#input-error")).to_be_visible()
            assert page.locator("#result-receipt").text_content() == good_receipt
            checks += ["actual-replay-download-and-recovery", "invalid-replay-does-not-import-results"]
            manual_replay = {
                **replay,
                "language": "en",
                "input": {"preset": "baseline", "policy": "beta", "seed": 42, "price": 10000},
            }
            page.locator("#import-replay").set_input_files(
                {
                    "name": "manual-price.json",
                    "mimeType": "application/json",
                    "buffer": json.dumps(manual_replay).encode(),
                }
            )
            expect(page.locator("#result-receipt")).to_contain_text(re.compile(r'"price"\s*:\s*10000'))
            manual_receipt = json.loads(page.locator("#result-receipt").text_content() or "{}")
            assert manual_receipt["summary"]["offeredPrice"] == 10000
            page.locator("#replay").click()
            assert (
                json.loads(page.locator("#result-receipt").text_content() or "{}") == manual_receipt
            ), "Repeating an imported replay must preserve its explicit price and economics"
            expect(page.locator("#price-mode")).to_be_visible()
            for preset in ("stress", "frontier", "baseline"):
                page.locator("#preset").select_option(preset)
                repriced = json.loads(page.locator("#result-receipt").text_content() or "{}")
                assert repriced["input"]["price"] == repriced["summary"]["offeredPrice"] == 10000
            assert json.loads(page.locator("#result-receipt").text_content() or "{}") == manual_receipt
            page.locator("#lang-fr").click()
            assert json.loads(page.locator("#result-receipt").text_content() or "{}") == manual_receipt
            page.reload(wait_until="load")
            expect(page.locator("#results")).to_be_visible()
            assert json.loads(page.locator("#result-receipt").text_content() or "{}") == manual_receipt
            shared_url = page.url
            assert parse_qs(urlsplit(shared_url).query).get("price") == ["10000"]
            shared_context = browser.new_context(accept_downloads=True, reduced_motion="reduce")
            shared_page = shared_context.new_page()
            shared_page.on("pageerror", lambda error: errors.append(str(error)))
            shared_page.on(
                "request", lambda request: requests.append(request.url) if request.resource_type != "document" else None
            )
            if expected_page_sha256 and entry.startswith("https:"):
                shared_page.on("response", check_document)
            shared_page.goto(shared_url, wait_until="load")
            expect(shared_page.locator("#results")).to_be_visible()
            assert json.loads(shared_page.locator("#result-receipt").text_content() or "{}") == manual_receipt
            shared_page.locator("#evidence").evaluate("element=>element.open=true")
            with shared_page.expect_download() as manual_download:
                shared_page.locator("#export-replay").click()
            manual_file = output / "flywheel-manual-price-replay.json"
            manual_download.value.save_as(manual_file)
            exported_manual = json.loads(manual_file.read_text())
            assert exported_manual["input"] == manual_replay["input"] and exported_manual["language"] == "fr"
            assert manual_receipt["authority"] == [] and manual_receipt["modelsExecuted"] == []
            shared_page.locator("#optimize-price").click()
            searched_receipt = json.loads(shared_page.locator("#result-receipt").text_content() or "{}")
            assert searched_receipt["input"]["price"] == 0
            expect(shared_page.locator("#price-mode")).to_be_hidden()
            checks.append("manual-price-changes-only-after-explicit-return-to-search")
            share_parts = urlsplit(shared_url)
            share_query = parse_qs(share_parts.query, keep_blank_values=True)
            for invalid_price in ("", "NaN", "10000.5", "999", "24001"):
                invalid_url = share_parts._replace(
                    query=urlencode({**share_query, "price": [invalid_price]}, doseq=True)
                ).geturl()
                shared_page.goto(invalid_url, wait_until="load")
                expect(shared_page.locator("#input-error")).to_contain_text("prix demandé")
                expect(shared_page.locator("#results")).to_be_hidden()
                shared_page.locator("#lang-en").click()
                expect(shared_page.locator("#input-error")).to_contain_text("requested price")
                shared_page.locator("#replay").click()
                expect(shared_page.locator("#results")).to_be_hidden()
                shared_page.locator("#optimize-price").click()
                expect(shared_page.locator("#results")).to_be_visible()
                assert json.loads(shared_page.locator("#result-receipt").text_content() or "{}")["input"]["price"] == 0
            checks.append("invalid-price-links-refuse-until-explicit-reset")
            shared_context.close()
            report["manualPriceReplay"] = {
                "price": 10000,
                "profit": manual_receipt["summary"]["profit"],
                "input": exported_manual["input"],
            }
            checks.append("explicit-price-replay-survives-repeat-language-refresh-share-and-export")
            with page.expect_download() as project_download:
                page.locator("#export-project").click()
            project_file = output / "flywheel-alpha-project.json"
            project_download.value.save_as(project_file)
            project_data = json.loads(project_file.read_text())
            assert project_data["schema"] == "successor-alpha-project/v1"
            assert project_data["authority"] == "none" and not project_data["cycles"]
            assert project_data["opportunities"][0]["state"] == "hypothesis"
            if alpha_entry:
                alpha = context.new_page()
                alpha.goto(alpha_entry, wait_until="load")
                alpha.locator("#restore-project").set_input_files(str(project_file))
                expect(alpha.locator("#project-name")).to_have_value(project_data["name"])
                expect(alpha.locator("#restored-note")).to_contain_text(project_data["name"])
                alpha.close()
                checks.append("actual-existing-alpha-workspace-restoration")
            checks.append("existing-alpha-project-codec-with-hypothesis-only")
            for language in ("en", "fr"):
                page.locator("#lang-" + language).click()
                expect(page.locator("#general-case option")).to_have_count(12)
                page.locator("#general-case").select_option("7311")
                expect(page.locator("#general-metrics")).to_contain_text("46656")
                expect(page.locator("#general-alpha-decision")).to_contain_text(
                    "do not admit" if language == "en" else "ne pas admettre"
                )
                with page.expect_download() as evidence_download:
                    page.locator("#general-export").click()
                evidence_file = output / ("general-execution-" + language + ".json")
                evidence_download.value.save_as(str(evidence_file))
                general = json.loads(evidence_file.read_bytes())
                assert general["summary"]["actual_provider_calls"] == 0
                assert general["summary"]["actual_tool_invocations"] == 12
                assert general["summary"]["candidate_decision"] == "do not admit"
                assert all(not item["live_network_qualified"] for item in general["cases"])
            checks.append("recorded-general-execution-evidence-en-fr-no-authority")
            for language in ("en", "fr"):
                page.locator("#lang-" + language).click()
                expect(page.locator("#specialist-case option")).to_have_count(12)
                page.locator("#specialist-case").select_option("fresh-contention-2505")
                expect(page.locator("#specialist-artifacts")).to_contain_text("largest-demand")
                expect(page.locator("#specialist-states")).to_contain_text(
                    "DO NOT ADMIT" if language == "en" else "NE PAS ADMETTRE"
                )
                with page.expect_download() as relay_download:
                    page.locator("#specialist-export").click()
                relay_file = output / ("specialist-relay-" + language + ".json")
                relay_download.value.save_as(str(relay_file))
                relay = json.loads(relay_file.read_bytes())
                assert relay["summary"]["independently_accepted_v2"] == 12
                assert relay["summary"]["actual_admission"] == "do not admit"
                assert not relay["summary"]["live_qualified"] and not relay["summary"]["net_alpha_positive"]
            checks.append("specialist-artifact-change-transfer-and-distinct-states-en-fr-no-authority")
            for language in ("en", "fr"):
                page.locator("#lang-" + language).click()
                expect(page.locator("#enterprise-offering option")).to_have_count(2)
                page.locator("#enterprise-offering").select_option("resilient-placement")
                expect(page.locator("#enterprise-stages")).to_contain_text("commercially-assessed")
                expect(page.locator("#enterprise-states")).to_contain_text("USD 0")
                expect(page.locator("#enterprise-alternatives")).to_contain_text("µUSD")
                page.locator("#enterprise-offering").select_option("disruption-aware-rollout")
                expect(page.locator("#enterprise-stages")).to_contain_text("hypothesis")
                with page.expect_download() as enterprise_download:
                    page.locator("#enterprise-export").click()
                enterprise_file = output / ("enterprise-evidence-" + language + ".json")
                enterprise_download.value.save_as(str(enterprise_file))
                enterprise = json.loads(enterprise_file.read_bytes())
                assert enterprise["summary"]["next_selected_action"] == "hold"
                assert enterprise["summary"]["actual_admission"] == "rejected"
                assert not enterprise["summary"]["live_qualified"]
            checks.append("enterprise-offering-decision-qualification-en-fr-export-no-authority")
            for width, language in ((1440, "en"), (1440, "fr"), (390, "en"), (390, "fr"), (320, "en"), (320, "fr")):
                page.locator("#lang-" + language).click()
                expect(page.locator("html")).to_have_attribute("lang", language)
                page.set_viewport_size({"width": width, "height": 1050})
                assert page.evaluate(
                    "document.documentElement.scrollWidth<=innerWidth+1"
                ), f"Horizontal overflow: {width}"
                if axe_script:
                    page.evaluate(axe_script.read_text() + ";void 0")
                    audit = page.evaluate(
                        "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}})"
                    )
                    report["accessibility"].append(
                        {"width": width, "language": language, "violations": audit["violations"]}
                    )
                    assert not audit["violations"], audit["violations"]
                page.screenshot(path=str(output / f"flywheel-{width}-{language}.png"), full_page=True)
            checks.append("english-french-phone-and-reduced-motion")
            if axe_script:
                checks.append("axe-no-violations")
            page.locator("#lang-fr").click()
            page.locator("#seed").fill("0")
            page.locator("#replay").click()
            expect(page.locator("#input-error")).to_be_visible()
            assert not re.search(r"\bInvalid\b|\bseed\b", page.locator("#input-error").inner_text())
            page.locator("#seed").fill("42")
            page.locator("#replay").click()
            restored_receipt = page.locator("#result-receipt").text_content()
            page.reload(wait_until="load")
            expect(page.locator("#results")).to_be_visible()
            assert page.locator("#result-receipt").text_content() == restored_receipt
            checks.append("refresh-recovers-conditions-and-recomputes")
            if entry.startswith("file:"):
                context.set_offline(True)
                page.goto(entry, wait_until="load")
                page.locator("#start-example").click()
                expect(page.locator("#results")).to_be_visible()
                checks.append("self-contained-offline-reopen")
            else:
                context.set_offline(True)
                page.locator("#replay").click()
                expect(page.locator("#results")).to_be_visible()
                checks.append("loaded-public-page-computes-offline")
            assert not requests, requests
            assert not errors, errors
            checks.append("no-network-spending-model-or-identity-operation")
            no_script = browser.new_context(java_script_enabled=False)
            fallback = no_script.new_page()
            fallback.goto(entry, wait_until="load")
            expect(fallback.locator("noscript")).to_be_visible()
            no_script.close()
            checks.append("no-javascript-guidance")
            report["passed"] = True
            report["downloads"] = {
                path.name: sha256(path.read_bytes()) for path in (replay_file, manual_file, project_file)
            }
            browser.close()
    finally:
        (output / "browser.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "docs")
    parser.add_argument("--output", type=Path, default=Path("evidence/alpha-flywheel"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    parser.add_argument("--browser-executable", type=Path)
    args = parser.parse_args()
    expected = verify_packaged(args.site)
    entry = flagship_url(args.url) if args.url else (args.site.resolve() / "flywheel/index.html").as_uri()
    if args.url:
        verify_public(entry, expected)
    alpha_entry = (
        urljoin(entry, "../successor/alpha/")
        if args.url
        else (args.site.resolve() / "successor/alpha/index.html").as_uri()
    )
    executable = args.browser_executable or (
        Path(os.environ["FLYWHEEL_BROWSER_EXECUTABLE"]) if "FLYWHEEL_BROWSER_EXECUTABLE" in os.environ else None
    )
    report = {key: value for key, value in expected.items() if key not in {"page", "manifest"}}
    report["publicBytesVerified"] = bool(args.url)
    report["journey"] = browser_acceptance(
        entry,
        args.output / "browser",
        axe_script=args.axe_script,
        browser_executable=executable,
        alpha_entry=alpha_entry,
        expected_page_sha256=expected["pageSha256"],
    )
    report["passed"] = True
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps({"passed": True, "pageSha256": expected["pageSha256"], "checks": len(report["journey"]["checks"])})
    )


if __name__ == "__main__":
    main()
