# SPDX-License-Identifier: Apache-2.0
"""Exercise every production cycle edge in Chromium, without wallet or runtime permission.

Run from the repository root with ``python tests/nova-studio/edge_browser.py --output /tmp/cycle-edges``.
The standalone trial serves unchanged Studio assets with the generated archived deployment profile.
Synthetic history and model-state regressions are reported separately from canonical-chain evidence.
"""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any, cast
from urllib.parse import urlsplit

from playwright.sync_api import Page, Route, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_NODES = [
    "Insight",
    "Nova-Seeds",
    "MARK",
    "Sovereign",
    "Business",
    "Marketplace",
    "Jobs",
    "Agents",
    "Nodes",
    "Council",
    "Value Reservoir",
    "Architect",
]
EXPECTED_EDGES = [
    "Insight → Nova-Seeds",
    "Nova-Seeds → MARK",
    "MARK → Sovereign",
    "Sovereign → Business",
    "Business → Marketplace",
    "Marketplace → Jobs",
    "Jobs → Agents",
    "Agents → Value Reservoir",
    "Jobs → Value Reservoir",
    "Value Reservoir → Nova-Seeds",
    "Value Reservoir → Marketplace",
    "Agents → Nodes",
    "Nodes → Agents",
    "Architect → Sovereign",
    "Sovereign → Architect",
    "Architect → Insight",
    "Insight → Architect",
    "Council → Sovereign",
]


class Handler(SimpleHTTPRequestHandler):
    """Serve the disposable static copy without noisy request logs."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def show_graph(page: Page) -> None:
    """Reveal the actual graph through Studio's navigation and native disclosure."""
    step = page.locator("#cycle-graph").evaluate("el=>el.closest('.step').id.slice(5)")
    page.locator(f'[data-step="{step}"]').click()
    page.locator("#cycle-graph").evaluate(
        "el=>{for(let p=el.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true}"
    )
    expect(page.locator("#cycle-graph")).to_be_visible()


def wallet_calls(page: Page) -> list[str]:
    """Support both the refusing sentinel and the disposable EVM browser fixture."""
    return cast(list[str], page.evaluate("window.__edgeWalletCalls || window.__nova?.calls || []"))


def assert_edge_controls(
    page: Page, language: str = "en", keys: tuple[str, ...] = ("Enter", "Space")
) -> list[dict[str, Any]]:
    """Inspect all original edges and safely navigate to the indicated existing form.

    This is also used by the full native/EVM acceptance run, where the records are
    produced by actual workflow controls rather than injected model fixtures.
    """
    records: list[dict[str, Any]] = []
    calls = wallet_calls(page)
    show_graph(page)
    assert page.locator("#cycle-graph tbody th").all_text_contents() == EXPECTED_NODES
    assert [text.split(" · ")[0] for text in page.locator("#cycle-graph li").all_text_contents()] == EXPECTED_EDGES
    expect(page.locator("#cycle-graph li > button[data-cycle-edge]")).to_have_count(18)
    page.evaluate("window.__edgeTargetClicks=[]")
    for ordinal, label in enumerate(EXPECTED_EDGES, 1):
        edge_id = f"E{ordinal:02d}"
        for key in keys:
            show_graph(page)
            edge = page.locator(f'button[data-cycle-edge="{edge_id}"]')
            expect(edge).to_have_attribute("type", "button")
            expect(edge).to_have_attribute("aria-controls", "cycle-edge-inspector")
            assert edge.inner_text().startswith(label + " · "), edge_id
            edge.focus()
            expect(edge).to_be_focused()
            edge.press(key)
            expect(edge).to_have_attribute("aria-expanded", "true")
            expect(page.locator('[data-cycle-edge][aria-expanded="true"]')).to_have_count(1)
            panel = page.locator("#cycle-edge-inspector")
            expect(panel).to_be_visible()
            expect(panel).to_contain_text(edge_id)
            expect(panel).to_contain_text(label)
            state = page.locator("#cycle-edge-state").inner_text().strip()
            scope = page.locator("#cycle-edge-scope").inner_text().strip()
            assert state and scope, (edge_id, state, scope)
            record_text = page.locator("#cycle-edge-record").inner_text()
            record = json.loads(record_text)
            action = page.locator("#cycle-edge-action")
            expect(action).to_have_attribute("type", "button")
            expect(action).to_be_visible()
            expect(action).to_be_enabled()
            target_id = action.get_attribute("aria-controls") or action.get_attribute("data-cycle-target")
            assert target_id and target_id not in {"cycle-edge-action", "cycle-edge-inspector"}, edge_id
            target = page.locator("#" + target_id)
            expect(target).to_have_count(1)
            assert target.evaluate("el=>!!el.closest('.step')"), (edge_id, target_id)
            target.evaluate("el=>el.addEventListener('click',()=>window.__edgeTargetClicks.push(el.id))")
            action.focus()
            expect(action).to_be_focused()
            action.press(key)
            expect(target).to_be_visible()
            expect(target).to_be_focused()
            assert not page.locator("#preview-panel").is_visible(), edge_id
            assert wallet_calls(page) == calls, (edge_id, key, wallet_calls(page))
            assert page.evaluate("window.__edgeTargetClicks") == [], (edge_id, target_id)
            records.append(
                {
                    "edge": edge_id,
                    "key": key,
                    "language": language,
                    "state": state,
                    "scope": scope,
                    "record": record,
                    "action": action.inner_text(),
                    "target": target_id,
                }
            )
    return records


