# Read-only foundation / integration audit

Inspected 2026-10-26 for Discover the Work / Build the Advantage. No native held tests, credentials, live identity, transactions, service installation, security setting changes or public writes were performed by this audit.

## Exact inspected source

| Product | Main source inspected | Evidence |
|---|---|---|
| Alpha | `882456afe59d7bf9493ceaefc79f4f05c0cf7c9a` | Local shallow clone; AGENTS.md; FAST_RELEASE_POLICY; runtime and Workbench sources; compatibility/capabilities matrices |
| Manager | `5d5670df9dbbc79da115e0a44b71989f34df58c1` | Git tree; docs/ens-identity-and-namespaces.md; docs/successor/TRANSFORMATIONAL_WORK.md |
| Jobs | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` | Git tree; docs/ens-identity-policy.md; docs/successor/TRANSFORMATIONAL_WORK.md |
| Fleet | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | Complete Git tree; AGENTS.md; README; docs/local-skills/PROJECT_JOURNEY.md |
| Existing verified-capability study | `c9f2892c06e173cb0f9d5ae710cffc4a6f1fa723` / PR 4942 | Generic src/authority.mjs + src/commitments.mjs; heritage/foundations/audit.md; fixture/test paths |

Sources can be opened under `https://github.com/MontrealAI/REPOSITORY/blob/COMMIT/PATH`.

## Best existing route for an additive pure-code offering

`examples/successor-workbench/engine.mjs` exports `createWorkbench(adapters)`. The shipped `extension.mjs` demonstrates installed developer code, explicitly not imported mission/model code. Root may add an isolated research adapter without altering original runtime, dispatchers, contracts or native pins.

Required adapter shape:

```
{manifest:{id,version,en,fr,scope,artifact},validate(input),async execute(input,checkpoint)}
```

`createWorkbench([adapter])` returns `registry`, `validate`, `run`, `plan`, `inspectPack`. A spec has exact keys `schema,family,name,language,owner,rights,reviewMinutes,inputs`; schema is `successor-workbench/v1`; rights has `dataClass,source,license`, with class public/licensed-nonpersonal/synthetic. A run requires a real 64-hex `sourceHash` binding installed adapter and upstream source closure. Examples include upstream `workbench_sources.json` in this digest; record all actual transitive sources in a separate manifest.

The adapter result must contain exact fields `decision,summary,evidence,artifacts,limits`; 1–12 artifacts have name/type/content. Do not include arbitrary supplied executable code or mutate core policies. The existing engine compiles seven unfunded Jobs packages, retains original inputs, hashes artifacts and pack, and runs inspectPack. It limits canonical JSON to 2 MB, safe integer numeric values and bounded graph/object complexity. Use stringified decimals where needed, with explicit semantics. Execute checkpoints inside any significant iteration; wall limit is 60,000 ms at checkpoints.

Actual output semantics are `PUBLIC_LOCAL_EXECUTION`, `independentProof:false`, `admission:HOLD`, `authority:[]`, `settlement:NOT_CONNECTED`; history reimport is `UNAUTHENTICATED_HISTORICAL_IMPORT`, activeProof/activeAuthority empty. Stronger assertions require separate evidence. The engine itself measures elapsed milliseconds but leaves `computeCost` and `humanMinutes` null. Its provider/settlement spends are zero for this no-provider/no-settlement execution; this does not identify authoring/inference cost.

This pure installed extension is actual Workbench reuse. A JS Workbench wrapper around a separately executed Python result does not establish Python dispatch by the native Workbench. Label the external research operation and wrapper separately.

## Native Python runtime boundary

