# SUCCESSOR Ω requirement and acceptance evidence

This matrix maps the implementation mandate to executable code and checks. It is a traceability record, not a
certificate that every release gate or external qualification has passed. The exact accepted revision, command results,
platforms, failures, omissions, package hashes and deployment observations belong in the release validation evidence.

The advertised local mission is `streaming-metrics-v1`. Its candidate language is a closed composition of fixed
aggregation operators. The native and browser rehearsals execute real computation without credentials, wallets or a
model download. They do not execute arbitrary generated Python on the host. The separate legacy native coding runner
continues to require explicit Docker opt-in and its existing isolation acceptance gate.

## Evidence interpretation

| Status | What it establishes |
|---|---|
| Implemented with an automated check | The named implementation and assertion exist. A retained successful run is still required for release acceptance. |
| Local measured computation | Actual formation, aggregation, comparison or recovery ran in the declared local environment. It establishes neither independent verification nor customer value. |
| Fixture or fault injection | A deliberately controlled adversarial condition exercises a guard. It is not a live provider, independent organization or commissioned chain. |
| Required release gate | The workflow must run the named check on the final source and packaged bytes. An unavailable runner remains untested, not passed. |
| External qualification unavailable | A functional interface exists, but independent evidence, customer acceptance or accountable production authority has not been supplied. The qualification remains `HOLD`. |

## Architecture and protocol coverage

Implementation paths below are relative to the repository root. `successor/` abbreviates
`alpha_factory_v1/core/runtime/successor/`; test paths abbreviate `tests/runtime/` unless stated otherwise.

