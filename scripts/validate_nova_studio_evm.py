# SPDX-License-Identifier: Apache-2.0
"""Drive the shipped Nova Studio UI against a disposable exact-source local EVM."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread
import time
import tomllib
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import Page, expect, sync_playwright

from scripts.build_mark_wallet import build_local_profile
from scripts.nova_studio_evidence import EVM_CHECKS, ROOT, hashes, verify_evm_report

PROVIDER = r"""
(() => {
  const actors = ['business','validator1','validator2','validator3','funder','agent'];
  const state = {calls:[],sends:[],providers:[]};
  for (const [index, actor] of actors.entries()) {
    const events = new Map();
    const provider = {
      on(name, fn) { if (!events.has(name)) events.set(name,new Set()); events.get(name).add(fn); },
      removeListener(name, fn) { events.get(name)?.delete(fn); },
      async request(request) {
        state.calls.push({actor,method:request.method});
        const response = await window.__novaRPC({actor,request});
        if (response.error) throw Object.assign(new Error(response.error.message), {code:response.error.code});
        if (request.method==='eth_sendTransaction') state.sends.push({actor,hash:response.result});
        return response.result;
      }
    };
    state.providers.push({info:{uuid:`00000000-0000-4000-8000-${String(index+1).padStart(12,'0')}`,
      name:`Local fixture · ${actor}`,rdns:`test.nova.${actor}`},provider});
  }
  const announce = () => state.providers.forEach(detail =>
    window.dispatchEvent(new CustomEvent('eip6963:announceProvider',{detail})));
  window.addEventListener('eip6963:requestProvider',announce);
  window.__novaFixture=state;
  window.ethereum=state.providers[0].provider;
})();
"""


class Handler(SimpleHTTPRequestHandler):
    """Serve the copied build under a Pages project prefix."""

    def translate_path(self, path: str) -> str:
        return super().translate_path(path.removeprefix("/project"))

    def log_message(self, format: str, *args: object) -> None:
        pass


def fixture_request(fixture: dict[str, Any], path: str, data: dict[str, Any]) -> dict[str, Any]:
    """Send only to the authenticated, loopback disposable fixture."""
    if not fixture["endpoint"].startswith("http://127.0.0.1:"):
        raise ValueError("The browser acceptance fixture must be loopback-only")
    request = Request(
        fixture["endpoint"] + path,
        data=json.dumps(data).encode(),
        headers={"Authorization": "Bearer " + fixture["token"], "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as error:
        payload = json.loads(error.read())
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("The fixture must return a JSON object with string keys")
    return payload


def native_delivery(directory: Path, plan: dict[str, Any]) -> tuple[bytes, str, dict[str, Any]]:
    """Execute, review and sign a real bounded native mission for the exported plan."""
    from alpha_factory_v1.core.runtime.ascension import delivery, verify_delivery
    from alpha_factory_v1.core.runtime.engine import Engine
    from alpha_factory_v1.core.runtime.models import Mission
    from alpha_factory_v1.core.runtime.store import Journal, digest

    mission = Mission.model_validate(
        {
            "goal": plan["jobs"][0]["spec"]["goal"],
            "work": {
                "kind": "allocation",
                "budget": 10,
                "items": [{"id": "one", "cost": 3, "value": 8}, {"id": "two", "cost": 7, "value": 10}],
            },
        }
    )
    journal = Journal.initialize(directory / "native-state")
    engine = Engine(journal)
    record = engine.execute(journal.submit(mission)["id"])
    assert record["state"] == "review"
    assert record["result"]["value"] == 18 and record["result"]["cost"] == 10
    assert set(record["result"]["selected"]) == {"one", "two"}
    engine.review(
        record["id"],
        record["revision"],
        digest(record["result"]),
        True,
        "Local synthetic fixture review recomputed both items; not an independent real-world reviewer.",
    )
    data = delivery(journal, plan, 0, record["id"])
    verified = verify_delivery(data, journal.public, plan["planRoot"])
    if not isinstance(data, bytes) or not isinstance(journal.public, str) or not isinstance(verified, dict):
        raise ValueError("The native Engine did not return a signed delivery with verification")
    assert verified["valid"] is True
    return data, journal.public, verified


def validate(site: Path, output: Path) -> dict[str, Any]:
    """Exercise production browser controls through paid settlement on a disposable EVM."""
    output.mkdir(parents=True, exist_ok=True)
    source_assets = hashes()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    completed: list[str] = []
    errors: list[str] = []
    transactions: list[dict[str, Any]] = []
    storage_requests: list[dict[str, Any]] = []
    server = None
    process = None
    log = None
    report: dict[str, Any] = {
        "schema": "agialpha.nova-studio.evm-browser.v1",
        "passed": False,
        "commit": commit,
        "version": version,
        "sourceAssets": source_assets,
        "exactSource": True,
        "chainId": 31337,
        "realMainnetTransactions": False,
        "physicalWalletValidated": False,
        "realStorageProviderValidated": False,
        "fixtureLimitations": (
            "Disposable unforked local EVM; token, ENS, admission, review actors and public IPFS transport are "
            "fixtures. No real-world independent reviewer, storage provider or wallet hardware is certified."
        ),
        "checks": completed,
        "receipts": transactions,
        "storageRequests": storage_requests,
    }
    with tempfile.TemporaryDirectory(prefix="nova-studio-browser-") as temporary:
        temporary_root = Path(temporary)
        try:
            fixture_dir = temporary_root / "fixture"
            fixture_dir.mkdir()
            log = (output / "fixture.log").open("w")
            environment = dict(os.environ, NOVA_FIXTURE_OUTPUT=str(fixture_dir))
            process = subprocess.Popen(
                ["node", "scripts/nova-fixture.js"],
                cwd=ROOT / "tests/contracts",
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 45
            while not (fixture_dir / "fixture.json").exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Disposable EVM fixture did not start; inspect fixture.log")
                time.sleep(0.1)
            fixture = json.loads((fixture_dir / "fixture.json").read_text())
            if fixture["profile"]["chainId"] != 31337 or fixture["profile"]["mainnetQualification"] is not False:
                raise ValueError("Unexpected fixture chain or qualification")
            isolated = temporary_root / "site"
            for folder in ("assets", "ascension", "ascension-protocol"):
                shutil.copytree(site / folder, isolated / folder)
            built_profile = build_local_profile(
                ROOT, fixture_dir / "profile.json", isolated / "assets/ascension-wallet"
            )
            profile = json.loads(built_profile.read_text())
            report["profileHash"] = hashlib.sha256(
                json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest()
            report["profile"] = profile
            (output / "local-profile.json").write_text(json.dumps(profile, indent=2) + "\n")
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(isolated)))
            Thread(target=server.serve_forever, daemon=True).start()
            origin = f"http://127.0.0.1:{server.server_port}/project/"
            report["origin"] = "isolated local Pages build"
            artifacts: dict[str, bytes] = {}
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(
                    viewport={"width": 1440, "height": 1100}, accept_downloads=True, timezone_id="UTC"
                )
                context.expose_binding("__novaRPC", lambda _source, data: fixture_request(fixture, "/rpc", data))
                context.add_init_script(script=PROVIDER)

                def storage_route(route: Any) -> None:
                    request = route.request
                    if request.url.startswith(origin.removesuffix("project/")):
                        route.continue_()
                        return
                    cors = {
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Authorization,Content-Type",
                    }
                    if request.url == "https://uploads.pinata.cloud/v3/files":
                        if request.method == "OPTIONS":
                            route.fulfill(status=204, headers={**cors, "Access-Control-Allow-Methods": "POST,OPTIONS"})
                            return
                        assert request.method == "POST"
                        assert request.headers.get("authorization") == "Bearer LOCAL_FIXTURE_STORAGE_ONLY"
                        content_type = request.headers["content-type"]
                        message = BytesParser(policy=policy.default).parsebytes(
                            b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + (request.post_data_buffer or b"")
                        )
                        fields = {
                            part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
                            for part in message.iter_parts()
                        }
                        assert fields["network"] == b"public"
                        data = fields["file"]
                        if not isinstance(data, bytes):
                            raise ValueError("The public artifact upload must contain file bytes")
                        cid = "b" + base64.b32encode(
                            b"\x01\x55\x12\x20" + hashlib.sha256(data).digest()
                        ).decode().lower().rstrip("=")
                        artifacts[cid] = data
                        storage_requests.append({"operation": "upload", "cid": cid, "bytes": len(data)})
                        route.fulfill(
                            status=200,
                            content_type="application/json",
                            headers=cors,
                            body=json.dumps({"data": {"cid": cid}}),
                        )
                    elif request.url.startswith(("https://gateway.pinata.cloud/ipfs/", "https://ipfs.io/ipfs/")):
                        cid = request.url.rsplit("/", 1)[-1]
                        storage_requests.append({"operation": "retrieve", "cid": cid})
                        route.fulfill(
                            status=200 if cid in artifacts else 404,
                            content_type="application/json",
                            headers=cors,
                            body=artifacts.get(cid, b"{}"),
                        )
                    else:
                        errors.append("Unexpected external request: " + request.url)
                        route.abort()

                context.route("**/*", storage_route)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("requestfailed", lambda request: errors.append(request.url + ": " + str(request.failure)))
                page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                page.set_default_timeout(30000)

                def step(number: int) -> None:
                    page.locator(f"[data-step='{number}']").click()

                def actor(name: str) -> None:
                    step(3)
                    page.locator("#discover").click()
                    option = page.locator("#wallet-choice option").filter(has_text="Local fixture · " + name)
                    expect(option).to_have_count(1)
                    page.locator("#wallet-choice").select_option(option.get_attribute("value"))
                    page.locator("#connect").click()
                    expect(page.locator("#status")).to_contain_text("connected", ignore_case=True)
                    page.locator("#journal-consent").check()
                    page.locator("#inspect-wallet").click()
                    expect(page.locator("#status")).to_contain_text("observation verified", ignore_case=True)

                def transaction(button: str, label: str) -> None:
                    count = page.evaluate("window.__novaFixture.sends.length")
                    page.locator(button).click()
                    try:
                        expect(page.locator("#preview-panel")).to_be_visible()
                    except Exception as error:
                        raise AssertionError(
                            label + " preview failed: " + page.locator("#status").inner_text()
                        ) from error
                    expect(page.locator("#confirm")).to_be_disabled()
                    page.locator("#preview-ack").check()
                    page.locator("#confirm").click()
                    expect(page.locator("#status")).to_contain_text("Submitted, not yet confirmed", timeout=30000)
                    assert page.evaluate("window.__novaFixture.sends.length") == count + 1
                    sent = page.evaluate("window.__novaFixture.sends.at(-1)")
                    step(6)
                    page.locator("#refresh-receipt").click()
                    expect(page.locator("#status")).to_contain_text("finalized", ignore_case=True)
                    receipt = fixture_request(
                        fixture,
                        "/rpc",
                        {
                            "actor": sent["actor"],
                            "request": {"method": "eth_getTransactionReceipt", "params": [sent["hash"]]},
                        },
                    )["result"]
                    assert receipt["status"] == "0x1"
                    transactions.append(
                        {
                            "action": label,
                            **sent,
                            "transactionHash": sent["hash"],
                            "status": receipt["status"],
                            "receipt": receipt,
                        }
                    )
                    report["checks"] = completed

                page.goto(origin + "ascension/mainnet/")
                expect(page.locator("#mode")).to_be_visible()
                assert not page.evaluate(
                    "window.__novaFixture.calls.some(c=>c.method==='eth_requestAccounts'"
                    "||c.method==='eth_sendTransaction')"
                )
                completed.append("ui-no-wallet-preparation")
                page.locator("#start-explore").click()
                page.locator("#project-name").fill("Local fixture · verifiable resource allocation")
                page.locator("#project-description").fill(
                    "Run a bounded native mission on explicit synthetic inputs, then review its signed result."
                )
                page.locator(".job-goal").fill(
                    "Allocate budget 10 across synthetic items one (cost 3, value 8) and two (cost 7, value 10)."
                )
                page.locator(".job-success").fill(
                    "Select both items: total cost 10 and value 18 within budget 10. "
                    "Return the signed native delivery bound to the exact FusionPlan."
                )
                page.locator("#compile").click()
                expect(page.locator("#plan-next")).to_be_enabled()
                page.locator("#plan-next").click()
                page.locator("#evidence-text").fill(
                    "Local EVM acceptance fixture. Public synthetic inputs; this is not an independent live review."
                )
                passphrase = "local EVM browser acceptance passphrase only"
                page.locator("#passphrase").fill(passphrase)
                page.locator("#passphrase-confirm").fill(passphrase)
                page.locator("#seal-package").click()
                expect(page.locator("#export-kit")).to_be_enabled()
                page.locator("#recovery-disclosure").check()
                with page.expect_download() as download:
                    page.locator("#export-kit").click()
                kit_path = output / "local-pre-mint-recovery-kit.json"
                download.value.save_as(kit_path)
                kit = json.loads(kit_path.read_text())
                assert passphrase not in kit_path.read_text()
                plan = kit["content"]["package"]["plan"]
                completed.append("ui-compile-seal-recover-export")
                page.locator("#public-name").fill("Local fixture · Nova UI lifecycle")
                page.locator("#public-description").fill(
                    "Exact-source disposable EVM acceptance. No Mainnet transaction."
                )
                page.locator("#publication-disclosure").check()
                page.locator("#storage-token").fill("LOCAL_FIXTURE_STORAGE_ONLY")
                page.locator("#publish").click()
                expect(page.locator("#status")).to_contain_text("verified", ignore_case=True)
                assert len(artifacts) == 3
                completed.append("ui-publication-roundtrip-fixture-transport")
                page.screenshot(path=str(output / "01-published.png"), full_page=True)
                actor("business")
                completed.append("ui-explicit-wallet-selection")
                transaction("#mint", "seal")
                seed_id = page.locator("#summary-seed").inner_text().strip()
                assert seed_id.isdigit() and int(seed_id) > 0
                report["seedId"] = seed_id
                completed.append("ui-mint-receipt-and-readback")
                step(4)
                transaction("#request-review", "openReview")
                for name in ("validator1", "validator2"):
                    actor(name)
                    step(4)
                    details = page.locator("#attest-risk").locator("xpath=ancestor::details[1]")
                    if details.count() and details.get_attribute("open") is None:
                        details.locator("summary").click()
                    page.locator("#risk-score").fill("1000")
                    page.locator("#risk-decision").select_option("true")
                    page.locator("#risk-evidence").fill(kit["content"]["package"]["commitments"]["evidenceHash"])
                    transaction("#attest-risk", "attest")
                completed.append("ui-separate-validator-review-transactions")
                actor("business")
                step(4)
                block = fixture_request(
                    fixture,
                    "/rpc",
                    {"actor": "business", "request": {"method": "eth_getBlockByNumber", "params": ["latest", False]}},
                )["result"]
                total = int(plan["totalBounty"])
                budget = str((total + 10**18 - 1) // 10**18)
                page.locator("#campaign-base").fill("1")
                page.locator("#campaign-slope").fill("0")
                page.locator("#campaign-lots").fill(budget)
                page.locator("#campaign-target").fill(budget)
                page.locator("#campaign-end").fill(
                    datetime.fromtimestamp(int(block["timestamp"], 16) + 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M")
                )
                page.locator("#campaign-days").fill("14")
                transaction("#open-campaign", "open")
                actor("funder")
                step(6)
                transaction("#revoke-allowance", "approve-reset")
                step(4)
                page.locator("#fund-lots").fill(budget)
                page.locator("#quote-funding").click()
                expect(page.locator("#fund-max")).to_have_value(budget)
                transaction("#approve-funding", "approve")
                step(4)
                transaction("#fund", "buy")
                completed.append("ui-campaign-open-and-funding")
                actor("business")
                step(5)
                transaction("#activate", "bloom")
                completed.append("ui-bloom-phase-transition")
                step(5)
                page.locator("#route-job").select_option("0")
                page.locator("#auction-seconds").fill("60")
                for index in range(1, 4):
                    page.locator(f"#reviewer-{index}").fill(fixture["actors"][f"validator{index}"])
                transaction("#route", "route")
                job_id = page.locator("#summary-job").inner_text().strip()
                assert job_id.isdigit() and int(job_id) > 0
                report["jobId"] = job_id
                completed.append("ui-committed-first-job-routing")
                step(5)
                expect(page.locator("#execution-states")).to_contain_text("Not connected", ignore_case=True)
                completed.append("ui-runtime-not-connected-truth")
                page.screenshot(path=str(output / "02-job-posted.png"), full_page=True)
                with page.expect_download() as download:
                    page.locator("#export-work").click()
                work_path = output / "local-work-package.json"
                download.value.save_as(work_path)
                work_package = json.loads(work_path.read_text())
                assert work_package["seedId"] == seed_id and work_package["jobId"] == job_id
                assert work_package["plan"] == plan and work_package["planIndex"] == 0
                with page.expect_download() as download:
                    page.locator("#export-native-plan").click()
                native_plan_path = output / "local-fusion-plan.json"
                download.value.save_as(native_plan_path)
                native_plan = json.loads(native_plan_path.read_text())
                assert native_plan == plan
                mark_url = page.locator("#work-mark-link").evaluate("element => element.href")
                assert mark_url.startswith(origin + "ascension-protocol/mainnet/")
                mark_page = context.new_page()
                mark_page.on("pageerror", lambda error: errors.append(str(error)))
                mark_page.goto(mark_url)
                expect(mark_page.locator("#seed-id")).to_have_value(seed_id)
                expect(mark_page.locator("#job-id")).to_have_value(job_id)

                def mark_actor(name: str) -> None:
                    mark_page.locator("#discover").click()
                    choice = mark_page.locator("#wallet-choice option").filter(has_text="Local fixture · " + name)
                    expect(choice).to_have_count(1)
                    mark_page.locator("#wallet-choice").select_option(choice.get_attribute("value"))
                    mark_page.locator("#connect").click()
                    expect(mark_page.locator("#status")).to_contain_text("Account connected")

                def mark_action(action: str, fields: dict[str, str]) -> None:
                    mark_page.locator("#action").select_option(action)
                    for field, value in fields.items():
                        control = mark_page.locator("#field-" + field)
                        if control.evaluate("element => element.tagName") == "SELECT":
                            control.select_option(value)
                        else:
                            control.fill(value)
                    mark_page.locator("#prepare").click()
                    try:
                        expect(mark_page.locator("#preview-panel")).to_be_visible()
                    except Exception as error:
                        raise AssertionError(
                            "MARK " + action + " preview failed: " + mark_page.locator("#status").inner_text()
                        ) from error
                    expect(mark_page.locator("#confirm")).to_be_disabled()
                    mark_page.locator("#ack").check()
                    count = mark_page.evaluate("window.__novaFixture.sends.length")
                    mark_page.locator("#confirm").click()
                    expect(mark_page.locator("#status")).to_contain_text("Submitted, not yet confirmed", timeout=30000)
                    assert mark_page.evaluate("window.__novaFixture.sends.length") == count + 1
                    mark_page.locator("#receipt").click()
                    expect(mark_page.locator("#status")).to_contain_text("finalized")
                    sent = mark_page.evaluate("window.__novaFixture.sends.at(-1)")
                    receipt = fixture_request(
                        fixture,
                        "/rpc",
                        {
                            "actor": sent["actor"],
                            "request": {"method": "eth_getTransactionReceipt", "params": [sent["hash"]]},
                        },
                    )["result"]
                    assert receipt["status"] == "0x1"
                    transactions.append(
                        {
                            "action": action,
                            "surface": "shared-mark",
                            **sent,
                            "transactionHash": sent["hash"],
                            "status": receipt["status"],
                            "receipt": receipt,
                        }
                    )

                mark_actor("agent")
                mark_action("approve", {"spender": "Jobs", "amount": "0"})
                mark_action("approve", {"spender": "Jobs", "amount": "10"})
                mark_action("agentDeposit", {"amount": "10"})
                mark_action("bid", {"job": job_id, "price": "80", "duration": "3600"})
                mark_page.locator("#inspect").click()
                expect(mark_page.locator("#status")).to_contain_text("Observation complete")
                awarded = json.loads(mark_page.locator("#snapshot").text_content())
                advanced = fixture_request(fixture, "/advance", {"timestamp": int(awarded["job"]["auctionEnd"]) + 1})
                assert "error" not in advanced, advanced
                mark_action("award", {"job": job_id})

                def token_observation() -> dict[str, str]:
                    values = {}
                    for name in ("agent", "validator1", "validator2", "funder"):
                        data = "0x70a08231" + fixture["actors"][name][2:].rjust(64, "0")
                        result = fixture_request(
                            fixture,
                            "/rpc",
                            {
                                "actor": "business",
                                "request": {
                                    "method": "eth_call",
                                    "params": [
                                        {"to": profile["contracts"]["Token"]["address"], "data": data},
                                        "latest",
                                    ],
                                },
                            },
                        )
                        assert "error" not in result, result
                        values[name] = str(int(result["result"], 16))
                    result = fixture_request(
                        fixture,
                        "/rpc",
                        {
                            "actor": "business",
                            "request": {
                                "method": "eth_call",
                                "params": [
                                    {"to": profile["contracts"]["Token"]["address"], "data": "0x18160ddd"},
                                    "latest",
                                ],
                            },
                        },
                    )
                    assert "error" not in result, result
                    values["totalSupply"] = str(int(result["result"], 16))
                    return values

                balances_before = token_observation()
                result_bytes, public_key, native_verified = native_delivery(temporary_root, native_plan)
                result_hash = native_verified["resultHash"]
                result_cid = "b" + base64.b32encode(
                    b"\x01\x55\x12\x20" + hashlib.sha256(result_bytes).digest()
                ).decode().lower().rstrip("=")
                artifacts[result_cid] = result_bytes
                delivery_path = output / "local-worker-delivery.json"
                delivery_path.write_bytes(result_bytes)
                report["nativeDelivery"] = {
                    "publicKey": public_key,
                    "verification": native_verified,
                    "byteDigest": hashlib.sha256(result_bytes).hexdigest(),
                    "bytes": len(result_bytes),
                    "uiHashAutofilled": False,
                    "uiSubmission": False,
                    "runtimeConnected": False,
                }
                page.bring_to_front()
                actor("agent")
                step(5)
                delivery_details = page.locator("#verify-delivery").locator("xpath=ancestor::details[1]")
                delivery_details.locator("summary").click()
                page.locator("#delivery-key").fill(public_key)
                page.locator("#delivery-file").set_input_files(delivery_path)
                page.locator("#verify-delivery").click()
                expect(page.locator("#status")).to_contain_text("Delivery verified")
                expect(page.locator("#delivery-result-hash")).to_have_value(result_hash)
                expect(page.locator("#delivery-result-hash")).to_have_attribute("readonly", "")
                expect(page.locator("#execution-states")).to_contain_text("Not connected")
                report["nativeDelivery"]["uiHashAutofilled"] = True
                page.locator("#delivery-uri").fill("ipfs://" + result_cid)
                transaction("#submit-delivery", "submit")
                report["nativeDelivery"]["uiSubmission"] = True
                mark_page.bring_to_front()
                for name in ("validator1", "validator2"):
                    mark_actor(name)
                    from alpha_factory_v1.core.runtime.ascension import verify_delivery

                    reviewed = verify_delivery(artifacts[result_cid], public_key, plan["planRoot"])
                    assert reviewed["valid"] is True and reviewed["resultHash"] == result_hash
                    mark_action(
                        "validate",
                        {
                            "job": job_id,
                            "result": result_hash,
                            "approved": "true",
                            "evidence": kit["content"]["package"]["commitments"]["evidenceHash"],
                        },
                    )
                mark_page.locator("#inspect").click()
                expect(mark_page.locator("#status")).to_contain_text("Observation complete")
                settlement_observation = json.loads(mark_page.locator("#snapshot").text_content())
                assert settlement_observation["job"]["state"] == "4", settlement_observation["job"]
                assert settlement_observation["job"]["resultHash"] == result_hash
                (output / "local-settlement-observation.json").write_text(
                    json.dumps(settlement_observation, indent=2) + "\n"
                )
                balances_after = token_observation()
                deltas = {name: str(int(balances_after[name]) - int(balances_before[name])) for name in balances_before}
                assert deltas["agent"] == "75240000000000000000", deltas
                assert deltas["validator1"] == deltas["validator2"] == "1980000000000000000", deltas
                assert deltas["funder"] == "0" and deltas["totalSupply"] == "-800000000000000000", deltas
                assert settlement_observation["job"]["refund"] == "20000000000000000000"
                report["settlement"] = {
                    "state": "paid",
                    "resultHash": result_hash,
                    "resultURI": "ipfs://" + result_cid,
                    "worker": fixture["actors"]["agent"],
                    "job": settlement_observation["job"],
                    "accounting": {
                        "before": balances_before,
                        "after": balances_after,
                        "deltas": deltas,
                        "verified": True,
                    },
                }
                mark_page.screenshot(path=str(output / "03-result-settled-mark.png"), full_page=True)
                mark_page.close()
                page.bring_to_front()
                step(4)
                page.locator("#refresh-review").click()
                expect(page.locator("#status")).to_contain_text("observations refreshed")
                step(5)
                expect(page.locator("#execution-states")).to_contain_text("Accepted payment")
                expect(page.locator("#execution-states")).to_contain_text("Not connected")
                page.screenshot(path=str(output / "04-settlement-in-studio.png"), full_page=True)
                completed.append("ui-worker-delivery-review-settlement")
                step(6)
                with page.expect_download() as download:
                    page.locator("#export-kit-again").click()
                routed_kit = output / "local-routed-recovery-kit.json"
                download.value.save_as(routed_kit)
                exported = json.loads(routed_kit.read_text())
                assert len(exported["content"]["receipts"]) >= 8
                assert passphrase not in routed_kit.read_text()
                completed.append("ui-recovery-kit-after-routing")
                assert not errors, errors
                browser.close()
            assert hashes() == source_assets, "The production asset set changed during the isolated fixture test"
            completed.append("production-profile-unchanged")
            report["storageRequests"] = storage_requests
            report["passed"] = True
            assert set(completed) == set(EVM_CHECKS)
            verify_evm_report(report, commit, version)
        except Exception as error:
            report["passed"] = False
            report["error"] = str(error)
            report["browserErrors"] = errors
            raise
        finally:
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            if server:
                server.shutdown()
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            if log:
                log.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "docs")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.site, arguments.output), indent=2))