def restore_unknown_history(page: Page) -> dict[str, Any]:
    """Import encrypted opaque records through production recovery controls."""
    phrase = "edge inspector synthetic private recovery phrase"
    original_texts = ["null", "[]", '{"candidate_verdict":"PASS"}', '{"execution_binding":null}']
    fixture = page.evaluate(
        """async ({phrase, originalTexts}) => {
          const cycle = await import(new URL('../../assets/nova-studio/cycle.mjs', location.href));
          let project = await cycle.createProject(null, {title: 'Synthetic edge historical recovery'});
          for (const originalText of originalTexts)
            project = await cycle.preserveSignedRecord(project, {kind: 'runtime-run', originalText});
          project = await cycle.preserveSignedRecord(project, {kind: 'settlement', originalText: 'null\\n'});
          return {kit: JSON.stringify(await cycle.exportProjectKit(project, phrase)), project};
        }""",
        {"phrase": phrase, "originalTexts": original_texts},
    )
    page.locator('[data-step="continue"]').click()
    page.locator("#project-file").set_input_files(
        {"name": "edge-history.encrypted.json", "mimeType": "application/json", "buffer": fixture["kit"].encode()}
    )
    page.locator("#project-restore-passphrase").fill(phrase)
    page.locator("#restore-project").click()
    expect(page.locator("#status")).to_contain_text("Linked project restored")
    expect(page.locator("#project-restore-passphrase")).to_have_value("")
    expect(page.locator("#cycle-history")).to_contain_text("5 retained records")
    expect(page.locator("#reuse-source option")).to_have_count(1)
    expect(page.locator("#candidate-summary")).to_contain_text("Unrecognized historical record retained")
    assert wallet_calls(page) == []
    return cast(dict[str, Any], fixture["project"])


