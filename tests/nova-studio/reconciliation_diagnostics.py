# SPDX-License-Identifier: Apache-2.0
"""Failure-only public-state diagnostics for the disposable browser fixture."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit
from weakref import WeakKeyDictionary

HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
PRIVATE = re.compile(r"token|passphrase|secret|authorization|private.?key|password", re.IGNORECASE)
MONITORS: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()


def public_message(value: str) -> str:
    """Keep bounded fixture errors while discarding messages that may contain credentials."""
    return "[credential-related message omitted]" if PRIVATE.search(value) else value[:1600]


def monitor_action_failures(page: Any, output: Path) -> None:
    """Retain bounded error events for failure-only diagnostics on synthetic local pages."""
    state: dict[str, Any] = {"output": output, "console": [], "pageErrors": []}
    MONITORS[page] = state

    def console(message: Any) -> None:
        if message.type in {"error", "warning"}:
            state["console"].append({"type": message.type, "message": public_message(message.text)})
            state["console"][:] = state["console"][-20:]

    def error(value: Any) -> None:
        state["pageErrors"].append(public_message(str(value)))
        state["pageErrors"][:] = state["pageErrors"][-20:]

    page.on("console", console)
    page.on("pageerror", error)


def capture_action_failure(page: Any, operation: str, transaction: str | None = None) -> bool:
    """Preserve the failed synthetic action without wallet inputs, RPC parameters or retrying it."""
    try:
        monitor = MONITORS.get(page)
        if monitor is None or urlsplit(page.url).hostname != "127.0.0.1":
            return False
        if transaction is not None and not HASH.fullmatch(transaction):
            return False
        safe_operation = re.sub(r"[^a-zA-Z0-9-]", "-", operation)[:80]
        output = Path(monitor["output"])
        output.mkdir(parents=True, exist_ok=True)
        destination = output / f"action-failure-{safe_operation}.json"
        report = {
            "schema": "agialpha.disposable-action-failure.v1",
            "operation": safe_operation,
            "transaction": transaction,
            "console": monitor["console"],
            "pageErrors": monitor["pageErrors"],
            "state": None,
        }

        def save() -> None:
            destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

        # Save event evidence first, even when the failed page cannot answer a
        # short read. These diagnostics never extend or replace the assertion.
        save()
        responsive = False
        try:
            status = page.locator("#status").inner_text(timeout=1500)
            state = page.locator("html").evaluate(
                """() => {
                  let journal;
                  try { journal = JSON.parse(document.querySelector('#journal')?.textContent || 'null'); } catch {}
                  const fixture = window.__nova;
                  return {
                    controls: Object.fromEntries(['deployment-choice','confirm','reconcile','refresh-review']
                      .map(id => [id, document.getElementById(id)?.disabled ?? null])),
                    focusedControl: document.activeElement?.id || null,
                    statusError: document.querySelector('#status')?.classList.contains('error') === true,
                    sends: Number.isSafeInteger(fixture?.sends) ? fixture.sends : null,
                    recentMethods: (fixture?.calls || []).slice(-100)
                      .filter(method => typeof method === 'string' && /^eth_[A-Za-z]+$/.test(method)),
                    pendingReads: Object.values(fixture?.pendingReads || {}).slice(-20)
                      .map(read => ({method:read.method, ageMs:Math.max(0, Date.now()-read.startedAt)})),
                    recentReads: (fixture?.recentReads || []).slice(-20)
                      .map(read => ({method:read.method,outcome:read.outcome,errorCode:read.errorCode,
                        durationMs:Math.max(0,read.finishedAt-read.startedAt)})),
                    pendingIntents: (journal?.transactions || []).slice(-10)
                      .map(record => ({action:record.action,status:record.status,hash:record.hash ?? null}))
                  };
                }""",
                timeout=1500,
            )
            state["status"] = public_message(status)
            report["state"] = state
            save()
            responsive = True
            page.screenshot(path=str(output / f"action-failure-{safe_operation}.png"), full_page=True, timeout=2000)
        except Exception as error:
            responsive = False
            report["captureError"] = type(error).__name__
            save()
        return responsive
    except Exception:
        # A failed capture must never hide the original browser failure.
        return False


def capture_reconciliation_failure(page: Any, output: Path, transaction: str) -> None:
    """Never mask the original assertion or persist wallets, inputs or environment."""
    try:
        if urlsplit(page.url).hostname != "127.0.0.1" or not HASH.fullmatch(transaction):
            return
        state = page.evaluate(
            """async hash => {
          const fixture = window.__nova;
          let receipt;
          try {
            receipt = await Promise.race([
              window.ethereum.request({method:'eth_getTransactionReceipt',params:[hash]}),
              new Promise((_, reject) => setTimeout(() => reject(new Error('diagnostic deadline')), 2000))
            ]);
          } catch { receipt = undefined; }
          return {
            status: document.querySelector('#status')?.textContent?.startsWith('Submitted, not confirmed')
              ? 'submitted-not-confirmed' : 'other',
            confirmDisabled: document.querySelector('#confirm')?.disabled === true,
            reconcileDisabled: document.querySelector('#reconcile')?.disabled === true,
            sends: Number.isSafeInteger(fixture?.sends) ? fixture.sends : null,
            methods: (fixture?.calls || []).slice(-100).filter(x => typeof x === 'string' && /^eth_[A-Za-z]+$/.test(x)),
            receipt: receipt ? {transactionHash:receipt.transactionHash,blockHash:receipt.blockHash,
              blockNumber:receipt.blockNumber,status:receipt.status,gasUsed:receipt.gasUsed}
              : receipt === null ? null : 'unavailable'
          };
        }""",
            transaction,
        )
        (output / "reconciliation-failure.json").write_text(
            json.dumps(
                {"schema": "agialpha.disposable-reconciliation-failure.v1", "transaction": transaction, "state": state},
                indent=2,
            )
            + "\n"
        )
    except Exception:
        # Diagnostics must never turn the failed assertion into a different outcome.
        return
