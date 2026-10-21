<!-- SPDX-License-Identifier: Apache-2.0 -->
# Frozen future-task continuation: exact local evidence

Source PR: #4853. Final source commit c8486c611ee1c8be354a03a3b7a6a7ece442f6e8,
tree 2024238cd46f80f29d254691f9bc3a8a105984c8, normal parent d1d17d724a9eefc23e655f097b19de995523053b.
The only difference from tested d1 is AST-identical wrapping of a browser diagnostic
literal to satisfy the configured 120-character Flake8 limit. All 35 production
catalog inputs, generated HTML/catalog and 432-asset workers are byte-identical.
Both public commits are unsigned; no verified-signature claim is made.

Production sourceHash: 1c6d719a9b5b78878fb4ec9b813c4b38dad91d0483f63c111b7be0ad926090b5.
Generated page SHA256: 98603c3b7de92686e5265476217514a01f6f3fc605e15cda0d07a9f25373b90c.

## Known configured findings on this historical source

Configured review on d1 found two valid P2s, also present in c848:
[embedded-request reframing can bypass semantic receipt deduplication](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4853#discussion_r4343168923)
and [timed-out RPC needs internal cancellation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4853#discussion_r4343168930).
These findings are not cleared by the passing results below. Repairs and fresh
source-bound qualification are in progress separately; retain this evidence as
historical positive cases with explicitly unresolved boundaries.

## Observed results

- Required Node command:355/355 on Node22.17.1; raw TAP retained.
- Delivery:16/16 in isolated pytest8.4.1. Strict typing:10files pass local
  mypy1.17.0; required hosted2.4.0 is not inferred from this.
- Independent workspace/snapshot regressions:49/49 on22.17.1 and24.21.0.
- New actual Playwright journey:14/14, no page errors, desktop/mobile Axe.
- Preserved Discovery Lab journey:12/12 on the same production source.
- Actual public Manager68d1 and Jobs852 adapters plus independently captured
  current Alpha inspector: both browser-exported requests return real local
  receipts. Browser return journey:8/8, no page errors, exact raw bytes,
  duplicate refusal without history change, separate currency accounting,
  same mission and byte-identical docket after explicit saved-mission reopening.
- The downloaded thirteen-section docket independently replays against its
  expected mission/head. Its totalComplete:false and unattested source context
  remain explicit. No authority is created by imported receipts.

The receipt helper independently authenticates source bytes/catalog and rebuilds
campaign context/caps from the actual exported history; it does not supply a
fixture receipt or borrow a browser acceptance boolean. Manager and Jobs are
public source executions, not installed-package or release acceptance. Fleet is
outside this particular browser return proof.

## Reproduction and custody

The original source commit contains the browser test and normal workflow gate.
The reproduction helpers here retain original local paths for traceability; set
the documented input paths to the downloaded unchanged files in a new isolated
checkout. Never rebind old histories to a new source. Source manifest hashes
identify all41candidatefiles relative to0c; the evidence manifest independently
hashes every retained file. The rendered mobile PNG is the actual browser capture. Verbose Axe/contrast JSON
records are losslessly gzip-compressed; the manifest binds both compressed bytes
and the original decoded raw bytes. No result was rewritten during compression.

The exact baseline reconstruction used committed0c assets plus candidate files,
not the other owner's mutable checkout. It independently regenerated the same
page/catalog and three workers from432assets. Early partial-checkout missing
imports/vectors, stale catalog failures, unrelated installed pytest-plugin
corruption and the fixed two-line Flake8 failure remain under historical-failures.
The final pytest environment contains only the required packages, with no
unrelated plugins. Earlier browser reload failure is retained unchanged; its
source is historical. The first receipt helper's auto-open assumption was fixed
by using the existing saved selector and explicit Open flow, with no product
change. These failures are not relabeled as passing acceptance.

The supplied competent static alternative is cheaper overall. Public seeded
cases are not protected holdouts. Live deployment inspection and operational
real-task execution remain NOT_RUN. Full hooks/Python coverage, configured
review, hosted artifacts, paper integration, installed receiver/profile checks,
final-main checks, releases, public HTTPS and current-chain verification remain
separate required gates. No gate is waived by this evidence branch.
