# SPDX-License-Identifier: Apache-2.0
"""Browser regressions for archived-history preservation and atomic save races."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, expect


def _idle(page: Page) -> None:
    """Wait for a completed, successfully saved browser action."""
    expect(page.locator("#evolve-import")).to_be_enabled(timeout=120000)
    expect(page.locator("#evolve-form")).to_have_attribute("aria-busy", "false")


def _history(page: Page) -> dict[str, Any]:
    """Read the same complete event record available through the UI export."""
    value: dict[str, Any] = json.loads(page.locator("#evolve-history-json").text_content() or "{}")
    return value


def _saved(page: Page, identity: str) -> dict[str, Any]:
    """Read actual IndexedDB bytes rather than assuming a successful UI write."""
    value: dict[str, Any] = page.evaluate(
        """id => new Promise((resolve, reject) => {
            const open = indexedDB.open('agialpha.out-evolve.workspace.v1', 1);
            open.onerror = () => reject(open.error);
            open.onsuccess = () => {
                const db = open.result;
                const tx = db.transaction('history', 'readonly');
                const request = tx.objectStore('history').get(id);
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
                tx.oncomplete = () => db.close();
            };
        })""",
        identity,
    )
    assert isinstance(value, dict), identity
    return value


def _import_history(page: Page, path: Path, identity: str) -> None:
    """Import an independently valid full history and verify its saved identity."""
    page.locator("#evolve-import").set_input_files(path)
    _idle(page)
    expect(page.locator("#evolve-status")).to_contain_text("History imported")
    assert _history(page)["id"] == identity
    assert _saved(page, "current") == _history(page)


def _reuse(page: Page, seed: int) -> dict[str, Any]:
    """Create a real independently checked continuation with a reproducible case seed."""
    page.evaluate(
        "seed => { crypto.getRandomValues = array => { array[0] = seed; return array; }; }",
        seed,
    )
    page.locator("#evolve-reuse").click()
    _idle(page)
    expect(page.locator("#evolve-status")).to_contain_text("Frozen-package reuse: PASS")
    return _history(page)


def _open_saved(page: Page, identity: str) -> None:
    """Open the saved-history disclosure and choose the actual stored record."""
    disclosure = page.locator("details").filter(has=page.locator("#evolve-saved"))
    if not disclosure.evaluate("element => element.open"):
        disclosure.locator("summary").click()
    page.locator("#evolve-saved").select_option(identity)
    page.locator("#evolve-open").click()
    _idle(page)


def _write(path: Path, value: object) -> None:
    """Retain actual histories and database observations as structured evidence."""
    path.write_text(json.dumps(value, indent=2) + "\n")


def _inject_archive_race(page: Page, later: dict[str, Any]) -> None:
    """Advance one archive atomically after read-only validation and before the application's save."""
    page.evaluate(
        """later => {
            window.__outEvolveArchiveRace = later;
            window.__outEvolveArchiveRaceFired = false;
            const transaction = IDBDatabase.prototype.transaction;
            IDBDatabase.prototype.transaction = function(stores, mode, ...options) {
                const names = typeof stores === 'string' ? [stores] : Array.from(stores);
                if (mode === 'readwrite' && names.includes('history') && window.__outEvolveArchiveRace) {
                    const next = window.__outEvolveArchiveRace;
                    window.__outEvolveArchiveRace = null;
                    window.__outEvolveArchiveRaceFired = true;
                    const race = transaction.call(this, stores, mode, ...options);
                    race.objectStore('history').put(next, next.id);
                }
                return transaction.call(this, stores, mode, ...options);
            };
        }""",
        later,
    )


