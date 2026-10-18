# SPDX-License-Identifier: Apache-2.0
"""Exercise the self-contained Alpha flagship, its actual downloads and offline reuse."""

from __future__ import annotations

import csv
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Page, Response, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
URL = (ROOT / "docs/successor/alpha/index.html").as_uri()
EXPECTED_PAGE_SHA256: str | None = None
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


def document_identity(url: str) -> tuple[str, str, str]:
    parsed = urlsplit(url)
    return parsed.scheme, parsed.netloc, parsed.path


def observe_response(response: Response, errors: list[str]) -> None:
    if response.status >= 400:
        errors.append(f"HTTP_FAILURE:{response.status}:{response.url}")
    if (
        EXPECTED_PAGE_SHA256
        and response.request.resource_type == "document"
        and document_identity(response.url) == document_identity(URL)
    ):
        try:
            observed = hashlib.sha256(response.body()).hexdigest()
            if observed != EXPECTED_PAGE_SHA256:
                errors.append(f"DOCUMENT_SOURCE_CHANGED:{response.url}")
        except Exception as error:
            errors.append(f"DOCUMENT_SOURCE_UNAVAILABLE:{response.url}:{error}")


def context_page(
    browser: Browser, errors: list[str], external: list[str], width: int = 1440, disable_worker: bool = False
) -> tuple[BrowserContext, Page]:
    context = browser.new_context(
        viewport={"width": width, "height": 1050}, accept_downloads=True, reduced_motion="reduce"
    )
    context.add_init_script(
        "document.addEventListener('securitypolicyviolation', e => console.error('ALPHA_CSP_VIOLATION:' + "
        "JSON.stringify({directive:e.violatedDirective, blocked:e.blockedURI})))"
    )
    if disable_worker:
        context.add_init_script("globalThis.Worker = undefined")
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console",
        lambda message: errors.append(message.text) if message.text.startswith("ALPHA_CSP_VIOLATION:") else None,
    )
    page.on(
        "request",
        lambda request: (
            external.append(request.url)
            if request.url.startswith(("http://", "https://"))
            and not (request.resource_type == "document" and document_identity(request.url) == document_identity(URL))
            else None
        ),
    )
    page.on("response", lambda response: observe_response(response, errors))
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
    for width in (1440, 1363, 1280, 1024, 900, 768, 600, 390, 320):
        page.set_viewport_size({"width": width, "height": 1050})
        for language in ("en", "fr"):
            page.locator(f"#lang-{language}").click()
            expect(page.locator("html")).to_have_attribute("lang", language)
            assert page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
            ), f"{language} first-use page overflows horizontally at {width}px"
    page.locator("#lang-en").click()
    page.set_viewport_size({"width": 1440, "height": 1050})
    page.goto(URL)
    english_alt = page.locator(".institution img").get_attribute("alt")
    assert english_alt and "Alpha" in english_alt
    page.keyboard.press("Tab")
    expect(page.locator(".skip")).to_be_focused()
    page.keyboard.press("Enter")
    assert page.url.endswith("#computer-title")
    expect(page.locator("#computer-title")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator('[data-i18n="computerRunnerGuide"]')).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator("#computer-example")).to_be_focused()
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
    expect(page.locator('#hero-start[data-i18n="firstAdvantage"]')).to_have_text("Run the maintained catalog example")
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
    page.evaluate(
        """() => {
        globalThis.originalFileRead = File.prototype.arrayBuffer;
        File.prototype.arrayBuffer = function() {
            return new Promise(resolve => {
                globalThis.releaseFileRead = () => originalFileRead.call(this).then(resolve);
            });
        };
    }"""
    )
    upload(page, "#left-file", b"sku,name\nC,Stale\n", "catalog.csv")
    page.locator("#left-csv").fill("sku,name\nD,Keep my edit\n")
    page.evaluate("() => { File.prototype.arrayBuffer = originalFileRead; releaseFileRead(); }")
    expect(page.locator("#error")).to_contain_text("Inputs changed")
    expect(page.locator("#left-csv")).to_have_value("sku,name\nD,Keep my edit\n")
    page.screenshot(path=str(output / "05-invalid-and-stale-input.png"), full_page=True)
    context.close()


