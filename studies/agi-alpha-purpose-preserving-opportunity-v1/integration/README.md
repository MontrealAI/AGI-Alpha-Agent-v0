# Native lifecycle and accounting fixture

This adapter uses the installed repository's actual `Journal`, `TrustRegistry`, `ResourceAccess`,
`CapsuleManifest` and `CostLedger`. It does not copy their implementations or create another production
registry. Source fingerprints cover the native Python modules actually imported during execution.

Run from the repository root:

```bash
python studies/agi-alpha-purpose-preserving-opportunity-v1/integration/native_adapter.py \
  --artifact /absolute/path/to/frozen/capability.py \
  --output /absolute/path/to/native-report.json
python -m unittest discover -s studies/agi-alpha-purpose-preserving-opportunity-v1/integration -v
```

The supplied artifact's real bytes and SHA-256 bind two purpose-distinct fixture missions. A source-byte
acceptance receipt is signed by a separate local acceptance principal. The real native resource access
implementation verifies local wallet signatures, binds each challenge to its exact action, resource and
mission, and consumes it atomically with the journal record. Its ENS authority dependency is explicitly
replaced by a fictional local association checked through the existing `TrustRegistry`. No RPC is sent.
Current revocation denies a new request. A successor retains the same source bytes while beginning with
empty current acceptance and authority; it needs a fresh receipt and fresh one-use challenge.

The fixture's supported invocation is immutable source-byte inspection. It does not independently accept
the ecological instrument's scientific conclusions, run arbitrary imported code, or constitute a new
production service. The core study remains responsible for actual instrument execution and semantic
acceptance. The native protected capsule schema rejects the new ecological scope, which remains
`NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE`. Jobs validators, settlement roles and production trust are
unchanged. The fictional `*.agent.agi.eth` labels are not asserted to be owned or authenticated on-chain.

## Accounting boundaries

One native ledger records actual-session costs as unknown accruals in optional research bucket C.
No customer collection is recorded; complete cost, profit and available funds remain unknown. A native
completeness seal is refused. Zero new recorded cash payments does not mean free research.

A separate temporary ledger exercises fully assumed arithmetic: A=$40, B=$10, C=$100; assumed opening
capital $200, paid costs $120, liabilities $30, reserve $25 and available funds $25. No customer collection
is entered. These are deliberately simple accounting test inputs, not calibrated commercial quantities,
bank attestations, the root study's economic results or evidence that a buyer exists. Every resource
category is included once per bucket; duplicate activity is rejected. Native signer attestations remain
attributed statements, not bank verification.

All wallet, signing and journal keys are temporary and deleted after report construction. Public signed
journal events, acceptance envelopes and fixture public signer keys are retained in the JSON report for
inspection. Importing these exported public keys does not confer trust or authority. Fresh runs regenerate keys and timestamps,
so semantic check results and source commitments are reproducible while receipt bytes differ.

## Executed evidence

`evidence/selftest-native-report.json` runs the adapter against the explicitly synthetic
`fixtures/source-inspection.json`. It records 18 passing native boundary/accounting checks, 16 imported
native source fingerprints and the runtime dependency versions. It is an adapter self-test, not the final
capability's source commitment. Run the CLI against the frozen study artifact to generate that commitment.

`evidence/validation.json` retains commands, results and earlier validation corrections. Seven unittest
cases pass, including verification of the exported successor acceptance signature. Ruff lint and formatting
checks and strict mypy pass. The installed Black tool cannot start because
`pathspec.patterns.gitignore` is missing; the exact environment error is preserved. Repository-wide test
success is not claimed by this adapter's scoped checks.
