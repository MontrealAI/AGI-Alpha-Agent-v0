# SPDX-License-Identifier: Apache-2.0
"""Failure-only public-state diagnostics for the disposable browser fixture."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


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
              blockNumber:receipt.blockNumber,status:receipt.status,gasUsed:receipt.gasUsed} : receipt === null ? null : 'unavailable'
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
