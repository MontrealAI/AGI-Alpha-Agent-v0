# Runtime integration audit — 2026-10-22

## Exact source snapshot

- Alpha main: 61532fb82621a065e668fd11e57289dcfb65c67b; tree 7814d1bd9dcd3845b349590e0bcac57ba93b3167.
- Jobs main: ba67d5d19ef7d9ac643f99f2b8f49c160714fdf6; tree 16c29d934e8bb4d36d286fae7fbf3f9b9d506a85.
- Manager main: 3153ac394d37eeecb03e825ecce37559427bc6c3; tree 4a08ce51d68ea57bbb7193275870053b79943c25.
- Fleet main: 45759fb096faf8988f58ae5ea71248d0f35a97c7; tree 71a0ab1f0d2784ba552d0126903bd31d60262313.

The repositories were read through authenticated GitHub GET tools. This is a source snapshot, not an installed compatibility manifest.

## Current ownership and restrictions

Issue 4850: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850

- Alpha 4855: head 60daaf8d4135dc3f198190f101be026d6f6c84c9, branch additive/autonomous-enterprises-foundry-c165, proposed v1.39 experimental foundry. Current source lease owns ordinary qualified integration after v1.38 acceptance.
- Research 4869: 19a13e4440da93668dd42c537ac43a011cd2a0c2, branch research/foundry-v2-publication-20261022. Known historical fixed-count tests fail; do not merge this source independently.
- Research site 4870: 0b6630a15c8d2765b5c242856a4525e5490bdb83, stacked on 4869. Existing owner corrects catalogue/generator and HTML/CTA. Safe main integration comes after 4855/v1.39 release lease closes. Do not duplicate site infrastructure.
- Harness 4863: c455ad4ce109c86df2fef09d19674810290b5185, branch codex/successor-omega-harness-20261022. Existing restriction remains explicit in issuecomment-6347342683. Configured review summary-6345107482 still RUNNING since 15:54:08Z; empty reviews do not clear it. Do not retry denied merge unchanged, copy held source into another PR, trigger duplicate review, or change settings.
- Ascension 4865: 6bb361d522d80dc900cc2a480014531c6a44b66e, stacked on 4863. Existing owner connects enterprise configuration to Studio prepare/seal/assignment/fixed-worker/review/settlement; no new executor.
- Thermal 4871: 175d8a50473ea94f8c63d20959c22c95dfc6b886, branch feat/thermal-volume-witness-20261022. Uses released createWorkbench(adapters). Native registration/recovery enhancement is actively owned; do not duplicate.
- Jobs 4021, Manager 1623 publication, Fleet 65+64+66 retain their existing owners. Fleet 61 remains held.
- Issue body has historical status. Latest comments are more current: issuecomment-6352557424 is the current four-repository coordination map; source lease is issuecomment-6351696344.

## Existing extension seam

Canonical source: examples/successor-workbench/engine.mjs (Git blob d3f20b907b4d57867d9a12f46e4c32fb71a03b21 at Alpha615).

createWorkbench accepts an array of trusted installed adapters:
- manifest: id, version, en, fr, scope, artifact;
- validate(inputs);
- async execute(inputs, checkpoint).

Execute returns exactly decision, summary, evidence, artifacts, limits. Each artifact has name, type, content. Max 12; max 200,000 characters per content. Filename must be a simple bounded safe basename; reserved export filenames and device names reject. Inputs are closed-schema workbench/v1 with family, name, language, owner, rights, reviewMinutes, inputs. Rights dataClass is public, licensed-nonpersonal, or synthetic.

The returned runtime exposes registry, validate, plan, run, inspectPack. run requires a 64-hex sourceHash. It captures inert input, commits mission/source/adapter version, calls cooperative checkpoints, retains outcomes/artifacts, and computes complete pack integrity. An adapter must checkpoint throughout bounded search.

run uses a 60-second cooperative deadline; the native wrapper has an independent 65-second process deadline. New adapter code must enforce a deterministic total work budget as well. Existing sourceHash is caller supplied; the new runner must hash the complete actual transitive source closure, not manufacture a version label.

plan uses existing build-successor compiler: 21 obligations grouped into seven lifecycle work packages (constitution, evidence, formation, challenge, verification, admission, renewal); zero currency cap. inspectPack checks pack/artifact/mission and compilation bindings and returns historical unauthenticated import with empty proof and authority. It does not promote capability or prove scientific truth.

Extension example: examples/successor-workbench/extension.mjs (blob de6907e09facab25061b251df5f42c8f38d8dc37). Prefer importing the existing engine in a new narrow directory. Do not modify built-in registry or accept adapter code from mission JSON.

## Native persistence and control already exist

Canonical source: alpha_factory_v1/core/runtime/successor/workbench.py (blob d90d6321cb9b75b3cfc466945874b72c2c8ebdfa).

- invoke(request, checkpoint) launches only the shipped Node worker with scrubbed environment, 2 MB request/output cap, polling cancellation, 65-second deadline, bounded error class.
- execute(home, spec, run_id, resume=False) validates/compiles, initializes/verifies Journal, freezes lifecycle, persists @successor-work record, enforces request idempotency, CAS revisions, 70-second lease, three attempts, global operator pause and stop/retire.
- Completed review/accepted/rejected records return idempotently. Interrupted pure work requires explicit --resume. Terminal stopped/retired work cannot resume.
- write_artifacts writes only an absent directory. Existing artifacts are not overwritten.
- freeze uses existing SuccessorStore, Institution, MissionConstitution, CandidateReleaseManifest and local role custody; authority ceiling none, unknown compute and human-review costs.
- review requires current result digest and bounded note. Local operator review explicitly independent:false.
- restore validates pack then exports only task plus historical observations with empty proof/authority.
- exports add lifecycle.json and Ed25519 signed-receipt.json; external source key must be supplied independently to establish attribution.
- Existing owner is fixing source-hash upgrade/requalification behavior. At Alpha615, freeze happens before completed-record return, and source/config changes can cause idempotency conflict; do not implement a competing patch.

