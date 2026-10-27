# Offline AGI ALPHA study integration

This study-scoped adapter executes unchanged existing AGI ALPHA components from
`MontrealAI/AGI-Alpha-Agent-v0` commit
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`.
It creates a public research opportunity record, a real encrypted Nova-Seed genome,
an offline native FusionPlan, and an actual native A/B/C ledger sample. It exercises
the existing refusals for unsupported production scope, unreviewed rights, and
missing current ENS authority. It does not implement another registry or publisher.

## Execute

The included `upstream/` directory contains 40 unchanged source/license files,
449,967 bytes. `source-lock.json` binds every file's SHA-256, Git blob ID and size to
the original commit. No full repository or network access is needed at execution.

The observed environment is Python 3.12.14 and Node 24.22.1 with package versions in
the run receipt. The repository's production Node pin is 22.17.1; this scoped
research execution does not claim the production release qualification. Install
the direct dependencies from `requirements.txt` in an isolated environment when
they are missing. `requirements-resolved.txt` records the installed transitive
dependency closure. No new model or inference service is required.

```bash
python run_adapter.py --input example-opportunity.json --output results/my-new-run
```

The output path must be new. Existing outcomes are never overwritten. The wrapper
can instead point to an exact checkout with `--repo /path/to/repository`; it then
checks the commit and all consumed files before importing them. Do not point it at
a different current main and relabel that source as the old experiment.

Replace the example with the selected study's actual opportunity, sources,
transformation witness, uncertainty, milestones and costs. The example is explicitly
unselected and cannot establish discovery, usefulness, novelty or commercial value.
The input is limited to public research content; customer secrets are refused.

### Required input

- `study_id`: an ordinary bounded identifier.
- `opportunity`: title, beneficiary, valuable outcome, source records, uncertainty,
  transformation witness and next experiment. Additional public fields are preserved.
- `milestones`: objects with `id`, `goal`, `acceptance`, `dependencies`, `budget_usd`
  and `permissions`. `duration_seconds` and `price_weight` can be specified.
- `cost_sample`: each activity has unique `activity_id`, bucket A/B/C, native cost
  category, `estimated_micro_usd` integer or null, and an explanation. Include all
  three buckets. Values are assumed and unpaid; null remains unknown.
- `rights`: `public_research_only: true`, `contains_customer_secrets: false`, and
  the actual research and production rights qualifications.

## Evidence produced

| File | What actually happened |
|---|---|
| `novaseed-payload.json`, `novaseed-sealed.json`, `novaseed-recovered.json` | Existing `sealSeed` / `openSeed` used native AES-256-GCM, and recovered exactly the canonical original payload. |
| `novaseed-report.json` | Matching payload digests; wrong-passphrase and modified-header refusals. The fixed passphrase is public, so this fixture claims no confidentiality. |
| `fusion-plan.json`, `fusion-plan-verification.json` | Existing Python `compile_plan` / `verify_plan` compiled and rebuilt indexed Keccak Merkle commitments. A changed metric was refused. |
| `cost-ledger.json` | Actual Journal, TrustRegistry and CostLedger accepted signed local fixture charge records. A/B/C cannot reuse an activity ID. Unknown/unsealed costs prevent a complete-profit claim. |
| `admission.json` | Actual CapsuleManifest validation rejects the new instrument's unsupported scope; a separate control rejects unreviewed rights. Actual ResourceAccess checks a locally signed challenge, then actual ENSAuthority reaches a deliberately unavailable local RPC adapter and refuses authority. No RPC request leaves the process. |
| `mark-review-packet.json` | The plan, genome and actual MARK contract source identities are inspectable. MARK execution is explicitly NOT_EXECUTED. |
| `run-report.json`, `artifact-manifest.json` | Actual checks, exact imported modules, runtime versions and final output identities. |

The native FusionPlan leaf commits only index, goal, metric, token bounty,
duration and price weight. Dependencies, USD budgets, broader permissions and
falsifiers remain in the full seed's `experiment_milestones` and opportunity
payload; they must not be represented as automatically enforced on-chain rules.
The minimum parser-valid `100` base-unit bounties are test fixtures and have no
relationship to USD prices or customer funds. No transaction is constructed or
submitted, no NFT is minted, no lot is issued or traded, and no validator votes.

## Results of the included sample

`results/example-v1/` records 13 passed directed checks and no failures. The actual
native ledger reports A USD1.20, B USD0.40 and C unknown under the sample's explicit
assumptions, zero collections, incomplete costs and null complete profit.
`production_admission` is DENIED. This is the desired admission outcome for an
unqualified new instrument, not a failure to deliver the research artifact.

The accounting signer and EOA key are explicitly public fixture identities. The
native Journal creates a fresh temporary local signing key and API token only in a
temporary directory; that directory is deleted at completion and neither secret is
copied into the result. Public signatures and event hashes do not establish external
independence, actual payments or ENS ownership.

Cryptographic salt, IV, blinding and the ephemeral journal identity vary per run.
Reproduction means exact source identity and the same checked semantic outcomes,
not byte-identical ciphertext or event hashes. The FusionPlan root is deterministic
for identical specifications. The adapter preserves all supplied scientific and
economic inputs but does not judge their truth.

## Original interfaces and scope

- `docs/assets/ascension/crypto.mjs`: Nova-Seed sealing/recovery, no imports.
- `alpha_factory_v1/core/runtime/ascension.py`: native offline FusionPlans.
- `alpha_factory_v1/core/runtime/store.py`: existing atomic Journal.
- `alpha_factory_v1/core/runtime/successor/trust.py`: configured local-role trust.
- `alpha_factory_v1/core/runtime/successor/flywheel_costs.py`: existing A/B/C ledger.
- `alpha_factory_v1/core/runtime/successor/flywheel_capsules.py`: unchanged protected
  scope `bounded-public-source-selection/v1` and rights validator.
- `alpha_factory_v1/core/runtime/successor/flywheel_access.py`: current authority
  required independently of a valid wallet signature.
- `contracts/ascension/NovaSeed.sol` and `AscensionMark.sol`: unchanged source
  identities for later qualified inspection, not executed by this adapter.

Other vendored modules are the actual imported package closure, retained unchanged
to avoid rewriting imports or creating a substitute implementation. They do not run
scientific searches, inference, self-editing, market actions or production jobs in
this adapter. The Apache-2.0 license is retained in `upstream/LICENSE`.

No upstream file was modified. Public publication, production admission, current
authority and commercial validation remain separate from this local evidence.