`alpha_factory_v1/core/runtime/successor/workbench.py` invokes only shipped `workbench_worker.mjs`; no imported executable selection. Native `freeze()` registers a MissionConstitution with authority_ceiling none, prohibited live-settlement/network/host-code/automatic-admission, and 3 attempts / 60,000 ms budget. Native invocation scrubs environment, requires Node 22+, caps input/output at 2 MB and handles cancellation. Its journal uses local rehearsal principals, never independent proof. Native worker main is generated from the existing fixed domain adapters; installing a new Python executor there is a separate reviewed implementation, not a study wrapper.

`model_program_operator.py` only exposes a closed typed `SelectionProgram` language. It does not execute arbitrary model-authored code.

`docs/agent/SUCCESSOR_SOURCE_OPERATION.md` describes `alpha-agent successor-study` through CampaignExperiment, DiscoveryLoop, fixed selectors and signed Journal. Shared-closed-artifacts reuses exact accepted selector source with fresh trials and gives conventional reuse identical access. Example is concurrency 1, absolute 60 seconds, at most 3 crash attempts. Existing broad `OperationSpec` permits declared horizons up to 3600, but do not extend a frozen/held experiment's accepted bound; the active numerical lane explicitly preserves complete native 60 seconds.

`docs/agent/FLYWHEEL_CAPABILITIES.json` states public-repository maintenance is unimplemented: coding sandbox is a solve-function benchmark, not a pinned repository repair adapter; host-code fallback false. Its public source-note runtime reports conventional reuse tie and full/human costs unknown. New study should not overstate supported native operations.

## Cross-product semantics and identity

`docs/agent/FLYWHEEL_COMPATIBILITY.json` contains no qualified_connected_profiles; four_product_installation_qualified false and live_financial_authority false. Historical individual release qualifications must not be promoted to a new four-product qualification.

Manager `scripts/integrations/transformational-work-request.mjs` retains a complete inert native campaign and a separate unfunded USDC6 proposal. Jobs `integrations/alpha-agent/transformational-work-request.mjs` preserves the same inert TI campaign under AGIALPHA18. Current free-native caps are both zero; positive proposals fail. Any conditional positive proposal interface is not permission or live execution. No conversion or price appreciation can create earnings.

Fleet `docs/local-skills/PROJECT_JOURNEY.md` supports an explicit public integer CSV project via `local-runtime/project/transfer.mjs`: createProjectRequest, inspectProjectRequest, inspectProjectReturn. It uses an existing bounded JS report worker and separately authorized internal Node check, not the separately gated Python alpha-run backend. It retains original project/request/return history, authority and STOP. Manager/Jobs attached histories remain unverified claims until their own native receivers inspect them. Production qualification false, funded work disabled. The source preview is not a new saved-package/public-install qualification.

Jobs role guidance retains ordinary agents under agent.agi.eth / alpha.agent.agi.eth and job validators under club.agi.eth / alpha.club.agi.eth, with existing owner governance exceptions. Manager similarly has preserved owner-managed Merkle/additional lists. Do not change these rules when adding graph validation. The new graph-only policy can demand eligible direct *.agent.agi.eth attestations without changing Jobs validation.

## Reusable graph/authentication primitives

At verified-capability PR 4942 source c9f2892…, reuse exact files with attribution:

- `studies/agi-alpha-verified-capability-v1/src/authority.mjs`
- `studies/agi-alpha-verified-capability-v1/src/commitments.mjs`
- `studies/agi-alpha-verified-capability-v1/fixtures/authority.json`
- `studies/agi-alpha-verified-capability-v1/tests/authority.test.mjs`
- `studies/agi-alpha-verified-capability-v1/tests/commitments.test.mjs`
- `studies/agi-alpha-verified-capability-v1/heritage/foundations/audit.md`

Authority exports include createFixtureResolver, createFixtureAttestation, authenticateAttestation, createFixtureRoot, authorizeRoot, skillBinding and fixtureNode. Every successful report remains FIXTURE_ONLY, liveIdentityEnforcement NOT_RUN and cryptographicAuthentication false. Names are conservative normalized ASCII direct labels under agent.agi.eth; nested labels and club identities fail. Attestation action ISSUE_SKILL_ATTESTATION and root action COMMIT_GRAPH_ROOT have separate grants. Root authority does not confer attestation authority or execution.

