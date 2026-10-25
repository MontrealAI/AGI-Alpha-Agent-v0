# Fresh public-source assurance missions

Two finished source-reconciliation packages use the existing, unchanged
`examples/ti-guide/guide.mjs` implementation on freshly extracted repository inputs.
They are ordinary local Node execution, not an authenticated browser-to-executor test.

| Mission | Current public source inventory | Inspections | Result |
| --- | --- | ---: | --- |
| Guide source assurance | `docs/try/sources.json` | 8 | Every declared SHA-256 matches current committed bytes |
| Transformational source assurance | `docs/transformational-intelligence/sources.json` | 24 | Every declared SHA-256 matches current committed bytes |

The two scopes contain 31 unique source paths. Each package contains the declared
and observed CSV inputs, complete computed result, difference CSV, action-plan CSV,
recomputable workspace and receipt. Empty difference/action exports are the useful
checked outcome here: no source drift was discovered in these scopes. They do not
approve source behavior or assert absence of defects.

The second mission uses different actual inputs and the identical executable
dependency identity `82494db90559cbadfeda79d6d1a17a5f95ff1fc1498660c8d6403d50f46a873e`.
There are two primary `guide.compute` calls and two further computations during
workspace restoration. This demonstrates ordinary executable reuse. It does not
demonstrate invented methods, a promotion, superiority, expansion or acceleration.

Reproduce from the repository root:

```sh
node contrib/productive-capability-ledger/evidence/run-source-missions.mjs
python contrib/productive-capability-ledger/evidence/verify-source-missions.py
node --test examples/ti-guide/guide.test.mjs
```

The runner requires current committed source to match every inspected byte; it
refuses changed working files. Re-execution refreshes this evidence directory.
The Python checker separately reads CSVs, hashes actual files, compares committed
bytes and checks outputs without using the JavaScript comparison algorithm.
The recorded acceptance has 116 checks, zero failures; the existing guide suite
also passed all six cases. Same-session authorship is not independent custody.

Process wall/CPU observations cover local instrumentation only. Whole engineering,
model-assisted authorship/review, setup, human attention, hardware, maintenance and
business costs remain unknown. No human-work saving, collected revenue or surplus
is inferred. No credential, operator home, signed journal, network, contract,
financial action, production grant or held Harness/Fleet operation is used.
