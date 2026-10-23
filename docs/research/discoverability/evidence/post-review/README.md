# Post-review corrections

Run identity: `discoverability-20261022-v1`. Amendment identity:
`review-correction-20261023-5aef-v1`.

These corrections respond to review comments on PR #4872 at source
`5aef0c1a0bbbd254b228cc309922ef5934445e22`. They are review-assisted software
maintenance, not autonomous recursive self-improvement or a new load campaign.
The machine-readable record is `../post-review-amendment.json`.

## Compiler 1.0.1-experimental

The compiler now returns a qualified empty measurement program immediately after
validated framing when every declared world requires the same decision. Input
framing, cooperative cancellation and result serialization remain accounted for.
Grammar construction and response evaluation are unnecessary for this case.

For the retained digital problem with a single common goal and a 2,000-unit work
budget, the preserved compiler returns `BUDGET_EXHAUSTED`. The corrected compiler
returns `COMPILED`, with zero acquisition cost, no measurements and 248 metered
logical work units. Work units are not money, CPU instructions or energy.

The final checks on Node 24.19.0 pass 22 core tests (the original 21 plus one
regression), 13 adapter tests and 7 delivery tests. A separate comparison reads
the original 124 reference cases and four former held-out cases without changing
their reports. All 128 statuses and programs match the historical records. The
111 nontrivial results match the preserved compiler completely except for the
explicit compiler version. The 17 same-goal cases preserve their programs while
avoiding unnecessary construction. The unchanged independent implementation
accepts all 61 returned programs.

From the repository root:

```sh
node examples/successor-discoverability/test.mjs
node examples/successor-discoverability/workbench-adapter.test.mjs
node examples/successor-discoverability/execution.test.mjs
node docs/research/discoverability/evidence/post-review/verify-correction.mjs
```

The comparison writes JSON to stdout. Redirect a reproduction to a new file; do
not overwrite these retained logs. The former held-out inputs are now public,
so this comparison does not recreate withholding or external independence.

The exact prior compiler and original 21-test file are retained as
`../frozen-source/compiler.mjs.txt` and `../frozen-source/test.mjs.txt`. To reproduce
the original experiments, use these bytes under their original `.mjs` basenames
with the original source closure and helpers. Current application source is the
corrected descendant; historical measurements remain attributed to the frozen
compiler. The preliminary `core-*` log predates the explicit version bump; the
`core-final-*` log qualifies the final `1.0.1-experimental` source.

## Qualification runner for future executions

`examples/successor-discoverability/qualification-runner.py` supersedes the
executed historical custody wrapper for future use. The historical
`../local-evm/qualification-02/run.py` and its successful receipts remain unchanged.
The new runner propagates test and separate-fixture failure after retaining the
command, timestamps, streams, hashes and subprocess status. Timeout returns 124;
failed tests prevent the separate fixture from running. Nonempty output
directories are refused.

Seven deterministic OS-subprocess tests passed on Python 3.12.14:

```sh
python examples/successor-discoverability/qualification-runner.test.py
```

They check success, test failure, test timeout, fixture failure, fixture timeout,
preservation of an existing output directory and the public CLI's corresponding
refusal. These fixtures do not execute Solidity or an EVM. The retained real
qualification's 36 tests were not rerun for this amendment.

For a future real local qualification, first prepare the exact preserved Alpha
source and already installed dependencies, then choose a new output directory:

```sh
python examples/successor-discoverability/qualification-runner.py \
  --source /absolute/path/to/retained-alpha-source \
  --output /absolute/path/to/new-qualification-output
```

The runner verifies the historical source inventory, uses the unchanged four-file
`npm test -- ...` selection, and copies the unchanged separate snapshot script
into the new output. This is a local EVM path with simulated balances; it adds no
authorization for live operations or financing. Full installed-environment
qualification of this new runner's real CLI remains a future execution; the
present evidence qualifies its subprocess control and statically confirms the
unchanged real command.
