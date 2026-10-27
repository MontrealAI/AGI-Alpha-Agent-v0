# Existing-interface integration

This adapter reuses unchanged native Journal/trust/A-B-C accounting code and the existing research
capability lifecycle. It does not create a production registry, extend protected scientific admission,
or change AGI Jobs roles, governance or settlement.

`source_manifest.json` binds every vendored file to its original immutable Git source. `verify_sources()`
fails before execution if any source byte changes. `bridge.py` exposes two narrow research interfaces:

- `run_lifecycle(candidates, operations, ...)` carries actual frozen component bytes through the existing
  research AES-GCM capsule and fixture-only lifecycle. Its input paired monetary evidence is explicitly
  caller-supplied; no routine derives actual frontier performance or revenue from it.
- `replay_native(commands, controls=False)` executes actual signed Journal and CostLedger commands in a
  new private temporary runtime. It exports only source identities, command projections, accounting
  reports and control verdicts, never keys or runtime credentials.

Run conformance against a frozen technical checkpoint:

```sh
python integration/run_integration.py --artifact technical/artifacts/v2.json --out integration/results/new-conformance
```

The output directory must not already exist, preserving prior attempts. The command runs source checks,
actual byte retrieval by all four declared fixture members, private/shared rights, unknown/nested-name
refusal, denied export and ungranted execution, revocation, Beta change, negative-value rejection,
duplicate-version refusal, known-protected-material exclusion, AES-GCM tamper controls and native
accounting controls. Artificial positive monetary values are used only to reach the admission/access
branches. They are never evidence of measured Alpha. The actual research ledger remains incomplete
when actual expense is unknown, with zero observed collections.

The file `received-v2.*` contains exactly the decrypted recipient bytes. A separate technical recipient
runner must load and execute those bytes to establish useful work; lifecycle retrieval alone never
claims execution. Replaying an already evaluated case checks transport/integration and is not a fresh
independent transfer trial. Technical confirmation, prospective admission evidence and this integration
conformance are separate records.

The recorded `results/conformance-v1/summary.json` passes 29/29 controls with the actual v2 JSON bytes.
`results/recipient-v1/` then executes those recovered bytes on a separately declared synthetic case,
seed 1010007, using 31 fit observations, eight visible validation observations and one final plan query.
It meets the unchanged response and cost conditions within 40 observations. The same observations,
bytes and permissions in an ordinary local library produce identical output. This one integration
challenge is not appended to the technical confirmation set or used to estimate a transfer rate.

To repeat that controlled execution in a new output directory:

```sh
python integration/recipient_check.py \
  --original technical/artifacts/v2.json \
  --retrieved integration/results/new-conformance/received-v2.json \
  --out integration/results/new-recipient
```

The command writes its seed, source digests, artifact identities and observation budget before generating
the task. The recipient receives only declared observations; the protected synthetic scorer is consulted
after its proposed plan is fixed. Additional scorer work is research overhead, not hidden free delivery.

`admission_check.py` separately replays the actual development-only economics in
`economics/lifecycle_inputs.json`. The saved `results/development-admission-v1/` rejects both the
96-query and 40-query v2 candidates, with no admission and denied retrieval. No positive conformance
fixture replaces that decision. The 12 development clusters were also used to select policies, so these
conditional assessments are explicitly exploratory. They are not independent confirmation or frontier-model
Alpha. The numerical observations are executed; the price, dollar resource costs and 44 future uses are
assumptions. The separate controlled recipient run remains outside production admission.

```sh
python integration/admission_check.py --out integration/results/new-development-admission
```

No live ENS call, proprietary-model update, frontier API call, customer sale or on-chain action occurs.
Main's protected scientific scope remains `NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE`. An ordinary
library with the same bytes and permissions has equal content; this adapter makes no graph-specific
economic claim. Local AES-GCM and Ed25519 checks do not establish deployed security or organizational
independence. Revocation blocks subsequent mediated retrieval, not possession of an existing copy.

Dependencies: Python 3.11-3.13, `pydantic` 2, `cryptography`, and Node.js. The study's pinned environment
record identifies the exact versions used. Upstream licenses are retained in each vendored closure.
The recipient execution also uses the technical study's NumPy, SciPy and scikit-learn dependencies.
