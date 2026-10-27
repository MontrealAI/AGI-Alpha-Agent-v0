# Existing-component integration for the opportunity-construction study

This small offline harness binds the **actual supplied research opportunity** and its public provenance to existing
AGI ALPHA components. The discovered offering, experiments and economics are supplied by the study. Creating a
project, encrypting a capsule or compiling a plan does not discover an opportunity or establish customer acceptance.

The dependency closure is copied unchanged from repository commit
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. `source_manifest.json` pins every source and license file by
SHA-256 and original URL. The harness checks all pins before importing any component. No installed registry,
production asset, wallet, provider or native runtime is changed. The copied qualified-profile registry stays empty.

## Run on the selected opportunity

From the study directory, using the repository's Node 22.17.1 environment:

```sh
node integration/run_integration.mjs --input config/venture.json
```

The available research environment initially provides Node **24.22.1**. Syntax, imports and all pinned-source
hashes were checked there; the eventual execution receipt records the actual runtime. A pass on that version
does not establish compatibility with every supported platform or substitute for repository release gates.

Outputs go to `integration/artifacts/selected/`. A run refuses an existing destination so that earlier evidence
cannot be silently replaced. For a fresh replay:

```sh
node integration/run_integration.mjs --input config/venture.json --output integration/artifacts/replay-02
```

`config/venture.json` must be supplied by the study after selection. This integration does not author an
application or a candidate. Its required fields are:

| Field | Meaning |
|---|---|
| `schema` | `agialpha.opportunity-construction.venture.v1` |
| `title` | Actual selected-opportunity title, up to 160 UTF-8 bytes |
| `evidence_scope` | `offline-research` |
| `publication_safe` | Explicit `true` for this public research record |
| `protocol_amounts` | `unfunded-encoding-only` |
| `opportunity` | Complete actual opportunity object: preserve discovery source, limitation, construction, acceptance and falsifiers |
| `fusion_plan_jobs` | Actual work specifications using the existing five fields `goal`, `successMetric`, `bounty`, `duration`, `priceWeight` |
| `provenance_files` | Optional list of study-relative public record `path` and exact `sha256`; each referenced file is hash-checked |

Nova's existing strict parser accepts safe integer numbers and exact decimal strings. Express monetary or
other fractional amounts as strings; this harness does not silently round or change them. The compatible
capsule limit is 250 KB; reference larger public records by hash. File references remain inside this study.

FusionPlan requires 1–128 jobs, a positive duration at most 90 days, 0–10,000 price-weight basis points,
1–512 UTF-8 bytes each for goal and metric, and a bounty string of at least 100 in 18-decimal token base units.
These protocol amounts are **unfunded encoding fixtures**. They have no asserted conversion to study costs,
buyer prices, financing, profit or collected receipts. The compiler checks commitment structure, not whether
the scientific success criterion is sufficient.

An optional `mark_curve_fixture` must have `scope: "unfunded-integer-arithmetic-only"`,
`usd_equivalent: null`, and canonical nonnegative integer strings for `supply`, `count`, `base`, and `slope`.
It runs the existing MARK curve and independently checks the integer calculation. It never funds a campaign,
grants a role, calls a wallet, supplies a token price, or contributes to modeled service profit.

An optional `discovery_scenario` can run and replay the existing Discovery prioritization engine **only if
the study has independently supplied its exact schema and assumptions**. This harness does not manufacture
scores, sources, probabilities or an economic envelope merely to obtain a passing component result.

## What executes and what the evidence means

| Existing component | Real local execution | Evidence boundary |
|---|---|---|
| Insight Atlas | Serialize the exact opportunity; call `buildEvidence` on it and preserve the actual schema refusal | Its scheduling model cannot validate generic opportunity truth. No empty Chronicle or promotion count is used. |
| Discovery | Existing safe parse and canonical digest; optionally evaluate/replay a supplied priority scenario | Canonical bytes prove integrity, not truth. Priority scores are supplied assumptions, not forecast probabilities or value. |
| Nova-Seed Studio | `createProject(null, {title, opportunity})`, `validateProject`, `projectCycleState` | The actual opportunity survives unchanged. No deployment package, minted seed, current authority or settlement is claimed. |
| FusionPlan | `compilePlan` and `verifyPlan` on the actual work specifications; altered goal and total are refused | Correct Merkle commitments bind text and numeric terms; scientific acceptance remains separate. |
| Nova-Seed crypto | `sealSeed` / `openSeed` on the actual complete project, plan and public provenance; wrong key and altered ciphertext are refused | A compatible standalone genome binds this project and plan. It is public, unminted, unfunded research material. |
| MARK | Optional existing `curve` arithmetic, with no USD equivalent | No provider, wallet, transaction or funding interaction occurs. |

The capsule uses the explicitly public passphrase
`PUBLIC-RESEARCH-ONLY-NO-CONFIDENTIALITY-2026`. This makes the public research round trip independently
inspectable and provides **no confidentiality**. Production encryption would require a separate private
passphrase and a separately authorized workflow. Random IVs, salts, blinds and project/cycle UUIDs mean that
fresh executions have new encrypted bytes; the input, opportunity and plan commitment remain independently
comparable. The evidence receipt binds every actual artifact from each run.

The project state remains `runtime: requires-current-authorization`, `settlement: not-observed`, and
`fresh: false`. The compatible capsule is not misrepresented as an attached deployment package. Existing
business (`*.alpha.agi.eth`), Ascension agent (`*.alpha.agent.agi.eth`) and validator (`*.alpha.club.agi.eth`)
namespaces remain distinct. The broader `*.agent.agi.eth` interface is not substituted for these roles.
No live ENS authorization is tested.

## Native research interface inspection

At this source commit, there is no exported function named `nativeResearchMission`. The existing
`Insight.buildDossier()` constructs native mission objects of the form:

```json
{"goal":"...","work":{"kind":"research","sources":[{"id":"...","title":"...","text":"...","url":"..."}]}}
```

Its complete input still requires Atlas scheduling fixtures and an allocation envelope. We do not invent
those fields to package a new opportunity. The native `Research` model and work executor operate on a fixed,
attributable corpus; execution and semantic review have separate scope. The current integration therefore
binds supplied hosted blind-search records by exact hashes and leaves native research execution uninvoked.

Authoritative existing interfaces:

- [Insight engine](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/assets/insight/engine.mjs)
- [Discovery engine](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/assets/discovery/engine.mjs)
- [Nova project model](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/assets/nova-studio/cycle.mjs)
- [Nova engineering guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/agent/NOVA_SEED_STUDIO_ENGINEERING.md)
- [Native mission types](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/alpha_factory_v1/core/runtime/models.py)
- [MARK restrictions and role namespaces](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4/docs/agent/MARK_WALLET.md)

**REUSE** stable structure. **RECHECK** each new mission's meaning. **REGRANT** authority separately.
