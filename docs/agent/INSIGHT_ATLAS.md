[Project notice](../DISCLAIMER_SNIPPET.md)

# Insight Atlas field guide

[Open Insight Atlas](../insight/index.html) · [Ascension Lab](../ascension/index.html) · [Operate your own agent](OPERATIONS.md)

Insight Atlas connects the Living Treasure Map, Second-Order Agency and Alpha Ontology visions in one
working browser experience. No account, wallet, API key or model download is needed. The original
flywheels, white paper, workspace and all 26 catalog entries remain available.

## A useful first expedition

1. Choose **Energy × compute**, **Science × discovery** or **Enterprise × machine labor**.
2. Select a frontier on the map. Inspect its hypothesis and exact allocation. The **$15 quadrillion**
   starting envelope is an editable scenario assumption, not measured wealth, a valuation or a forecast.
3. Open **Second-order agency**. Compare the baseline with your agent firm. Change agents, validators,
   independent groups, quorum, budget, time horizon or operator review capacity. Run the comparison.
4. Explore **18 architectures**. Selection uses training results only; the selected design is then
   evaluated on a separate holdout fixture. Apply the design you want to inspect.
5. **Build & replay evidence**. Read failed gates and task-level timings. A one-vote quorum with a faulty
   validator group exposes unsafe acceptances. Capacity and budget shortages remain visible.
6. If every model gate passes, write what you checked and what remains uncertain. Record the modeled
   capability in the Chronicle. Reuse a reviewed design in another comparison while retaining your current
   budget, horizon, operator capacity and fault model; fresh evidence is always required. This does not
   validate the economic hypotheses.
7. Open **Alpha under trial**. Search claims, inspect references and acceptance criteria, add a falsifiable
   hypothesis, and export a validation brief or native research mission.
8. **Save expedition & recovery file** before closing the tab. This retains inputs, architecture, reviews,
   evidence and revocations. Download editable inputs to replace sources, weights or task fixtures.

The three-minute field guide is available beside the expedition selector. All sector controls are
buttons with keyboard focus and accessible names. Exact data is available in tables alongside the
visuals. Layouts are exercised at 320, 390, 768 and 1440 pixels; reduced-motion preferences are respected.

## What the implementation actually does

| Original concept | Working implementation | Boundary |
|---|---|---|
| Living treasure map | Twelve selectable sectors, editable envelope, exact dollar ledger, claim inspector | Allocations are assumptions; verified economic value is explicitly zero |
| Second-order agency | Resource-constrained scheduling; independent reviewer groups; operator capacity; baseline/candidate comparisons | Discrete-event planning model, not deployed autonomous firms |
| Alpha frontier | Eighteen architectures, training-only selection, nondominated cost/output frontier, held-out evaluation | Both fixture sets are synthetic and public; repeated tuning can overfit |
| Alpha ontology | Typed sector/claim/source/proof-debt graph, search, custom hypotheses, portable dossier | Source references are context, not independent verification |
| Proof debt → work | Concrete validation briefs and native `research` missions | Unassigned and unfunded; no external job posting, fabricated IPFS receipt or wallet operation |
| Only validated capability compounds | Exact-input evidence replay, failed gates, explicit review, hash-linked Chronicle, revocation | Only local modeled capability; no external certification or identity proof |
| Artifact workbench | Inputs, per-claim briefs, native missions, dossiers, evidence and recoverable expedition downloads | Plain JSON; keep sensitive source text private |

The planner does not use an LLM. Its decisions are computed from explicit inputs. The existing
[browser workspace](PAGES_GUIDE.md) offers real local ONNX text completion, and the
[native operator](OPERATIONS.md) supports optional local inference and signed mission records.
The [Ascension Lab](WHITEPAPER_IMPLEMENTATION.md) retains encrypted Nova-Seeds, modeled $AGIALPHA
funding/settlement, governance and policy search. This remains the **$AGIALPHA agent project**, distinct
from AGI Jobs. No public mainnet action is added by Atlas.

## Methods and assumptions

### Exact envelope accounting

