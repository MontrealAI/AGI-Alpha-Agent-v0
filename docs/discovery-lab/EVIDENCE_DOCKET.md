<!-- SPDX-License-Identifier: Apache-2.0 -->

# Discovery Lab Evidence Docket

The docket is a derived, replayable export of the existing capability workspace.
It retains the original event chain, completed failures, inconclusive searches,
interruptions, six typed artifacts, capability ancestry and ordered future-task
or real-task contract attachments. It creates no second history store.

The schema is `successor-discovery-evidence-docket/v1`. The canonical JSON file
map uses the manuscript's thirteen sections, following the directory contract in
`alpha_factory_v1/core/runtime/transfer.py`:

| Section | Contents |
| --- | --- |
| `00_manifest.md` | Mission, exact history head and complete run commitment |
| `01_claims_matrix.md` | Demonstrated scope and absent operational evidence |
| `02_environment.md` | Bounded synthetic environment and provenance limits |
| `03_benchmark_tasks/` | All original charters and task evidence locations |
| `04_baselines/` | Original complete campaign comparisons |
| `05_agialpha_runs/` | Original workspace and exact raw receiver attachments |
| `06_proof_bundles/` | Six source-bound artifacts per campaign and receipts |
| `07_replay_logs/` | Every event digest, replay method and receipt digest |
| `08_cost_ledgers/` | Incremental work, recorded replay, route costs and unknowns |
| `09_safety_ledgers/` | Retained reservations, rollback and authority boundaries |
| `10_validator_reports/` | Checker relationship and pending external review |
| `11_alpha_wu_calibration/` | Explicitly uncalibrated; no invented alpha-WU |
| `12_summary_tables/` | Every campaign outcome, parent and unresolved attempt |

`checksums` covers each exact UTF-8 file. The complete export uses the existing
bounded two-megabyte JSON language. Oversized histories refuse this export;
preserve the original workspace rather than silently dropping old evidence.
This format is a JSON file map, not a ZIP archive or an externally signed report.

## Export and replay

From the repository root, with the pinned Node runtime:

```javascript
import {readFileSync, writeFileSync} from 'node:fs';
import {parseWorkspace} from './examples/successor-capability/workspace.mjs';
import {exportDiscoveryDocket, verifyDiscoveryDocket} from './examples/successor-capability/discovery-lab-docket.mjs';
const mission = await parseWorkspace(readFileSync('mission.json', 'utf8'));
const head = mission.events.at(-1).digest;
const text = await exportDiscoveryDocket(mission);
await verifyDiscoveryDocket(text, {expectedMissionId: mission.missionId, expectedWorkspaceHead: head});
writeFileSync('discovery-evidence-docket.json', text);
```

Verification reconstructs every admitted original workspace event, finite
campaign, artifact and ordered evidence attachment, then regenerates every
section. Rehashing an edited cost table, erased failure, substituted artifact or
forged acceptance does not make it match replay. Duplicate JSON keys, extra
paths, changed attachment heads, duplicate semantic receipts and broken ancestry
reject. Data is captured inertly before asynchronous work; imported source code
is never evaluated.

An independently retained mission/head is essential for detecting replacement
of the *entire* export by another internally consistent history. Hashes alone
cannot authenticate an external producer or prove that a supplied history is
the latest one. Supply `expectedMissionId` and `expectedWorkspaceHead` from
trusted custody. Optional `expectedSources` and `expectedReceiverSources` compare
the supplied declarations against independently installed source identities.
Those expectations must come from the verifier, not from the imported docket.

## Receiver attachments

Use `emptyDocketAttachments(mission)` to create a container bound to the exact
mission head. Its mutable `sources` and legacy `receipts` collections remain
available for older export integrations. Returned raw receipts should enter the
same persisted mission through `lab-evidence-attached`, kind `receiver-receipt`.
Future-task, real-task and receiver records are derived from those ordered
events during replay. A receipt repeated in both history and the legacy external
collection rejects; it can never count twice.

A source entry has `repository`, exact Git `commit` and `tree`, and a `files`
array of safe relative `path` and `sha256` pairs. A receipt entry has:

```javascript
{raw: exactOriginalReceiptText,
 source: {repository, commit, tree, adapterSha256, contractSha256}}
```

Receipt validation binds the exact original typed request, mission/source
bindings, commission, currency route, six-stage artifact prefix and full
ancestor payload. It verifies resource component sums, fixed admission charges,
native replay-prefix costs, the compact receipt's recorded storage footprint,
resource-envelope outcomes and the absence of imported authority.

Raw receipts remain **unattested observations**. Structural/replay consistency
and matching an installed source context do not prove that those bytes were
produced by an authenticated external party. Receiver receipts do not promote
a capability, establish organizational independence, prove remote execution,
reserve funds or establish settlement.

