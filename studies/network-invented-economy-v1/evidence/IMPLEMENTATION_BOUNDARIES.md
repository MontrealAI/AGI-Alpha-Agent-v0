# Implementation, evidence and operational boundaries

This document describes the research package as an executable local study. It separates
what the code actually performs from modeled events and from future production work.
It does not turn a passing local test, mathematical certificate, identity string or
public commitment into an operational authorization.

## 1. Evidence categories

| Component | What actually executes locally | What remains modeled or unestablished |
|---|---|---|
| Mechanism witness | Exact finite-distribution compilation, budget-frontier optimization, certificate checking, bounded deviation/constraint enumeration, negative controls and deterministic replay | Autonomous frontier-model invention, general truthfulness outside the declared mechanism family, empirical buyer demand and commercial delivery cost |
| Alpha gate | Immutable inputs, weighted paired-gain arithmetic, explicit total cost lines, binding hashes and strict positive lower-net-bound decision | Truth of observations, competence of a supplied Beta, complete cost calibration, future reuse/demand and statistical coverage of a declared margin |
| Economic simulator | Chronological cash ledger, reservations and obligations, resource budgets, modeled job and skill state, buyer-choice/pricing/investment policies and matched modeled counterfactuals | Actual jobs, independent model executions, customer acceptance, revenues, payments, or enterprise profitability |
| Research graph | Public-API lifecycle checks, fixture session provenance, role separation, current Beta/policy/evidence checks, signatures, capsule integrity, Merkle commitments and one-use reuse authorization receipts | Live ENS authentication, production governance, durable service enforcement, useful or truthful evidence merely from validator agreement, and execution of capsule code |
| Modeled admission adapter | Preserves deterministic recipient economics while binding it to actual graph records; exercises conditional admission, rejection, failure memory, all-member retrieval and separate action permissions | Empirical Alpha, an executable new invention in the descriptor capsules, actual job history, successful future reassessment, or a graph call for every Monte Carlo job |
| Cryptographic fixtures | AES-GCM, Ed25519 and SHA-256 computations | Production confidentiality or identity trust: all fixture keys are public and reproducible |
| Native accounting seam | Unchanged source-pinned accounting helpers, bounded JSON projection and local arithmetic/rejection checks | Native service installation, a settlement route, contractual receipts or live integration qualification |
| English/French demonstration | Rendering retained evidence and explicitly labeled local exploratory controls | New confirmation results, provider execution or a production administration console |

The mechanism witness is a known-method experiment on synthetic public inputs. Its strong
baseline already knows ordinary mechanism theory, dynamic programming and verification.
It evaluates input-specific construction and reuse; it does not infer recipient ignorance
from a missing file. A validated compiled instance can still have negative reuse value
when import, checking, adaptation and maintenance exceed reconstruction costs.
The actual transfer preserves outputs relative to competent reconstruction; it does not
demonstrate a previously infeasible class of frontier work. Shared-route certificate counts
include the creator and all recipients, and separate operation classes are not combined
into an unmeasured net time or dollar benefit.

The economic simulator uses explicit assumptions for mission difficulty, capability
construction, transfer, demand, buyer preferences, quality, trust and useful lifetime.
Reported model benchmarks are not customer acceptance rates. The research assistant's
own work on this package is not a metered trial of frontier roles solving the simulated
customer jobs, and its actual compute bill is not reconstructed by the simulation.

## 2. Authority is divided, not inferred from a suffix

The research directory recognizes only enrolled **direct-child ASCII fixture names** of
the form `label.agent.agi.eth`, with a lowercase 1–63-character label of letters, digits
and permitted internal hyphens. Nested names such as `x.y.agent.agi.eth` do not receive
authority. A syntactically valid name alone is insufficient: opening a fixture session
requires the exact enrolled owner, and every operation rechecks current membership.

The name grammar and fixture owner check are executable research rules. The directory
does not query ENS, resolve Registry/NameWrapper state, verify a live wallet challenge,
establish chain finality, or normalize arbitrary internationalized names. The integer
clock comes from the trusted research harness; it is monotone but is not a network time
or chain-finality service.

