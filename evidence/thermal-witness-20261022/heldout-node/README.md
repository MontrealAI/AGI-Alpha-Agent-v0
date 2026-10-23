# Frozen thermal evaluation executed in native Node

**Twelve of twelve cases passed all six publicly frozen criteria using unchanged source `175d8a50473ea94f8c63d20959c22c95dfc6b886` in actual Node 22.17.1.** This bundle qualifies that numerical replay only. Current native package installation, Python workbench lifecycle/recovery, changed PR code, the held SUCCESSOR Ω Harness, Fleet independent review, contracts and settlement require their own evidence.

The cases and criteria were published in [the frozen protocol](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#issuecomment-6352588248) before the previously reported V8 evaluation. This is a later native replay of those same frozen cases; it is not a newly unseen holdout. The full original public comment is retained in `frozen-protocol-comment.json`, with its body hash checked by the runner. Prior V8 results remain available through [their original public report](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4871#issuecomment-6353311037); unavailable full V8 run JSON is not reconstructed here.

## Run and reproduce

Use Node **v22.17.1**, with no npm installation or external dependency. In this directory:

```sh
node runner.mjs replay-receipt.json
```

Use a new output filename: the runner opens its receipt with exclusive creation and will not overwrite an existing receipt. The three bundled ESM source files must retain their exact bytes; the runner verifies their Git blob identities before evaluating any case. The fixed public protocol body and source commit are verified too. The process needs permission to spawn a bounded local Node subprocess. Each of the twelve workers has a 15-second process timeout and a 2 MB output/input transport limit. No network, credential, contract, role, or payment provider is used.

The approved original execution was:

```sh
/workspace/scratch/5d02e86cc826/thermal-toolchain/node-v22.17.1-linux-x64/bin/node runner.mjs native-receipt-approved.json > native-run-approved.stdout.json 2> native-run-approved.stderr.log
```

The evaluator constructs each unchanged fixture, keeps its options, hidden parameters and numerical-reference audit in the evaluator, and sends only `fixture.input` as JSON on the worker's standard input. The child imports only the production adapter and executes `executeThermal` unchanged. Reference and fixture modules remain evaluator imports. This is process/data separation, not an OS filesystem sandbox or an independent validator approval.

## Retained attempts

Both attempts use the same runner and exact pinned source bytes. `ATTEMPTS.json` records commands, times, exits and raw receipt hashes.

- The ordinary sandbox attempt failed all twelve worker launches with `spawnSync ... EPERM`, before any adapter execution. `native-receipt.json` retains every attempted case, exception and incomplete criterion. This is an environment failure, not a failed scientific measurement.
- Approved local execution allowed the same bounded processes. `native-receipt-approved.json` retains all twelve full inputs, fixture audits, adapter outputs, 721 ordered checkpoint labels per case, integer acceptance comparisons and runtime metadata. It passed every frozen criterion. No case, tolerance or source was changed between attempts.

## Native result

Approved execution: `2026-10-22T23:46:40.075Z` to `2026-10-22T23:46:41.215Z`. Runtime: `v22.17.1`, V8 `12.4.254.21-node.27`, `linux/x64`. Node executable SHA-256: `e5207b0c9f178fe6b5caf8f5bab550b9f589a3f8e0e802165340e8bbf7f90927`.

Every case completed 720 of 720 intervals, 720 work units and 720,000 ms coverage. Every decision was `CONDITIONAL_BOUNDS_MET`, using the explicitly declared `CONSTANT_WITHIN_INTERVAL` property model. Exactly 720 `thermal-interval` checkpoints preceded one `thermal-evidence` checkpoint, with no other label or worker exception.

`L`, `E` and `U` below are exact integer **microjoules**, and `R` is the returned numerical reference in joules. `P` is the adapter's declared relative-error bound in ppm. Observed error is `100 * abs(E/1e6 - R) / R`; it measures agreement with the numerical model under the declared acquisition assumptions.

| Case | Regime | Initial history K | Volume bias | Differential bias K | R J | L µJ | E µJ | U µJ | P ppm | Observed error % | Result |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H01 | nominal | -9.5 | -0.005 | -0.005 | 5175.850703167601 | 5023163268 | 5119877806 | 5217315390 | 19398 | 1.08142410548 | PASS |
| H02 | nominal | -6.75 | -0.005 | 0.005 | 5175.850704822077 | 5082914666 | 5180064136 | 5278103626 | 19289 | 0.0814055779081 | PASS |
| H03 | nominal | -3.25 | 0.005 | -0.005 | 5175.850706927702 | 5073648564 | 5171334272 | 5269750283 | 19398 | 0.087259760442 | PASS |
| H04 | nominal | 0.75 | 0.005 | 0.005 | 5175.850709334173 | 5134000490 | 5232125496 | 5331149450 | 19288 | 1.08725675886 | PASS |
| H05 | flow-power-uncertainty | -8.25 | -0.005 | -0.005 | 5009.624447663096 | 4865447120 | 4956890995 | 5048999613 | 18932 | 1.05264283209 | PASS |
| H06 | flow-power-uncertainty | -5.5 | -0.005 | 0.005 | 5009.6244491715415 | 4920418423 | 5012262430 | 5104924799 | 18833 | 0.052658255229 | PASS |
| H07 | flow-power-uncertainty | -1.5 | 0.005 | -0.005 | 5009.624451365664 | 4914346116 | 5006708566 | 5099742434 | 18932 | 0.0582056677895 | PASS |
| H08 | flow-power-uncertainty | 2.5 | 0.005 | 0.005 | 5009.624453559817 | 4969869904 | 5062636505 | 5156229682 | 18833 | 1.05820410156 | PASS |
| H09 | nominal | 4.25 | 0 | 0 | 5175.850711439779 | 5078432589 | 5175851045 | 5274080311 | 19343 | 6.44454873224e-06 | PASS |
| H10 | nominal | 7.75 | 0.0015 | -0.0035 | 5175.850713545477 | 5064999846 | 5162411989 | 5260577185 | 19382 | 0.259642816017 | PASS |
| H11 | flow-power-uncertainty | 6 | 0 | 0 | 5009.624455479661 | 4917519336 | 5009623991 | 5102474142 | 18882 | 9.271746116e-06 | PASS |
| H12 | flow-power-uncertainty | 9.25 | -0.0025 | 0.001 | 5009.624457262442 | 4910737136 | 5002651420 | 5095324773 | 18872 | 0.139192814191 | PASS |

Maximum declared bound: **19,398 ppm** (1.9398%). Maximum observed numerical error: **1.08725675886%**, H04. All twelve returned references lie within the integer bounds, and both integer reference endpoints satisfy the declared error bound without added tolerance.

The exact acceptance arithmetic uses `RL=floor(R*1e6)` and `RU=ceil(R*1e6)`: `0 < L <= E <= U`, `L <= RL`, `RU <= U`, `L >= 1000000`, and for both endpoints `T`, `abs(E-T)*1000000 <= P*T`, with `0 <= P <= 50000`. The raw receipt retains both sides of every integer comparison. These checks bracket the returned numerical reference; they do not certify an exact ODE solution.

Every run retained `simulation:true`, `physicalValidity:NOT_ESTABLISHED`, `independentReview:false`, `acceptedCapability:false`, `authority:[]` and `settlement:NOT_CONNECTED`. The complete inherited failure record was unchanged in canonical JSON, including the original release, three heat values, residual `0.049477122810963045` and true-heat error `0.08696402400224054`. This new witness does not rewrite or retroactively qualify the earlier Foundry failure.

## Scope and limitations

These are twelve deliberately selected acquisition-bias/history combinations, including sign corners and interior values, in **two fixed actuator regimes of the same four-state ODE**. The model, 180-second reset, 720-second mission, RK4 step of 1/32 second, fixed material properties, calibration and temporal assumptions remain the public frozen setup. They are not physical trials, representative statistical sampling, unknown-plant evaluation or broad distributional-generalization evidence.

The reset suppresses most initial-history variation: reference spans within each regime are only about `1e-5 J`. The meaningful numerical challenge here is the selected acquisition bias and actuator-regime mismatch; changing the initial history does not create twelve distinct physical models. Declared calibration bounds, flow coverage, constant within-interval properties and temporal bounds remain modeled premises. Physical validity is unestablished.

Conditional arithmetic has created no independent acceptance, capability registration, live approval, eligibility, enterprise authority, financial transaction or legal status. The full Ascension lifecycle and four-repository integration are outside this narrow receipt.

## Source and integrity

All files below were copied from the exact historical commit; none were adapted to current source. `SOURCE_MANIFEST.json` records how they were acquired, including a failed Git promisor fetch before the exact adapter blob was retrieved through the read-only GitHub connector and checked by Git object identity.

| File | Git blob | SHA-256 | Bytes |
|---|---|---|---:|
| thermal-witness.mjs | 604bd36528e5c688d357ae91c42dd52c2987612c | 566d89907408d9f7fc3389e62da865b9dac2880bc7fd25c0c7e3bb26e2947df5 | 19357 |
| thermal-witness-reference.mjs | 36b7c5efa42250fb30d5c212d0a5ca0b4b07076f | 623b396ec4d4cf72329811d9eaee5092e79b3df41225322b0a39db454612a01a | 7208 |
| thermal-witness-fixtures.mjs | 00ff7fe2b1836de6801a076df7617b805ba0888d | 5644b9325eef1c54444357a3ddb22f55ad230dbb98180ff87fe851829ef12ad4 | 1167 |

Runner SHA-256: `d2e0ef8bba178ff288970c3db67663bd16bf1044bf7d2b71b7618af988bc4c38`. Frozen protocol body SHA-256: `7aa9e6ee7e16a2fa6b55c3152862041c2eb8ff2765fb69e5e7a0effb0ed7709e`. Approved raw receipt SHA-256: `66a29e45419fd3248af4c98b949e10771f88ccc8508e4644131a67a85df16f10`. Failed-attempt receipt SHA-256: `412558c166c99963b966390441e552c3cbc156fba9ead9da7ffcb3590eb621a1`.

`SHA256SUMS` inventories the complete bundle, excluding itself. Validate it with `sha256sum -c SHA256SUMS` where that utility is available. The receipt stores exact source IDs, timestamps, runtime identity, full cases and failures; the concise result table is derived from that receipt.