| Mandate responsibility | Implementation | Verification and limits |
|---|---|---|
| Persistent identity; separate WORLD, POLICY, PROOF and AUTHORITY | `protocol.py`, `state.py`, `mission.py`, `evaluation.py` | Strict records, separate scientific receipts/admission/grants and a signed institution journal. `test_successor_state.py` exercises distinct transitions. |
| Versioned shared objects, schema rejection, canonical signatures and commitments | `protocol.py`, `schemas.json`, `canonical-vectors.json`, `trust.py` | `test_successor_protocol.py`; `tests/browser/successor_engine.test.mjs`. Four vectors cover UTF-8, Unicode normalization distinctions, control escapes, ASCII key ordering and safe integer boundaries. Historical signature formats remain unchanged. |
| Explicit specialist designation policy | `SpecialistDesignationPolicy` in `protocol.py`; `assess_designation` in `state.py` | Six comparator families require explicit applicability decisions. Signed policy and currently trusted independent receipts bind mission, validity, superiority threshold, evaluation units and replication. Local proof cannot earn the label. |
| Underwriting and distinct economic records | `UnderwritingDecision`, `ForecastRecord`, `ExperimentalMeasurement`, `AcceptedOutcome`, `SettlementReceipt`, `ResourceReservation`, `AllocationDecision` | `test_successor_protocol.py` rejects unconsidered selections, unknown measurements disguised as zero and allocations exceeding available resources after reserves. Local runtime economics do not create realized customer value. |
| Atomic transitions, shared budgets, idempotency and crash recovery | `state.py`, existing `core/runtime/store.py` | `test_successor_state.py` uses actual signed SQLite journals, concurrent reservations and crash injection. Conservative reservations cannot be refunded by a caller reporting zero consumption. |
| Single complete grant at the actual action boundary | `SuccessorStore`, `ActionGateway` in `state.py` | State and independent adversarial tests deny wrong context/target, another institution's controller approval, omitted resource units, grant-fragment union, local proof promoted to production and post-dispatch revocation. Only operator-installed fixed handlers are exposed. |
| Sealed jobs, seven families, typed dependencies and finite repair | `jobs.py` and protocol job schemas | `test_successor_jobs.py`: actual fixed tools execute; cycles, missing coverage, role overlap, incomplete inputs and changed terms reject. Version one rejects cycles rather than claiming a general bounded-cycle executor. |
| Actual construction and WORLD-informed experiment selection | `GrammarSupplier`, `discover`, `_world` in `mission.py` | `test_successor_mission.py`: at least two distinct compositions are constructed, predictions are committed before candidate measurements and measured residuals affect selection. Unexecuted legacy laboratories retain their original names and scopes. |
| Exact aggregation and competent fixed comparators | `aggregation.py`, `comparator_manifest` in `evaluation.py` | All eight grammar compositions obey exact integer/Unicode/malformed-input semantics. Current is a one-pass dictionary; Beta is a separately implemented sorted reducer. Missing frontier inference is explicitly unavailable. |
| Complete freeze and fresh protected examination | `validate_frozen`, `evaluate_frozen`, `examine` | `test_successor_mission.py` binds code, program, supplier configuration, memory, environment, WORLD/POLICY, comparators, costs and proof protocol. `test_successor_adversarial.py` mutates the caller's freeze during examination: the private snapshot remains the examined artifact. |
| Protected evidence custody | Closed grammar plus separate local verifier process | Real examination uses fresh custodian entropy after freeze. The independent adversarial test inserts private canaries and confirms neither raw values nor private seeds reach exported reports or cancellation callbacks. A separate local process is not an independent organization. |
| Matched second generation and honest compounding claims | `renew_study` in `mission.py` | `test_successor_mission.py` checks preregistration, equal allowances, fresh proof, separate supplier/context copies, complete paired runs and no inherited permission. Small formation-trial results remain descriptive; losses are valid outcomes. |
| Replaceable cognitive suppliers | `GrammarSupplier`, `OpenAICompatibleSupplier`, existing `core/runtime/provider.py` | Two deterministic implementations run; live transport tests explicitly use a transport double. Real model substitution, remote-cache independence and frontier superiority require separately retained authorized provider runs. |
| Evidence rights, memory admission and revocation | `EvidenceSubmission`, `record_evidence`, `admit_memory`, dependency checks in `state.py` | `test_successor_state.py` checks revoked-memory influence; `test_successor_adversarial.py` denies inherited rights widening, removed restrictions, changed scope and cross-mission memory admission. Historical retention does not grant influence. |
| Portable restoration with independently supplied trust | `export_portable`, `restore_portable`, `JournalCheckpoint` | State and independent two-hop restore tests require an explicit source key/checkpoint, retain attributable historical records and leave active proof/grants/influence empty. A package cannot supply its own trusted key. Secret-bearing disaster recovery remains separate. |
| Private disaster recovery and role-key continuity | Existing `core/runtime/store.py` backup/restore; recovery validators in `trust.py` | `test_successor_backup.py` preserves original five-member backups, optionally retains the exact three role keys/public inventory and explicit public registry, restores private permissions and resumes a real signed state transition. Partial, mismatched, duplicate, traversal and linked members reject. This archive contains secrets. |
| Native/browser round trip and bilingual accessible journey | `cli.py`, `transport.py`, `docs/assets/successor/`, `docs/successor/` | `test_successor_transport.py`, browser engine tests and `scripts/validate_successor.py`. Actual browser acceptance includes native CLI file handoff; installed-wheel isolation is a separate gate. Screens or unsigned checksums do not establish authenticity. |
| Legacy functionality, diagrams, routes and release compatibility | Existing native runtime; `scripts/check_successor_preservation.py` | Machine inventory and existing regression suites remain required. New institution qualification is not imposed on legacy analytical commands. |
| Packaging, final-source identity and asset-size ceiling | `scripts/package_agent_release.py`, `scripts/release_packs.py`, existing release workflow | Wheel contents include runtime, schemas and vectors. Core and optional packs retain content; every distributed file must remain at or below 450,000,000 bytes. Final packaged-byte execution and hashes are separate required evidence. |

## Mandatory adversarial scenarios

