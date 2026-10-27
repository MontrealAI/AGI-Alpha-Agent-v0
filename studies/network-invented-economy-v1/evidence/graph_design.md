# Beyond Beta: validated network capability lifecycle and evidence boundary

This document describes the executable research components in `src/skill_graph.py` and
`src/alpha_assessment.py`, and the adversarial checks in their corresponding test files.
The graph is an in-memory lifecycle specification
with executable enforcement at its public Python API. It is not a production registry,
authentication service, wallet integration, confidential repository or deployed contract.

## What is implemented

The implemented sequence is:

`candidate -> evidenced -> alpha-assessed -> validated -> admitted -> discovery / retrieval / optional reuse`.

An admitted skill may begin a fresh evidence revision, which immediately removes its prior
admission and canonical status and clears the earlier Alpha assessment and attestations.
Revalidation then repeats evidence, Alpha assessment, attestation, validation and admission
under the current policy and versioned Beta comparator. `retired`,
`revoked` and `superseded` versions are terminal. A corrected replacement needs a new skill
identity, a later version and a separately completed admission; history remains present.

Every manifest binds its creator, record writer, version, scope, prerequisites, action
permissions, exact dependency-manifest identities, payload hash, reuse rights, sanitization
declaration, limitations and rollback. The research fixture uses the same principal as
creator and record writer, but stores and checks those concepts separately. A validator
does not acquire record-writing authority. A record owner does not acquire admission
authority. Creator self-validation is refused even if that actor has a validator role.

Canonical promotion calls the same current-admission checks as discovery and reuse. It
cannot change a candidate or merely validated record into an admitted skill. Promotion is a
presentation status with no additional operational authority. Duplicate canonical payloads
are refused; a count of records is never accepted as evidence of distinct capability.

## Alpha requires positive net mission advantage

Novelty, executable validity, persuasive labels, signatures and inclusion proofs do not
establish Alpha. The separate `AlphaAssessment` is an immutable, scoped comparison against
`BetaBaseline`: a versioned specification of competent frontier-model use, settings,
context, tools, decomposition, critique and existing experience. The graph's fixture Beta
is explicitly synthetic. A production or empirical baseline would require the separately
justified comparator configuration and its actual replayable mission evaluations.

Each assessment records a Beta ID, an exact hash of Beta plus the currently admitted
capability-set snapshot, paired incremental mission gains, declared prospective reuse,
uncertainty margin, complete incremental lifecycle costs, scope, evidence hash, protocol,
source category and pinned bundle dependencies. The arithmetic is:

\[
 N_{\mathrm{mean}}=R\,\overline{g}-C,\qquad
 N_{\mathrm{lower}}=R(\overline{g}-u)-C,\qquad
 N_{\mathrm{upper}}=R(\overline{g}+u)-C.
\]

Here `g` is paired per-mission gain before the separately listed costs. Its mean uses
explicit nonnegative `paired_weights` when supplied, or equal weights otherwise; no probe
is duplicated to create artificial sample size. `R` is planned
reuse, `u` is the declared per-mission uncertainty margin, and `C` is total incremental
acquisition, construction, validation/confirmation, integration, operating, risk,
maintenance, migration and distribution cost. Every amount must use one declared unit and
scope. Construction includes allocated unsuccessful search, integration includes adaptation
and recovery, and risk includes residual expected loss. Costs already deducted in gains
must not also be entered as costs; the experiment's accounting protocol defines the
partition. Zero-valued lines remain explicit, and their completeness is a substantive
validation responsibility rather than something arithmetic can establish.

For the v2 paid-job learning mechanism, the cost context must distinguish complete paid
delivery (`A_job`), only the incremental extraction/confirmation/sanitization/distribution/
maintenance needed for retention (`B_retention`), and optional separate invention work
(`C_R&D`). A paid job's already accounted development work is not charged again as new
retention construction. The graph binds the supplied comparison and allocation; it does
not replace the economic ledger or decide which expenses were already paid.

