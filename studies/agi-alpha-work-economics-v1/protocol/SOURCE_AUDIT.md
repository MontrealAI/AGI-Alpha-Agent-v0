# Read-only runtime and foundation audit

Date: 25 October 2026. Source: MontrealAI/AGI-Alpha-Agent-v0 main `f836f06e8351e64db1da770e16e304b5feb01f28`.

## Execution seam ready for the economics study

The shared `alpha_repo/` directory is a selected source snapshot, not a complete repository clone or an installed release. Its 37 files have exact Git blob SHA-1 and SHA-256 verification in `source_manifest.json`. The runnable runtime and CSV files also match public release `v1.43.0`, source `5499495911bf8822ac0aa8c9007f00789c1132b5`. Only `alpha_factory_v1/__init__.py` and `pyproject.toml` differ from that release (current metadata); do not describe this directory as the released wheel or as a clean package installation.

Actual smoke execution completed: Python import of `alpha_factory_v1.core.runtime.successor.workbench` and `invoke({'operation':'example','family':'public-data'})`; Node `cli.mjs --help`; original CLI `--example --out runtime_audit/development_smoke_catalog`. The last command produced nine files from the shipped 120-by-360-row example, with 120 matched pairs and nine conflicting pairs; all four internal methods passed their local exact checks. This is development smoke evidence only. No customer task, human comparison or confirmation outcome is counted by this audit. No private journal keys or external credentials were created by these calls.

### Catalog reconciliation: strongest immediately usable employer job

`examples/successor-alpha/cli.mjs` uses the actual maintained Alpha engine, project history and artifact builder. Command:

```sh
node alpha_repo/examples/successor-alpha/cli.mjs --left left.csv --right right.csv --left-key sku --right-key id --out NEW_DIRECTORY
```

The nine outputs are `joined.csv`, `unmatched-left.csv`, `unmatched-right.csv`, `conflicts.csv`, `exact-result.json`, `comparison.json`, `report.html`, `project.json`, and `successor-tool.mjs`. Inputs are public, licensed nonpersonal, or synthetic records; each CSV is bounded to 200,000 bytes, 1,500 rows and 32 columns, with 10,000 matching-pair cap. Outputs preserve duplicate matching pairs and source information. Identifiers use exact string equality. The deliverable is an exception/reconciliation package, not a claim that ambiguous business conflicts have been resolved.

`project.buildCapability()` emits a standalone executable containing the current maintained engine. A subsequent invocation is:

```sh
node successor-tool.mjs fresh-left.csv fresh-right.csv sku id NEW_DIRECTORY
```

It emits six artifacts. It still runs the four existing join strategies and their checks. The builder reads the selected strategy but does not specialize the emitted program to it. Therefore an inherited executable can establish useful reuse and portability, but not a claim of newly invented or selected-only optimized code, faster algorithm construction, or autonomous learning. The current user-authorized study need not turn those four internal methods into its primary comparison; their role is internal work and validation.

`examples/ti-guide/guide.mjs` exposes `compute({leftCsv,rightCsv,leftKey,rightKey})`, full differences CSV, action-plan CSV, workspace creation and recomputation-based restore. It imports the original Alpha `engine.mjs` and `research.mjs`. It groups related exceptions while preserving all original occurrences; it refuses evidence truncation and unsafe sizes. `LIMITATIONS` explicitly records no automatic resolution, no measured time savings and no measured accuracy improvement. These are upstream boundaries, not findings of the new study.

### Other useful jobs supported by the shipped workbench

`workbench.invoke()` calls the bundled original `workbench_worker.mjs`. Default maintained families:

| Family | Actual supported work | Useful outputs | Boundary |
|---|---|---|---|
| public-data | Group two-column `group,amount` CSV and reconcile exact integer totals | HTML report, editable summary CSV, analysis JSON | 2,000 rows; integer amounts; descriptive arithmetic |
| documentation | Execute URI component encoding/decoding and UTF-8 byte count examples | Original/corrected Markdown and per-example checks | Three supported operations only; invalid URI cases retained |
| reliability | Repair a closed-interval `contains` function | Source, patch, runnable Node checks | Finite grammar, not arbitrary software defects |
| performance | Measure exact sorted integer deduplication | Timings, selected source, values | Local device/JIT timing; no general economic conclusion |
| numerical | Exact-rational polynomial quadrature | Calculation input and comparison JSON | Degree at most six; declared interval/step/tolerance |