Fleet uses this same wrapper and event chain. Its `raw` value is an inert
`agi-fleet/discovery-review-return/v1` envelope with exactly `schema`, `original`
(the original typed request text), and `receiptRaw` (the unchanged serialized
`agi-fleet/discovery-review/v1` native receipt). The underlying Fleet receiver
schema is preserved. The docket retains independent digests for the envelope,
original request and native receipt. It checks the actual Fleet serializer's one
admission check, native replay prefix and canonical receipt storage charge.
Malformed, swapped, source-mismatched or authority-bearing returns reject.
`receiptRequestBindings(wrapper)` selects the campaign from the original typed
request without executing receipt content.

Fleet identity `discovery-lab-fleet-receipt-identity/v1` binds the canonical typed
request, adapter/contract code and exact logical prefix. Free executor/runtime
declarations, timers, diagnostic/outcome flags and request/receipt formatting
cannot create another same-work invocation identity. Those declarations remain
visibly unattested; installed provenance requires independent package/source
qualification. Overflow receipts whose exact cost cannot be reconstructed are
not silently admitted; preserve them outside the bounded history for review.

Every retained receipt has a semantic `receiptId` for logical work and a separate exact-byte
`receiptDigest`. Identity version `discovery-lab-receipt-identity/v3` binds only
the parsed canonical work request, validated receipt schema and code source,
fixed admission checking charge, and exact validated native logical work prefix
(acquisitions, search, checking, storage, installations and worker capacity).
Different stages or early/full native replay prefixes retain distinct work and
costs within one logical commission and route. Whitespace, property order, units
labels, diagnostics, timers, permissive memory, reservations, derived allowances
and outcome/envelope flags cannot mint another identity. All exact raw hashes,
states, diagnostics and validated reported resource charges remain in the
retained evidence and ledger; they establish no authenticated invocation count.
The commission's alternative routes are still listed once each. The receiver
schema has no authenticated invocation nonce; two actual invocations with the
same request and logical prefix cannot be distinguished without a separately
retained authenticated invocation trace, even if their timing or outcome reports
differ. Such invocation counts and missing costs remain unknown. No trace is
invented retrospectively.

## Cost interpretation

Each campaign's incremental construction and recorded verification work is
counted once. Descriptive ancestor cumulative totals are retained but never
summed again. Memory and worker counts are peak metrics. Actual route-inspection
work is retained separately for Manager/USDC6 and Jobs/AGIALPHA18; alternative
routes create no duplicate payment obligation, currency conversion or combined
balance. Each logical commission stays `DRAFT_NOT_SUBMITTED` with zero reserved
base units.

Fleet observations have a separate `fleetLocalReviewObservations` bucket. They
do not create another commission, alter USDC6/AGIALPHA18 alternatives, or add
their overlapping Alpha checker work to a combined system total. Each retained
observation describes a distinct reported Fleet invocation; without authenticated
invocation custody, multiplicity and total completeness remain unknown. A local
Fleet checker is not remote execution or independent institutional validation.
The original typed work-reference branch remains consistent across all receipts.
A contradictory reference is refused without changing history or costs. This
preservation rule creates no additional commission, route, reservation, currency
balance or authority. An intentional revision needs a separately identified
authorized history revision; changing an imported reference is not that revision.

`knownHistoryTotal` covers Discovery Lab campaigns and their recorded checks.
Preserved v1 witness metrics and unique real-task contract checker charges have
separate ledger records; differing units and untrusted observation costs are
never silently added to that total. Real-task checks bind an immutable proposal
identity, including its original mission head. Identical work from two separate
proposals retains both charges. Only repeated evidence for the same proposal
and check identity can deduplicate. The current history contract rejects silent
reanchoring of a proposal; a general progressive-snapshot workflow is not claimed.

Interrupted attempts retain their conservative reservation and **unknown**
spent work; they never become free attempts. Future-task costs remain in their
replayed protocol results, separate from original construction totals and with
their explicit amortization assumptions. Open and stopped future runs retain
their unknown spent work and the full task-count × treatment-count × per-task
allowance. A later completed run never clears an earlier stopped reservation.
The logical cost of one full attached-evidence replay is reported separately;
the cumulative number of exports/reopens remains unknown. Additional export/replay
overhead, review/coordination time, energy, monetary compute cost and delayed
commercial outcomes remain unmeasured. Real-task contract checks remain
`NOT_RUN` operationally until actual qualified runtime/operator evidence exists.

Local replay, a separately implemented checker, hosted CI, independent
organizational reproduction, merged/released software and live operational
acceptance are separate evidence claims. This docket grants none of those
statuses merely by being well formed.

Run the focused regression suite with:

```sh
node --test examples/successor-capability/discovery-lab-docket.test.mjs
```
