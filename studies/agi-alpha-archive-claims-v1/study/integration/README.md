# Native research bridge

This thin adapter executes unchanged AGI ALPHA code pinned to main commit
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. The retained 44-file closure is
475,183 bytes, includes original notices and Apache-2.0 license, and is verified
before imports. It is a research dependency closure, not a complete production
runtime distribution. Solidity files are included for inspection, not execution.

## Run

From the study directory, using Python 3.11 through 3.13:

```sh
python -m pip install -r integration/requirements-native.txt
python integration/native_bridge.py --input integration/example-input.json --output integration/fixture-run
```

The requirements record observed versions of external packages needed by this
bounded path. They are not a new full-repository dependency lock or clean-install
qualification. Optional upstream agent SDK imports retain their existing fallback;
no model API is called. The observed environment uses user-site packages, so
Python's `-I` isolation flag omits a required installed dependency there; that
initial failed attempt is retained. Execution from an unrelated working directory
passes, with every loaded native module bound to the verified retained closure.
Use a fresh output path for every run: existing output is
preserved and never overwritten.

For the actual study, replace the example input with its candidate/source/witness
metadata. The required JSON shape is demonstrated by `example-input.json`. The
example is solely an interface fixture, not a discovered commercial opportunity.
Fields retain their full content in `input.json` and the research sidecar. Native
Insight text bounds apply; excessively long metadata must be explicitly revised,
never silently truncated. Milestones require declared dependencies, budgets,
permissions, acceptance criteria and falsifiers.

An optional `--repo /path/to/AGI-Alpha-Agent-v0` uses another source checkout only
if every retained file matches the pinned manifest. The default vendored source
closure makes the bounded bridge independent of an external repository checkout.

## Executed path and scope

1. Verify exact source SHA256 values in `provenance/native_sources.json`.
2. Call native Insight `evaluate`, `verify` and `artifacts`. A single previously
   selected candidate has equal neutral supplied scores. This exercises provenance;
   it is neither an additional discovery experiment nor measured priority accuracy.
3. Compile and verify an actual native FusionPlan, including the native opportunity
   verification job and explicit research milestones. Token base units are inert
   compiler inputs, not USD, customer revenue, funding or an on-chain instruction.
4. Bind the native draft, source dossier, full transformation witness, rights,
   uncertainty, milestones and plan root in a richer research Nova-Seed sidecar.
   Original native outputs remain byte-for-byte outputs of unchanged native code.
5. Demonstrate refusal of a tampered plan and tampered Insight score.
6. Demonstrate the unchanged production capsule's unsupported scientific-scope
   refusal. The wallet/agent strings in that schema probe are explicit fixtures.
7. Exercise the existing Journal/TrustRegistry/CostLedger with one unavailable-cost
   fixture. It returns unknown profit/funds and refuses a completeness seal. Fresh
   private keys and the temporary journal are removed after the check; no actual
   bill, paid work, ENS authorization, receipt or customer acceptance is invented.

The normalized observed controls and artifact hashes reproduce deterministically.
The environment record varies with Python/package versions. Journal signatures
use fresh random fixture keys internally; private keys are not persisted or shared.
No minting, listing, funds movement, settlement, validator-role change or MARK
activation occurs. Existing production scope and publication authority are intact.

## Evidence outputs

`insight/` contains actual native output bytes. `fusion-plan.json` is the actual
compiler result. `research-sidecar.json` and `research-nova-seed.json` are explicitly
research schema objects. `native-controls.json` records executed controls and
unknown-cost boundaries. `MANIFEST.json` binds every output file except itself.
These controls establish integration behavior, not scientific truth, commercial
profit, external certification, prospective foresight or network superiority.