Original workbench ESM `createWorkbench(adapters)` is an installed-software extension seam. An extension supplies a versioned manifest, validator and bounded execute function. Source adapters require explicit reviewed installation; importing mission JSON cannot install code. A new study extension must be labeled as newly authored, not as a shipped capability.

## Runtime controls and operational limits

`workbench.execute(home,spec,run_id,resume=False)` is the original native Journal-backed path. It validates before initialization, uses exact task binding, a durable state record, a three-attempt ceiling, 70-second lease, local role inventory, fixed source identity and `SuccessorStore` nomination. Worker checkpoints respect global operator pause and per-run state changes. The JS inner worker enforces 60 seconds; Python kills after a 65-second wall-clock limit. Interrupted pure work requires explicit resume with the same request; stopped/retired work is terminal. New export directories preserve earlier outputs. CLI review binds the current result digest and is explicitly local-operator review, not independent acceptance.

These are source-inspected behaviors, not operations-test results from this audit. The main investigator must separately execute any claimed STOP/recovery/budget/rollback tests. Normal native initialization creates local signing-role material: exclude private home directories from public evidence. Pure `invoke` avoids native Journal creation but does not exercise its persistence/recovery controls.

The released `successor-study` recurring source-note operation has actual documented concurrency **1**, a finite foreground run, no installed background service, no connected browser executor, no external network and zero USDC/$AGIALPHA allowances. Concurrency tests of the catalog CLI would establish local process throughput for that adapter, not a new production fleet scheduler. Closing a page stops browser-local computation; an independently running native process needs its own lifetime management. No daemon or continuously operating company was established here.

Computer Use is a separate explicit Docker browser adapter. It requires an existing reviewed immutable image and operator-selected model/provider configuration and exact preparation permit. It cannot fall back to unrestricted host execution. Its existence does not mean it ran in the economics demonstration. Full desktop/document/filesystem computer use and public-repository maintenance are marked unimplemented or unqualified in the current capability inventory.

## Four-repository snapshot