| Authority or access | Current research rule | Authority it does not confer |
|---|---|---|
| Creator identity | Stored in the immutable manifest | Record-writing, validation or admission rights by authorship alone |
| Record writer | Current direct member with `record.write`, matching that record's writer identity | Permission to edit another owner's record or bypass validation |
| Validator eligibility | Current direct member with `graph.validate`; the creator cannot validate its own candidate; the policy requires distinct eligible signed attestors | Admission, execution, or proof that different agents made independent correct judgments |
| Admission authority | Separate `graph.admit` permission after positive Alpha and current validation; the actor cannot be the producer/writer or one of this record's attestors | A route around evidence, current comparator, scope, dependency or sharing-rights checks |
| Policy/Beta authority | Separate `graph.policy` permission; updates require a new version | Native governance or authority over existing AGI Jobs contracts |
| Network inspection/export | Every current authenticated direct member can discover and retrieve every current admitted shared capability | Permission to execute actions named in that capability |
| Execution authorization | Required actions are checked for the actor and recursively for the dependency/component closure, alongside current applicability | Financial, external-service or customer-data authority merely because a capsule is readable |
| Public commitments | `public_commitment()` exposes typed roots and epoch/schema metadata | Private capsule contents, membership, admission, factual truth, capability value or action permission |

Creator and writer fields are distinct even though the basic fixture uses the same
principal for both. The current permission assignments are explicit fixtures, not a
claim that string ownership alone should grant every production role. A different
operational adapter would need to preserve these separations under the applicable policy.

Existing AGI Jobs/Manager Agent/Node role families, their documented alternatives,
`*.club.agi.eth` validation roles, contracts, governance and settlement remain unchanged.
The additional agent-network graph policy does not retrospectively redefine those roles.
The [foundation audit](foundation_audit.md) records the inspected source snapshots.

## 3. All-member availability and separate action permissions

A shareable admitted skill must declare rights for all authenticated direct-agent
members. The graph refuses a preferred-subgroup sharing rule. Every current member sees
the same eligible catalog and can inspect the manifest and assessment, retrieve/export
the capsule, and inspect provenance. A receiving agent still evaluates its own scope,
tools, dependencies, freshness and current permissions. Availability is not mandatory use.

Candidate-only complementary components can be retrieved by every member through their
admitted bundle. They do not independently enter selection or acquire standalone Alpha
labels. The bundle's exact component evidence, scope and dependency conditions must
remain current. A scoped joint benefit does not imply that each component is profitable
or independently safe to execute.

No customer-confidential information, protected evaluation testcases, scorer internals or
restricted third-party material is included in the fixture capsules. The implementation
checks explicit sanitization and rights declarations and rejects declared protected
evaluation contents from capsules and failure memory. It does not prove that arbitrary
future submitted material is lawfully shareable or free of protected content. A real
extraction and validation process must establish that claim. Material that cannot be
sanitized and lawfully shared cannot enter the shared capability base.

Exported contents can be copied by an authorized member. Authentication and encryption
at rest do not prevent that copying. A future controlled-execution design could expose
less plaintext, but no such non-exporting execution service is implemented here. Access
restriction is therefore a boundary on this API, not evidence of a durable economic moat.

## 4. Correctness, Alpha, admission and history remain separate

The graph requires candidate creation, an exact evidence revision, a positive scoped
Alpha assessment, eligible signed validation attestations and a distinct admission.
Canonical promotion can only mark an already admitted current record; it cannot admit
one. Evidence binds the manifest, policy, scope, replay and observation identities, cases,
failures, provenance and freshness. The gate checks those supplied records; it does not
independently execute every referenced replay artifact.

Alpha adds a versioned competent Beta and a snapshot of currently available capabilities,
plus paired gains, full incremental costs, dependencies and uncertainty. The available
snapshot is rechecked before admission. Changing Beta removes previous admission and
canonical authority pending reassessment. Historical observations remain inspectable but
do not grant future selection. A retired, revoked or superseded version is terminal.