| Scenario | Enforced or measured result | Primary automated evidence |
|---|---|---|
| Complete offline mission through two generations | Actual formation, frozen fresh examination, honest verdict and matched renewal execute; missing external qualification remains `HOLD`. | `test_successor_mission.py`; installed CLI acceptance in the release workflow; `scripts/validate_successor.py` |
| Candidate beats Current but loses to Beta | The strongest measured fixed alternative is retained; no custom-candidate Alpha claim. | `test_candidate_faster_than_current_but_slower_than_beta_retains_beta` uses declared measurement fixtures. |
| One wrong result despite faster execution | Hard correctness failure vetoes speed. | `test_live_wrong_candidate_is_rejected_by_actual_examination` injects an actual faulty candidate execution. |
| Excess resources or injected effectful instructions | Bounded grammar rejects unsupported operators and oversized inputs; measured resource failures fail evaluation. Arbitrary Python needs the separate Docker boundary. | `test_successor_mission.py`; `test_instruction_shaped_input_stays_data_and_cannot_open_files`; `scripts/validate_agent_sandbox.py` remains a required real-Docker gate. |
| Code, prompts/routing, memory, environment, objectives, comparator or cost rules change after freeze | The release commitment changes; stale or unsupported terms cannot reuse the old examination. | `test_changed_behavior_or_economics_cannot_reuse_exact_freeze`; caller-mutation adversarial test. |
| Formation attempts to read protected cases | Candidate grammar has no file, network or evaluator-access operator; protected canaries and entropy are not exported. | Closed-language tests and `test_protected_values_are_not_exposed_in_report_or_callbacks`. |
| Forged receipt/status or attacker-selected key | Integrity and authenticity are separate; only out-of-band configured keys satisfy authentication and roles. | `test_successor_transport.py`; receipt guards in `test_successor_state.py`. |
| Local verifier relabelled as external | Local provenance remains local and cannot authorize production. | `test_receipt_identity_independence_expiry_and_claim_guards`; `test_no_fragment_union_wrong_context_or_local_production`. |
| Valid proof without an applicable current grant | Complete action context is denied. | `test_successor_state.py`. |
| Action/target/budget fragments taken from separate grants | No synthetic union of permission is constructed. | `test_no_fragment_union_wrong_context_or_local_production`. |
| Concurrent work or retries exhaust a shared budget | Atomic reservations and conservative spending prevent double allocation; unknown costs remain explicit. | `test_parallel_reservations_never_overspend`; cumulative budget tests; job retry tests. |
| Revocation after dispatch | Both operational and development tool boundaries revalidate. | `test_real_boundary_revocation_and_idempotent_conservative_accounting`; `test_revoked_dependency_after_dispatch_blocks_actual_action`. |
| Missing evidence, expired rights or revoked dependency | Dependent influence and claims fail closed while history remains. | Memory-revocation tests, job dependency tests and inherited-rights adversarial tests. |
| Cycles or unbounded repair | Cyclic graphs reject; per-job attempts have finite declared bounds. | `test_compiler_rejects_cycles_missing_coverage_role_overlap_and_partial_ports`; retry tests. |
| Nonzero plan index or identical specs at different indices | Actual-index Merkle leaf and zero-index market hash remain distinct. | `test_successor_ascension.py`; `tests/contracts/test/ascension/successor-adapter.test.js`. |
| Rich terms change while legacy Spec remains the same | New domain-separated terms digest changes; legacy commitments retain their historical meaning. | `test_seal_freezes_richer_terms_even_when_legacy_spec_is_unchanged`. |
| Wrong chain, market, job, worker, release, environment or duplicate settlement | Exact assignment/delivery bindings reject mismatches; concurrent imports attribute once. | `test_successor_ascension.py`; RPC doubles are labelled as unit fixtures. |
| Useful negative evaluation report is accepted | Work acceptance and settlement do not admit the evaluated candidate. | Negative-report adapter test and local EVM successor-adapter contract test. |
| Settlement review quorum is missing | Existing refund/unlock behavior is preserved, not recast as failed work. | Missing-quorum adapter and Solidity lifecycle tests. |
| New provider violates correctness or fails | Failure remains unavailable/failed; no deterministic fixture silently becomes live inference. | Live-supplier transport and failure tests; hard correctness gate; impairment tests. |
| Stronger Beta or worsened economics | Alpha is withheld or impaired separately from unrelated claims. | Comparative-decision fixtures and claim-specific impairment state tests. |
| Descendant or restored package carries predecessor grants | Active proof and authority do not transfer. | Restore/descendant state tests and generation-two empty-inheritance assertions. |
| Memory loses or only helps inspected tasks | Every pair is reported; no fresh-transfer or recursive-improvement claim is made. | Full renewal test and report assertions; actual signed study results record the observed direction. |
| Crash, duplicate command or concurrent cutover | Durable execution intent prevents an uncertain effect being replayed; cutover uses one serialized serving state. | State/job crash injection, idempotency and reservation tests. |
| Corrupt, oversized, deep, duplicate-key or malformed import | Bounded rejection precedes parsing/state replacement; portable JSON has no archive extraction. Legacy backup extraction retains its own traversal/symlink checks. | `test_successor_protocol.py`, `test_successor_transport.py`, existing `test_execution_boundaries.py`. |
| Browser/native canonical commitments and round trip | Exact semantics and request/evidence bindings match; displayed scope remains local. | Four canonical vectors, browser engine tests and real CLI/browser acceptance. |
| Clean restore and supplier substitution | Separate source trust/checkpoint is required; deterministic substitution executes equivalent bounded probes. | State restore tests and mission substitution report. Real model substitution remains unqualified. |
| Preserved missions, demonstrations, diagrams and URLs | Inventory and old runtime/website checks remain required. | `scripts/check_successor_preservation.py`, native regression suite, public-site acceptance. |