def check_synthetic_view_invalidation(page: Page, origin: str) -> dict[str, Any]:
    """Real renderer with explicitly synthetic observations, never chain qualification."""
    page.route("**/assets/nova-studio/app.mjs*", lambda route: route.fulfill(body="// Synthetic renderer fixture"))
    page.goto(origin + "/ascension/mainnet/")
    page.evaluate(
        """async () => {
          const base = new URL('../../assets/nova-studio/', location.href);
          const model = await import(new URL('cycle-edges.mjs', base));
          const ui = await import(new URL('cycle-ui.mjs', base));
          const cycle = await import(new URL('cycle.mjs', base));
          const project = await cycle.createProject(null, {title:'Synthetic renderer fixture, no chain evidence'});
          const client = {epoch:1, account:'synthetic-account', history:[], profile:{chainId:31337}};
          const flow = {project, currentCycle:project.cycles[0], client, session:{client}, seedId:'7',
            package:{schema:'synthetic-only', plan:{planRoot:'synthetic-plan', jobs:[]}}, jobIds:[]};
          const go = step => {
            for (const node of document.querySelectorAll('.step')) node.hidden=node.id!==`step-${step}`;
          };
          for (const button of document.querySelectorAll('[data-step]'))
            button.addEventListener('click',()=>go(button.dataset.step));
          ui.installCycleUI({getFlow:()=>flow, getLanguage:()=>document.documentElement.lang,
            go, status:message=>{document.getElementById('status').textContent=message;},
            run:()=>{throw Error('Effects are forbidden in the renderer fixture');},
            download:()=>{throw Error('Downloads are forbidden in the renderer fixture');},
            packageView:()=>{}, setNativeResult:()=>{}});
          for (const edge of model.CYCLE_EDGES) for (const kind of edge.observations)
            model.rememberEdgeEvidence(flow,kind,{kind,synthetic:true,verdict:'FAIL',authority:'not_granted'},
              {now:Date.now()-120001});
          window.__edgeFixture={flow,model,ui};ui.renderCycleUI(flow);
        }"""
    )
    rows = assert_edge_controls(page, keys=("Enter",))
    for row in rows:
        if row["record"]["observations"]:
            assert all(item["state"] == "stale" for item in row["record"]["observations"]), row
            assert all(item["record"]["verdict"] == "FAIL" for item in row["record"]["observations"]), row
    show_graph(page)
    page.evaluate(
        """() => {
          const {flow,model,ui}=window.__edgeFixture;
          model.rememberEdgeEvidence(flow,'chain',{synthetic:true,seedId:'7',green:false},
            {now:Date.now()-119000});ui.renderCycleUI(flow);
        }"""
    )
    page.locator('[data-cycle-edge="E03"]').press("Enter")
    expect(page.locator("#cycle-edge-state")).to_have_attribute("data-state", "observed")
    expect(page.locator("#cycle-edge-state")).to_have_attribute("data-state", "stale", timeout=4000)
    scenarios = ["epoch", "account", "profile", "cycle", "seed", "package"]
    for scenario in scenarios:
        page.evaluate(
            """scenario => {
              const {flow,model,ui}=window.__edgeFixture;
              model.rememberEdgeEvidence(flow,'chain',{synthetic:true,green:false,seedId:flow.seedId});
              if(scenario==='epoch')flow.client.epoch++;
              if(scenario==='account')flow.client.account='changed-account';
              if(scenario==='profile')flow.client.profile.chainId=1;
              if(scenario==='cycle')flow.currentCycle={...flow.currentCycle,cycleId:'different-cycle'};
              if(scenario==='seed')flow.seedId='8';
              if(scenario==='package')flow.package.plan.planRoot='changed-plan';
              ui.renderCycleUI(flow);
            }""",
            scenario,
        )
        expect(page.locator("#cycle-edge-state")).to_have_attribute("data-state", "stale")
    page.evaluate(
        """() => {
          const {flow,ui}=window.__edgeFixture;
          flow.client.history=[{status:'unknown',action:'seal'}];ui.renderCycleUI(flow);
        }"""
    )
    expect(page.locator("#cycle-edge-action")).to_have_attribute("aria-controls", "reconcile-hash")
    page.locator("#cycle-edge-action").press("Enter")
    expect(page.locator("#reconcile-hash")).to_be_focused()
    assert wallet_calls(page) == []
    return {
        "classification": "Synthetic state model through the real renderer; no chain qualification",
        "controls": rows,
        "invalidations": scenarios,
        "idleExpiry": True,
        "unknownIntentNavigation": True,
    }


def prepare_site(destination: Path) -> dict[str, str]:
    """Copy current production files and generate the standard non-signing profile."""
    for relative in [
        "ascension/mainnet",
        "assets/nova-studio",
        "assets/ascension-wallet",
        "assets/ascension",
        "assets/successor",
    ]:
        shutil.copytree(ROOT / "docs" / relative, destination / relative)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_mark_wallet.py"),
            "--root",
            str(ROOT),
            "--docs-dir",
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(destination.rglob("*"))
        if path.is_file()
    }