Only a **strictly positive lower net bound** passes. A positive mean with a nonpositive
lower bound fails. A zero net benefit fails. A declared redundant capability fails even
if a contradictory positive number is supplied. The graph also rejects an exact current
payload duplicate that is already available over the proposed scope. These checks do not
solve semantic equivalence or establish that arbitrary supplied gains are true.

`u` is not presented as a statistical confidence interval, and a declared reuse forecast
is not observed demand. `source_kind` explicitly distinguishes an actual local experiment,
a modeled/simulation assessment and a reported measurement. The executable numeric gate
does not promote modeled observations into empirical evidence. The standalone graph demo
uses only `simulation-fixture` values.

The creator submits this assessment through `assess_alpha`. A rejected record becomes
`alpha-rejected`, is unavailable, and cannot obtain validation attestations. A passing
record becomes `alpha-assessed`; independent eligible fixture validators must still attest
to the exact combined manifest, evidence, Alpha context and policy before validation and
separate admission. Alpha arithmetic does not replace correctness or rights checks.

### Comparator freshness and moving Beta

`comparator_hash` snapshots the versioned Beta specification plus every currently admitted
available capability, excluding the candidate being assessed. It does not infer lack of
ability from lack of a skill file. The snapshot is checked both at validation and admission;
another admitted capability arriving during the evaluation requires reassessment against
that changed available set. After admission, an unrelated new skill does not automatically
invalidate every existing admission. The retained snapshot records the assessment's exact
comparator; relevant overlap or baseline improvement calls for an explicit Beta update and
fresh comparison. Detecting such improvement is a controller/measurement responsibility,
not an automatic intelligence claim of this module.

`set_beta_baseline` requires policy authority and a never-before-used Beta version. It
immediately removes canonical status and admission and clears attestations for records
with older assessments. Their status becomes `needs-alpha-reassessment`. Old records and
full assessment observations remain in authenticated `assessment_history`, but history
cannot grant discovery, selection, canonical status or reuse. A held permit becomes invalid.
A new positive assessment and fresh attestation/validation/admission are required, or the
owner may retire a capability that competent Beta has made redundant. Reintroducing a
superseded Beta ID is refused. Historical construction costs remain historical; a separately
identified continuation assessment can use prospective incremental costs without erasing
the original assessment or the simulator's historical cash ledger.

### Complementary bundles

An admitted skill may depend on already admitted skills through `Manifest.dependencies`.
It may also contain jointly useful candidate-only assets through `Manifest.components`.
Components need current executable evidence, rights and scope coverage, but need not have
individually positive Alpha or standalone admission. The complete bundle carries the
paired advantage, complete costs and dependency conditions. Its validators attest the
combined assessment with exact component evidence hashes. A component evidence revision,
expiry, revocation or retirement invalidates future use of the bundle.

Every member can inspect/export each bundle-only component using `retrieve_component` on
the admitted bundle. These components do not enter standalone discovery or selection and
cannot obtain an independent reuse permit. Bundle scope, tools and action permissions
remain mandatory. This avoids forcing every complementary part to be profitable alone
while avoiding unsupported standalone Alpha labels. Candidate-only components are one
level deep in this bounded implementation; a deeper bundle must first obtain its own
admission and then be referenced as a dependency.

## Separate failure memory and protected evaluation material

`FailureMemory` is an immutable negative-report type in a distinct `_failures` store.
`record_failure` requires current record-writing authority, a unique identity disjoint
from skill identities, a scope, sanitized summary, failure category, exact evidence hash,
honest provenance and sharing-rights declarations. It binds the exact policy and Beta
configuration—including model, tool and environment context—at observation time.