A new unrelated admission does not automatically erase every existing assessment. The
current implementation records each assessment's comparator snapshot and uses explicit
Beta updates/reassessment for relevant changes in ordinary competence or overlap. Detecting
those changes is an evaluation/controller responsibility. Neither the graph nor a hash
automatically discovers that a better ordinary method has become available.

The graph also retains a distinct `FailureMemory` store with authenticated all-member
reading. These negative reports bind scope, evidence, source category, policy and the
model/tool/environment baseline. They never enter the positive skill catalog or obtain
canonical, admission or execution authority. Their identifiers cannot be reused as skill
identifiers. A changed baseline marks their context historical; owners can withdraw
reports from future reading. Preserving failures is implemented, but its benefit to later
decisions is not assumed or measured merely from the existence of those records.

The economic simulator's direct Alpha probes compare the same recipient and task depth
with and without an optional candidate, while allowing the comparator its best currently
available method. They are deterministic modeled cost comparisons. The uncertainty and
future-use terms remain assumptions. The pure arithmetic gate establishes only whether
those declared inputs imply a positive lower net bound.

Correctness checks and economic assessment can disagree: a mathematically correct asset
may add no value beyond Beta, and a seemingly valuable design may fail validation. An
unresolved claim remains unavailable, is deferred, or leaves the offering. This package
does not insert unrecorded routine human review or manual onboarding to make the modeled
automated configuration succeed.

### Deterministic modeled integration

`integration/modeled_admission.py` connects the fixed recipient-v2 retention and optional
new-R&D cases to separate instances of the actual graph. It preserves every numerical
economic decision input while explicitly mapping comparator, evidence, scope and component
hashes. Recipient-local equivalents remain in the bound baseline. An existing cost-model
`admitted` label is not imported as graph authority: the adapter starts new candidates and
requires evidence, Alpha assessment, eligible signed attestations, validation and a distinct
admitter. A rejected case enters only separate negative memory.

The source Beta identifier describes a projected lifecycle with a declared moving-baseline
path. The graph configuration hash binds that projection, its inputs and replay environment;
it does not certify current production competence or future successful revalidation. The
source's historical A-job memo remains unspecified, while incremental B and optional C costs
remain explicit. The zero uncertainty margin in the fixed recipient panel is a declared
scenario input, not statistical coverage or an empirical lower bound.

The shared capsules are public modeled-work descriptors. Recorded validation checks concern
schema and accounting consistency, not measured task capability. All six enrolled members
are tested for equal discovery and retrieval; execution action permission is tested
separately. A synthetic model/tool/environment change blocks the earlier admission. The
Monte Carlo economic simulator maintains its own reduced skill-state model and does not
invoke the cryptographic graph API for each simulated job. The adapter establishes a local
implementation connection between components, not an operational invention service.

## 5. Cryptographic and execution boundaries

The graph uses actual local AES-GCM encryption, Ed25519 signatures, and SHA-256
domain-separated commitments. The encryption and signing keys are deterministic **public
test fixtures**. Anyone with the source can derive them. The fixture nonce construction
is not presented as production encryption design. No production credential is generated,
stored, requested or used.

Public commitments include state/event/policy/Beta/failure-memory roots, schema, tree policy, epoch and
previous-root linkage. They do not export private capsule bytes. Merkle inclusion proves
membership in a committed record set; even a rejected candidate can have a valid inclusion
proof. It does not prove evidence truth, usefulness, current admission, access rights or
permission to act. There is no implemented zero-knowledge circuit or on-chain publication.

The documented serializer is sorted compact Python JSON with nonfinite numbers rejected;
the typed tree uses SHA-256 and sorted pairs. It is not a claim of Ethereum Keccak,
EIP-712, RFC 8785 serialization, or compatibility with another production graph profile.

A reuse permit is bound to the current epoch, policy, manifest, evidence, Alpha assessment,
Beta, actor, scope and tools. It is checked again under an in-process lock immediately
before one-time consumption. Membership loss, changed graph state, stale evidence or
revocation prevents consumption. The result is an authorization **receipt**, with
`code_executed=false`; no capsule program or external action runs through this path.

The graph is an in-memory research object, not an adversarial-process security boundary.
A caller with arbitrary Python process access can alter internals. Production isolation,
transactional storage, rollback protection and authenticated artifact transport are not
established by the public-API tests.

