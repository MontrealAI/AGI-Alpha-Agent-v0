# SPDX-License-Identifier: Apache-2.0
"""Real same-origin native budget forms, races and exact interrupted-request recovery."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
import socket
import threading
import time
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, Request, Route, expect, sync_playwright
import uvicorn

from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.budget import BudgetCommand, BudgetScope, inspect, operate
from alpha_factory_v1.core.runtime.store import Journal

ROOT = Path(__file__).resolve().parents[2]
KEY = "agialpha.native-budget.pending.v1"
SCOPE = BudgetScope(owner="0x" + "a" * 40, chain_id=31337, token="0x" + "b" * 40)


@pytest.fixture
def native(tmp_path: Path) -> Iterator[tuple[Journal, str, str]]:
    journal = Journal.initialize(tmp_path / "agent")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    try:
        yield journal, origin, (journal.root / "api.token").read_text().strip()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


@contextmanager
def browser() -> Iterator[Browser]:
    with sync_playwright() as driver:
        assert Path(driver.chromium.executable_path).is_file(), "Install pinned Chromium before browser acceptance"
        instance = driver.chromium.launch(headless=True)
        try:
            yield instance
        finally:
            instance.close()


def login(page: Page, origin: str, token: str, *, navigate: bool = True) -> None:
    if navigate:
        page.goto(origin + "/budget-studio")
    page.locator("#token").fill(token)
    page.locator("#token").press("Enter")
    expect(page.locator("#workspace")).to_be_visible()
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
    expect(page.locator("#token")).to_have_value("")


def inspect_scope(page: Page, *, restored: bool = False) -> None:
    if not restored:
        page.locator("#owner").fill(SCOPE.owner)
        page.locator("#chain-id").fill(str(SCOPE.chain_id))
        page.locator("#asset-token").fill(SCOPE.token)
    page.locator("#inspect").press("Enter")
    expect(page.locator("#snapshot-panel")).to_be_visible()
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")


def prepare(
    page: Page,
    action: str,
    amount: str = "0",
    reservation: str = "",
    *,
    purpose: str = "Reviewed project/cycle planning; no wallet authority",
) -> dict[str, Any]:
    page.locator("#action").select_option(action)
    if action != "set_limit":
        page.locator("#reservation-id").fill(reservation)
    if action not in {"release", "commit"}:
        page.locator("#amount").fill(amount)
    page.locator("#purpose").fill(purpose)
    page.locator("#prepare").press("Enter")
    expect(page.locator("#preview-panel")).to_be_visible()
    expect(page.locator("#confirm")).to_be_disabled()
    envelope: dict[str, Any] = json.loads(page.locator("#preview-record").inner_text())
    page.locator("#confirm-ack").focus()
    page.keyboard.press("Space")
    expect(page.locator("#confirm-ack")).to_be_checked()
    return envelope


def confirm(page: Page) -> None:
    page.locator("#confirm").press("Enter")
    expect(page.locator("#message")).to_contain_text("Request recorded")
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
    expect(page.locator("#pending-panel")).to_be_hidden()


def seed(journal: Journal, amount: str = "10") -> None:
    operate(
        journal,
        BudgetCommand(
            scope=SCOPE,
            request_id="initial",
            action="set_limit",
            expected_revision=0,
            amount=amount,
            purpose="Synthetic native browser planning ceiling",
        ),
    )


def retained(page: Page) -> str | None:
    value: str | None = page.evaluate("key=>sessionStorage.getItem(key)", KEY)
    return value


def test_actual_forms_exact_units_keyboard_localization_and_accessibility(
    native: tuple[Journal, str, str], tmp_path: Path
) -> None:
    journal, origin, token = native
    with browser() as instance:
        page = instance.new_page(viewport={"width": 1440, "height": 1080})
        errors: list[str] = []
        mutations: list[dict[str, Any]] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script(
            "window.__walletCalls=[];window.ethereum={request:p=>{window.__walletCalls.push(p);throw Error('Forbidden');}}"
        )

        def remember_request(request: Request) -> None:
            if request.url.endswith("/budget/operate"):
                payload = request.post_data_json
                assert isinstance(payload, dict)
                mutations.append(payload)

        page.on("request", remember_request)
        page.goto(origin + "/ascension-studio")
        expect(page.get_by_role("link", name="Planning budget", exact=True)).to_have_attribute("href", "/budget-studio")
        page.get_by_role("link", name="Planning budget", exact=True).click()
        login(page, origin, token, navigate=False)
        assert not mutations and retained(page) is None
        inspect_scope(page)
        expect(page.locator("#snapshot-state")).to_contain_text("No pool")
        limit = str(2**200)
        preview = prepare(page, "set_limit", limit)
        assert preview["command"]["expected_revision"] == 0
        assert preview["journal"] == journal.identity
        assert not mutations and retained(page) is None
        confirm(page)
        assert inspect(journal, SCOPE)["limit"] == limit
        expect(page.locator("#totals")).to_contain_text(limit)
        # Native bounds count Unicode characters, not JavaScript UTF-16 code units.
        prepare(page, "reserve", "9007199254740993", "p" * 64, purpose="📋" * 500)
        confirm(page)
        assert inspect(journal, SCOPE)["available"] == str(2**200 - 9007199254740993)
        assert inspect(journal, SCOPE)["reservations"]["p" * 64]["purpose"] == "📋" * 500
        prepare(page, "commit", reservation="p" * 64)
        confirm(page)
        assert inspect(journal, SCOPE)["committed"] == "9007199254740993"
        prepare(page, "reserve", "7", "project-second")
        confirm(page)
        prepare(page, "release", reservation="project-second")
        confirm(page)
        state = inspect(journal, SCOPE)
        assert state["reservations"]["project-second"]["state"] == "released"
        assert state["committed"] == "9007199254740993"
        assert not state["wallet_balance_verified"] and not state["external_transfers_prevented"]
        assert token not in page.evaluate("JSON.stringify({...sessionStorage,...localStorage})")
        assert page.evaluate("window.__walletCalls") == []
        axe = (ROOT / "tests/browser/node_modules/axe-core/axe.min.js").read_text()
        page.evaluate(axe)
        for language in ["en", "fr"]:
            page.locator("#language").select_option(language)
            expect(page.locator("html")).to_have_attribute("lang", language)
            expect(page.locator("#message")).to_contain_text(
                "Demande enregistrée" if language == "fr" else "Request recorded"
            )
            for width in [1440, 390, 320]:
                page.set_viewport_size({"width": width, "height": 1080})
                audit = page.evaluate(
                    "async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
                )
                assert not audit["violations"], audit["violations"]
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                page.screenshot(path=str(tmp_path / f"budget-{language}-{width}.png"), full_page=True)
        page.locator("#disconnect").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#workspace")).to_be_hidden()
        expect(page.locator("#token")).to_have_value("")
        assert not errors


def test_two_real_browser_sessions_race_current_revision_and_reconcile_rejection(
    native: tuple[Journal, str, str],
) -> None:
    journal, origin, token = native
    seed(journal)
    with browser() as instance:
        pages = [instance.new_page(), instance.new_page()]
        for index, page in enumerate(pages):
            login(page, origin, token)
            inspect_scope(page)
            prepare(page, "reserve", "7", f"project-{index}")
        for page in pages:
            page.evaluate("document.getElementById('confirm').click()")
        for page in pages:
            expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        assert inspect(journal, SCOPE)["reserved"] == "7"
        assert inspect(journal, SCOPE)["available"] == "3"
        rejected = [page for page in pages if page.locator("#pending-panel").is_visible()]
        assert len(rejected) == 1
        page = rejected[0]
        expect(page.locator("#pending-state")).to_contain_text("explicit rejection")
        expect(page.locator("#prepare")).to_be_disabled()
        pending = json.loads(retained(page) or "null")
        assert pending["state"] == "rejected"
        inspect_scope(page, restored=True)
        page.locator("#dismiss-ack").check()
        page.locator("#dismiss").click()
        assert retained(page) is None
        inspect_scope(page)
        prepare(page, "reserve", "3", "remaining-project")
        confirm(page)
        assert inspect(journal, SCOPE)["reserved"] == "10"
        assert len(inspect(journal, SCOPE)["reservations"]) == 2


def test_committed_response_loss_reload_and_exact_retry_do_not_duplicate(
    native: tuple[Journal, str, str], tmp_path: Path
) -> None:
    journal, origin, token = native
    seed(journal)
    with browser() as instance:
        page = instance.new_page(accept_downloads=True)
        login(page, origin, token)
        inspect_scope(page)
        envelope = prepare(page, "reserve", "7", "lost-response")
        sent: list[dict[str, Any]] = []
        headers: list[str | None] = []

        def lose_response(route: Route) -> None:
            payload = route.request.post_data_json
            assert isinstance(payload, dict)
            sent.append(payload)
            headers.append(route.request.header_value("X-AGIALPHA-Journal"))
            response = route.fetch()
            assert response.status == 200
            if len(sent) == 1:
                route.abort("failed")
            else:
                route.fulfill(response=response)

        page.route("**/api/budget/operate", lose_response)
        page.locator("#confirm").click()
        expect(page.locator("#message")).to_contain_text("Response unavailable")
        assert inspect(journal, SCOPE)["reserved"] == "7"
        before = journal.verify()
        assert json.loads(retained(page) or "null")["command"] == envelope["command"]
        assert token not in (retained(page) or "")
        with page.expect_download() as exported:
            page.locator("#export-pending").click()
        path = tmp_path / "pending.json"
        exported.value.save_as(path)
        assert token not in path.read_text()
        assert json.loads(path.read_text())["command"] == envelope["command"]
        page.reload()
        expect(page.locator("#workspace")).to_be_hidden()
        expect(page.locator("#token")).to_have_value("")
        assert len(sent) == 1
        login(page, origin, token, navigate=False)
        expect(page.locator("#retry")).to_be_disabled()
        inspect_scope(page, restored=True)
        page.locator("#retry-ack").check()
        page.locator("#retry").click()
        expect(page.locator("#message")).to_contain_text("Exact request recognized")
        assert sent == [envelope["command"], envelope["command"]]
        assert headers == [journal.identity, journal.identity]
        assert journal.verify() == before
        assert retained(page) is None


def test_offline_changed_journal_and_untrusted_recovery_fail_closed(native: tuple[Journal, str, str]) -> None:
    journal, origin, token = native
    seed(journal)
    with browser() as instance:
        page = instance.new_page()
        login(page, origin, token)
        inspect_scope(page)
        prepare(page, "reserve", "7", "offline-project")
        page.context.set_offline(True)
        page.locator("#confirm").click()
        expect(page.locator("#message")).to_contain_text("Response unavailable")
        expect(page.locator("#prepare")).to_be_disabled()
        expect(page.locator("#retry")).to_be_disabled()
        assert inspect(journal, SCOPE)["reserved"] == "0"
        page.context.set_offline(False)
        page.locator("#disconnect").click()
        expect(page.locator("#workspace")).to_be_hidden()
        login(page, origin, token, navigate=False)
        inspect_scope(page, restored=True)
        page.locator("#retry-ack").check()
        page.route(
            "**/api/status",
            lambda route: route.fulfill(json={"valid": True, "identity": "urn:agialpha:ed25519:" + "f" * 64}),
        )
        page.locator("#retry").click()
        expect(page.locator("#message")).to_contain_text("journal changed")
        assert inspect(journal, SCOPE)["reserved"] == "0"
        original = json.loads(retained(page) or "null")
        page.unroute("**/api/status")
        # An exact-shape recovery record for another journal cannot authorize this one.
        foreign = {**original, "journal": "urn:agialpha:ed25519:" + "f" * 64}
        page.evaluate("([key,value])=>sessionStorage.setItem(key,JSON.stringify(value))", [KEY, foreign])
        page.reload()
        login(page, origin, token, navigate=False)
        inspect_scope(page, restored=True)
        page.locator("#retry-ack").check()
        expect(page.locator("#retry")).to_be_disabled()
        expect(page.locator("#prepare")).to_be_disabled()
        expect(page.locator("#pending-state")).to_contain_text("different journal")
        for raw in ['{"unexpected":"value"}', "x" * 8193]:
            page.evaluate("([key,value])=>sessionStorage.setItem(key,value)", [KEY, raw])
            page.reload()
            login(page, origin, token, navigate=False)
            expect(page.locator("#invalid-panel")).to_be_visible()
            inspect_scope(page)
            expect(page.locator("#prepare")).to_be_disabled()
            assert inspect(journal, SCOPE)["reserved"] == "0"


def test_disconnect_during_committed_response_keeps_exact_recovery_and_ignores_late_result(
    native: tuple[Journal, str, str],
) -> None:
    journal, origin, token = native
    seed(journal)
    with browser() as instance:
        page = instance.new_page()
        login(page, origin, token)
        inspect_scope(page)
        envelope = prepare(page, "reserve", "7", "disconnect-project")

        def disconnect_after_commit(route: Route) -> None:
            response = route.fetch()
            assert response.status == 200
            page.locator("#disconnect").click()
            try:
                route.fulfill(response=response)
            except Exception:
                # Disconnect deliberately aborts the pending fetch; the native commit persists.
                pass

        page.route("**/api/budget/operate", disconnect_after_commit)
        page.locator("#confirm").click()
        expect(page.locator("#workspace")).to_be_hidden()
        expect(page.locator("#token")).to_have_value("")
        assert inspect(journal, SCOPE)["reserved"] == "7"
        assert json.loads(retained(page) or "null")["command"] == envelope["command"]
        before = journal.verify()
        page.unroute("**/api/budget/operate")
        login(page, origin, token, navigate=False)
        inspect_scope(page, restored=True)
        page.locator("#retry-ack").check()
        page.locator("#retry").click()
        expect(page.locator("#message")).to_contain_text("Exact request recognized")
        assert journal.verify() == before


def test_preview_expiry_scope_changes_and_unavailable_storage_never_dispatch(native: tuple[Journal, str, str]) -> None:
    journal, origin, token = native
    seed(journal)
    with browser() as instance:
        page = instance.new_page()
        page.clock.install()
        login(page, origin, token)
        inspect_scope(page)
        prepare(page, "reserve", "7", "constructor")
        page.clock.fast_forward(60001)
        expect(page.locator("#prepare")).to_be_disabled()
        expect(page.locator("#preview-panel")).to_be_hidden()
        assert inspect(journal, SCOPE)["reserved"] == "0"
        inspect_scope(page)
        prepare(page, "reserve", "7", "constructor")
        page.locator("#owner").fill("0x" + "c" * 40)
        expect(page.locator("#preview-panel")).to_be_hidden()
        expect(page.locator("#prepare")).to_be_disabled()
        inspect_scope(page)
        prepare(page, "reserve", "7", "constructor")
        # A storage-denied browser must not send a request it cannot recover exactly.
        page.evaluate(
            "() => { Storage.prototype.setItem=function(){throw new DOMException('Denied','SecurityError')}; }"
        )
        page.locator("#confirm").click()
        expect(page.locator("#invalid-panel")).to_be_visible()
        expect(page.locator("#prepare")).to_be_disabled()
        assert inspect(journal, SCOPE)["reserved"] == "0"
        assert retained(page) is None
