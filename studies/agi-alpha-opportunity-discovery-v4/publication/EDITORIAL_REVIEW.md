# Adversarial editorial and evidence review

**Scope:** `sections/01_question.md`, `02_instrument.md`, `04_economics.md`, and
`05_operation.md`, reviewed 27 October 2026 against the actual development,
primary/prospective confirmation, transfer, accounting and foundational-source
records. The review began after primary and prospective technical execution.
The core developer was explicitly authorized to inspect confirmation evidence
for this editorial review. No frozen runtime, evaluator, original economic
program or original result was changed.

**Disposition:** the bounded technical and negative commercial conclusions are
supported, with the corrections below. The material issue was an undisclosed
financing assumption: development-milestone acceptance was guaranteed in the
model even though the proposed contract permits its rejection and then promises
a full refund. That issue is now explicit and has a separate adverse solvency
audit. The original positive-profit paths and zero-new-crossing result remain
conditional model outputs, not commercial evidence. There is no support for a
claim of actual earned revenue, physical substitution, live ENS authentication,
graph-specific productive advantage, or commercial compounding.

The low-cost expertise and prospective 0.1.1 results sections were still being
assembled. Their absence from the reviewed snapshots was not treated as a
failure. This review does not certify the final bibliography, assembled PDF,
public link or publication permissions; those are separate completion steps.

## Material findings and resolution

### 1. Milestone rejection was outside the original financing model

**Severity before correction: important claim blocker for unconditional
financeability. Resolved by explicit scope correction and adverse audit, not by
rewriting the original simulation.**

The proposed contract says an unaccepted development/failure record earns
nothing and requires a full refund. In the frozen `economics/model.py`, however,
`realize` unconditionally records `accepted-development-failure-record` and earns
`(1-r)*a*P` whenever an audit fails. No separate milestone acceptance/rejection
event exists. After day one the cash ledger reserves only `r*unearned`, and
`evaluate_plan` reduces required opening cash by the other portion of advances.
Therefore the original partial-refund financial result covers audit failure
conditional on accepted development artifacts; it does not cover rejection of
those artifacts. A full-refund *terms* scenario is a useful control, but is not
an independently modeled milestone-rejection event.

Section 04 now states the guaranteed-milestone-acceptance assumption and narrows
the liquidity claim. The frozen protocol is retained as historical evidence;
its broader proposed-contract text must be read with this qualification. No
expected-profit result was revised or reported as recovered confirmation.

At the commissioning parent's request, a separate calculation was frozen before
execution in `economics/postconfirmation_solvency_v1/`. It independently
reconstructs current buyer inputs and precollection A/B/C costs without importing
the original planner, job-cost or realization functions. Every one of the 3,520
original arm-horizon rows is inspected. The precise exposure population is the
1,889 originally selected `plan.action == produce` commitments, including plans
that later cancelled after withdrawal.

The adverse condition is rejection of the development milestone after all
committed precollection work, a full refund of every advance, and no final
collection available to finance the work. Advances and their refunds cancel;
opening cash must therefore equal full committed A-precollection + B + C.
Bad debt is not charged again as a cash outflow. The scenario seed is unchanged.

| Original arm | Selected commitments | Exposed commitments | Maximum shortfall USD |
|---|---:|---:|---:|
| Expert, payment on acceptance | 772 | 0 | 0 |
| Retained, payment on acceptance | 127 | 0 | 0 |
| Expert, commission terms | 796 | 62 | 3,311.46 |
| Retained, commission terms | 194 | 52 | 5,222.25 |

Central-scenario exposures are 2/75 expert-arranged plans (maximum USD559.57)
and 15/38 retained-arranged plans (USD739.85). The full-refund-contract scenario
has no additional exposure. Complete per-scenario/arm rows appear in the audit's
`README.md` and `RESULTS.json`. Eleven of the 114 exposed commitments later
cancelled under the original withdrawal realizations. These counts are
conditional commitment exposures, not 114 realized insolvencies or independent
market observations. The stress assumes all committed work is incurred and does
not supply a rejection probability.

Independent need reconstruction exactly matched 36 retained buyer objects.
Precollection cash reconciliation to the original partial-refund formula differs
by at most USD1.0688e-12. Audit code passed Ruff. This is one finite calculation,
not a broad new campaign or a test of actual contractual/legal enforceability.
Other nonperformance, partial/disputed acceptance, strategic behavior, actual
metrology costs and payment delay remain unmodeled.

- Audit freeze SHA256:
  `847a5abe0b7efedc5e0a9a84c9e9477ada4adeb8a6c3308f9382f5523b802f78`.
- Result SHA256:
  `70423143134e3f7f4eb87175283daff9600b83545b2adece0fc440c78a75293f`.
- Original economic freeze SHA256 remains
  `1e8aea2ed0913c10cde17fae98a4a8b9b13d9dcfb1c43eaf53362cdee1ab64ce`.

### 2. The financial simulation does not execute artifact-gated sales

**Severity before correction: material synthesis overclaim. Resolved in section
01 and by the expressly proposed offering package.**

