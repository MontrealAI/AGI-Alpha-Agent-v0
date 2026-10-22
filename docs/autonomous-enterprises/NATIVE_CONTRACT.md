<!-- SPDX-License-Identifier: Apache-2.0 -->

# Native enterprise inspection contract

`examples/autonomous-enterprises/native-contract.mjs` exports `createNativeExport`, `inspectNativeRequest`,
fixed routes and strict context validators. This is a source contract. Installed custody, receiver history commit,
release qualification and operational real-task execution remain **NOT_RUN**.

| Receiver | Fixed route | Currency cap | Existing owner lane |
| --- | --- | --- | --- |
| Manager | `manager-usdc` / USDC6 / chain 1 | `0` | MontrealAI/AGIJobManager #1613 |
| Jobs | `jobs-agialpha` / AGIALPHA18 / chain 1 | `0` | MontrealAI/AGIJobsv0 #4010 |
| Fleet | `fleet-check` / NONE / no chain | `0` | MontrealAI/AGI-Fleet-Linux #64 |

Use the actual frozen workspace with `createNativeExport(workspace, {attempt, inspectionId,
logicalCommissionId, route, source, limits})`. It returns `{request, docket}`. Source has exact `repository`,
`commit`, `constructor`, `checker`, `closure` identities; the binding includes the entire event-prefix commitment,
mission/revision/head, attempt/state, freeze, artifacts and invocation. The raw docket stays a separate string.

The receiving host must independently establish a `autonomous-enterprise-native-context/v1` context with those
identities and limits. It passes the unchanged docket to `inspectNativeRequest(request, context, {docket,
effectiveLimits})`. Effective limits can only decrease the installed reservation. A literal commit field is never
proof that those code bytes were installed. Local tests explicitly label their uncommitted fixture identities.

## Protocol and recovery

The versioned transport has exactly `{request, docket}`. The docket is the unchanged raw thirteen-section
Evidence Docket; the request carries the actual mission workspace and commits to those exact docket bytes.
The fixed Alpha inspector replays the history and docket, including the frozen artifacts and later tasks.

An operator must independently install the reviewed inspector and select source, mission, event-prefix,
freeze, artifact, invocation, inspection, logical commission, route and resource identities from trusted custody.
Copying those values from an incoming request does not establish that custody. Imported data never chooses
code, a runtime path, a provider or an acceptance policy. A callback or matching source label alone does not
prove installed-source authenticity. This source increment explicitly reports installed capture as unqualified.

The receiver reserves its one installed context synchronously before awaiting inspection. Concurrent duplicates
and every restored pending/consumed record refuse another invocation. Save `exportJournal()` and the original
transport and returned receipt through the **existing mission history**; there is no new database. A restored
journal blocks execution and grants no acceptance. Cross-process durable journal and receipt commits remain
an owner integration prerequisite; this in-memory receiver does not establish exactly-once settlement.

A missing/uncertain native report retains an unknown reservation and stops. Known unstarted budget or full-queue
refusals retain known zero replay; they do not authorize a blind retry. Known rejection charges remain visible.
A later receipt-presentation failure preserves any validated native receipt, known counters, original transport
and unknown partial replay in its immutable owned error and journal. The original error cause is preserved.

Each receiver charges 10,000 declared admission units before the native inspector’s separate 10,000-unit charge.
Current replay work is a conservative shared-session delta. Native calls are serialized with at most four
retained admissions; unrelated host work is not excluded. Memory is an encoded-input/receipt reservation,
not measured peak VM heap. Time and checking caps are soft checks surrounding complete bounded replays,
with no JavaScript preemption. Allocation, framing/control overhead, money, energy and institutional review
remain excluded or unmeasured. Never reinterpret these counts as currency spent or production billing.

## Qualification scope

Actual local tests used the real fixed Alpha modules, constructed/frozen workspace and the same canonical
thirteen-section docket. They establish source-level interoperability, not an installed service, provider pilot,
source-package custody, release compatibility or payment authority. The ordinary test file reports its optional
actual-source cases as **NOT_RUN** unless the separately reviewed fixed-source development driver is supplied.
The bare test command must not be described as successful native integration when those cases are skipped.

The public real-task operational pilot, fresh approved chain observations and production acceptance remain
**NOT_RUN**. Owner-reviewed source capture/profile pins, an independently selected installed context, durable
mission receipt commits, exact-head CI, compatible releases, clean installation and served journeys are required.
Existing release tags, deployment/ENS history, STOP and authority/spend journals remain unchanged.

## Actual bounded results

The Alpha contract has eleven passing ordinary cases on Node 22.23.3; the complete current enterprise and owner
metadata set passes 160/160 on both Node 24.19.0 and 22.23.3 after the history-capacity repair. A separate earlier n32 inspection reused the retained
recovery workspace/docket and accepted its full fifteen-treatment/changed-kernel history with 19,414,180 declared
checking units (19,404,180 current replay plus 10,000 admission), 4,198 measured milliseconds and a 5,687,296-byte
encoded-footprint reservation. Its preparation/export replays are separately retained and not free.
This older frozen mission is a new-inspector source observation, not installed custody of public head5711145.

The current Manager/Jobs source receivers pass 22 ordinary and actual-source cases per local runtime, and Fleet
passes 15 on each Node profile. Fleet’s fresh separate n32 case retains all 1,024 convolution basis pairs and 32 inverse bases. Source manifests, original failures and the
bounded static review distinguish implementation from final installed four-repository acceptance.
Fresh browser qualification of the history-capacity repair is blocked by missing Python test dependencies and
Chromium IPC permissions. Earlier browser evidence remains historical; hosted acceptance is required for the new source.