The envelope is an unsigned whole-dollar **string**, up to 21 digits. Sector weights are integer basis
points and must total **10,000**. Each sector receives the floor of its exact rational allocation; the
remaining dollars go to the largest remainders, with sector order breaking ties. Calculations use
`BigInt`, including above JavaScript's safe-number range. Allocations always sum to the input envelope.

The form accepts up to three decimal places in quadrillions. Imported amounts with finer precision
remain exact in the ledger; the form shows a custom-amount placeholder until the operator explicitly
enters a replacement. Downloaded inputs can express any allowed whole-dollar amount and sector weights.

### The agent-firm model

Each scenario has 28 training and 24 holdout tasks with disjoint IDs, known validity labels, arrivals,
execution times, review times and deadlines. These are deterministic authored fixtures, not operational
measurements. Imported splits accept 4–40 tasks each and must include positive and negative cases.

Execution schedules tasks by arrival, then ID, on the earliest available worker. Reviews are scheduled
by execution completion, then ID, on the earliest available validators in distinct groups. A quorum
requires unanimous votes. Honest groups follow the fixture truth label; group zero accepts all work
when the single-fault stress test is enabled. Operator decisions are ordered by review completion,
take two minutes each and cannot exceed the chosen review-slot capacity. These are modeled failure
domains, not proof that real organizations are independent.

The budget reserves eight credits per execution agent and six per validator, then, for each admitted
task, `2 × execution minutes + 3 × review minutes × quorum + 4`. The four operator credits are reserved
even for a subsequently rejected task. Reservations include planned work beyond the horizon. This is
conservative planning accounting, not measured spend, dollars or token prices. Rejected work does not
release its reservation. Resource use, votes, blocked tasks and final times are retained in the ledger.

**Useful output** means a valid task accepted after quorum and operator review, on or before both its
deadline and the horizon. Invalid accepted tasks are counted separately. The baseline has two execution
agents, two validators in two groups and quorum two; budget, horizon, operator capacity and fault model
match the candidate. Search considers six worker counts and three validator counts, always with distinct
groups and quorum two. It orders candidates by fewer unsafe acceptances, more useful training outputs,
lower reserved cost, then lower median decision latency. Holdout outcomes do not choose the winner.

### Replay and the Chronicle

Evidence contains the complete scenario, configuration, comparison, gate results, input hash, engine
version and bundle digest. Verification recomputes the report from inputs and compares the entire
canonical result. Editing results and recomputing a hash does not make a forged report pass replay.
Imported evidence must also match the current workspace inputs. Editing controls immediately disables
promotion until the inputs are applied and new evidence is built.

Promotion requires reviewer independence, conserved budget, rejection of negative controls in both
splits, no unsafe acceptance, nonregressing useful holdout output, exact replay and a 12–500 character
operator note. Every event links to its predecessor's SHA-256 hash. Duplicate promotion fails.
Revocation preserves the original evidence and review. Recovery verifies the complete event chain and
recomputes every promoted bundle, including revoked ones, before replacing the workspace.

The portable format is bounded to 250 KB and 20 events; large inputs can reach the byte limit sooner.
If an additional event exceeds a bound, it is rejected and the current workspace stays intact. Save the
current expedition, then start a separate expedition for more experiments. A local hash chain cannot
prevent someone rewriting an entire file and all hashes. Retain a trusted copy/digest separately when
history provenance matters. Native signed journals provide a different identity boundary.

## Recovery and native handoff

- **Browser restart:** open Atlas, choose **Restore expedition**, select the recovery JSON and wait for
  replay verification. Check the active-capability count, scenario and architecture. No passphrase is used
  for this plain-JSON export; Ascension's encrypted Nova-Seed format remains separate.
- **Suspected corruption:** do not edit the evidence to make it pass. Retain the failed file for analysis
  and restore a known-good download. Failed import does not change the current workspace.
- **Rollback:** use **Revoke capability** to stop treating a modeled result as active. Its original event,
  note and evidence remain available. Restoring an older saved expedition deliberately restores that older
  state; compare its externally retained digest/head if rollback detection is required.
- **Offline:** load the site once and allow the gallery worker to finish caching. Atlas can then reload,
  restore, compute, replay and export without a network. A first-ever visit requires connectivity; a browser
  that blocks service workers reports that offline caching is unavailable.