def verify_archive_recovery(browser: Browser, url: str, package_path: Path, history_path: Path, output: Path) -> None:
    """Reject archived rollback/forks and protect every archive during racing history switches."""
    destination = output / "archive-recovery"
    destination.mkdir(parents=True, exist_ok=True)
    contexts: list[BrowserContext] = []
    errors: list[str] = []

    def new_page() -> Page:
        context = browser.new_context(accept_downloads=True)
        contexts.append(context)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        _idle(page)
        return page

    try:
        original_a: dict[str, Any] = json.loads(history_path.read_text())
        page = new_page()
        page.locator("#evolve-import").set_input_files(package_path)
        _idle(page)
        expect(page.locator("#evolve-status")).to_contain_text("Executable package imported")
        older_b = _history(page)
        assert older_b["id"] != original_a["id"]
        older_path = destination / "older-B.json"
        with page.expect_download() as downloaded:
            page.locator("#evolve-export-history").click()
        downloaded.value.save_as(older_path)
        assert json.loads(older_path.read_text()) == older_b
        later_b = _reuse(page, 0)
        _write(destination / "later-B.json", later_b)
        assert later_b["events"][: len(older_b["events"])] == older_b["events"]

        fork_page = new_page()
        _import_history(fork_page, older_path, older_b["id"])
        divergent_b = _reuse(fork_page, 1)
        assert divergent_b["revision"] == later_b["revision"]
        assert divergent_b["events"][-1]["digest"] != later_b["events"][-1]["digest"]
        divergent_path = destination / "divergent-B.json"
        _write(divergent_path, divergent_b)

        _import_history(page, history_path, original_a["id"])
        rejections: list[dict[str, Any]] = []
        for label, attempted in (("older", older_path), ("divergent", divergent_path)):
            before = _history(page)
            page.locator("#evolve-import").set_input_files(attempted)
            _idle(page)
            expect(page.locator("#evolve-error")).to_contain_text("discard or replace")
            expect(page.locator("#evolve-status")).not_to_contain_text("History imported")
            after = _history(page)
            assert after["id"] == original_a["id"]
            assert after["events"][: len(before["events"])] == before["events"]
            assert after["events"][-1]["kind"] == "failure"
            assert _saved(page, "current") == after
            assert _saved(page, later_b["id"]) == later_b
            _write(destination / f"{label}-rejection-current-A.json", after)
            rejections.append(
                {
                    "attempt": label,
                    "currentIdentityRetained": after["id"],
                    "latestBRevisionRetained": _saved(page, later_b["id"])["revision"],
                    "status": page.locator("#evolve-status").text_content(),
                    "error": page.locator("#evolve-error").text_content(),
                }
            )
        _open_saved(page, later_b["id"])
        assert _history(page) == later_b

        newer_a_page = new_page()
        _import_history(newer_a_page, history_path, original_a["id"])
        later_a = _reuse(newer_a_page, 2)
        assert later_a["events"][: len(original_a["events"])] == original_a["events"]
        _write(destination / "later-A.json", later_a)
        races: list[dict[str, Any]] = []
        for label, advanced in (("incoming-archive", later_b), ("saved-current-archive", later_a)):
            racing = new_page()
            _import_history(racing, older_path, older_b["id"])
            _import_history(racing, history_path, original_a["id"])
            _inject_archive_race(racing, advanced)
            racing.locator("#evolve-import").set_input_files(older_path)
            expect(racing.locator("#evolve-form")).to_have_attribute("aria-busy", "false", timeout=120000)
            expect(racing.locator("#evolve-retry-save")).to_be_visible()
            expect(racing.locator("#evolve-construct")).to_be_disabled()
            expect(racing.locator("#evolve-status")).to_contain_text("has not been saved")
            expect(racing.locator("#evolve-status")).not_to_contain_text("History imported")
            assert racing.evaluate("window.__outEvolveArchiveRaceFired") is True
            assert _history(racing) == older_b
            assert _saved(racing, "current") == original_a
            expected_a = later_a if label == "saved-current-archive" else original_a
            expected_b = later_b if label == "incoming-archive" else older_b
            assert _saved(racing, original_a["id"]) == expected_a
            assert _saved(racing, older_b["id"]) == expected_b
            candidate_path = destination / f"{label}-unsaved-candidate.json"
            with racing.expect_download() as downloaded:
                racing.locator("#evolve-export-history").click()
            downloaded.value.save_as(candidate_path)
            assert json.loads(candidate_path.read_text()) == older_b
            _write(destination / f"{label}-saved-A.json", expected_a)
            _write(destination / f"{label}-saved-B.json", expected_b)
            races.append(
                {
                    "race": label,
                    "injectedArchiveIdentity": advanced["id"],
                    "injectedArchiveRevision": advanced["revision"],
                    "currentPointerIdentity": _saved(racing, "current")["id"],
                    "currentPointerRevision": _saved(racing, "current")["revision"],
                    "archiveARevision": expected_a["revision"],
                    "archiveBRevision": expected_b["revision"],
                    "unsavedCandidateExported": True,
                    "status": racing.locator("#evolve-status").text_content(),
                    "error": racing.locator("#evolve-error").text_content(),
                }
            )
            racing.reload()
            _idle(racing)
            assert _history(racing) == original_a
            assert _saved(racing, original_a["id"]) == expected_a
            assert _saved(racing, older_b["id"]) == expected_b
            _open_saved(racing, advanced["id"])
            assert _history(racing) == advanced
        assert not errors, errors
        _write(destination / "archive-monotonicity.json", {"status": "PASS", "rejections": rejections, "races": races})
        print("Archived rollback/fork rejection and both atomic archive race guards: PASS")
    finally:
        for context in reversed(contexts):
            context.close()