Skill binding covers id/version/implementationDigest/dependencyDigests/scopeDigest/environmentDigest/policyDigest/evidenceDigest/rightsDigest/expiresAt. Context additionally binds graph, chain, registry and current snapshot; validates scope, evidence availability, expiry, revocation, supersession and nonce reuse policy. Current reuse after changed owner/epoch or unsupported registry schema fails. These are modeled authority checks, not live ownership proof.

Commitments exports include canonicalize, digest, buildMerkle, inclusionProof, verifyProof, buildForest, buildGraphEpoch, graphEpochRoot, verifyEpochInclusion, validateRootHistory. Typed Merkle commitments use explicit schema/hash/canonicalization/tree policies, typed roots and previous-root/epoch binding. Imported roots without authorizer report ROOT_AUTHORIZATION_NOT_CHECKED. Validate compositions separately and provide registry/graph exactly the same dependency/evidence records.

Foundations audit verifies original Merkle v114 PDF SHA256 `3276b66b3aa84d1fadc51d2a398579a8b3108294fafea1a5e239e70dd0fed7de` and PROOF LOOPS v2 PDF SHA256 `2c41599a893c4c5ac0eacdf9b4416f4420b3d47ee73c04ed868049b29a6055db`, from goalos-agialpha-sovereign-machine-economy commit `1e9a5675b1662e98074fb1c71cf2c5b94c7d259f`. It explicitly finds no separately tracked deployed V107 graph registry implementation. Historical other GoalOS contracts remain distinct. Never turn this audit into an assertion of mainnet enforcement.

## Active work to preserve

Capability Advantage owner announced isolated `studies/agi-alpha-capability-advantage-v1/`, then froze at issue comment 6426738789: 12 connected forward/inverse/design chains, 36 jobs / 144 A/B/C/D evaluations, 100/625/1600/2500 node strata. Original design's reverse transfer failed; stronger recipient contributed low-rank design@2 selected during development. Fresh production not to duplicate. Freeze SHA256 4875524173fc08162115526ea7ee0f96889126b66bdc0d60f2fa11ce08a55d01.

Where Autonomy Earns Its Advantage had no matching checkpoint in issue comments 451–462 as inspected. Root must coordinate its boundary rather than assume ownership of that work.

Verified Capability completed 72 metadata production packets and 1152 paired modeled worlds with zero qualifying second investments; original primary negative result preserved at #4942. Its frozen-source lint gate remains blocking; generic JS reuse need not import failed Python source or duplicate that metadata campaign. Second Investment #4940, Productive Transfer #4939 and previous studies likewise remain separate.

## Publication gates

Follow AGENTS.md and FAST_RELEASE_POLICY. Local hook absence does not block a draft; disclose failures/unrun checks. PR Lint (Ruff) and Smoke are blocking, while named formatting hooks are advisory. Type checks, security, integrity, behavior, exact-source and release checks remain required. Do not freeze newly written unlinted code and then seek an exclusion; format/type/lint before scientific freeze and preserve any later successor separately.

Finite held-source guard protects exact f9d2e3ff… bytes of tests/test_successor_capability_delivery.py, tests/browser/fleet_receipt_native.mjs, fleet_git_metadata.mjs, fleet_module_boundary.mjs, test_discovery_lab_continuation.py. It is inert byte verification only. Four held outcomes remain unqualified; no native/browser/import execution is authorized by inspecting these source identities.

Recommended new path: `studies/agi-alpha-discover-work-v1/` or equivalent unique additive namespace, after posting scope in #4850. Preserve every pre-existing file, immutable source/data freeze, source provenance and failed results. Use normal review/qualified merge/publication route. A draft contribution is not a published release or installed service.
