# The Capability Advantage: foundation and integration audit

Read-only audit, 26 October 2026. Scope: both supplied original papers; existing verified-capability implementation; preserved four-repository integration specifications. No external source was modified and no live identity, operator, contract, credential or financial operation was run. Exact inspected bytes are listed in `foundation-source-identities.json`.

## What the foundations require

**PROOF LOOPS v2**, sections 6–12 and 14–18, specifies that mission acceptance and proof level precede work; evidence, risks, replay and reviewer observations belong in a dossier; Chronicle admission is a scoped policy decision. A skill is executable, versioned, evidenced and rollbackable. Current influence requires admission, scope match, freshness and no blocking condition. The paper calls for future-work benefit and complete-cost comparisons; node/edge growth does not satisfy that demand. Its L1–L5 proof levels are distinct from this assignment's six economic success levels. Same-session research review cannot be renamed external organizational validation.

**Merkle Roots v114**, sections 5–12 and 15–23, specifies typed domain-separated commitments to nine object classes, explicit hash/canonicalization/tree policies, previous-root-bound epochs, and distinct Chronicle admission and root-writer authority. Root writing requires control or appropriate delegation for the direct `label.agent.agi.eth` node; deeper names do not inherit it. Inclusion establishes committed membership, not correctness or execution permission. Candidate commitments do not confer future influence. Revocation and supersession preserve historical state while blocking current use. The stated V107 registry surface, M0–M9 conformance levels and zero-knowledge design are specifications, not evidence that these features are deployed or audited.

The assignment's exclusive eligible-agent skill-attestation policy is **additional**. The Merkle paper's direct-agent rule is specifically a root-writing rule. Neither paper changes AGI Jobs' existing `*.club.agi.eth` validators.

Original PDF identities, verified against their preserved source inventory at GoalOS commit `1e9a5675b1662e98074fb1c71cf2c5b94c7d259f`:

| Foundation | Bytes | SHA-256 |
| --- | ---: | --- |
| Merkle Roots v114 | 508050 | `3276b66b3aa84d1fadc51d2a398579a8b3108294fafea1a5e239e70dd0fed7de` |
| PROOF LOOPS v2 | 240928 | `2c41599a893c4c5ac0eacdf9b4416f4420b3d47ee73c04ed868049b29a6055db` |

## Implemented versus proposed

The preserved GoalOS `kernel.py` is a local reference loop. It uses `local-reference-signature`, structural gating, simulated settlement and candidate capability emission. It is not live ENS authentication. A separate historical mainnet contract atlas records other GoalOS contracts; it contains no named VSG/Merkle graph-epoch registry. Do not generalize absence of this registry into absence of all historical GoalOS deployments. The prior foundation audit inspected AEP/Chronicle/namespace source controls as role-based `onlyOperator`; those checks do not authenticate an exclusive agent namespace. Current deployed bytes/state remain unverified.

The existing `verified-capability` study has implemented and tested a **fixture-only research layer**. Its architecture is reusable, but its prior four skills are ordinary metadata workflow components, and its tests do not establish scarce-capability transfer. It reports equal accepted outcomes for all four arms and no economic adoption. Those negative findings must remain preserved.

## Reuse these modules unchanged

Source root: `/workspace/scratch/56915413375a/verified-capability`.

| File | Reusable contract | Scope to preserve |
| --- | --- | --- |
| `src/authority.mjs` | `createFixtureResolver`, `createFixtureAttestation`, `authenticateAttestation`, `createFixtureRoot`, `authorizeRoot` | Direct ASCII agent subset; operation grants; exact scoped bindings; historical versus current validity; explicit `FIXTURE_NOT_CRYPTOGRAPHIC`; live mode refuses. |
| `src/commitments.mjs` | Canonical records, typed forests, inclusion, epochs, history | `SHA256_RESEARCH_V1`, safe-integer NFC canonicalization, sorted-pair duplicate-last trees; not byte-compatible with the paper's `JCS_KECCAK256_V2`. |
| `fixtures/authority.json` | Fixed ownership/wrapper/delegation/operation scenarios | Test fixtures only. Names/addresses never establish actual ownership. Scope and grants must be updated in new fixtures if changed, rather than assuming permission. |
| `native/` plus `native/SOURCE.json` | Seven unchanged native Workbench modules and existing Jobs compiler closure | Source commit `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`; local zero-authority extension seam; preserve licenses and hashes. |
| `src/selection.mjs` | Example equally evidenced registry/graph selection, lifecycle and proof gates | **Do not import prior admission as authority for new jobs.** It is tied to its own filesystem root, one scope, exact environment and one independently validated composition. New task families need new dossiers and admission. |