The initial wording said the same instrument identity appeared throughout the
commercial/common-component/transfer decision chain. The original runtime and
transfer records do bind exact source identities, but the frozen economic
program is artifact-agnostic. It does not read the runtime hash, consume a
technical acceptance result to authorize a sale, or estimate its quality and
cost parameters from observed delivery. No transaction happened.

The rewritten paragraph distinguishes the actual 0.1.0 construction/qualification/
recipient identity from the separate 0.1.1 proposal. `offering/package.json`,
assembled after the results, now names the corrected capability, actual bounded
acceptance evidence, obligations, outside options, rights, responsibilities,
timing and conditional financing. Its explicit coupling limit correctly avoids
presenting this document as a prospectively executed economic chain. The actual
recipient handoff remains a 0.1.0 result, not a retest of 0.1.1.

This is a concrete proposed joint package and a conditional financial study.
It is not a measured end-to-end capability/acceptance/market flywheel.

### 3. A mathematical formulation comparison was not a timed solver diagnostic

**Severity: moderate wording overclaim, corrected.**

The invariance of a conjunction under permutation is established mathematics.
The phrase “that diagnostic” could imply a separately executed experiment in
which the original expert solver received the formulation. No such timed
solver receipt was identified in the reviewed evidence. Section 02 now says an
expert given the formulation can compute it with ordinary interval checks and
labels this a mathematical comparison. It does not establish algorithmic
superiority or a better discovery policy. The separate hosted method comparison
must retain its own actual controls and results.

### 4. Mission meaning is supplied and checked within a typed scope

**Severity: important interpretive boundary, clarified.**

The instrument preserves a caller-supplied `mission` object and dispatches on a
purpose enum. It does not understand arbitrary mission prose or autonomously
select the curator's family IDs. Section 02 now makes these supplied structures
explicit. The independent checker verifies the particular bounded obligations;
this cannot support unrestricted semantic requalification claims.

A record-only universal query may be useful without physical family identity.
A complete physical-family question still needs coverage and metrology evidence.
A localization or release query cannot be satisfied by renaming the weaker
record query. The existing text and receipts preserve those distinctions.

### 5. Smaller precision and disclosure corrections

- Section 02 now cites both `LinearValueType` and `ActualLinearValueType` for
  the exact QIF 2.1 meter default. The former alone is an incomplete label for
  the rule governing actual measurement quantities.
- Section 01 now says the foundational PDFs were read in full and the editable
  TeX sources were retained. This does not add an unsupported assertion that
  every editable source was separately read in full.
- Section 04 discloses that the six-horizon diagnostic charges USD100 of upkeep
  only when the retained arm is selected. Expert fallback incurs no idle-upkeep
  charge. This is a favorable assumed maintenance policy, not measured complete
  operating upkeep. The negative admission result already holds under it.
- The proposed contract's scheduled days and the 80-hour/ten-day gate are
  finite modeled scheduling assumptions. No queue, staffing, laboratory lead
  time or observed delivery SLA has been established; the reviewed text already
  excludes an achieved service-level claim.

## Quantities and boundaries checked against receipts

| Claim | Check and disposition |
|---|---|
| Foundational economy example | USD300,000 conditional success contribution; USD120,000 expectation; USD900,000 prefunding; common failure shared by four buyers. Correct. The values are synthetic. |
| Foundational inheritance result | 1,600 to 64 generic qualification cases, not total work; direct specialist faster in the final comparison. Correct. No customer saving inferred. |
| Plate geometry and trace | One valid solid, 261 faces, 722 edges, 34 cylinders, 18 cylindrical feature candidates, 17 characteristic/feature traces; actual102 is 3.017mm under incoming explicit mm, while parent result183 is FAIL. Matches development report. |
| Primary confirmation | 8 calls, no retries, 5 accepted scoped audits, 3 repair-actionability failures. Correct. Every physical-reuse flag is false. A rejected or unsupported physical claim may be a valid bounded audit outcome, not a physical-service success. |
| Prospective correction | Separate 0.1.1 freeze and 4/4 additional scoped audit results exist. Original 5/8 remains unchanged. The four requests reuse the same historical sources; do not pool them into a fresh industrial success-rate estimate. |
| Box/Cover numerical distinction | Box's hypothetical-mm family has an actual violating value; Cover's 400 records satisfy the hypothetical interval while 20 selected characteristics do not establish coverage of the represented four-feature destination family. The manuscript preserves that difference. |
| Actual transfer | 43,242-byte transport, 116,202 custom uncompressed bytes, 8,238,065 separately supplied data bytes, 1,088,987,406 installed dependency bytes rehashed. Correct. Native CAD/model intelligence was not acquired inside the small bundle. |
| Transfer timing and authority | CLI 3.011573 s and recipient execution 4.993252 s; 35 study controls and an aggregate check of 29 lifecycle controls pass. Local ephemeral Ed25519/Journaling is executed; no live ENS, hostile-host security proof or manufacturing scope admission. Correctly bounded. |
| Same-content library | Accepted semantic parity with identical code and permissions. No graph-specific advantage established. Correct. |
| Primary economic table | Central means USD 2,324.09, 492.72, 2,476.92, 771.24; financeable horizons 74, 27, 75, 38; accepted simulated audits 118, 57, 121, 84. Matches retained summaries. These are conditional assumed-world outcomes. |
| Feasibility crossings | All eleven scenario summaries have zero combined-versus-expert-standard crossings. Correct. Existing expert production remains the stronger modeled option. |
| Selected accounting example | Seed 21001: USD12,000 modeled collections/revenue, expenses 5,810.0737258, contribution 6,189.9262742, cash 12,189.9262742 including 6,000 seed. Native projection A 5,310.073726 / B 400 / C 100 and 12 checks reconcile. No seed or bad-debt double charge found. |
| Admission/lineage | USD 2,220.937 prospective benefit versus 2,950 proposed costs rejects the campaign. Forced 20-path final mean −USD 1,049.788; two nonnegative paths. Correctly not recovered/admitted profit. |
| Actual revenue and research costs | Actual customer collections and earned revenue are zero across study records. Complete research cost remains unknown. A simulation's positive contribution cannot offset unknown actual expense or establish zero actual loss. |
| Model sources | Saved official-source notes support Astra 10/1/50 and Terra 1/.05/5 USD/M tokens, with short-context/tier limits and no hosted-billing claim. No current account entitlement or exact served API snapshot follows. |