def _abort_new_history_save(page: Page, identity: str, stage: str) -> None:
    """Abort the real current-pointer write once, before or after the identity switch."""
    page.evaluate(
        """({identity, stage}) => {
            window.__outEvolveNewHistoryAbort = {stage, fired: false, identity: null};
            let armed = true;
            const put = IDBObjectStore.prototype.put;
            IDBObjectStore.prototype.put = function(value, key) {
                const request = put.apply(this, arguments);
                const isOriginal = value && value.id === identity;
                if (armed && this.name === 'history' && key === 'current'
                    && (stage === 'old' ? isOriginal : !isOriginal)) {
                    armed = false;
                    window.__outEvolveNewHistoryAbort.fired = true;
                    window.__outEvolveNewHistoryAbort.identity = value.id;
                    const transaction = this.transaction;
                    queueMicrotask(() => transaction.abort());
                }
                return request;
            };
        }""",
        {"identity": identity, "stage": stage},
    )


def verify_new_history_recovery(browser: Browser, url: str, pending_history_path: Path, output: Path) -> None:
    """Retain a genuine pending search through either New history save failure and retry."""
    destination = output / "new-history-recovery"
    destination.mkdir(parents=True, exist_ok=True)
    original: dict[str, Any] = json.loads(pending_history_path.read_text())
    pending = original["events"][-1]["payload"]["checkpoint"]
    assert pending["status"] == "qualified"
    assert pending["options"]["maxCost"] == 500
    assert all(event["kind"] != "package-frozen" for event in original["events"])
    _write(destination / "original-pending-history.json", original)
    contexts: list[BrowserContext] = []
    errors: list[str] = []
    receipts: list[dict[str, Any]] = []

    def visible_state(page: Page) -> dict[str, Any]:
        return {
            "status": page.locator("#evolve-status").text_content(),
            "storage": page.locator("#evolve-storage").text_content(),
            "error": page.locator("#evolve-error").text_content(),
            "retryVisible": page.locator("#evolve-retry-save").is_visible(),
            "constructDisabled": page.locator("#evolve-construct").is_disabled(),
            "finalizeDisabled": page.locator("#evolve-resume").is_disabled(),
        }

    try:
        for stage in ("old", "new"):
            context = browser.new_context(accept_downloads=True)
            contexts.append(context)
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            _idle(page)
            _import_history(page, pending_history_path, original["id"])
            assert _history(page) == original
            expect(page.locator("#evolve-construct")).to_be_disabled()
            expect(page.locator("#evolve-resume")).to_be_disabled()
            expect(page.locator("#evolve-new-history")).to_be_enabled()
            _abort_new_history_save(page, original["id"], stage)
            page.locator("#evolve-new-history").click()
            expect(page.locator("#evolve-form")).to_have_attribute("aria-busy", "false", timeout=120000)
            expect(page.locator("#evolve-retry-save")).to_be_visible()
            expect(page.locator("#evolve-import")).to_be_disabled()
            expect(page.locator("#evolve-new-history")).to_be_disabled()
            expect(page.locator("#evolve-storage")).to_contain_text("has not been saved")
            expect(page.locator("#evolve-status")).not_to_contain_text("Separate construction history started")
            fault: dict[str, Any] = page.evaluate("window.__outEvolveNewHistoryAbort")
            assert fault["fired"] is True
            failed_history = _history(page)
            assert _saved(page, "current") == original
            assert _saved(page, original["id"]) == original
            if stage == "old":
                assert fault["identity"] == original["id"]
                assert failed_history == original
                exported_path = destination / "old-save-failed-export.json"
                with page.expect_download() as downloaded:
                    page.locator("#evolve-export-history").click()
                downloaded.value.save_as(exported_path)
                assert json.loads(exported_path.read_text()) == original
            else:
                assert fault["identity"] != original["id"]
                assert failed_history["id"] == fault["identity"]
                assert failed_history["revision"] == 0
                assert failed_history["events"] == []
                expect(page.locator("#evolve-status")).to_contain_text("previous history remains saved")
            _write(destination / f"{stage}-save-failed-visible.json", failed_history)
            _write(destination / f"{stage}-save-failed-db-current.json", _saved(page, "current"))
            _write(destination / f"{stage}-save-failed-archive.json", _saved(page, original["id"]))
            receipt: dict[str, Any] = {"stage": stage, "fault": fault, "afterFailure": visible_state(page)}

            page.locator("#evolve-retry-save").click()
            _idle(page)
            expect(page.locator("#evolve-retry-save")).to_be_hidden()
            expect(page.locator("#evolve-error")).to_be_hidden()
            assert _history(page) == failed_history
            assert _saved(page, "current") == failed_history
            assert _saved(page, original["id"]) == original
            receipt["afterRetry"] = visible_state(page)
            if stage == "old":
                expect(page.locator("#evolve-new-history")).to_be_enabled()
                page.locator("#evolve-new-history").click()
                _idle(page)
                expect(page.locator("#evolve-status")).to_contain_text("Separate construction history started")
            fresh_history = _history(page)
            assert fresh_history["id"] != original["id"]
            assert fresh_history["revision"] == 0
            assert fresh_history["events"] == []
            assert _saved(page, "current") == fresh_history
            assert _saved(page, fresh_history["id"]) == fresh_history
            assert _saved(page, original["id"]) == original
            _write(destination / f"{stage}-save-retried-fresh-history.json", fresh_history)

            page.reload()
            _idle(page)
            assert _history(page) == fresh_history
            assert _saved(page, original["id"]) == original
            _open_saved(page, original["id"])
            assert _history(page) == original
            assert _saved(page, "current") == original
            expect(page.locator("#evolve-construct")).to_be_disabled()
            expect(page.locator("#evolve-resume")).to_be_disabled()
            expect(page.locator("#evolve-new-history")).to_be_enabled()
            expect(page.locator("#evolve-status")).to_contain_text("Saved history opened after semantic checks")
            page.reload()
            _idle(page)
            assert _history(page) == original
            assert _saved(page, "current") == original
            assert _saved(page, original["id"]) == original
            assert _saved(page, fresh_history["id"]) == fresh_history
            expect(page.locator("#evolve-status")).to_contain_text("checkpoint is retained")
            _write(destination / f"{stage}-save-reopened-pending-history.json", _history(page))
            receipt.update(
                {
                    "freshIdentity": fresh_history["id"],
                    "freshRevision": fresh_history["revision"],
                    "reopenedIdentity": original["id"],
                    "reopenedRevision": original["revision"],
                    "originalCheckpointRetained": True,
                    "freshHistorySavedAfterRetry": True,
                    "afterReopenAndReload": visible_state(page),
                }
            )
            receipts.append(receipt)
        assert not errors, errors
        _write(destination / "new-history-save-recovery.json", {"status": "PASS", "cases": receipts})
        print("New-history original-save and fresh-save abort recovery: PASS")
    finally:
        for context in reversed(contexts):
            context.close()


