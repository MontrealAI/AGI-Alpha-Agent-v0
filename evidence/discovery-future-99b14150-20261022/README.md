<!-- SPDX-License-Identifier: Apache-2.0 -->
# Repaired frozen-capability continuation

This dataset supports [PR #4853](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4853),
source commit `b062fde0118ca74e1f36fc96816ca6985ab64bc8`, tree
`00475e4f52bfeaedeec000cfc8a7741f8d38c1fc`. All 43 changed Git blobs, modes and sizes
match the independent source freeze. The commit is unsigned.

The [combined docket](native/same-history/browser-native-docket.json) and
[original mission](native/same-history/browser-native-workspace.json) retain the
actual browser requests, native receipts, treatments, controls and costs.

| Check | Observed result |
| --- | --- |
| Required Node selection, pinned 22.17.1 | 365/365 pass |
| Delivery, isolated pytest 8.4.1 | 16/16 pass |
| Fresh continuation browser journey | 14/14 pass |
| Preserved primary browser journey | 12/12 pass |
| Regenerated mirror browser journey | 12/12 pass |
| Actual Manager + Jobs receipt return journey | 8/8 pass |
| Nested-request attack in the browser | Duplicate refused; history and costs unchanged |
| Independent combined docket replay | Verified against expected mission and head |

Browser runs retain desktop/mobile Axe records and report no page errors. The
Manager and Jobs helpers invoke actual public source adapters with the captured
Alpha inspector, using the original browser-exported requests. They do not return
fixture receipts. Both receipts return to the same saved mission; raw bytes,
separate currency ledgers and the docket survive reopening unchanged.

## Source and evidence identity

- Production sourceHash: `99b14150b2ee503198687a2ff45b8adddf48acbbeadfa57151cd57a6442a0b0d`.
- Primary page SHA256: `1b2183fc4b27ce8865c6f183dcf24372d9ac5ab9dd90fbf0ed3530fb75a30c18`.
- Mirror page SHA256: `0d13bb8bdb320dda00e233c47ce7ed3caa33a05a013c3bb6db412cd380a15d8f`.
- Combined docket SHA256: `e56d3764326990477647922227120cf7d19050aa03e1bdc20ebba0580c1c6c00`.
- Mission: `capability-0714044c-3ef6-4979-b5b1-a104a2abfb18`.
- Final head: `8fa9100e8abcb70732c408ebc967c613032e798b74931d1b2e5794545fef25a6`.

Both page catalogs bind the same 35 source inputs. Ordinary mirror generation
changes links while preserving script/style bytes and their CSP. All 432 cache
assets regenerate to `agialpha-gallery-aadc2dd992f746f6`.

## Review finding repairs

The receipt repair derives semantic identity from the parsed request and a
normalized inspection, while retaining exact raw-byte hashes and complete ledger
validation. Original, pretty and reversed-key request encodings remain individually
valid with one semantic identity and three raw hashes. History, external and
combined imports reject their duplication. Distinct incomplete, successful and
other-stage inspections retain three identities and exactly 254,030 checking
units. The receipt/docket suite passes 20/20 on Node 22 and 24. Regressions fail
before the repair; independent native probes and the fresh browser attack agree.

The RPC repair links an owned cancellation signal to the caller, aborts on timeout
and cleanup, removes the caller listener, and includes cleanup in final timing.
Independent review reproduced a further cleanup overrun and verified its repair:
40 ms of cleanup under a 20 ms allowance returns inconclusive, reports the full
43 ms, and retains the block, five partial rows and eleven calls. All 14 cases pass
Node 22.17.1 and 24.21.0, including the actual five-second per-call deadline.
This covers cooperative transports; it claims no synchronous hard preemption.

## Historical custody and qualification limits

The original [source1c dataset](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/e02df9618fedc55c5bc9e8decc7c99369f0a32a9/evidence/discovery-future-1c6d719a-20261021)
remains unchanged, with both findings explicitly unresolved for those bytes.
Its original hosted run 39696030569 completed successfully before the branch
advanced. Artifact 12391073368 was downloaded and authenticated: 23,945,557 bytes,
SHA256 `df3c2941b02a0f27ce1b92160166c02a1ece83123638b903d93c18cd7e8164c3`,
184 CRC-valid entries, and independently verified merge3476/tree202/source1c.
The custody records here do not transfer those older hosted results to source99.

Verbose or repeated JSON records are losslessly gzip-compressed. The manifest
binds both compressed bytes and decoded original bytes. Reproduction helpers keep
original local paths for traceability; adapt paths in an isolated exact checkout
and use unchanged inputs. Never reanchor an old mission to another source.

These results establish local synthetic/browser and native-source interoperability.
Installed packages, fresh hosted checks, public HTTPS, current-chain observation
and operational real-task execution remain separate qualifications. Docket
`totalComplete:false`, unattested source context and no authority remain explicit.
The supplied competent static alternative is cheaper overall; public seeds are
not protected holdouts. Live observation and qualified real-task execution remain
NOT_RUN. Configured review, full hooks/Python coverage, paper/main integration,
versioned receiver profiles, final-main checks and release/deployment acceptance
remain required. No gate is waived by this dataset.