def validate(output: Path) -> dict[str, Any]:
    """Check native keyboard activation, truthful recovery, localization and reflow."""
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    external_requests: list[str] = []
    effect_requests: list[str] = []
    controls: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="nova-edge-browser-") as temporary:
        site = Path(temporary)
        sources = prepare_site(site)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site)))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True)
                context.add_init_script(
                    "window.__edgeWalletCalls=[];window.ethereum={request:async({method})=>{"
                    "window.__edgeWalletCalls.push(method);throw Error('No wallet permission in edge trial');}};"
                )

                def guard(route: Route) -> None:
                    request = route.request
                    if urlsplit(request.url).netloc != urlsplit(origin).netloc:
                        external_requests.append(request.url)
                        route.abort()
                    elif request.method not in {"GET", "HEAD"}:
                        effect_requests.append(request.method + " " + request.url)
                        route.abort()
                    else:
                        route.continue_()

                context.route("**/*", guard)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/ascension/mainnet/")
                expect(page.locator("#status")).to_contain_text("Start locally")
                assert page.evaluate("Function.prototype.toString.call(window.fetch).includes('[native code]')")
                controls.extend(assert_edge_controls(page))
                project = restore_unknown_history(page)
                history_controls = assert_edge_controls(page)
                controls.extend(history_controls)
                for row in history_controls:
                    assert row["record"]["observations"] == []
                    if row["edge"] == "E13":
                        originals = [item["originalText"] for item in row["record"]["historical"]["signedRecords"]]
                        assert originals == ["null", "[]", '{"candidate_verdict":"PASS"}', '{"execution_binding":null}']
                axe = (ROOT / "tests/browser/node_modules/axe-core/axe.min.js").read_text()
                page.evaluate(axe)
                for language in ["en", "fr"]:
                    if page.locator("html").get_attribute("lang") != language:
                        page.locator("#language").click()
                    expect(page.locator("html")).to_have_attribute("lang", language)
                    for width in [1440, 390, 320]:
                        page.set_viewport_size({"width": width, "height": 1080})
                        for large in [False, True]:
                            if page.locator("#text-size").get_attribute("aria-pressed") != str(large).lower():
                                page.locator("#text-size").click()
                            rows = assert_edge_controls(page, language)
                            controls.extend(rows)
                            show_graph(page)
                            audit = page.evaluate(
                                "async()=>await axe.run(document,{runOnly:{type:'tag',"
                                "values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
                            )
                            result = {
                                "language": language,
                                "width": width,
                                "largeText": large,
                                "violations": audit["violations"],
                            }
                            audits.append(result)
                            assert not audit["violations"], result
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), result
                            page.screenshot(
                                path=str(output / f"edges-{language}-{width}-{'large' if large else 'normal'}.png")
                            )
                fixture_page = context.new_page()
                fixture_page.on("pageerror", lambda error: errors.append(str(error)))
                synthetic = check_synthetic_view_invalidation(fixture_page, origin)
                fixture_page.close()
                assert not errors, errors
                assert not external_requests, external_requests
                assert not effect_requests, effect_requests
                assert wallet_calls(page) == []
                report = {
                    "schema": "agialpha.ascension.cycle-edge.browser-acceptance.v1",
                    "passed": True,
                    "classification": "Actual production Studio controls, synthetic encrypted history, refusing wallet",
                    "sourceHashes": sources,
                    "browserVersion": browser.version,
                    "controls": controls,
                    "historicalProject": project,
                    "audits": audits,
                    "syntheticStateChecks": synthetic,
                    "pageErrors": errors,
                    "externalRequests": external_requests,
                    "effectRequests": effect_requests,
                    "walletRequests": 0,
                    "mainnetTransactions": 0,
                    "runtimeExecutions": 0,
                    "canonicalChainObservation": False,
                    "manualScreenReaderTrial": "not performed",
                }
                (output / "edge-browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
                context.close()
                browser.close()
                return report
        finally:
            server.shutdown()
            server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.output)
    print(
        f"Cycle-edge Chromium acceptance passed: {len(report['controls'])} keyboard inspections, {len(report['audits'])} layouts"
    )


if __name__ == "__main__":
    main()
