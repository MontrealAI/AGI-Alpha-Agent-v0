# SPDX-License-Identifier: Apache-2.0
"""Browser regressions for archived-history preservation and atomic save races."""

from __future__ import annotations

import json
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
