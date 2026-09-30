[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# 1.21.0 — Finance Alpha: evidence before exposure

Finance Alpha now has a dependency-free local research terminal and a finite CLI.
The same engine powers the notebook, standalone HTML exports and recorded gallery examples.
Synthetic trend, reversal and gap scenarios expose both gains and losses; users can import
bounded, aligned price CSVs without contacting an external service.

Signals use prior closes and execute at the next supplied open. The cash ledger includes
fees, adverse slippage, average-cost realized P&L and marked open positions. A same-window,
same-cost buy-and-hold reference and cash baseline make comparisons inspectable. Historical
tail-risk checks and next-open drawdown exits expose their decisions and limitations.

Exports contain prices, configuration, every fill and equity mark, source fingerprints and
checksums. Exact replay rejects tampered measurements. The UI clears stale reports when settings
change or runs fail, supports retry, and provides accessible tables and offline JSON downloads.

The legacy agent's always-zero marked P&L and cashless position sizing are corrected. Portfolio
risk aligns asset histories; empty/positive tail samples and optional statistics now behave
correctly. Missing prices abort cycles, broker credentials alone do not activate testnet, and
uncertain order outcomes halt for review. Legacy Docker ports bind loopback and dotenv files
are parsed as literal values rather than executed. Original scripts, notebook and research
are retained byte-for-byte in a checksummed archive; original diagrams and gallery assets remain.

Release acceptance adds calculation, causality, replay, HTTP-boundary, browser and notebook
checks. Linux Python 3.11–3.13 is the release-tested platform. This is paper research, not a
profitability claim, real-funds deployment or achievement of the full autonomous-enterprise vision.
Native Mac/Windows operation and external broker/service integrations require separate validation.

[Finance setup and methodology](../demos/finance_alpha.md).
[Start here](START_HERE.md) for the wider agent installation and operator workflow.