Every authenticated member can inspect the sanitized reports through `read_failures`.
Responses explicitly contain `positive_alpha=false` and
`eligible_for_skill_selection=false`. The positive skill catalog, canonical promotion,
validation, admission and execution-permit paths do not consume these records. A report
cannot be converted into a skill by reusing its identifier. A separately corrected asset
would require a fresh identity and the full positive-capability lifecycle.

After a policy or Beta change, earlier reports remain readable as historical context with
`context_current=false`; they do not silently become a current conclusion. The record
owner can withdraw a report from future reading without reusing its identity or deleting
its committed history. This is a memory interface, not evidence that failure memory has
already improved a later mission. Its actual future benefit would need its own comparison.

Both skill creation and failure-memory admission explicitly reject a declaration that
the content contains protected evaluation testcases or scorer internals. Rights and
sanitization assertions remain mandatory, and the test fixtures contain only public or
synthetic summaries. **These are enforced declarations, not a semantic classifier or
proof of sanitization.** Actual protected evaluators require separate custody and an
extraction process that excludes protected material before sharing. A false declaration
is not made true by a signature, encrypted capsule or commitment.

Model, tool or execution-environment changes must produce a new `BetaBaseline` version
with the complete changed configuration hash. The tests exercise each change category
and refuse reuse under old admission. An attempt to reuse a Beta ID for changed contents
is rejected. The graph does not inspect external runtime state to discover unreported
configuration changes; the trusted adapter must supply the changed specification.

## Authority model

The direct-label grammar is the exact strict ASCII grammar used by the earlier Alpha
research authority implementation: one label of 1--63 lowercase letters, digits or internal
hyphens, followed by `.agent.agi.eth`. A nested name such as `x.y.agent.agi.eth` does not
match. Neither a suffix match nor a valid-looking name proves ownership.

`FixtureDirectory` is a trusted test-harness adapter containing explicit simulated
name-to-owner assignments. `open_session` requires both an enrolled direct name and its
exact fixture owner. A newly constructed object with identical session fields is refused:
the directory accepts only the actual session objects that it issued. Every access rechecks
current membership, and every action rechecks the distinct permission it needs.

| Concept | Research representation | What it does not establish |
|---|---|---|
| Creator identity | Exact manifest identity of the candidate's creator | Originality or truthful authorship outside the fixture |
| Record-writing authority | `record.write`, plus ownership of that record's writer identity | Authority over another member's records |
| Validator eligibility | Current direct member with `graph.validate`, excluding the creator | Independence of judgment or freedom from correlated errors |
| Admission authority | Separate `graph.admit` permission; the actor cannot be the producer/writer or one of this record's attestors | A power to bypass evidence or validation |
| Policy authority | Separate `graph.policy` permission | Production governance authority |
| Execution authority | Required action permissions, checked recursively over dependencies | Permission inferred from skill access alone |

The fixtures do not implement ENS Registry or NameWrapper reads, normalized ENS namehash,
wallet challenges, chain finality, operator delegation or identity expiry. The caller's
integer clock is supplied by the trusted research harness; the graph prevents it from
moving backward. It is not an authenticated network time service. Existing AGI Jobs
`*.club.agi.eth` roles, governance, contracts and settlement are unchanged and unused.

## Availability to the whole authenticated network

Every currently authenticated fixture member receives the same eligible admitted catalog.
There is no preferred recipient list. Admission explicitly refuses a reuse-rights value
other than `all-authenticated-direct-agents`.

Members may discover manifests, inspect scope and validation status, retrieve and export
the synthetic capsule, and inspect its provenance. They can compose admitted capabilities
by referencing exact dependency versions in a new candidate, which needs its own evidence
and admission. Retrieval and export do not require execution permission.

Selection is optional and checks the mission's family, scope, tools and current dependency
closure. Action authorization is a separate operation. A member without
`execute.synthetic` can retrieve the entire admitted capsule but is refused an execution
permit. This distinguishes universal skill availability from permission to act.

Exported material can be copied by an authorized recipient. Neither this API nor ENS
authentication can prevent that. Network restriction means controlled retrieval at this
boundary; it is not proof of non-copyability or of an economic moat.