`authority.mjs` binds skill ID/version, implementation, dependency digests, scope, environment, policy, evidence, rights and expiry. Its attestation envelope also binds signer, exact agent, chain/registry, authority snapshot, issue/expiry time, nonce and graph. `ISSUE_SKILL_ATTESTATION` and `COMMIT_GRAPH_ROOT` are independent grants. Current reuse refuses expiry, revoked/superseded skills, unavailable evidence, authority changes and contextual mismatch. Reuse is distinguished from a new admission action so a legitimate read-only reuse need not consume the admission nonce again.

The selector checks the complete typed state, trusted expected root/epoch, authorized history, source/evidence bytes, dependency bindings, independent composition dossier and lifecycle records. Registry and graph receive the same skills, evidence and restrictions. Its existing implementation is adequate evidence of these bounded mechanisms; it is not a general planner or evidence of scaling superiority.

## Four-repository integration boundaries

Preserved source set: Alpha `b1d52a7…`; Fleet `45759fb…`; Jobs `bc4abbd…`; Manager `5d5670d…`. These are audited historical snapshots; the integration lead must refresh current refs separately.

- **Alpha:** `createWorkbench([adapter])` accepts explicitly installed developer code with `manifest`, `validate` and `execute`; `run` requires a source digest, produces native plan/history/evidence, and `inspectPack` checks the result. `examples/successor-workbench/extension.mjs` documents this seam. A new bounded local research adapter can use it without installing a scheduler or asserting operational adoption.
- **Fleet:** Local Skills admission reports exact supported tasks, prerequisites, source/tool/session binding and review arrangement. It creates no grant or budget reservation. Arbitrary code, live models, browser/desktop work, native Mac execution and independently controlled market review remain outside the inspected preview. A local research run is not an admitted Fleet job.
- **Jobs v0:** Native transformation intake is inert and supports zero AGIALPHA cap; positive proposals require a separate future authorized native charter. It neither executes nor settles. The 18-decimal AGIALPHA route remains separate.
- **Manager:** Preserved Alpha continuity and local integer-CSV recomputation can produce an unfunded USDC proposal. Imported evidence is historical and unauthenticated. It confers no cross-repository commissioning, worker reservation or settlement authority.

The preserved capability inventory explicitly says `host_code_fallback: false` and references original restriction comment `6386746278` under issue #4850. Do not execute an untrusted repository through the local host as a substitute for a held Harness/Fleet/native path. Author-written bounded numerical research is a local research execution and must be labeled accordingly. Source-profile adoption and the approved operator were NOT APPROVED / NOT RUN in the inspected integration record. Existing release/security/publication owners retain their gates.

## Recommended evidence additions for this study

Keep creator, eligible validation attester, root publisher and actual execution authorization as four separate fields. Retain each new executable's motivating job, failed candidates, source version, public dependencies, validation dossier, tested scope, status and cost records. A composed numerical capability needs combined validation, not only component proofs. Give B/C identical validation and lifecycle checks. Freeze held-out answers outside skill records/indexes. Report the existing fixture authority as such and keep live authentication NOT RUN.

No new material security defect was demonstrated during this read-only audit. The important limitation is semantic scope: prior metadata admissions, fixture identity and local Workbench integration cannot be promoted into a claim of live authenticated agents performing admitted network jobs. Source identities and the new task evidence must remain explicit.
