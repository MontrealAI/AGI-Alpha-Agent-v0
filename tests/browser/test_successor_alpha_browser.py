# SPDX-License-Identifier: Apache-2.0
"""Exercise the self-contained Alpha flagship, its actual downloads and offline reuse."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
URL = (ROOT / "docs/successor/alpha/index.html").as_uri()
CONTRACTS = {
    "AscensionAccess": "0x9ee41df6d076fa4f89b102b76def1c503a1e7c3a",
    "NovaSeed": "0x31bd0736dcd55da2f9a2bb586c8a98695f86f19e",
    "AscensionRiskOracle": "0x198fc6ebee21c6a0b34e4d055afd6d811aa6de58",
    "AscensionJobMarket": "0xc1d3d7fb064c23c46c4eb20d24ab6ea650ff0cee",
    "AscensionMark": "0x6d5323b2609e36fdc4db3b2501b7bcf0e131033c",
}
expect.set_options(timeout=30_000)


def download(page: Page, selector: str) -> bytes:
    with page.expect_download() as pending:
        page.locator(selector).click()
    return Path(pending.value.path()).read_bytes()


def upload(page: Page, selector: str, value: bytes, name: str = "project.json") -> None:
    page.locator(selector).set_input_files({"name": name, "mimeType": "application/json", "buffer": value})


def rows(raw: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(raw.decode("utf-8"))))


def safe_cell(value: Any) -> str:
    rendered = str(value)
    if rendered.startswith(("\t", "\r", "\n")) or rendered.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + rendered
    return rendered


def expected_outputs(mission: dict[str, Any]) -> dict[str, list[list[str]]]:
    left, right = mission["left"], mission["right"]
    pairs = [
        (a, b)
        for a, ra in enumerate(left["rows"])
        for b, rb in enumerate(right["rows"])
        if ra[left["keyIndex"]] == rb[right["keyIndex"]]
    ]
    joined = [["left." + h for h in left["headers"]] + ["right." + h for h in right["headers"]]]
    joined.extend([safe_cell(x) for x in left["rows"][a] + right["rows"][b]] for a, b in pairs)
    unmatched_left = [left["headers"]] + [
        [safe_cell(x) for x in row] for a, row in enumerate(left["rows"]) if not any(i == a for i, _ in pairs)
    ]
    unmatched_right = [right["headers"]] + [
        [safe_cell(x) for x in row] for b, row in enumerate(right["rows"]) if not any(j == b for _, j in pairs)
    ]
    conflicts = [["key", "left_data_row", "right_data_row", "field", "left_value", "right_value"]]
    for a, b in pairs:
        for li, header in enumerate(left["headers"]):
            if li == left["keyIndex"] or header not in right["headers"]:
                continue
            ri = right["headers"].index(header)
            if ri != right["keyIndex"] and left["rows"][a][li] != right["rows"][b][ri]:
                conflicts.append(
                    [
                        safe_cell(x)
                        for x in [
                            left["rows"][a][left["keyIndex"]],
                            a + 1,
                            b + 1,
                            header,
                            left["rows"][a][li],
                            right["rows"][b][ri],
                        ]
                    ]
                )
    return {
        "download-joined": joined,
        "download-unmatched-left": unmatched_left,
        "download-unmatched-right": unmatched_right,
        "download-conflicts": conflicts,
    }


def context_page(
    browser: Browser, errors: list[str], external: list[str], width: int = 1440
) -> tuple[BrowserContext, Page]:
    context = browser.new_context(
        viewport={"width": width, "height": 1050}, accept_downloads=True, reduced_motion="reduce"
    )
    context.add_init_script(
        "document.addEventListener('securitypolicyviolation', e => console.error('ALPHA_CSP_VIOLATION:' + "
        "JSON.stringify({directive:e.violatedDirective, blocked:e.blockedURI})))"
    )
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console",
        lambda message: errors.append(message.text) if message.text.startswith("ALPHA_CSP_VIOLATION:") else None,
    )
    page.on(
        "request",
        lambda request: external.append(request.url) if request.url.startswith(("http://", "https://")) else None,
    )
    page.goto(URL)
    expect(page.locator("#hero-start")).to_be_enabled()
    return context, page


def verify_comparison(page: Page, result: dict[str, Any]) -> None:
    page.locator(".comparison-detail > summary").click()
    expect(page.locator("#comparison-table > tr")).to_have_count(4)
    for index, strategy in enumerate(result["strategies"]):
        cells = page.locator("#comparison-table > tr").nth(index).locator("td")
        assert cells.count() == 6
        metrics = strategy["metrics"]
        for column, name in [(1, "logicalOperations"), (2, "indexedRows"), (3, "sortedRows")]:
            assert int(cells.nth(column).inner_text().replace(",", "")) == metrics[name]
        expect(cells.nth(5)).to_have_text("Exact match")
    assert "independent" in page.locator(".comparison-detail").inner_text().lower()


def accessibility(page: Page) -> None:
    axe = os.environ.get("AXE_SCRIPT")
    if not axe:
        return
    page.evaluate(Path(axe).read_text(encoding="utf-8"))
    report = page.evaluate(
        "async () => await axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21aa']}})"
    )
    assert not report["violations"], json.dumps(report["violations"], indent=2)


def first_use(browser: Browser, output: Path, errors: list[str], external: list[str]) -> bytes:
    context, page = context_page(browser, errors, external)
    english_alt = page.locator(".institution img").get_attribute("alt")
    assert english_alt and "Alpha" in english_alt
    page.keyboard.press("Tab")
    expect(page.locator(".skip")).to_be_focused()
    page.keyboard.press("Enter")
    assert page.url.endswith("#mission")
    page.keyboard.press("Tab")
    expect(page.locator("#mode-example")).to_be_focused()
    page.screenshot(path=str(output / "01-first-use.png"), full_page=True)
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    expect(page.locator("#evidence-title")).to_be_focused()
    csv_downloads = {
        name: rows(download(page, "#" + name))
        for name in ("download-joined", "download-unmatched-left", "download-unmatched-right", "download-conflicts")
    }
    page.locator("#keep-capability").click()
    expect(page.locator("#successor-title")).to_be_focused()
    page.locator("#project-name").fill("My catalog advantage")
    project_raw = download(page, "#download-project")
    project = json.loads(project_raw)
    assert project["name"] == "My catalog advantage"
    assert project["authority"] == "none" and len(project["cycles"]) == 1
    cycle = project["cycles"][0]
    assert csv_downloads == expected_outputs(cycle["mission"])
    page.locator("#back-evidence").click()
    verify_comparison(page, cycle["result"])
    expect(page.locator("#comparison-bars > div")).to_have_count(4)
    accessibility(page)
    page.screenshot(path=str(output / "02-useful-result.png"), full_page=True)
    page.locator("#keep-capability").click()
    tool = download(page, "#download-tool").decode()
    assert "Usage: node successor-tool.mjs" in tool and "createJoinMission" in tool
    report = download(page, "#download-report").decode()
    assert "My catalog advantage" in report and "Evidence scope" in report
    page.locator(".deployment-detail > summary").click()
    expect(page.locator("#contract-list > a")).to_have_count(5)
    for name, address in CONTRACTS.items():
        link = page.locator("#contract-list > a").filter(has_text=name)
        expect(link).to_have_attribute("href", f"https://etherscan.io/address/{address}#code")
    page.locator(".next-steps > summary").click()
    usdc = json.loads(download(page, "#handoff-usdc"))
    agialpha = json.loads(download(page, "#handoff-agialpha"))
    assert usdc["route"] == "USDC" and usdc["deployment"] is None
    assert agialpha["route"] == "AGIALPHA"
    assert {k: v["address"] for k, v in agialpha["deployment"]["contracts"].items()} == CONTRACTS
    for item in (usdc, agialpha):
        assert item["state"] == "unfunded_draft" and item["authority"] == "none"
        assert item["transactionPrepared"] is False and item["projectId"] == project["id"]
    page.screenshot(path=str(output / "03-capability-and-history.png"), full_page=True)
    page.locator("#lang-fr").click()
    expect(page.locator("html")).to_have_attribute("lang", "fr")
    portable = download(page, "#download-workspace")
    portable_path = output / "portable-workspace.html"
    portable_path.write_bytes(portable)
    assert "data:image/webp;base64," in portable.decode()
    context.close()

    context, page = context_page(browser, errors, external)
    context.set_offline(True)
    page.goto(portable_path.as_uri())
    expect(page.locator("#restored-note")).to_contain_text("histor")
    page.locator("#lang-en").click()
    expect(page.locator("#hero-title")).to_contain_text("Find your")
    expect(page.locator('#hero-start [data-i18n="firstAdvantage"]')).to_have_text("Find my first advantage")
    expect(page.locator("#restored-note")).to_contain_text("historical")
    expect(page.locator(".institution img")).to_have_attribute("alt", english_alt)
    page.locator("#custom-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#keep-capability").click()
    current = json.loads(download(page, "#download-project"))
    assert current["id"] == project["id"] and len(current["cycles"]) == 2
    assert current["cycles"][0] == project["cycles"][0]
    page.screenshot(path=str(output / "04-portable-offline-rerun.png"), full_page=True)
    context.close()
    return project_raw


def restore_and_interrupt(browser: Browser, raw: bytes, output: Path, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external)
    upload(page, "#restore-project", raw)
    expect(page.locator("#restored-note")).to_contain_text("1 historical")
    expect(page.locator("#pane-alpha")).to_be_visible()
    expect(page.locator("#pane-evidence")).not_to_be_visible()
    page.evaluate(
        "() => { document.querySelector('#hero-start').click(); document.querySelector('#cancel-run').click(); }"
    )
    expect(page.locator("#status")).to_contain_text("Run canceled")
    expect(page.locator("#pane-alpha")).to_be_visible()
    page.locator("#example-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#keep-capability").click()
    renewed = json.loads(download(page, "#download-project"))
    old = json.loads(raw)
    assert len(renewed["cycles"]) == 2 and renewed["cycles"][0] == old["cycles"][0]
    assert renewed["cycles"][1]["id"] != old["cycles"][0]["id"]
    upload(page, "#restore-project", b" " * 2_000_001, "oversize.json")
    expect(page.locator("#error")).to_contain_text("no larger than 2 MB")
    assert json.loads(download(page, "#download-project"))["cycles"] == renewed["cycles"]
    upload(page, "#restore-project", b'{"schema":"unsupported"}', "invalid.json")
    expect(page.locator("#error")).to_contain_text("Unsupported or invalid")
    assert json.loads(download(page, "#download-project"))["cycles"] == renewed["cycles"]
    context.close()


def custom_and_errors(browser: Browser, output: Path, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external)
    page.locator("#hero-custom").click()
    expect(page.locator("#left-csv")).to_be_focused()
    page.locator("#left-csv").fill('sku,name,price\nA,"Alpha, one",10\nA,=SUM(1),11\nZ,Missing,0\n')
    page.locator("#right-csv").fill('id,name,price\nA,"Alpha, one",10\nA,Other,12\nY,New,3\n')
    page.locator("#check-columns").click()
    page.locator("#left-key").select_option("sku")
    page.locator("#right-key").select_option("id")
    page.locator("#custom-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    expect(page.locator("#matched-count")).to_have_text("4")
    expect(page.locator("#unmatched-count")).to_have_text("2")
    expect(page.locator("#conflict-count")).to_have_text("3")
    actual = {
        name: rows(download(page, "#" + name))
        for name in ("download-joined", "download-unmatched-left", "download-unmatched-right", "download-conflicts")
    }
    assert actual["download-joined"][1] == ["A", "Alpha, one", "10", "A", "Alpha, one", "10"]
    assert actual["download-joined"][3][1] == "'=SUM(1)"
    assert actual["download-unmatched-left"][-1] == ["Z", "Missing", "0"]
    assert actual["download-unmatched-right"][-1] == ["Y", "New", "3"]
    page.locator("#keep-capability").click()
    project = json.loads(download(page, "#download-project"))
    assert actual == expected_outputs(project["cycles"][0]["mission"])
    page.locator("#next-cycle").click()
    for value, message in [
        ('sku,name\nA,"not closed', "Unclosed quoted"),
        ("sku,sku\nA,A", "nonempty and unique"),
        ("sku,name\nA", "header column count"),
    ]:
        page.locator("#left-csv").fill(value)
        page.locator("#check-columns").click()
        expect(page.locator("#error")).to_contain_text(message)
        expect(page.locator("#left-csv")).to_have_attribute("aria-invalid", "true")
    page.locator("#left-csv").fill("sku,name\nA,Fresh\n")
    page.locator("#right-csv").fill("id,name\nA,Fresh\n")
    page.locator("#check-columns").click()
    expect(page.locator("#key-mapping")).to_be_visible()
    page.locator("#left-csv").fill("sku,name\nB,Edited\n")
    expect(page.locator("#key-mapping")).not_to_be_visible()
    page.evaluate("""() => {
        globalThis.originalFileRead = File.prototype.arrayBuffer;
        File.prototype.arrayBuffer = function() {
            return new Promise(resolve => { globalThis.releaseFileRead = () => originalFileRead.call(this).then(resolve); });
        };
    }""")
    upload(page, "#left-file", b"sku,name\nC,Stale\n", "catalog.csv")
    page.locator("#left-csv").fill("sku,name\nD,Keep my edit\n")
    page.evaluate("() => { File.prototype.arrayBuffer = originalFileRead; releaseFileRead(); }")
    expect(page.locator("#error")).to_contain_text("Inputs changed")
    expect(page.locator("#left-csv")).to_have_value("sku,name\nD,Keep my edit\n")
    page.screenshot(path=str(output / "05-invalid-and-stale-input.png"), full_page=True)
    context.close()


def mobile_and_french(browser: Browser, output: Path, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external, 390)
    assert page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    ), "Mobile page overflows horizontally"
    page.screenshot(path=str(output / "06-mobile-first-use.png"), full_page=True)
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile results overflow"
    accessibility(page)
    page.screenshot(path=str(output / "07-mobile-useful-result.png"), full_page=True)
    page.goto(URL + "?lang=fr")
    expect(page.locator("html")).to_have_attribute("lang", "fr")
    expect(page.locator("#hero-title")).to_contain_text("Trouvez votre")
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    expect(page.locator("#evidence-title")).to_have_text("Une clarté exploitable.")
    page.locator("#keep-capability").click()
    expect(page.locator("#successor-title")).to_have_text("Gardez plus qu’un résultat.")
    page.screenshot(path=str(output / "08-french-capability.png"), full_page=True)
    context.close()


def main() -> None:
    output = Path(os.environ.get("SUCCESSOR_ALPHA_SCREENSHOTS", tempfile.mkdtemp(prefix="successor-alpha-browser-")))
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    external: list[str] = []
    with sync_playwright() as playwright:
        options: dict[str, Any] = {}
        if os.environ.get("CHROMIUM_EXECUTABLE"):
            options = {
                "executable_path": os.environ["CHROMIUM_EXECUTABLE"],
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            }
        browser = playwright.chromium.launch(**options)
        raw = first_use(browser, output, errors, external)
        restore_and_interrupt(browser, raw, output, errors, external)
        custom_and_errors(browser, output, errors, external)
        mobile_and_french(browser, output, errors, external)
        browser.close()
    assert not errors, errors
    assert not external, external
    print(f"SUCCESSOR Alpha browser acceptance passed; screenshots: {output}")


if __name__ == "__main__":
    main()