## Evidence, attestation and freshness

An evidence object binds exact manifest and policy hashes, observation and replay hashes,
the covered scope, a case count and failures, a bounded benefit observation, rights checks,
provenance category and a validity interval. The gate refuses insufficient cases, failed
checks, nonpositive recorded benefit under the default policy, missing scope coverage,
stale evidence, malformed identities, nonfinite values, unsanitized material and narrowed
sharing rights. Default research thresholds are fixture policy parameters, not calibrated
scientific estimates or production acceptance thresholds.

The `source_kind` must be `actual-local-experiment` or `simulation-fixture`. This records
the supplied provenance claim; it does not authenticate an experiment by itself. The
standalone graph demonstration uses only simulation fixtures. A true capability claim
still requires the separately measured experiment and its complete replayable artifacts.

Attestations are immutable typed statements covering the exact skill/version manifest,
evidence revision, Alpha context (including Beta and component bindings), policy,
validator, verdict and expiry. Ed25519 signs and checks these
bytes. A changed verdict, evidence identity, policy identity or manifest fails signature
or binding verification. Two submissions by one validator still count as one attestor.
An unresolved adverse verdict blocks validation. Loss of validator eligibility or
attestation expiry invalidates future reuse.

Validation records the deterministic gate result; admission is a distinct transition
performed by a separately authorized actor. No reviewer label, user-interface score,
Merkle membership or creator assertion can replace those transitions. Even a valid
quorum can agree on a wrong claim: correlated producer/validator errors are an economic
and scientific uncertainty, not solved by the signature mechanism.

Every discovery, retrieval, selection and reuse authorization rechecks status, policy,
current Beta, positive bound Alpha assessment, evidence freshness, attestations, capsule
integrity and the full dependency/component closure.
Changing policy invalidates old admissions until they are freshly revalidated. A policy
version cannot be silently reused for different content or reintroduced after replacement.

A reuse permit is bound to the exact graph epoch, policy, evidence, Alpha assessment, Beta
and manifest. Immediately
before it is consumed, the graph rechecks the actor, scope, prerequisites, permissions,
current epoch and dependencies, under one in-process lock. Revocation, supersession,
policy/Beta change, expiry or lost membership between authorization and consumption causes
refusal. Permits are one-use. The operation returns an authorization receipt only: it
never runs capsule code, sends a transaction or executes a customer mission. The epoch
rule is deliberately conservative: even an unrelated graph mutation requires a fresh permit.

## Cryptography and privacy boundary

AES-GCM encryption, Ed25519 signatures and SHA-256 hashing are real local computations.
All encryption and signing keys are deterministically derived PUBLIC TEST FIXTURES.
They are not secrets, generated production credentials or evidence of real identity.
Anyone with this source can derive them. The deterministic nonce scheme is confined to
these synthetic fixtures and is not presented as a production encryption design.

The component stores synthetic capsule ciphertext and exposes public commitments
containing typed roots, schema, tree policy, current policy/Beta hashes, epoch and previous root.
Private capsule bytes do not appear in that public commitment. Authorized retrieval
checks the authenticated ciphertext and its plaintext content hash before returning it.
Because the fixture keys are public, the demonstration provides no real confidentiality.

Merkle construction uses SHA-256, domain-separated schema-bound leaves, lexicographically
sorted pairs and duplication of the last leaf at an odd-width level. Epochs bind the
previous root, typed state/event/policy/Beta/failure-memory roots and tree policy. The serializer is explicitly
Python's sorted-key, compact, ASCII-escaped JSON with nonfinite numbers refused. It is
not RFC 8785 JCS, Ethereum Keccak, EIP-712, or byte-compatible with another graph profile.
Inclusion verifies commitment membership only; a candidate can have a valid inclusion
proof while remaining entirely unavailable for reuse. No ZK proof, circuit or on-chain
publication is implemented or simulated as having passed.

