# SPDX-License-Identifier: Apache-2.0
"""Exercise saved freeze, future tasks, docket and unprovisioned real-task preparation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import traceback
from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from playwright.sync_api import Page, expect, sync_playwright

if TYPE_CHECKING:
    from tests.browser import test_discovery_lab_browser as preserved
else:
    import test_discovery_lab_browser as preserved

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("DISCOVERY_CONTINUATION_EVIDENCE", "/tmp/discovery-continuation"))
FLEET_VARIANTS = (
    "executor",
    "runtime",
    "elapsed",
    "memory",
    "outcome",
    "raw-framing",
    "receipt-framing",
    "request-framing",
    "source-repository",
    "forged-authority",
    "swapped-mission",
)


def fleet_return(page: Page) -> dict[str, Any]:
    """Return actual pinned Fleet native bytes to the browser's existing saved mission."""
    fleet_root = os.environ.get("DISCOVERY_FLEET_ROOT")
    required = os.environ.get("DISCOVERY_FLEET_REQUIRED") == "1"
    if not fleet_root:
        if required:
            raise RuntimeError("Required native Fleet acceptance has no pinned checkout")
        return {"state": "NOT_RUN", "checks": [], "scope": "Standalone run did not request native Fleet acceptance"}
    output = OUTPUT / "fleet-native"
    workspace_path, request_path = OUTPUT / "fleet-browser-workspace.json", OUTPUT / "fleet-browser-request.json"
    original_workspace = preserved.download_json(page, "#export", workspace_path)
    preserved.download_request(page, request_path, "USDC")
    try:
        native = subprocess.run(
            [
                "node",
                str(ROOT / "tests/browser/fleet_receipt_native.mjs"),
                str(Path(fleet_root).resolve()),
                str(workspace_path.resolve()),
                str(request_path.resolve()),
                str(output.resolve()),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "NODE_OPTIONS": "", "NODE_PATH": ""},
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or ""
        stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
        (OUTPUT / "fleet-native.log").write_text(
            f"Native helper exceeded its 180-second process deadline: {error}\n{stdout}{stderr}"
        )
        raise
    (OUTPUT / "fleet-native.log").write_text(native.stdout + native.stderr)
    native.check_returncode()
    proof = json.loads((output / "native-proof.json").read_text())
    assert proof["variants"] == list(
        FLEET_VARIANTS
    ), "Every predeclared native receipt attack case is required exactly once"
    assert proof["workspaceSha256"] == hashlib.sha256(workspace_path.read_bytes()).hexdigest()
    assert proof["requestSha256"] == hashlib.sha256(request_path.read_bytes()).hexdigest()
    assert proof["sourceHash"] == json.loads((OUTPUT / "served/sources.json").read_text())["sourceHash"]
    page.locator("#lab-import-receipt").set_input_files(output / "wrapper.json")
    expect(page.locator("#lab-receipt-status")).to_contain_text("Receiver receipt retained", timeout=120000)
    accepted_path = OUTPUT / "fleet-return-docket.json"
    accepted = preserved.download_json(page, "#lab-export-docket", accepted_path)
    costs = json.loads(accepted["files"]["08_cost_ledgers/costs.json"])
    assert costs["commissions"] == [] and costs["receiverInspectionByRoute"] == {}
    assert costs["fleetLocalReviewObservations"] == proof["receipt"]["resources"]
    assert costs["totalComplete"] is False
    returned = json.loads(accepted["files"]["05_agialpha_runs/run.json"])["workspace"]
    assert returned["missionId"] == proof["missionId"]
    assert len(returned["events"]) == len(original_workspace["events"]) + 1
    assert json.dumps(returned["events"][:-1], sort_keys=True) == json.dumps(
        original_workspace["events"], sort_keys=True
    )
    assert returned["revision"] == original_workspace["revision"] + 1
    assert returned["events"][-1]["kind"] == "lab-evidence-attached"
    assert returned["events"][-1]["previous"] == original_workspace["events"][-1]["digest"]
    assert returned["events"][-1]["payload"]["kind"] == "receiver-receipt"
    assert returned["events"][-1]["payload"]["campaignDigest"] == proof["campaignDigest"]
    assert returned["events"][-1]["payload"]["record"] == json.loads((output / "wrapper.json").read_text())
    exported = preserved.download_json(page, "#export", OUTPUT / "fleet-return-workspace.json")
    assert json.dumps(exported, sort_keys=True) == json.dumps(returned, sort_keys=True)
    expected_bytes = accepted_path.read_bytes()
    for name in FLEET_VARIANTS:
        page.locator("#lab-import-receipt").set_input_files(output / f"{name}.json")
        expect(page.locator("#lab-receipt-status")).to_contain_text("Receiver receipt rejected:", timeout=120000)
        path = OUTPUT / f"fleet-refused-{name}-docket.json"
        preserved.download_json(page, "#lab-export-docket", path)
        assert path.read_bytes() == expected_bytes, name
    response = page.reload()
    assert response is not None and response.body() == (OUTPUT / "served/index.html").read_bytes()
    expect(page.locator("#lab-export-docket")).to_be_enabled(timeout=120000)
    reopened = OUTPUT / "fleet-reopened-docket.json"
    preserved.download_json(page, "#lab-export-docket", reopened)
    assert reopened.read_bytes() == expected_bytes
    return {
        "state": "source-module-browser-return-passed",
        "checks": [
            "actual-native-return",
            "separate-cost-ledger",
            "raw-request-and-receipt-retained",
            *["refused-" + name for name in FLEET_VARIANTS],
            "reload-byte-identity",
        ],
        "docketSha256": hashlib.sha256(expected_bytes).hexdigest(),
        "scope": proof["scope"],
    }


@contextmanager
def retain_failure(page: Page, sources: dict[str, Any]) -> Iterator[None]:
    """Retain a refused journey as failed evidence with its actual visible state."""
    try:
        yield
    except BaseException as error:
        record: dict[str, Any] = {
            "passed": False,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "source": sources,
            "scope": "failed-local-generated-continuation-acceptance",
        }
        try:
            record["visibleState"] = page.evaluate(
                "() => Object.fromEntries([\n                'lab-future-status', 'lab-status"
                "', 'lab-error', 'error', 'identity', 'lab-run-future', 'lab-commit-future',"
                "\n                'lab-freeze-future', 'lab-real-task-report'].map(id => {co"
                "nst item = document.getElementById(id);\n                return [id, item ? "
                "{text: item.textContent, disabled: item.disabled ?? null, hidden: item.hidd"
                "en} : null];}))"
            )
            (OUTPUT / "failure-page.html").write_text(page.content())
            page.screenshot(path=str(OUTPUT / "failure.png"), full_page=True)
        except Exception as capture_error:
            record["diagnosticCaptureError"] = str(capture_error)
        (OUTPUT / "failure.json").write_text(json.dumps(record, indent=2))
        raise


def main() -> None:
    """Run actual controls and retain exact browser downloads and dispositions."""
    if not __debug__:
        raise RuntimeError("Continuation acceptance requires Python assertion checks enabled")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    packaged = ROOT / "docs/successor/capabilities"
    frozen = OUTPUT / "served"
    frozen.mkdir(parents=True, exist_ok=True)
    for name in ["index.html", "sources.json"]:
        (frozen / name).write_bytes((packaged / name).read_bytes())
    destination = frozen / "index.html"
    expected_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(preserved.QuietHandler, directory=str(destination.parent)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            )
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            sources = json.loads((destination.parent / "sources.json").read_text())
            with retain_failure(page, sources):
                response = page.goto(url)
                print("Continuation page loaded", flush=True)
                assert response is not None and response.body() == destination.read_bytes()
                page.locator("#lab-public-confirmation").check()
                preserved.idle(page)
                page.locator("#lab-construct").click()
                preserved.idle(page)
                expect(page.locator("#lab-outcome-summary")).to_contain_text("ACCEPTED")
                print("Accepted construction saved", flush=True)
                page.locator("#lab-freeze-future").click()
                expect(page.locator("#lab-commit-future")).to_be_enabled(timeout=120000)
                print("Frozen capability saved", flush=True)
                page.locator("#lab-future-seed").fill("18")
                page.locator("#lab-commit-future").click()
                expect(page.locator("#lab-future-status")).not_to_contain_text(
                    "Committing the complete", timeout=120000
                )
                expect(page.locator("#lab-run-future")).to_be_enabled(timeout=5000)
                print("Future bank committed", flush=True)
                response = page.reload()
                assert response is not None and hashlib.sha256(response.body()).hexdigest() == expected_hash
                expect(page.locator("#lab-run-future")).to_be_enabled(timeout=120000)
                page.locator("#lab-future-budget").fill("3000000")
                page.locator("#lab-run-future").click()
                expect(page.locator("#lab-future-status")).to_contain_text("Complete comparison saved", timeout=120000)
                print("All future alternatives saved", flush=True)
                report = json.loads(page.locator("#lab-future-report").inner_text())["evaluation"]
                assert len(report["runs"]) == 42
                assert any(run["status"] == "rejected" for run in report["runs"])
                assert any(item["relation"] == "warm-tie" for row in report["relations"] for item in row["comparisons"])
                summaries = {row["treatment"]: row for row in report["summaries"]}
                assert sum(summaries["competent-static"]["total"].values()) < sum(
                    summaries["frozen-capability"]["total"].values()
                )
                page.locator("#lab-prepare-real-task").click()
                expect(page.locator("#lab-future-status")).to_contain_text("contract saved as NOT_RUN", timeout=120000)
                contract = json.loads(page.locator("#lab-real-task-report").inner_text())
                assert contract["operationalState"] == "NOT_RUN" and contract["authority"] == "none"
                identity_before = page.locator("#identity").inner_text()
                page.locator("#lab-import-receipt").set_input_files(
                    {
                        "name": "malformed-receiver.json",
                        "mimeType": "application/json",
                        "buffer": json.dumps({"raw": "{}", "source": {}}).encode(),
                    }
                )
                expect(page.locator("#lab-receipt-status")).to_contain_text(
                    "Receiver receipt rejected:", timeout=120000
                )
                expect(page.locator("#identity")).to_have_text(identity_before)
                docket = preserved.download_json(page, "#lab-export-docket", OUTPUT / "browser-docket.json")
                assert len(docket["files"]) == 13
                history = json.loads(docket["files"]["05_agialpha_runs/run.json"])["workspace"]
                kinds = [
                    event["payload"]["kind"] for event in history["events"] if event["kind"] == "lab-evidence-attached"
                ]
                assert kinds == [
                    "future-freeze",
                    "future-task-bank",
                    "future-run-reserved",
                    "future-evaluation",
                    "real-task-contract",
                ]
                (OUTPUT / "browser-workspace.json").write_text(json.dumps(history))
                before = page.locator("#lab-future-report").inner_text()
                response = page.reload()
                assert response is not None and hashlib.sha256(response.body()).hexdigest() == expected_hash
                expect(page.locator("#lab-future-report")).to_have_text(before, timeout=120000)
                expect(page.locator("#lab-run-future")).to_be_disabled()
                expect(page.locator("#lab-real-task-report")).to_contain_text("NOT_RUN")
                expect(page.locator("#lab-deployment-summary")).to_contain_text('"recordedContracts": 39')
                fleet = fleet_return(page)
                preserved.OUTPUT = OUTPUT
                preserved.audit(page, "continuation-desktop")
                page.set_viewport_size({"width": 320, "height": 900})
                preserved.audit(page, "continuation-mobile")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.locator("#discovery-lab").screenshot(path=str(OUTPUT / "mobile-continuation.png"))
                assert not errors
                receipt = {
                    "passed": True,
                    "pageSha256": expected_hash,
                    "source": json.loads((destination.parent / "sources.json").read_text()),
                    "checks": [
                        "saved-freeze",
                        "separate-bank",
                        "reload-before-execution",
                        "actual-frozen-invocations",
                        "all-seven-arms",
                        "losses-and-ties",
                        "saved-reservation",
                        "real-task-NOT_RUN",
                        "malformed-receiver-rejected-without-history-change",
                        "docket-download",
                        "reload-after-result",
                        "39-recorded-contracts",
                        "accessibility",
                        "320px",
                    ],
                    "pageErrors": errors,
                    "fleetLocalReview": fleet,
                    "scope": "local-generated-synthetic; no public release or operational pilot",
                }
                (OUTPUT / "journey.json").write_text(json.dumps(receipt, indent=2))
                print(
                    json.dumps(
                        {
                            "passed": True,
                            "checks": len(receipt["checks"]),
                            "fleetState": fleet["state"],
                            "fleetChecks": len(fleet["checks"]),
                        }
                    )
                )
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