| Repository | Main source | Observed public release context | Role in this study |
|---|---|---|---|
| AGI-Alpha-Agent-v0 | `f836f06e8351e64db1da770e16e304b5feb01f28` | v1.43.0 published 25 Oct 01:19:36 UTC; v1.44 candidate remains separate | Actual local catalog/workbench source |
| AGIJobManager | `5d5670df9dbbc79da115e0a44b71989f34df58c1` | v1.20.2 published 24 Oct 22:39:29 UTC | Distinct USDC commissioning route; no transaction |
| AGIJobsv0 | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` | rc.21 reported in current coordination; release-list first page contains older drafts, so do not infer latest by list order | Separate $AGIALPHA work protocol; draft compiler can be used |
| AGI-Fleet-Linux | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | v0.1.0-local-skills-preview.5 published 16 Oct 10:31:59 UTC | No executor claimed admitted or running |

The original held Harness/Fleet operations, current strategy/release owners and PR #4899 remain untouched. This audit does not clear their holds. Source inspection, a local fixed function, native installed acceptance and production authority remain different statuses.

## Five Alpha contracts: source-level contribution only

Source files are retained under `runtime_audit/source/contracts/ascension/`. Their observed deployed-source record is `c0fc5217e364a39a4cd123d17a8317c06b80f820`; current-source and deployed-source identities must not be conflated.

| Contract | Inspected function | Potential contribution | Study status |
|---|---|---|---|
| AscensionAccess | Live ENS ownership and expiring attributable admission | Role/eligibility checks | Source inspected; no new chain read or write |
| NovaSeed | ERC-721 capsule hash, immutable FusionPlan and optional lineage | Commit a seed/plan identity | Source inspected; no sealing/minting |
| AscensionRiskOracle | Staked validators, owner/plan-bound expiring reviews and capacity | Scoped review evidence | Source inspected; no attestation/stake |
| AscensionJobMarket | Bounded auctions, collateral, artifact-bound review, payouts/refunds | Commissioned accepted work | Source inspected; no work posted or settled |
| AscensionMark | Reversible lot curve, plan-limited funding/routing, close/reclaim | Govern plan execution/funding | Source inspected; no funding/trade/route |

The Oct 18 deployment document reports historical EXACT_MATCH verification and scoped graph observations at block 26220072, with activation/public funding not approved. This audit neither repeats that observation nor upgrades it to current operational compatibility. The five-contract graph does not include the separate canonical $AGIALPHA token as a sixth new deployment.

Manager uses USDC. Alpha Ascension and Jobs v0 use $AGIALPHA but remain different protocols. Sharing a token does not transfer approvals, balances, identity or settlement rights. The workbench's seven typed lifecycle work packages are unfunded drafts. None is an on-chain transaction.

## Foundation mechanisms and the new paper

All named foundations were accessed as original LaTeX/Markdown or downloaded PDF text. The original PDFs' bytes and SHA-256 are in `paper_bytes.json`; named web references are in `foundation_references.bib`. The study should use mechanisms at their demonstrated implementation scope, not inherit their titles as empirical achievements.

| Foundation | Mechanism useful for this study | Concrete implementation/claim boundary |
|---|---|---|
| AGI ALPHA unified paper | Work → evidence → reusable capability → productive capacity; Evidence Docket and full burden | Deliver artifact, exact source/input/output identities and cost/intervention record; architecture is not a human benchmark |
| Transformational Intelligence | Separate intent charter, formulation and evaluator; preserve purpose while changing method | Freeze employer acceptance, allow efficient legitimate internal methods on each side; no requirement that every improvement be algorithmically novel |
| Out-Learn | Construct useful observation/acquisition; charge calibration and transfer | Identify schema, identifier semantics and ambiguity before work; retain schema knowledge only within scope |
| Out-Think | Executable purpose-specific representation; retire invalid representations | Group exceptions without losing pair/field provenance; new identifiers or semantics require renewed checks |
| Out-Design | Construct a useful replacement while maintaining required service; freed capacity needs useful location | Produce directly usable CSV/report/tool outputs and verify the complete brief; CPU saved is not automatically labor capacity |
| Out-Strategise | Decide what to observe/build, maintain uncertainties and invalidate stricter successor scope | Choose available exact tools, preserve ambiguous cases, use fallback/refusal rather than claim unresolved conflicts fixed |
| Out-Execute | Retain valid execution progress/interfaces; current acceptance after change and interruption | Fresh-input rerun, source binding, idempotency/recovery record; inherited artifact is not inherited acceptance |
| Out-Evolve | Build means of future discovery/production, distinguish family from distinct successor | Retained executable used on fresh inputs; adapted composition separately evaluated; reuse alone is not an increasing improvement rate |
| The Possibility Foundry | Explicit resource frontier, charge construction across all uses, preserve strong alternatives and stress losses | Capacity at accepted quality with total burden, disclose failed/excluded tasks and construction cost; prior synthetic gains are not human-work evidence |
| Mission-Sovereign Successor v5 | Scoped, expiring authority under fresh proof; complete architecture rather than model label | Local evidence cannot imply admission or production authorization; current study's human-relative advantage is narrower than original Mission Alpha |
| Neural-Symbolic SUCCESSOR Ω | Observe/hypothesize/synthesize/execute/test/falsify/revise; portable executable evidence with failure memory | A generated reusable module is concrete inheritance; its formation here uses maintained source composition, not an autonomously learned world model |
| Mission Gym v2.1 | Executable mission/constraints/termination/evidence; complete candidate includes humans and review | Job-level acceptance, matched briefs, actual human observations required; same-session checker is not external organizational independence |
| SUCCESSOR Ω × AGI Jobs v2 | Sealed bounded contracts, typed graph, evidence dependencies, separate acceptance/Chronicle/admission | Freeze task, input rights, tools, budget, artifact, acceptance and rollback; no wallet or automatic authority |

The Out-stage sequence can be recorded as real operations (schema inspection → preserved distinctions → artifact design → tool selection → execution → retained tool and later invocation). It should not be emitted as seven generic labels after an unrelated benchmark.

## Essential interpretation for the employer-centered paper

1. This study's central comparator is competent human work without AI. The older foundations often define Mission Alpha against both incumbent and best rentable AI; do not import that broader designation or reintroduce the removed same-AI-without-learning arm.
2. The available default routes are capable deterministic tool execution within AGI ALPHA. They deliver real files, but do not measure frontier-model inference, unsupervised open-ended planning or general computer use. Any AI orchestration during development is distinct from task-time calls and must be costed or marked unknown.
3. The catalog CLI's internal software checks do not replace an independent acceptance implementation. An independently authored checker in the same team is procedural separation, not an independent employer, blinded human assessor or external institution.
4. The retained tool proves that source and execution are reusable on new inputs if invoked and accepted. It does not by itself prove lower complete cost, freed employee time, cash savings, broader intelligence or self-acceleration.
5. No observed human task data, consent or paid recruitment authorization was found by this audit. Primary human comparison must be NOT RUN unless the main investigator obtains actual eligible observations.