## Supplied drafts and preserved foundations

The supplied documents were read as design references, with these concrete corrections:

| Source | Relevant draft behavior or rule | Implemented treatment |
|---|---|---|
| GoalOS V93 HTML, `gateStatus` / `canonicalStatus` | Slider-derived scores and a nonempty validator array count toward illustrative gates | Exact evidence revisions and signed eligible attestors; no slider inputs |
| GoalOS V93 HTML, `canonicalReview` | A successful separate canonical score path writes `canonical-admitted` | Promotion requires a previously admitted, currently valid record |
| GoalOS V93 HTML, `generateNextMission` | It reads the last Chronicle entry without checking current retirement | Selection recursively checks current status and evidence; old history never grants authority |
| GoalOS V93 HTML, `reuseSelected` | Status strings decide reuse; scopes and dependencies are not revalidated there | Exact scope/prerequisite/dependency/permission checks at selection and use |
| GoalOS V97.4, sections 3, 6--8 | Direct child owner authority, typed attestations, encrypted capsules, admission before influence | Exact direct-name fixture ownership and role checks; tested stateful admission; explicit simulation boundary |
| Merkle Roots v114 | Domain-separated leaves, typed roots, previous-root continuity, inclusion distinct from truth | Executable SHA-256 research profile with policy-bound epochs; no Ethereum compatibility claim |
| PROOF LOOPS v2 | Proof debt, replay, bounded Chronicle admission and future-use scope | Evidence and validation stages, rejection/refusal, fresh revalidation and terminal removal |

Local source SHA-256 identities:

- V93 HTML: `3c3d606a76ec6a0ca1e854205032042284f83cff866e5eb3f3ae541675dac6ee`.
- V97.4 PDF: `ab140a1f7420a6e7c907f4e2f4e51fdb7075ac521b0ffca2bbf59b8e63cbbe2e`.
- Merkle v114 LaTeX: `c7e212fbb12381576ce2bc7cbdd9f73f5a93cb7ce28b33ffb03dde740911a178`.
- PROOF LOOPS v2 LaTeX: `439cf85ed3967fe0f8eaeedade36b3f3dcf93f40ed9c9fca61d4e904b706cd4b`.

Public foundation source commit is
`1e9a5675b1662e98074fb1c71cf2c5b94c7d259f` in
[goalos-agialpha-sovereign-machine-economy](https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/tree/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper).

The existing Alpha graph study was inspected at PR #4942, commit
`c9f2892c06e173cb0f9d5ae710cffc4a6f1fa723`:

- `src/authority.mjs`, Git blob `eec888f9ff3c60248f1c0e81aaf20a50f15fe9c8`.
- `src/commitments.mjs`, Git blob `c9108720455f80a8d36e54b25d0e6bee2738bcb2`.
- `src/selection.mjs`, Git blob `e8704096982bef6c0c3abf19a6f9c28382a24f00`.

Those assets already implement scoped immutable-catalog selection, operation-scoped
fixture authority and typed Merkle checks for the earlier dependency study. Their exact
direct-label grammar, immutable input principle, current-authority distinction and
commitment-versus-admission separation are reused here. This module is a Python stateful
research specification for the new creation-to-sharing lifecycle, all-member retrieval
and immediately checked reuse permits. It does not copy or replace the earlier selector,
change its owner, silently adopt its frozen source, or treat its earlier economic result
as the result of this study. No active production runtime or graph is replaced.

## Additional Navigator manuscript: full reading and applied principles