## Checks that must remain separate

1. Python tests of a closed grammar do not establish operating-system isolation for arbitrary code. Preserve the real
   Docker test, with no host fallback.
2. RPC doubles do not establish local-EVM settlement. Execute the Solidity successor-adapter test on its verified
   disposable local chain and retain the trace. Neither establishes mainnet commissioning.
3. Deterministic supplier substitution does not establish two real model providers or neural execution.
4. Hash/signature replay authenticates recorded measurements; a fresh examination produces new measurements and a new
   receipt. Repeated timing samples are not additional independent formation trials.
5. Source-tree tests do not establish installed-wheel completeness, browser-cache upgrades, deployment or final asset
   identity. Run the release workflow's installed and public acceptance checks on the exact packaged revision.
6. Local controller/verifier keys implement a useful rehearsal of distinct roles. They do not establish independent
   organizations, an external proof network, customer Alpha, specialist ASI designation or production authority.

## Reproduction entry points

Use the documented minimal-runtime profile and supported tool versions. The focused Python suite is:

```sh
python -m pytest tests/runtime/test_successor_*.py
```

The browser engine checks are:

```sh
node --test tests/browser/successor_engine.test.mjs
```

`scripts/validate_successor.py` drives real browser controls, native file handoff, authenticity downgrade when the
separately supplied key is removed, malformed imports, cancellation, changed-input invalidation, bilingual keyboard
operation, narrow layouts, mirrored routes and cached offline operation. The release workflow additionally invokes
it on the packaged site and, after authorized publication, the deployed URL. A first uncached offline visit and
optional downloaded model assets are not implied by cached-operation success.

Release completion requires the existing full acceptance workflow, not just these focused commands. Consult
[release readiness](RELEASE_READINESS.md), [validation scope](VALIDATION.md) and
[the architecture decision](SUCCESSOR_ARCHITECTURE.md) for the surrounding release and deployment boundaries.