- **Native research:** export a native mission from a claim dossier. Install the matching release following
  [OPERATIONS.md](OPERATIONS.md), inspect the source excerpts, and use the operator's documented mission
  submission flow. The JSON conforms to the same bounded `Mission` schema; a research result summarizes
  the supplied excerpts and does not create new external evidence by itself.

Inputs and history are held in memory. There is no third-party telemetry, automatic source fetching,
wallet connection or browser credential storage. Sources are validated HTTP(S) links and opened only by
the operator; their presence in a dossier does not guarantee content accuracy.

## Original source provenance

The three original HTML experiences were read in full. Their heuristic scores and declared pass flags
informed the interaction design but are not used as proof by this implementation. Original sites remain
linked from the Atlas; their source files and the original repository material are not removed.

| Reference in `MontrealAI/MontrealAI.github.io` | Last source commit inspected | SHA-256 of inspected HTML |
|---|---|---|
| [v67 Living Treasure Map](https://montrealai.github.io/goalos-v67-alpha-agi-insight-living-treasure-map-masterclass-interface.html) | `2bd71648d0bb3cc752d7b36a899dece8ce6d243e` | `74f6e00b8c15dbfb85e7a7c6aa62a84035d4ee7dd1f4c0b6c7be7f476691db54` |
| [v65 Second-Order Agency](https://montrealai.github.io/goalos-v65-second-order-agency-economic-reality-interactive-masterclass-interface.html) | `c69478840c9f902659a29841040335eb552986b6` | `44ee032844c70ffa7a182f4b9bc0e48fe2ff1e800a4e52f6cfdc9e1121f10a1d` |
| [v62 Ontology HyperTerminal](https://montrealai.github.io/goalos-v62-agi-native-bloomberg-terminal-asi-sovereign-ontology-nexus-interface.html) | `5e6aa0d2b2c2af19915ec3159f4f80430522590f` | `f5f5c85bdbeefcc7a3be25afcbf5e4d4a4843b49afe250f58ed82d010fde9dd8` |

The corresponding public posts are [Living Treasure Map](https://x.com/Montreal_AI/status/2074507052538356209),
[earlier Insight announcement](https://x.com/agialphaagent/status/1935730247711756371),
[Second-Order Agency](https://x.com/Montreal_AI/status/2074494836627902894) and
[Ontology HyperTerminal](https://x.com/Montreal_AI/status/2074345851581804741).
The interface also takes visual inspiration from [agialpha.com](https://agialpha.com/): spacious
composition, restrained monochrome typography and sculptural metallic forms. Atlas adds its own
ivory/obsidian system, interactive constellation, warm metallic accents and accessible data views.

## Validation and release evidence

```bash
node --test tests/browser/insight_engine.test.mjs
npm ci --prefix tests/browser --ignore-scripts
python -m scripts.validate_insight_atlas --site site --output evidence/insight-atlas \
  --axe-script tests/browser/node_modules/axe-core/axe.min.js
```

The independent engine tests cover exact conservation, invalid inputs, resource exclusivity, vote-group
separation, holdout isolation, the Pareto frontier, forged/stale evidence, duplicate promotion, revocation,
recovery and graph integrity. Real Chromium acceptance exercises all three scenarios, all 18 native
mission exports, execution and signed-result verification for one native research mission per expedition,
reviewed-design reuse without stale approval, negative proof cases, safe text rendering, exact envelope changes, search, custom claims,
four viewport sizes, canonical/mirrored paths and offline reload/recovery/replay. It retains actual
downloads, screenshots and `insight-atlas.json` with individual check names and scenario digests.

Pinned axe-core 4.10.3 additionally runs seven automated WCAG A/AA scans across the homepage and Atlas
views, with no reported violations required for publication. Incomplete checks are preserved in
`accessibility.json` for human review; this is not comprehensive accessibility certification. Keyboard
selection must retain focus when the map or claim list updates.

Both minimal and full gallery builds run these checks. Publication additionally requires the same Atlas
journey on the canonical public HTTPS site and appends the evidence to the release validation archive and
manifest. Passing Chromium does not constitute comprehensive accessibility certification or testing every
browser engine. Read [release readiness](RELEASE_READINESS.md) for the full project's supported scope.