The supplied Vincent Boucher manuscript, *Mission-Sovereign Successors: GoalOS
Singularity Navigator Ω + SEIZE*, v5.0.0, 9 August 2026, was read across all 71 PDF pages'
extracted text, including the full main text, appendices and references. Printed body page
1 is PDF page 11. The image-only visual plate and other figure artwork were interpreted
through captions and surrounding typeset text, not decoded as quantitative evidence.
No textual page was omitted. The supplied PDF SHA-256 is
`9dd9caa6170bd1905e52926516d687c47313d58cd5e2a59e6038eabf0014639b`;
the extracted `navigator_successor.txt` SHA-256 is
`817417f713db8458e70e522ce25d2706ffff70ebefe0942331b1036c3e7e6706`.

| Manuscript principle and location | Application in this bounded study |
|---|---|
| The mission-bearing object includes models, data, harness, tools, verifier, workflow, evidence and authority; novelty alone is insufficient. §§2–3, printed pp.3–6 / PDF pp.13–16 | The manifest, evidence, Alpha comparison, exact dependencies and separate permissions bind a complete scoped capability claim. The economic comparator includes ordinary methods and current assets. |
| Gross opportunity is distinct from residual advantage after complete burden. §§7.3–7.4, printed pp.14–15 / PDF pp.24–25 | The Alpha gate subtracts attributable costs and a declared uncertainty margin. Paid delivery, incremental retention and separate R&D are separate accounting contexts; historical paid work is not charged twice. |
| Producer, verifier and admitter are distinct; protected cases and scorer internals are outside candidate formation. §§5.2, 9.6, 10.1–10.4, printed pp.10,22–24 / PDF pp.20,32–34 | Admission rejects the producer/writer and this record's attestors even if they hold overlapping role permissions. Capsule/failure inputs reject declared protected evaluation contents. Signatures still do not prove truthful independent judgment or semantic sanitization. |
| Authority is capped by current evidence and is not inherited with a replacement. §§7.9, 10.3, printed pp.16,24 / PDF pp.26,34 | Current evidence/policy/Beta, membership, scope, dependencies and permissions are checked at use. Admission is separate from access, validation and canonical presentation. |
| Material model, tool, prompt, representation, provider, runtime or environment change creates a new release requiring fresh proof. §13.1, printed p.31 / PDF p.41 | Beta binds the complete model/tool/environment specification; fresh versions invalidate older admission. Tests exercise model, tool and environment updates. The adapter remains responsible for reporting an external change. |
| A separate negative capability graph preserves failed architectures, invalidated assumptions and unsafe-use conditions. §14.3, printed p.33 / PDF p.43 | `FailureMemory` is a distinct authenticated negative-report store and commitment root. It cannot become positive Alpha, appear in skill selection or authorize execution. |
| Recurrence and more memory are not recursive improvement; fresh mission gain must be measured. §§13.4, 15.4–15.5, printed pp.32,35–36 / PDF pp.42,45–46 | Transfer effects require matched comparisons; counts of entries, uses or reports do not establish compounding. The graph's failure-memory API does not claim a measured learning benefit. |
| Protected evaluation custody is separate from public navigation and formation. §§17.1–17.3 and appendix D, printed pp.37–38,57 / PDF pp.47–48,67 | Shared capsules and demos exclude protected testcases/scorer internals by declared policy. The in-memory fixture does not claim a deployed independent proof plane. |
| Value states distinguish modeled, realized, collected and reinvestable amounts. §15.2, printed p.35 / PDF p.45 | Simulated values remain explicitly modeled; prospective savings do not supply cash for present spending. Token utility does not create operating earnings. |
| Clean rejection is a valid outcome, and the broader institutional claims are falsifiable. §25, printed pp.53–54 / PDF pp.63–64 | Rejection, no retention, waiting, retirement and negative findings remain valid outcomes. No Specialist ASI, Mission-Sovereign deployment or commercial proof is asserted. |

The document is a design reference, not inherited task authority or calibration. Its
illustrative acquisition scorecard—such as the percentage targets on printed p.52 / PDF
p.62—is not evidence for this venture. Its canonical 21-job portfolio and proposed
commercial rollout are not mandatory workloads here. The manuscript's human-release
choices are not imported as routine provider review into the user's fully automated
primary configuration. Likewise, its separate public Navigator dual-access rule on
printed pp.36–37 / PDF pp.46–47 does not widen this study's direct-agent network or alter
native AGI Jobs roles. Its broad best-alternative doctrine motivates a competent internal
Beta control; the user's matched human-service commercial reference remains unchanged.