Generator/source owners: scripts/generate_successor_workbench.py, workbench_worker.mjs, workbench_sources.json. New adapter does not enter installed alpha-agent until legitimate reviewed registration/bundling occurs. A standalone SDK run is not native acceptance.

## Controlled promotion is already a distinct lifecycle

SuccessorStore in state.py (blob c008688e5e0ab8301d8a6062992660129497867e):
- register_release freezes full behavior and nominates it; does not change serving release.
- record_proof authenticates verifier identity, exact release/environment, rejects producer self-verification, retains negative verdicts.
- admit requires accountable controller/admission role and constitution-required positive proofs; rejected admissions impair grants.
- grant enforces exact release, separate issuer/controller, positive resource limits, valid time and constitution ceiling.
- dispatch_action / execute_action reserve/charge, track uncertain effects and require explicit recovery.
- cutover, recover and descendant are existing APIs; descendant creates a candidate without inheriting authority.
- evidence/memory rights, expiry, revocation and dependence are checked; proofs of Alpha refuse unknown costs/overruns.
- Independent provenance cannot be asserted by relabeling a local key.

The public workbench's review state is not equivalent to these serving-release, admission, proof or authority gates.

## Four-repository boundaries actually supported

Manager3153:
scripts/integrations/discovery-installed-operator.mjs (blob 01c805e21cc70fc2a2dc8ac7a52ea474111a598d) inspectInstalledRequest accepts an already verified saved Alpha capsule, original workspace/request, campaignDigest, sourceContext. It selects exactly one accepted current-source campaign, independently reconstructs request, calls installed semantic checker, appends one receiver receipt in same history, rejects duplicates/forged authority, verifies docket/reopen byte identity. Output cap 0 USDC6, authority none, external execution unprovisioned. It is not a generic new-adapter receiver.

Jobsba67:
integrations/alpha-agent/README.md and actual receiver facilities select backend agijobsv0-jobregistry-v2 explicitly. Assignment is first eligible apply, not employer offer auction. Fixed public-data and computer receipt integration exists; workbench drafts do not transfer admission or settlement. Real modular Solidity local fixtures exist with permissive identity and operator-controlled validation; those assumptions are not real validator independence. Discovery receiver changes remain with 4021.

Fleet457:
local-runtime/project/transfer.mjs (blob 03f5912fe20744c05fa7f7a067234d0ac38ca33a) maps Alpha public-data projects to bounded offline row work, separately retains execution and internal review, authority none, settlement not-connected, source authenticity not established. New adapter task support needs existing owner qualification; it cannot be declared native/external merely by wrapping JSON.

local-runtime/alpha/native-qualification/README.md is candidate IPC qualification with synthetic isolated grants; production trust targets stay null. It requires real namespace/cancellation/CPU/output probes on qualified Linux host. Passing candidate fixture is not production provisioning/admission.

## Minimal additive plan

Implement only new nonthermal capability-construction adapter, independent reference/checker, three distinct mission families, frozen requirement/capability certificates, explicit no-inheritance baseline and rejected successor. Use existing engine and inert source-bound packs. Source changes owned by this lane should be restricted to new adapter/research paths and one agreed test selector later.

Coordinate native registration with current 4871 owner. Coordinate formal enterprise lifecycle through legitimate 4863/4865 integration. Coordinate site placement/catalogue through research owner after current source lease. Existing Alpha/Manager/Jobs/Fleet adapters may be listed in architecture but only claim exercised paths that actually accept and execute this family.

## Meaningful verification sequence

1. New adapter unit/independent-reference tests and workbench package round-trip/tamper/cancel/budget checks.
2. Frozen acceptance before search; whole-budget exhaustive or competent conventional baseline; held-out successor requirement committed after parent freeze; reject stale boundary and regression.
3. Exact native registration: real worker execution, idempotent duplicate, worker interruption, explicit resume, stop, exhausted attempts, full source upgrade/requalification and retained earlier result.
4. 1/10/100 heterogeneous missions in a single pinned runtime, concurrency 1 and bounded shared-resource concurrency, p50/p95 and per-mission quality/cost; count failures/retries and benchmark overhead. Do not pretend cached identical requests are scale evidence.
5. Distinct producer/checker algorithms and identities; same acceptance; record ordinary ties/wins/losses. Local keys remain local controlled roles.
6. Existing source-controlled contract adapter on disposable EVM; no custom Python substitute or forced supported-family claim.
7. Qualified integration and publication through owner lease; then public bytes/routes.

## Audit execution limitation

Initial local commands and five source-file materializations succeeded in /tmp/successor-runtime-audit. Git HTTP failed at unavailable browser proxy; urllib socket was denied by sandbox. Later local exec transport disconnected. No new tests, local EVM, browser run, installed release, remote execution or public release was performed in this audit. Existing test assertions and owner's reported results are attributed to source/history, not reexecuted here.
