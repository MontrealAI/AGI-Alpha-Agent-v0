# SUCCESSOR Ω workbench

An additive portable workbench with five distinct domain adapters and optional native Computer Use.
The existing combined metrics workshop and every earlier lab remain available.

Start with [the user/operator guide](../../docs/agent/SUCCESSOR_WORK.md),
[the Computer Use guide](../../docs/agent/SUCCESSOR_COMPUTER_USE.md), or the
[working public page](https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/work/).
The new page is available publicly only after an accepted Pages deployment.

`engine.mjs` is the shared source; `scripts/generate_successor_workbench.py` bundles it for both
the standalone HTML and installed native worker. `missions/` contains five editable input packages.
`extension.mjs` demonstrates a sixth adapter registered through `createWorkbench`, without editing core.

Run all domain/conformance tests with `node --test examples/successor-workbench/test.mjs`.
Run the extension with `node examples/successor-workbench/extension.mjs`.
Each exported pack retains limits, failures, hashes and an unfunded seven-package Jobs compilation.
Local execution is not independent proof, institutional admission or live market operation.

Supported development runtime: Node 22.17.1 or later; native CLI additionally uses the existing
Python 3.11–3.13 runtime. Source code is Apache-2.0; imported AGI Jobs code retains its MIT license
and pinned provenance in `../build-successor/vendor/agijobs`.