## Sources inspected and attribution boundaries

The foundational audit and exact provenance are in `dossier/FOUNDATIONS_AUDIT.md`
and `dossier/source_manifest_foundations.json`, with the pinned source commit
`80b345828f34fd8a6e592977dd17ef37141305f4`. The new text preserves the papers'
different claim levels, the common-failure arithmetic, and the direct-specialist
result. It does not turn their supplied finite examples into autonomous discovery.

The strong incumbent discussion is supported by `dossier/CADofferinggrounding.md`,
`round2_industry.md`, NIST's original/reference data, and the 2024 integration
report. Vendor pages support advertised features and an outside option, not the
assumed USD 125–225/hour or 12–31-hour service envelope. The manuscript explicitly
labels those labor/price figures as researcher estimates. It must retain that
label when tables or excerpts move into the executive brief.

The owner QIF 2.1 archive's Part2 copyright page contains the copying/use
permission conditioned on preserving its notice. `QIF_DMSC_NOTICE.md` accompanies
the new runtime and should accompany publication of the unchanged old schema
bundle. The material is not being called NIST public domain or relicensed Apache.
Byte hashes identify data; they do not themselves establish rights or meaning.

Official-model and original-vision source notes were inspected at
`research_sources/current_evidence/EVIDENCE_NOTES.md` in the shared scratch
sources. They support the explicit exclusion of the USD 15 quadrillion projection
and promotional superlatives from market/value assumptions. The issue #4850
coordination link is recorded in the inherited v3 provenance; citation 16 still
needs to resolve properly in final assembly.

## Limitations already stated: do not present them as new defects

- One historical public three-part assembly, procedural withholding on a shared
  host, potential model pretraining contamination and no independently sampled
  customer population.
- Known interval/permutation mathematics and a shared OCP kernel between builder
  and independent checker; no new GD&T algorithm, metrology qualification or
  theorem claimed.
- Missing physical identity/coverage/measurement evidence and no part release.
- No observed buyer commitments, human-service trial, complete delivery cost,
  legal-classification determination, token valuation or live settlement.
- Hypothetical markets, costs, delivery probabilities, timing and maintenance;
  no simulation confidence interval validates those assumptions.
- Local signed authority fixtures and unchanged production scope refusals;
  eligible membership is not unrestricted execution permission.
- Actual transferred executable structure, but no demonstrated commercial
  private-retention-versus-selective-sharing benefit. Library parity removes a
  graph-specific claim; it does not erase the bounded transfer result.
- No improved discovery-policy learning or specialist ASI established. Separate
  new campaigns would be needed for those claims.

## Changes made and final assembly conditions

Changes are confined to section 01, section 02 and section 04. Section 05 was read
and left unchanged. Original reviewed snapshots, before/after hashes and the
exact prose diff are retained in `publication/review_history/`. No original
confirmation row was replaced. Runtime 0.1.0, runtime 0.1.1 and the original
economic frozen files were independently rehashed and all still match.

The financial adverse audit is new, separately versioned work with its own
protocol/code/input freeze, result and summary. It is labeled post-confirmation
at every reporting point. Its original-commitment denominator, later withdrawal
cancellations, assumed full-cost envelope and unmodeled contractual risks must
stay visible in any figure or executive extract.

Before final release, retain the three distinct technical result groups
(0.1.0 primary 5/8; original recipient transfer; 0.1.1 prospective 4/4), resolve all
numbered primary citations, include the DMSC notice with schema distribution,
and preserve unconditional zero actual collections/revenue. The manuscript can
report the narrower construction/transfer achievement and negative conditional
commercial result after those assembly checks. It cannot call this an observed
profitable enterprise or an executed autonomous market-creation loop.