## Executed checks

From the package root:

```bash
python3 -m unittest discover -s tests -p 'test_skill_graph.py' -v
python3 -m unittest discover -s tests -p 'test_alpha_assessment.py' -v
python3 src/skill_graph.py > evidence/graph_demo.json
```

The original development graph passed 28 test methods before the user's Beyond Beta
steering. Those checks remain in the extended suite. The new focused suites passed
44 lifecycle and 6 Alpha arithmetic test methods on Python 3.12.14 with cryptography 50.0.2.
It covers direct-name rejection and exact ownership, forged sessions, role separation,
canonical/admission bypass, failed and adverse evidence, zero benefit, signature and
binding tampering, duplicate attestors, self-validation, availability to every member,
action-permission separation, scope/tools, rights/sanitization, terminal revocation and
retirement, freshness, monotone time, policy migration, evidence revision, dependencies,
supersession, one-use permits, membership/eligibility changes, ciphertext tampering,
snapshot isolation, typed Merkle proofs and honest demo labels. The extension also covers
Alpha-stage bypass, full-cost and redundancy rejection, Beta/scope/comparator/evidence
binding, a comparator changing during admission, exact duplicate payloads, moving-Beta
invalidation and reassessment, retirement after Beta catches up, jointly useful components
without standalone Alpha, component evidence revisions, explicit matched-probe weights
and uncertainty-bound arithmetic.

The v2 extension additionally checks negative memory, disjoint identifiers, all-member
reading, historical context, withdrawal, protected-material declarations, model/tool/
environment changes and producer/attestor/admitter separation even with overlapping
permission assignments. These are software checks, not 50 inventions, buyers, validators
or scientific trials.
The generated demo admits one synthetic capsule, makes it available to all six fixture
members, allows retrieval by a member lacking execution permission, authorizes one
simulated reuse, changes Beta and blocks earlier authority, then completes fresh assessment
and admission before revocation. It also rejects a separate valid-looking but uneconomic
candidate. The positive fixture uses paired gross gains 90 and 110, ten declared future
uses, a 20-per-use uncertainty margin and 220 total costs: lower/mean/upper net values
are 580/780/980 in the declared fixture USD unit. The costly candidate's lower bound is
negative 1,200. These numbers test arithmetic and lifecycle behavior; they are not measured
research or commercial outcomes. The final fixture refuses held reuse and readmission.
It records zero
on-chain transactions, no code execution, no production confidentiality and no ZK proofs.

The full Alpha environment setup, repository-wide coverage, hosted checks, production
ENS enforcement and external security review were not run by this component worker.
Black, Ruff and mypy were not initially installed in its isolated environment; the root
delivery process may perform and report additional checks. This is not a gate waiver.

## Remaining production work

Production adoption requires separately authorized and reviewed identity resolution,
wallet challenge verification, current ENS Registry/NameWrapper ownership observations,
expiry/revocation and authority-epoch handling; durable transactional state; an audited
policy and admission service; secret key management and encryption with real recipient
access control; sandboxed execution; secure artifact retrieval; independent task-specific
validation; versioned competent Beta evaluations with current existing capabilities; and
measurement of actual recipient benefit and complete operation costs.

The public Python object boundary is not a hostile-process sandbox. A caller with arbitrary
memory access can alter private internals; process isolation and server-side authority
would be required in operation. Encrypted at-rest storage does not stop an authorized
recipient copying an exported skill. Rights and sanitization assertions need substantive
review mechanisms in a real deployment. These limitations are separate from, and must not
be hidden by, successful signatures, inclusion proofs or the lifecycle test results.
