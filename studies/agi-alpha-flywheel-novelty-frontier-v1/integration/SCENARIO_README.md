# Native scenario analyzer: seven supplied rejections

## Result and interpretation

Actual local execution of the unchanged Ascension scenario analyzer selected **zero of seven candidates** after checking
all **128 subsets**. It produced eight exact excerpts from the supplied candidate evidence. The native `makeGenome`
function refused to create a venture genome because the selected set was empty.

The discovery team had already supplied each rejection after its prior-art review. This execution checks how the
existing scenario path handles those findings. It does not conduct autonomous opportunity discovery or a semantic
novelty review. The source-ranking mechanism uses keyword overlap and verifies that returned quotations occur in the
supplied text; it performs no external retrieval or model inference.

All seven candidates have `cost: 1`, `value: 0`, `risk: 0` and `effort: [1, 1, 1]`. The budget is 7 and the unit is
`supplied flagship eligibility units`. Value zero encodes the supplied flagship rejection; it is not an estimate of
customer benefit or future economic value. Cost is a unit counter. Risk is a neutral routing parameter, not a measured
hazard probability. Effort contains required placeholders; no work is scheduled when selection is empty.

Every candidate fits the budget. The empty set wins because every nonempty set has equal value and risk but greater
cost. This is the native lower-cost tie-break, not an independently discovered scientific rejection. All seven
coordinate-identical candidates also remain in the native nondominated `frontier` array. That membership does not
mean selection, approval or substantive novelty.

The exact native refusal is:

> Increase the budget or risk allowance to select a feasible project.

That generic suggestion does not diagnose this scenario: budget already permits all seven candidates. The runner
preserves the message and does not change budget, risk or supplied values. A separate research Nova-Seed may preserve
the negative evidence; it must not be presented as the venture genome that this native path declined to construct.
No MARK settlement, minting, listing, trade, fund transfer or permission expansion was run.

## Reproduction

From the study directory:

```sh
node integration/run_scenario.mjs
```

The runner uses only Node built-ins and two copied upstream modules. It verifies their hashes before import, checks
the input and original source-lock hashes, executes `analyseScenario`, asserts empty selection and no schedule,
calls `makeGenome`, records the expected refusal, and checks that the original lock remains unchanged.

The recorded execution passed all assertions. The runtime version and duration are in
`results/scenario-v1/run_manifest.json`. Re-execution updates the runtime manifest; the analysis and refusal artifacts
are deterministic for the locked input and source files.

## Files and provenance

- `scenario-upstream/docs/assets/ascension/engine.mjs`: unchanged upstream scenario/genome functions.
- `scenario-upstream/docs/assets/portal/mission-engine.mjs`: unchanged allocation and extractive-research functions.
- `scenario-source-lock.json`: separate upstream commit, byte sizes, Git blob IDs and SHA-256 manifest.
- `scenario-input.json`: the exact native scenario supplied to the analyzer.
- `scenario-input-provenance.json`: candidate-record hash, verdict mapping, parameter meanings and evidence scope.
- `run_scenario.mjs`: the local integration runner and its assertions.
- `results/scenario-v1/analysis.json`: complete native result, including supplied inputs, excerpts and the empty set.
- `results/scenario-v1/genome_refusal.json`: exact native exception and retained interpretation.
- `results/scenario-v1/run_manifest.json`: runtime, verified input/source hashes and output hashes.

The pinned upstream commit is `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. Each copied source was checked byte-for-byte
against `git show` at that commit before execution. The existing `integration/source-lock.json` was not changed; its
SHA-256 remains `aa67470a1ba0febcdaa6ef6b2c1a64437129961585442f3f8e62bbd9465987b6`.

| Unchanged source | SHA-256 |
|---|---|
| `docs/assets/ascension/engine.mjs` | `50b2a741485d92220cd5bfcf67221626dab22b62744e033f3a53259d6e14635a` |
| `docs/assets/portal/mission-engine.mjs` | `d0bf8c765f755c8cf872081bf72699a4fb62ef6ee3e71a10c80732cb8652408f` |

Hashes establish the recorded bytes and execution inputs. They do not establish truth, foresight, physical feasibility
or customer demand. The substantive prior-art review and its limits remain in the discovery record.