def verify_report_capacity(browser: Browser, url: str, package_path: Path, output: Path) -> None:
    """Reject report work before evaluation when a valid history cannot retain its result."""
    destination = output / "report-capacity"
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    generator_path = destination / "generate-report-capacity.mjs"
    generator_path.write_text(
        """import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';
const [packagePath, destination, modulePath, constructorPath] = process.argv.slice(2);
const workspace = await import(pathToFileURL(modulePath).href);
const {canonical} = await import(pathToFileURL(constructorPath).href);
assert.equal(process.version, 'v22.17.1');
const pkg = JSON.parse(readFileSync(packagePath, 'utf8'));
assert.ok(!pkg.scope.includes('reservoir'));
const bytes = value => Buffer.byteLength(canonical(value), 'utf8');
const packageEvent = {status: 'qualified', package: pkg};
let full = workspace.createOutEvolveWorkspace('report-capacity-full-events');
full = await workspace.appendOutEvolveEvent(full, 'package-frozen', packageEvent);
while (full.events.length < workspace.WORKSPACE_LIMITS.events) {
    const filler = {
        kind: 'report-capacity-fixture', status: 'NOT-EVALUATED',
        description: 'Synthetic capacity fixture; no task evaluation was performed.', note: String(full.events.length)
    };
    if (full.events.length === 1) {
        filler.exposedCaseIds = {historical: 'non-array metadata'};
        filler.reuse = {exposedCaseIds: 'not-an-array'};
    }
    full = await workspace.appendOutEvolveEvent(full, 'comparison', filler);
}
const fullReport = await workspace.inspectOutEvolveWorkspace(full);
assert.deepEqual(fullReport.latestPackage, pkg);
assert.equal(fullReport.failed, 0);
assert.equal(fullReport.checkpoint, null);
let nearPrefix = workspace.createOutEvolveWorkspace('report-capacity-near-bytes');
nearPrefix = await workspace.appendOutEvolveEvent(nearPrefix, 'package-frozen', packageEvent);
const payload = {kind: 'report-capacity-fixture', status: 'NOT-EVALUATED',
    description: 'Synthetic capacity fixture; no task evaluation was performed.', note: '',
    exposedCaseIds: {historical: 'non-array metadata'}, reuse: {exposedCaseIds: 'not-an-array'}};
const emptyNote = await workspace.appendOutEvolveEvent(nearPrefix, 'comparison', payload);
const targetBytes = 7_999_000;
const padding = targetBytes - bytes(emptyNote);
assert.ok(padding > 0);
payload.note = 'é'.repeat(Math.floor(padding / 2)) + 'x'.repeat(padding % 2);
const near = await workspace.appendOutEvolveEvent(nearPrefix, 'comparison', payload);
const nearReport = await workspace.inspectOutEvolveWorkspace(near);
assert.equal(bytes(near), targetBytes);
assert.deepEqual(nearReport.latestPackage, pkg);
assert.equal(nearReport.failed, 0);
assert.equal(nearReport.checkpoint, null);
const cases = [];
for (const [name, value] of [['full-events-history.json', full], ['near-byte-history.json', near]]) {
    writeFileSync(join(destination, name), canonical(value));
    cases.push({name, id: value.id, events: value.events.length, canonicalUtf8Bytes: bytes(value)});
}
console.log(JSON.stringify({status: 'PASS', node: process.version, cases}));
"""
    )
    generated = subprocess.run(
        [
            os.environ.get("NODE_EXECUTABLE", "node"),
            str(generator_path),
            str(package_path.resolve()),
            str(destination.resolve()),
            str(root / "examples/successor-capability/out-evolve-workspace.mjs"),
            str(root / "examples/successor-capability/constructor.mjs"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    (destination / "fixture-generation.log").write_text(generated.stdout + generated.stderr)
    assert generated.returncode == 0, generated.stderr
    fixture_receipt: dict[str, Any] = json.loads(generated.stdout)
    assert fixture_receipt["node"] == "v22.17.1"
    _write(destination / "fixture-generation.json", fixture_receipt)
    accepted_package: dict[str, Any] = json.loads(package_path.read_text())
    contexts: list[BrowserContext] = []
    errors: list[str] = []
    receipts: list[dict[str, Any]] = []

    def new_page() -> Page:
        context = browser.new_context(accept_downloads=True)
        contexts.append(context)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        _idle(page)
        return page

    def capacity_controls(page: Page) -> None:
        expect(page.locator("#evolve-reuse")).to_be_disabled()
        expect(page.locator("#evolve-successor")).to_be_disabled()
        expect(page.locator("#evolve-new-history")).to_be_enabled()
        expect(page.locator("#evolve-export-package")).to_be_enabled()
        expect(page.locator("#evolve-export-history")).to_be_enabled()
        expect(page.locator("#evolve-retry-save")).to_be_hidden()

    try:
        for fixture in fixture_receipt["cases"]:
            fixture_path = destination / fixture["name"]
            expected: dict[str, Any] = json.loads(fixture_path.read_text())
            metadata = expected["events"][1]["payload"]
            assert metadata["exposedCaseIds"] == {"historical": "non-array metadata"}
            assert metadata["reuse"] == {"exposedCaseIds": "not-an-array"}
            label = "full-events" if fixture["events"] == 256 else "near-byte"
            page = new_page()
            _import_history(page, fixture_path, expected["id"])
            assert _history(page) == expected
            capacity_controls(page)
            page.evaluate(
                """() => {
                    window.__outEvolveCapacitySpies = {randomValuesCalls: 0, digestCalls: 0};
                    const randomValues = crypto.getRandomValues.bind(crypto);
                    const digest = crypto.subtle.digest.bind(crypto.subtle);
                    crypto.getRandomValues = (...args) => {
                        window.__outEvolveCapacitySpies.randomValuesCalls += 1;
                        return randomValues(...args);
                    };
                    crypto.subtle.digest = (...args) => {
                        window.__outEvolveCapacitySpies.digestCalls += 1;
                        return digest(...args);
                    };
                }"""
            )
            attempts: list[dict[str, Any]] = []
            for control in ("reuse", "successor"):
                page.locator(f"#evolve-{control}").dispatch_event("click")
                _idle(page)
                capacity_controls(page)
                expect(page.locator("#evolve-status")).to_contain_text(
                    re.compile(r"(capacity|retain|full|space|reserve)", re.IGNORECASE)
                )
                expect(page.locator("#evolve-status")).to_contain_text(
                    re.compile(r"(export|separate history)", re.IGNORECASE)
                )
                spies: dict[str, Any] = page.evaluate("window.__outEvolveCapacitySpies")
                assert spies == {"randomValuesCalls": 0, "digestCalls": 0}
                assert _history(page) == expected
                assert _saved(page, "current") == expected
                assert _saved(page, expected["id"]) == expected
                expect(page.locator("#evolve-error")).to_be_empty()
                attempts.append(
                    {"control": control, "spies": spies, "status": page.locator("#evolve-status").text_content()}
                )
            package_export = destination / f"{label}-accepted-package.json"
            with page.expect_download() as downloaded:
                page.locator("#evolve-export-package").click()
            downloaded.value.save_as(package_export)
            assert json.loads(package_export.read_text()) == accepted_package
            history_export = destination / f"{label}-exported-history.json"
            with page.expect_download() as downloaded:
                page.locator("#evolve-export-history").click()
            downloaded.value.save_as(history_export)
            assert json.loads(history_export.read_text()) == expected
            assert history_export.stat().st_size == fixture["canonicalUtf8Bytes"]
            assert history_export.stat().st_size <= 8_000_000
            receipt = {
                "fixture": fixture,
                "attempts": attempts,
                "acceptedPackageExportExact": True,
                "historyUnchanged": True,
                "historyExportBytes": history_export.stat().st_size,
                "nonArrayHistoricalMetadataRetained": {
                    "exposedCaseIds": metadata["exposedCaseIds"],
                    "reuse": metadata["reuse"],
                },
            }
            if label == "near-byte":
                roundtrip = new_page()
                _import_history(roundtrip, history_export, expected["id"])
                assert _history(roundtrip) == expected
                capacity_controls(roundtrip)
                roundtrip.reload()
                _idle(roundtrip)
                capacity_controls(roundtrip)
                assert _history(roundtrip) == expected
                assert _saved(roundtrip, "current") == expected
                assert _saved(roundtrip, expected["id"]) == expected
                with roundtrip.expect_download() as downloaded:
                    roundtrip.locator("#evolve-export-package").click()
                reloaded_package = destination / "near-byte-roundtrip-accepted-package.json"
                downloaded.value.save_as(reloaded_package)
                assert json.loads(reloaded_package.read_text()) == accepted_package
                receipt["exportFreshImportReloadExact"] = True
            receipts.append(receipt)
        overflow_page = new_page()
        overflow_page.locator("#evolve-import").set_input_files(package_path)
        _idle(overflow_page)
        expect(overflow_page.locator("#evolve-status")).to_contain_text("Executable package imported")
        original = _history(overflow_page)
        assert len(original["events"]) == 1
        assert original["events"][0]["kind"] == "package-frozen"
        assert original["events"][0]["payload"]["package"] == accepted_package
        _write(destination / "unexpected-overflow-original-history.json", original)
        expect(overflow_page.locator("#evolve-reuse")).to_be_enabled()
        overflow_page.evaluate(
            """() => {
                window.__outEvolveReportOverflow = {fired: false, actualUtf8Bytes: null, injectedUtf8Bytes: null};
                const encode = TextEncoder.prototype.encode;
                let armed = true;
                TextEncoder.prototype.encode = function(value) {
                    const encoded = encode.call(this, value);
                    if (armed && typeof value === 'string' && value.includes('"kind":"frozen-package-reuse"')) {
                        armed = false;
                        window.__outEvolveReportOverflow = {
                            fired: true, actualUtf8Bytes: encoded.length, injectedUtf8Bytes: 8_000_001
                        };
                        return new Uint8Array(8_000_001);
                    }
                    return encoded;
                };
            }"""
        )
        overflow_page.locator("#evolve-reuse").click()
        expect(overflow_page.locator("#evolve-export-report")).to_be_visible(timeout=120000)
        expect(overflow_page.locator("#evolve-form")).to_have_attribute("aria-busy", "false", timeout=120000)
        expect(overflow_page.locator("#evolve-status")).to_contain_text("evaluation completed")
        expect(overflow_page.locator("#evolve-status")).to_contain_text("complete report")
        expect(overflow_page.locator("#evolve-new-history")).to_be_disabled()
        expect(overflow_page.locator("#evolve-import")).to_be_disabled()
        expect(overflow_page.locator("#evolve-retry-save")).to_be_hidden()
        fault: dict[str, Any] = overflow_page.evaluate("window.__outEvolveReportOverflow")
        assert fault["fired"] is True
        assert 0 < fault["actualUtf8Bytes"] < 8_000_000
        assert fault["injectedUtf8Bytes"] == 8_000_001
        assert _history(overflow_page) == original
        assert _saved(overflow_page, "current") == original
        assert _saved(overflow_page, original["id"]) == original
        expect(overflow_page.locator("#evolve-error")).to_contain_text("storage reservation")
        pending_status = overflow_page.locator("#evolve-status").text_content()
        with overflow_page.expect_download() as downloaded:
            overflow_page.locator("#evolve-export-package").click()
        overflow_package = destination / "unexpected-overflow-accepted-package.json"
        downloaded.value.save_as(overflow_package)
        assert json.loads(overflow_package.read_text()) == accepted_package
        with overflow_page.expect_download() as downloaded:
            overflow_page.locator("#evolve-export-report").click()
        overflow_export = destination / "unexpected-overflow-report.json"
        downloaded.value.save_as(overflow_export)
        unrecorded: dict[str, Any] = json.loads(overflow_export.read_text())
        assert unrecorded["schema"] == "out-evolve-unrecorded-evaluation/v1"
        assert unrecorded["eventKind"] == "reuse"
        assert unrecorded["history"] == original
        assert unrecorded["package"] == accepted_package
        report = unrecorded["report"]
        assert report["kind"] == "frozen-package-reuse"
        assert len(report["cases"]) == 3
        assert len(report["measurements"]) == 24
        assert report["exposedCaseIds"] == [case["id"] for case in report["cases"]]
        assert report["ledger"]["tasks"] == len(report["cases"])
        assert report["ledger"]["measurementCalls"] == len(report["measurements"])
        assert report["ledger"]["total"] > 0
        assert report["packageDigestBefore"] == accepted_package["digest"]
        assert report["packageDigestAfter"] == accepted_package["digest"]
        assert _history(overflow_page) == original
        assert _saved(overflow_page, "current") == original
        assert _saved(overflow_page, original["id"]) == original
        _idle(overflow_page)
        expect(overflow_page.locator("#evolve-new-history")).to_be_enabled()
        expect(overflow_page.locator("#evolve-status")).to_contain_text("Start a separate history")
        overflow_receipt = {
            "faultInjection": "One completed reuse-report encoding returned an intentionally oversized byte array.",
            "fault": fault,
            "statusBeforeExport": pending_status,
            "statusAfterExport": overflow_page.locator("#evolve-status").text_content(),
            "historyAndDatabaseUnchanged": True,
            "acceptedPackageExportExact": True,
            "completeUnrecordedReportExported": True,
            "casesRetained": len(report["cases"]),
            "measurementsRetained": len(report["measurements"]),
            "exposedCaseIdsRetained": report["exposedCaseIds"],
            "ledgerRetained": report["ledger"],
            "explicitSeparateHistoryEnabledAfterExport": True,
        }
        assert not errors, errors
        _write(
            destination / "report-capacity-results.json",
            {
                "status": "PASS",
                "cases": receipts,
                "unexpectedOverflow": overflow_receipt,
                "pageErrors": errors,
                "evaluationSpiesInstalledAfterImport": True,
            },
        )
        print("Report capacity guards, compact export roundtrip and complete overflow-report recovery: PASS")
    finally:
        for context in reversed(contexts):
            context.close()