def advanced_continuity(browser: Browser, output: Path, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external)
    page.locator("#hero-custom").click()
    page.locator("#left-csv").fill('sku,name,price\nA,"Alpha, one",10\nA,=SUM(1),11\nZ,Missing,0\n')
    page.locator("#right-csv").fill('id,name,price\nA,"Alpha, one",10\nA,Other,12\nY,New,3\n')
    page.locator("#check-columns").click()
    page.locator("#left-key").select_option("sku")
    page.locator("#right-key").select_option("id")
    page.locator("#custom-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#research-panel > summary").click()
    page.locator("#research-memory").fill("64")
    page.locator("#research-weight").fill("0")
    page.locator("#research-run").click()
    expect(page.locator("#research-result")).to_be_visible()
    strategy = json.loads(download(page, "#download-research"))
    assert strategy["schema"] == "successor-strategy-research/v1"
    assert strategy["qualification"] == "local_engineering_only"
    for field in (
        "independentlyQualified",
        "protectedHoldout",
        "externalAuthority",
        "modelUsed",
        "algorithmNoveltyClaim",
    ):
        assert strategy[field] is False
    assert strategy["confirmation"]["publicSynthetic"] is True
    assert strategy["confirmation"]["protected"] is False
    assert strategy["decision"]["state"] in ("held", "local_improvement")
    candidates = strategy["candidates"]
    assert len(candidates) == 20 and all(x["correct"] for x in candidates)
    assert len({x["planHash"] for x in candidates}) > 1
    pairs_raw = json.dumps([[0, 0], [0, 1], [1, 0], [1, 1]], separators=(",", ":"))
    assert all(x["pairsHash"] == hashlib.sha256(pairs_raw.encode()).hexdigest() for x in candidates)
    plan_tool = download(page, "#download-plan-tool")
    assert strategy["decision"]["retainedPlanHash"].encode() in plan_tool
    changed_inputs = {
        "leftCsv": "code,title\nN,one\nN,two\nM,left\n",
        "rightCsv": "id,title\nN,one\nN,right\nQ,new\n",
        "leftKey": "code",
        "rightKey": "id",
    }
    with tempfile.TemporaryDirectory(prefix="alpha-downloaded-capability-") as directory:
        tool_path = Path(directory) / "retained.mjs"
        tool_path.write_bytes(plan_tool)
        script = (
            "const m=await import(process.argv[1]);const r=m.reconcileCatalogs(JSON.parse(process.argv[2]));"
            "console.log(JSON.stringify({metadata:m.metadata,result:r}));"
        )
        outcome = subprocess.run(
            [
                os.environ.get("NODE_EXECUTABLE", "node"),
                "--input-type=module",
                "-e",
                script,
                tool_path.as_uri(),
                json.dumps(changed_inputs),
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert outcome.returncode == 0, outcome.stderr
        executable_result = json.loads(outcome.stdout)
    assert executable_result["metadata"]["planHash"] == strategy["decision"]["retainedPlanHash"]
    exact_changed = json.loads(executable_result["result"]["exactJson"])
    assert exact_changed["mission"]["left"]["rows"] == rows(changed_inputs["leftCsv"].encode())[1:]
    assert exact_changed["mission"]["right"]["rows"] == rows(changed_inputs["rightCsv"].encode())[1:]
    changed_outputs = expected_outputs(exact_changed["mission"])
    for field, selector in {
        "joinedCsv": "download-joined",
        "unmatchedLeftCsv": "download-unmatched-left",
        "unmatchedRightCsv": "download-unmatched-right",
        "conflictsCsv": "download-conflicts",
    }.items():
        assert rows(executable_result["result"][field].encode()) == changed_outputs[selector]
    assert executable_result["result"]["scope"]["independentlyQualified"] is False
    assert executable_result["result"]["scope"]["externalAuthority"] is False
    frozen = strategy["frozen"]
    plan_raw = json.dumps(frozen["plan"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert frozen["planHash"] == hashlib.sha256(plan_raw.encode()).hexdigest()
    commitment = {key: value for key, value in frozen.items() if key != "commitment"}
    commitment_raw = json.dumps(commitment, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert frozen["commitment"] == hashlib.sha256(commitment_raw.encode()).hexdigest()
    expect(page.locator("#research-candidates > tr")).to_have_count(len(strategy["baselines"]) + len(candidates))
    page.locator("#research-run").click()
    expect(page.locator("#research-run")).to_be_enabled()
    repeated_strategy = json.loads(download(page, "#download-research"))
    assert repeated_strategy["frozen"] == frozen, "Repeating a fixed mission must retain the same plan commitment"
    page.locator("#resolution-panel > summary").click()
    page.locator("#resolution-run").click()
    expect(page.locator("#resolution-result")).to_be_visible()
    actions_csv = rows(download(page, "#download-actions"))
    assert actions_csv[0] == [
        "action",
        "exact_key",
        "type",
        "left_data_rows",
        "right_data_rows",
        "original_review_occurrences",
        "next_step",
    ]
    assert len(actions_csv) == 4
    occurrence_ids = [item for row in actions_csv[1:] for item in row[5].split(";")]
    expected_occurrences = {"left:2", "right:2", "conflict:0:1", "conflict:1:0", "conflict:1:1"}
    assert len(occurrence_ids) == 5 and set(occurrence_ids) == expected_occurrences
    assert {row[1] for row in actions_csv[1:]} == {"A", "Y", "Z"}
    page.screenshot(path=str(output / "09-constructed-strategy-and-reframing.png"), full_page=True)
    accessibility(page)
    page.locator("#keep-capability").click()
    page.locator("#project-name").fill("Catalog continuity")
    page.locator("#native-panel > summary").click()
    page.locator("#native-rights").select_option("synthetic")
    for selector, value in {
        "#native-source": "Synthetic browser acceptance catalogs",
        "#native-license": "Apache-2.0",
        "#native-owner": "local-owner",
        "#native-name": "Catalog continuity",
        "#native-review-minutes": "10",
    }.items():
        page.locator(selector).fill(value)
    page.locator("#native-prepare").click()
    expect(page.locator("#download-native-handoff")).to_be_enabled()
    handoff_raw = download(page, "#download-native-handoff")
    handoff = json.loads(handoff_raw)
    assert handoff["schema"] == "successor-alpha-native-handoff/v1"
    historical_project = json.loads(handoff["project"]["raw"])
    cycle = historical_project["cycles"][-1]
    assert handoff["project"]["id"] == historical_project["id"]
    assert handoff["project"]["sha256"] == hashlib.sha256(handoff["project"]["raw"].encode()).hexdigest()
    assert handoff["cycle"]["id"] == cycle["id"]
    assert handoff["cycle"]["sourceHash"] == cycle["sourceHash"]
    spec = json.loads(handoff["specRaw"])
    assert spec["family"] == "catalog-reconciliation"
    assert spec["inputs"] == {"mission": cycle["mission"]}
    assert spec["rights"] == {
        "dataClass": "synthetic",
        "source": "Synthetic browser acceptance catalogs",
        "license": "Apache-2.0",
    }
    assert handoff["route"] == {
        "backend": "native-jobs-compiler-local",
        "asset": "AGIALPHA",
        "funding": "unfunded-proposal",
    }
    compilation = json.loads(handoff["compilationRaw"])
    assert len(compilation["graph"]["nodes"]) == 7
    assert compilation["authorityCreated"] == "NONE"
    assert compilation["signatureStatus"] == "UNSIGNED_COMMITMENT"
    assert compilation["budgetReservations"]["reservedBaseUnits"] == "0"
    assert all(x["status"] == "REQUESTED_NOT_GRANTED" for x in compilation["capabilityRequests"])
    page.locator("#native-run").click()
    expect(page.locator("#download-native-return")).to_be_enabled()
    returned_raw = download(page, "#download-native-return")
    returned = json.loads(returned_raw)
    assert returned["schema"] == "successor-alpha-native-return/v1"
    assert returned["handoffSha256"] == hashlib.sha256(handoff_raw).hexdigest()
    assert returned["projectId"] == historical_project["id"] and returned["cycleId"] == cycle["id"]
    assert returned["authority"] == "none" and returned["settlement"] == "not-connected"
    pack = json.loads(returned["nativePackRaw"])
    assert pack["spec"] == spec
    assert pack["evaluation"] == {
        "scope": "PUBLIC_LOCAL_EXECUTION",
        "independentProof": False,
        "admission": "HOLD",
        "authority": [],
        "settlement": "NOT_CONNECTED",
    }
    assert pack["result"]["summary"] == {"matchedPairs": 4, "unmatchedLeft": 1, "unmatchedRight": 1, "conflicts": 3}
    produced = {x["name"]: x["content"].encode() for x in pack["result"]["artifacts"]}
    expected = expected_outputs(cycle["mission"])
    for filename, selector in {
        "joined.csv": "download-joined",
        "unmatched-left.csv": "download-unmatched-left",
        "unmatched-right.csv": "download-unmatched-right",
        "conflicts.csv": "download-conflicts",
    }.items():
        assert rows(produced[filename]) == expected[selector]
    assert json.loads(produced["exact-result.json"])["mission"] == cycle["mission"]
    with tempfile.TemporaryDirectory(prefix="alpha-native-host-") as directory:
        input_path = Path(directory) / "handoff.json"
        output_path = Path(directory) / "return.json"
        input_path.write_bytes(handoff_raw)
        outcome = subprocess.run(
            [
                os.environ.get("NODE_EXECUTABLE", "node"),
                str(ROOT / "examples/successor-alpha/native-cli.mjs"),
                str(input_path),
                str(output_path),
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert outcome.returncode == 0, outcome.stderr
        host_summary = json.loads(outcome.stdout)
        host_return_raw = output_path.read_bytes()
    assert host_summary["execution"] == "installed-local-node"
    assert host_summary["projectId"] == historical_project["id"] and host_summary["cycleId"] == cycle["id"]
    assert host_summary["sourceHash"] == handoff["runtimeSourceHash"]
    assert host_summary["independentlyQualified"] is False and host_summary["authority"] == "none"
    upload(page, "#native-return-input", host_return_raw, "host-return.json")
    if not page.locator("#learning-history-panel").evaluate("el => el.open"):
        page.locator("#learning-history-panel > summary").click()
    expect(page.locator("#learning-summary")).to_contain_text("2 checked native returns")
    assert download(page, "#download-native-return") == host_return_raw
    host_return = json.loads(host_return_raw)
    host_pack = json.loads(host_return["nativePackRaw"])
    assert host_pack["spec"] == spec and host_pack["result"]["summary"] == pack["result"]["summary"]
    for artifact in host_pack["result"]["artifacts"]:
        if artifact["name"] in produced and artifact["name"] != "exact-result.json":
            assert artifact["content"].encode() == produced[artifact["name"]]
    archive_raw = download(page, "#download-learning")
    archive = json.loads(archive_raw)
    assert archive["schema"] == "successor-alpha-learning-archive/v1"
    assert archive["project"]["id"] == historical_project["id"]
    assert archive["project"]["cycles"] == historical_project["cycles"]
    retained_record = next(x for x in archive["records"] if x["cycleId"] == cycle["id"])
    assert retained_record["strategy"] == repeated_strategy
    resolution = retained_record["resolution"]
    assert resolution["schema"] == "successor-discrepancy-resolution/v1"
    assert resolution["coverage"]["complete"] is True
    assert resolution["coverage"]["originalOccurrences"] == resolution["coverage"]["coveredOccurrences"] == 5
    assert resolution["coverage"]["missing"] == resolution["coverage"]["duplicates"] == []
    assert resolution["burden"]["groupedActions"] == 3 and resolution["burden"]["pairwiseReviewItems"] == 5
    assert resolution["burden"]["timeSavedClaim"] is False and resolution["burden"]["sameTaskSuperiority"] is False
    assert resolution["contract"]["changed"] is True
    assert resolution["automaticallyResolved"] is False and resolution["externalAuthority"] is False
    assert rows(resolution["actionsCsv"].encode()) == actions_csv
    continuity = json.loads(archive["nativeContinuityRaw"])
    assert continuity["projectId"] == historical_project["id"] and len(continuity["returns"]) == 2
    assert continuity["returns"][0]["handoffRaw"] == handoff_raw.decode()
    assert continuity["returns"][0]["returnRaw"] == returned_raw.decode()
    assert continuity["returns"][1]["returnRaw"] == host_return_raw.decode()
    assert continuity["authority"] == "none" and continuity["qualification"] == "not_independently_qualified"
    corrupt = dict(returned, cycleId="00000000-0000-4000-8000-000000000000")
    upload(page, "#native-return-input", json.dumps(corrupt).encode(), "changed-return.json")
    expect(page.locator("#native-error")).to_be_visible()
    assert json.loads(download(page, "#download-learning"))["nativeContinuityRaw"] == archive["nativeContinuityRaw"]
    page.screenshot(path=str(output / "10-native-catalog-continuity.png"), full_page=True)
    accessibility(page)
    portable_path = output / "learning-workspace.html"
    portable_path.write_bytes(download(page, "#download-workspace"))
    context.close()

    context, page = context_page(browser, errors, external)
    upload(page, "#restore-learning-top", archive_raw, "learning.json")
    expect(page.locator("#restored-note")).to_contain_text("historical")
    if not page.locator("#learning-history-panel").evaluate("el => el.open"):
        page.locator("#learning-history-panel > summary").click()
    expect(page.locator("#learning-summary")).not_to_have_text("")
    restored = json.loads(download(page, "#download-learning"))
    assert restored["project"]["cycles"] == historical_project["cycles"]
    assert restored["nativeContinuityRaw"] == archive["nativeContinuityRaw"]
    context.set_offline(True)
    page.goto(portable_path.as_uri())
    expect(page.locator("#restored-note")).to_contain_text("historical")
    page.locator("#learning-history-panel").evaluate("el => el.open = true")
    retained = json.loads(download(page, "#download-learning"))
    assert retained["nativeContinuityRaw"] == archive["nativeContinuityRaw"]
    assert retained["project"]["cycles"] == historical_project["cycles"]
    page.screenshot(path=str(output / "11-retained-learning-offline.png"), full_page=True)
    context.close()


def constructed_example(browser: Browser, output: Path, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external)
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#research-panel > summary").click()
    page.locator("#research-example").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#research-panel").evaluate("el => el.open = true")
    page.locator("#research-run").click()
    expect(page.locator("#research-result")).to_be_visible()
    report = json.loads(download(page, "#download-research"))
    assert report["decision"]["state"] == "local_improvement" and report["decision"]["promoted"] is True
    assert report["confirmation"]["passed"] is True and report["confirmation"]["developmentImproved"] is True
    assert report["confirmation"]["protected"] is False and report["independentlyQualified"] is False
    assert report["frozen"]["plan"]["guard"]["op"] == "uniform_key"
    assert report["confirmation"]["candidate"]["objectiveValue"] < report["confirmation"]["incumbent"]["objectiveValue"]
    assert report["qualification"] == "local_engineering_only" and report["externalAuthority"] is False
    page.screenshot(path=str(output / "12-constructed-example-local-improvement.png"), full_page=True)
    page.locator("#keep-capability").click()
    project = json.loads(download(page, "#download-project"))
    assert len(project["cycles"]) == 2
    mission = project["cycles"][-1]["mission"]
    assert len({row[mission["left"]["keyIndex"]] for row in mission["left"]["rows"]}) == 1
    assert len({row[mission["right"]["keyIndex"]] for row in mission["right"]["rows"]}) == 1
    assert len(mission["left"]["rows"]) > 64 and len(mission["right"]["rows"]) > 64
    context.close()


def worker_fallback(browser: Browser, errors: list[str], external: list[str]) -> None:
    context, page = context_page(browser, errors, external, disable_worker=True)
    assert page.evaluate("typeof Worker") == "undefined"
    page.locator("#hero-custom").click()
    page.locator("#left-csv").fill("sku,value\nA,one\nB,two\n")
    page.locator("#right-csv").fill("sku,value\nB,two\nC,three\n")
    page.locator("#check-columns").click()
    page.locator("#custom-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    expect(page.locator("#matched-count")).to_have_text("1")
    assert rows(download(page, "#download-joined")) == [
        ["left.sku", "left.value", "right.sku", "right.value"],
        ["B", "two", "B", "two"],
    ]
    page.locator("#research-panel > summary").click()
    page.locator("#research-run").click()
    expect(page.locator("#research-result")).to_be_visible()
    report = json.loads(download(page, "#download-research"))
    assert len(report["candidates"]) == 20 and all(x["correct"] for x in report["candidates"])
    assert report["decision"]["state"] == "held" and report["decision"]["promoted"] is False
    assert report["qualification"] == "local_engineering_only"
    for field in (
        "independentlyQualified",
        "protectedHoldout",
        "externalAuthority",
        "modelUsed",
        "algorithmNoveltyClaim",
    ):
        assert report[field] is False
    assert report["confirmation"]["publicSynthetic"] is True and report["confirmation"]["protected"] is False
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
    page.set_viewport_size({"width": 320, "height": 1050})
    page.goto(URL)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "320px first use overflows"
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "320px results overflow"
    accessibility(page)
    page.screenshot(path=str(output / "13-mobile-320-result.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 1050})
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


def controlled_computer_return(raw: bytes) -> bytes:
    """Exercise the actual native journal/export protocol with labeled supplier/actuator doubles."""
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.computer import commitment, run_session
    from alpha_factory_v1.core.runtime.successor.computer_handoff import ComputerHandoff, write_computer_return

    handoff = ComputerHandoff.model_validate(json.loads(raw))
    png = base64.b64encode(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489")).decode()

    class ControlledAdvisor:
        identity = {
            "mode": "responses",
            "model": "CONTROLLED_BROWSER_PROTOCOL_TEST",
            "endpoint": "https://example.com/v1",
        }

        def next(self, task: Any, observation: dict[str, Any]) -> dict[str, Any]:
            return {"actions": [], "done": True, "summary": "Controlled protocol double; no live model qualification."}

    class ControlledComputer:
        def __init__(self, *args: Any) -> None:
            pass

        def observe(self) -> dict[str, str]:
            return {"png": png, "text": "CONTROLLED TEST WORK PRODUCT. No real model or computer execution claimed."}

        def close(self) -> None:
            pass

    advisor = ControlledAdvisor()
    image = "sha256:" + "d" * 64
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        journal = Journal.initialize(root / "journal")
        permit = commitment(handoff.task, advisor, image, handoff.context())
        run_session(
            journal,
            handoff.task,
            advisor,
            image,
            root / "result",
            permit,
            factory=ControlledComputer,
            execution_context=handoff.context(),
        )
        write_computer_return(handoff, journal, advisor, image, root / "result")
        return (root / "result/computer-return.json").read_bytes()


def computer_strategy_journey(browser: Browser, output: Path, errors: list[str], external: list[str]) -> None:
    """Prepare, execute the native protocol, review and retain a Computer Use strategy study."""
    context, page = context_page(browser, errors, external)
    page.locator("#hero-computer").click()
    brief = (
        page.locator("#computer-context").input_value()
        + '\nUntrusted markup remains text: <img src="https://unapproved.example/brief">'
    )
    page.locator("#computer-context").fill(brief)
    page.locator("#computer-prepare").click()
    expect(page.locator("#computer-prepared")).to_be_visible()
    first = download(page, "#computer-download")
    handoff = json.loads(first)
    assert handoff["strategy"]["selected"] == "combine"
    assert "Value hypothesis (unverified): " + handoff["strategy"]["valueHypothesis"] in handoff["task"]["goal"]
    assert handoff["task"]["allowed_urls"][0].endswith("/alpha_factory_v1/core/runtime/successor/computer.py")
    assert "&lt;img src=&quot;https://unapproved.example/brief&quot;&gt;" in handoff["task"]["html"]
    assert not json.loads(handoff["projectRaw"])["cycles"]
    returned = controlled_computer_return(first)
    altered = json.loads(returned)
    altered["sourceHash"] = "0" * 64
    upload(page, "#computer-return", json.dumps(altered).encode(), "altered-return.json")
    expect(page.locator("#computer-error")).to_be_visible()
    expect(page.locator("#computer-returned")).to_be_hidden()
    upload(page, "#computer-return", returned, "controlled-return.json")
    expect(page.locator("#computer-returned")).to_be_visible()
    expect(page.locator("#computer-deliverable")).to_contain_text("CONTROLLED TEST WORK PRODUCT")
    page.locator("#computer-review-decision").select_option("accepted")
    page.locator("#computer-review-note").fill("Protocol test owner review; not independent qualification.")
    page.locator("#computer-review-save").click()
    expect(page.locator("#computer-error")).to_be_visible()
    for checkbox in page.locator("#computer-criteria-review input").all():
        checkbox.check()
    page.locator("#computer-review-actual").fill("7")
    page.locator("#computer-review-save").click()
    expect(page.locator("#computer-review-form")).to_be_hidden()
    expect(page.locator("#computer-history")).to_contain_text("Owner review: useful")
    page.locator("#computer-reframe-next").click()
    expect(page.locator("#computer-approach")).to_have_value("reframe")
    page.locator("#computer-prepare").click()
    expect(page.locator("#computer-history-count")).to_have_text("2 attempts")
    second = json.loads(download(page, "#computer-download"))
    assert second["strategy"]["selected"] == "reframe"
    assert second["attemptId"] != handoff["attemptId"]
    assert second["strategy"]["successCriteria"] == handoff["strategy"]["successCriteria"]
    assert second["strategy"]["originalGoal"] == handoff["strategy"]["originalGoal"]
    assert second["strategy"]["valueHypothesis"] == handoff["strategy"]["valueHypothesis"]
    assert second["task"]["html"] == handoff["task"]["html"]
    archive = download(page, "#computer-save-history")
    checked_archive = json.loads(archive)
    assert checked_archive["schema"] == "successor-alpha-learning-archive/v2"
    assert len(json.loads(checked_archive["computerHistoryRaw"])["records"]) == 2
    portable = download(page, "#computer-save-workspace")
    destination = (output / "computer-portable-workspace.html").resolve()
    destination.write_bytes(portable)
    page.goto(destination.as_uri())
    expect(page.locator("#computer-history-count")).to_have_text("2 attempts")
    expect(page.locator("#computer-context")).to_have_value(brief)
    expect(page.locator("#computer-history")).to_contain_text("Owner review: useful")
    assert page.locator("#saved-learning").text_content().count("</script>") == 0
    accessibility(page)
    page.screenshot(path=str(output / "14-computer-use-history.png"), full_page=True)
    page.goto(URL)
    upload(page, "#restore-computer-history", archive, "computer-history.json")
    expect(page.locator("#computer-history-count")).to_have_text("2 attempts")
    page.locator("#hero-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#keep-capability").click()
    combined = json.loads(download(page, "#download-project"))
    assert combined["project"]["id"] == checked_archive["project"]["id"]
    assert len(combined["project"]["cycles"]) == 1
    assert len(json.loads(combined["computerHistoryRaw"])["records"]) == 2
    page.set_viewport_size({"width": 320, "height": 1050})
    page.goto(URL + "?lang=fr")
    expect(page.locator("#computer-title")).to_contain_text("Quelle capacité utile")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#computer-prepare").click()
    expect(page.locator("#computer-prepared")).to_be_visible()
    french = json.loads(download(page, "#computer-download"))
    assert "Découvrir" in french["strategy"]["originalGoal"]
    accessibility(page)
    page.screenshot(path=str(output / "15-computer-use-mobile-fr.png"), full_page=True)
    context.close()

    # A controlled public-page fixture verifies that reading a source cannot lose the work editor.
    script = (
        "import {buildWorkSurface} from './examples/successor-alpha/computer.mjs';"
        "console.log(buildWorkSurface({goal:'Inspect the public-source fixture and save a decision.',"
        "allowedUrls:['https://public.example/source']}));"
    )
    surface = subprocess.check_output(["node", "--input-type=module", "-e", script], cwd=ROOT, text=True)
    reading_context = browser.new_context(viewport={"width": 1024, "height": 768})
    reading_page = reading_context.new_page()
    requested: list[str] = []

    def source_fixture(route: Any) -> None:
        requested.append(route.request.url)
        assert route.request.url == "https://public.example/source"
        route.fulfill(status=200, content_type="text/html", body="<h1>Controlled source</h1><p>HTML export: yes.</p>")

    reading_page.route("**/*", source_fixture)
    reading_page.set_content(surface)
    reading_page.locator("[data-source]").click()
    expect(reading_page.frame_locator("#source").get_by_text("HTML export: yes.")).to_be_visible()
    reading_page.locator("#answer").fill("Controlled source supports HTML export; offline use remains unverified.")
    reading_page.locator("#save").click()
    expect(reading_page.locator("#saved")).to_contain_text("offline use remains unverified")
    assert reading_page.url == "about:blank"
    assert requested == ["https://public.example/source"]
    reading_context.close()


def computer_mission_presets(browser: Browser, errors: list[str], external: list[str]) -> None:
    """Each bilingual mission must reach execution with its own outcome and strategy slate."""
    context, page = context_page(browser, errors, external)
    for language in ("en", "fr"):
        for preset in ("opportunity", "mathematics", "software", "research"):
            page.goto(URL + "?lang=" + language)
            page.locator("#computer-example").select_option(preset)
            outcome = page.locator("#computer-outcome").input_value()
            value_hypothesis = page.locator("#computer-value-hypothesis").input_value()
            allowed_urls = page.locator("#computer-urls").input_value().splitlines()
            page.locator("#computer-build-surface").click()
            surface = page.locator("#computer-html").input_value()
            assert "Fictional product specifications" not in surface
            page.locator("#computer-strategy-panel > summary").click()
            for approach in ("baseline", "combine", "reframe"):
                page.locator("#computer-approach").select_option(approach)
                page.locator("#computer-prepare").click()
                expect(page.locator("#computer-prepared")).to_be_visible()
                pack = json.loads(download(page, "#computer-download"))
                assert pack["strategy"]["originalGoal"] == outcome
                assert pack["strategy"]["valueHypothesis"] == value_hypothesis
                assert pack["strategy"]["selected"] == approach
                for statement in (
                    *pack["strategy"]["hypotheses"],
                    pack["strategy"]["combination"],
                    pack["strategy"]["reframing"],
                ):
                    assert len(statement.strip()) > 20 and statement.strip() not in {"undefined", "null"}
                assert pack["task"]["html"] == surface
                assert len(pack["task"]["goal"]) <= 4000
                for candidate in pack["strategy"]["hypotheses"]:
                    assert candidate in pack["task"]["goal"]
                assert pack["strategy"]["combination"] in pack["task"]["goal"]
                assert pack["strategy"]["reframing"] in pack["task"]["goal"]
                assert pack["authority"] == "none" and pack["settlement"] == "not_connected"
                assert pack["task"]["allowed_urls"] == allowed_urls
    context.close()


def run_acceptance(entry_url: str, output: Path, *, expected_page_sha256: str | None = None) -> dict[str, Any]:
    """Run the same complete journey against a source-bound packaged or public page."""
    global URL, EXPECTED_PAGE_SHA256
    previous_url, previous_digest = URL, EXPECTED_PAGE_SHA256
    URL, EXPECTED_PAGE_SHA256 = entry_url, expected_page_sha256
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    external: list[str] = []
    try:
        with sync_playwright() as playwright:
            options: dict[str, Any] = {}
            if os.environ.get("CHROMIUM_EXECUTABLE"):
                options = {
                    "executable_path": os.environ["CHROMIUM_EXECUTABLE"],
                    "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                }
            browser = playwright.chromium.launch(**options)
            try:
                raw = first_use(browser, output, errors, external)
                restore_and_interrupt(browser, raw, output, errors, external)
                custom_and_errors(browser, output, errors, external)
                advanced_continuity(browser, output, errors, external)
                constructed_example(browser, output, errors, external)
                worker_fallback(browser, errors, external)
                mobile_and_french(browser, output, errors, external)
                computer_strategy_journey(browser, output, errors, external)
                computer_mission_presets(browser, errors, external)
            finally:
                browser.close()
        assert not errors, errors
        assert not external, external
        return {
            "passed": True,
            "entryUrl": entry_url,
            "documentSourceVerified": expected_page_sha256 is not None,
            "checks": [
                "first-use-and-keyboard-focus",
                "exact-csv-artifacts",
                "all-competitive-comparisons",
                "separate-unfunded-routes-and-current-contracts",
                "portable-offline-french-english-rerun",
                "historical-restore-and-cancel",
                "malformed-and-stale-input-rejection",
                "constructed-program-and-frozen-commitment",
                "downloaded-tool-on-changed-inputs",
                "complete-discrepancy-actions",
                "native-sdk-and-node-host-return-import",
                "learning-archive-and-offline-continuity",
                "bounded-local-improvement-and-hold",
                "worker-disabled-fallback",
                "mobile-and-french",
                "computer-use-native-protocol-and-owner-review",
                "computer-use-strategy-reframing-and-portable-history",
                "computer-use-public-reading-pane-and-visible-work-product",
                "computer-use-bilingual-mission-presets-and-complete-strategy-slate",
                "no-page-errors-no-csp-violations-no-external-dependencies",
            ],
            "accessibilityAudited": bool(os.environ.get("AXE_SCRIPT")),
            "languages": ["en", "fr"],
            "viewports": [1440, 1363, 1280, 1024, 900, 768, 600, 390, 320],
            "errors": list(errors) + list(external),
            "browser_errors": [error for error in errors if not error.startswith("HTTP_FAILURE:")],
            "http_failures": [error for error in errors if error.startswith("HTTP_FAILURE:")],
            "screenshots": sorted(path.name for path in output.glob("*.png")),
        }
    finally:
        URL, EXPECTED_PAGE_SHA256 = previous_url, previous_digest


def main() -> None:
    output = Path(os.environ.get("SUCCESSOR_ALPHA_SCREENSHOTS", tempfile.mkdtemp(prefix="successor-alpha-browser-")))
    run_acceptance(URL, output)
    print(f"SUCCESSOR Alpha browser acceptance passed; screenshots: {output}")


if __name__ == "__main__":
    main()