## 6. Money, utility and commercial claims

The v2 accounting separates complete paid delivery (`A_job`), only incremental retention
and sharing of learning already produced through that work (`B_retention`), and optional
separately justified invention campaigns (`C_R&D`). Job reasoning and construction already
charged to `A_job` are not charged again as a fresh retention-development project. Extra
sanitization, reusable-scope confirmation, distribution and upkeep still belong in
`B_retention`. The total ledger preserves the job's full cost while a retention decision
compares only its genuinely additional future costs and benefits.

The simulator keeps seed capital, modeled customer collections, incurred/paid expenses,
reserves, unpaid obligations, closing commitments, receivables and available cash distinct.
Future receipts do not fund current spending. Construction, validation, corrections,
failed jobs, adaptation, recovery, maintenance and infrastructure belong in the cost
accounting. Prospective continuation can omit sunk construction from a new decision while
preserving its historical expense and original assessment.

The human-service reference supplies the commercial alternative in the buyer-choice
model. Its rates and hypothetical matched team effort do not establish an observed
human-only sale for every proposed offering. Willingness to pay and repeat demand remain
scenario inputs where no matched observation exists. Internally compared Beta and
isolated-retention arms test causality, not prices of competing AI products.

Positive modeled operating margin does not establish an invention benefit. Additional
skills, entries, members and invocations do not establish compounding. Compare useful
outcomes and complete-cost value, with failed transfer, reconstruction and maintenance
included. Adaptive-policy comparisons include downstream policy responses; a direct
capability effect requires the corresponding matched resource-controlled comparison.

**$AGIALPHA utility contributes zero to operating earnings in this package.** No token
issuance, transfer, assumed appreciation, exchange conversion, staking return or treasury
mark-up creates profit. Existing $AGIALPHA utility and native contract routes remain
distinct from modeled delivery economics and from the Manager's documented settlement
currency. No settlement contract or financial transaction is invoked.

All purchases, model-provider job calls, client engagements and receipts in economic
outputs are simulated variables. The package records zero realized sales and zero live
ENS or on-chain transactions. It does not claim that the research author's actual
unmeasured computation cost is zero.

## 7. Foundation preservation, source status and future operation

The four requested foundations were inspected at pinned source identities. The applicable
Alpha accounting helpers were reused as an unchanged minimal dependency closure with
their original license; the independent simulator supplies its own cash chronology.
The prior GoalOS drafts and earlier Alpha graph study informed concrete authority and
lifecycle corrections without inheriting illustrative reviewer labels, scores or economic
conclusions. Sources and ownership boundaries are recorded in
[foundation_audit.md](foundation_audit.md), [graph_design.md](graph_design.md), and
[the source manifest](../sources/foundation_manifest.json).

Publication belongs in the additive draft namespace
`studies/network-invented-economy-v1/`, coordinated through
[issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850).
Earlier experiments, owners, publications, native routes and settlement authority remain
preserved. A draft publication or local replay does not merge a production release or
enable an operational service. The full upstream environments, hosted release checks and
production security qualification are not claimed by these component tests.

The authorized offline work can continue using the documented research commands. A
specific future production proposal would need the additional resources and qualification
that it actually uses:

- Existing owners' review of the exact source and installed integration adapters, with
  the required upstream runtime and release checks.
- Real identity/ownership observations, authentication challenges, role delegation,
  expiry and revocation handling; durable transactional admission and audit state.
- Secret-key management, reviewed encryption and recipient access control, authenticated
  artifact retrieval, isolated execution and recovery appropriate to the operation.
- Task-matched competent frontier/Beta measurements, independent executable validation,
  truthful source and sharing-rights checks, and calibration of recipient integration,
  complete costs, demand, quality, correlated failures and useful lifetime.
- Authorization for any new provider spending, credentials, live deployment, contract or
  wallet action, client-confidential material, or funded commercial pilot that is proposed.

These items describe the gap to operation. They do not introduce a new mandatory approval
flow for reversible local research, require routine human review in the primary modeled
service, or authorize any live action that the user has excluded.
