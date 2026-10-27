# Foundation inspection and actual accounting reuse

Inspection date: 26 October 2026. This record describes bounded local research
reuse; it does not qualify an installed four-repository product.

## Source snapshots

| Foundation | Inspected commit | Applicable assets and preserved boundary |
| --- | --- | --- |
| [AGI Alpha Agent](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/d28818dc89a92c40d525d7f0c805e95d8be5978a) | `d28818dc89a92c40d525d7f0c805e95d8be5978a` | Mission/history and bounded successor research foundations; exact-source execution, admission and publication remain separate. |
| [AGI Fleet Linux](https://github.com/MontrealAI/AGI-Fleet-Linux/tree/45759fb096faf8988f58ae5ea71248d0f35a97c7) | `45759fb096faf8988f58ae5ea71248d0f35a97c7` | Qualified local execution/review architecture and explicit skill reuse; physical and live-provider commissioning remain open in the inspected README. |
| [AGIJobManager](https://github.com/MontrealAI/AGIJobManager/tree/5d5670df9dbbc79da115e0a44b71989f34df58c1) | `5d5670df9dbbc79da115e0a44b71989f34df58c1` | USDC job lifecycle and zero-cap inspection adapters; draft imports confer no execution, payment, settlement or capability authority. |
| [AGI Jobs v0](https://github.com/MontrealAI/AGIJobsv0/tree/bc4abbd5c28f3672275b13300e40ea26c820b8ee) | `bc4abbd5c28f3672275b13300e40ea26c820b8ee` | $AGIALPHA work-order ecosystem and bounded Discovery receiver; local zero-cap review is distinct from external execution and settlement qualification. |

The four READMEs were inspected at these exact local checkout heads. Their byte
identities and source links are in `sources/foundation_manifest.json`. The
checkouts were clean after inspection; this contribution changed no native file.

Alpha's contributor guidance was read from `foundations/AGENTS-source.md`; Fleet's
`AGENTS.md` was also read. The retained instructions require truthful fixtures and
checks, additive work, preserved evidence, and unchanged authority/settlement.
The scoped accounting exercise below has no native installation or service
requirement. Full repository environment setup and release checks are not claimed.

## Reused code, not only an architectural reference

The applicable canonical accounting helpers are in the separate existing
[PR #4915 source](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/c4a7febc02fb9d607e9da5ece2101c4b6b36fc64/examples/successor-alpha).
They were not represented as part of the inspected main snapshot. We vendored
their smallest executable dependency closure into `vendor/native-accounting/`:

| Original path | Git blob SHA-1 |
| --- | --- |
| `examples/successor-alpha/automated-costs.mjs` | `91da2937ba129793b21652f68560e8bd4aa32f56` |
| `examples/successor-alpha/shadow-ledger.mjs` | `581ff9217457b37682fe2dc42bc0aaf2d4e7b53d` |
| `LICENSE` | `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64` |

The local bytes reproduce all three upstream Git blob identities. Both modules
have no imports; no third-party or service dependency was omitted. Existing
SPDX notices and the original Apache-2.0 license are preserved.

`automated-costs.mjs` is actually executed against the native
`alpha-automated-costs/v1` schema. It requires preparation, planning, execution,
verification, correction, packaging, reporting and recovery; facts carry
measured/sourced/estimated/unknown provenance. Its rational arithmetic keeps
unknowns unknown and charges failures through attempts and acceptance volume.
The native names `base`, `conservative`, and `stress` are schema labels in the
isolated arithmetic fixture, not an inherited scientific design or the final
economic scenario definition.

`shadow-ledger.mjs` is actually executed through a new bounded-JSON projection.
Every supplied simulated mission includes delivery, business, capability and
maintenance costs, reserves and obligations. Rejected work remains in aggregate
costs. Modeled collections become an **assumed price/scenario amount**, because
the native schema correctly refuses assumed values labeled as collected receipts.
Observed revenue and observed available surplus remain unknown in this projection.
The outer record explicitly labels the events simulated. No experiment output is
presented as a native authenticated mission.

This projection is an accounting compatibility seam. It does not manage cash
chronology, invoke a settlement route, acquire a permission or make an investment.
The independent simulator must maintain its own finite-cash event ledger and
decision policy. Its validation can compare a completed horizon with this native
scenario arithmetic, while retaining the distinction between a cash ledger and
an amortized cost calculation.

## Actual local checks

Command, from the study directory:

```sh
node vendor/native-accounting/verify_projection.mjs evidence/native_accounting_check.json
```

Recorded runtime: **Node v24.22.1**. All **12** scoped checks pass. The complete
input, outputs and named checks are retained in `native_accounting_check.json`.
They cover eight-stage cost calculation; unknown human baseline and cost
propagation; rejection of missing stages and duplicate identities; inclusion of
construction, upkeep, reserves and unpaid obligations; modeled/observed revenue
separation; zero automatic reinvestment; rejection of an assumed collected
receipt; retention of failed-work losses; rejection of executable object input;
and preservation of a negative investment result.

One development failure is retained: the first authored assertion mis-summed
eight stage fixtures as USD860 instead of USD760. The expected arithmetic and
dependent fixture totals were corrected; the native modules were never modified.
This is a support-code development correction, not a changed economic protocol
or a suppressed experimental outcome.

These checks are genuine local executions over deliberately constructed examples.
They are not evidence of the frequency, cost or quality of actual venture jobs.
The full native suite, required upstream Node 22.17.1 profile, configured hosted
checks, installed adapters, ENS authentication, provider execution, contractual
settlement and production deployment are **NOT RUN** by this exercise.

## Authority and currency separation

The inspected Manager README retains Agent and Node role families, including
its separately documented configured alternatives. This research adds an
agent-network graph-admission model; it does not reinterpret or replace existing
`*.club.agi.eth` settlement validation. Direct-label authority in the research
graph must be enforced by that graph's own explicit policy, not inferred from
suffix matching or retroactively imposed on existing contracts.

Native Manager settlement is USDC. Alpha/Jobs v0's $AGIALPHA utility and contract
routes remain distinct. The reused helpers accept ordinary fiat accounting
units; they perform no token conversion. Token issuance, transfer and appreciation
are absent from operating revenue. No contract, governor, publisher, signer,
security setting, funded path or live permission was changed.

## What remains before operational integration

The research package can supply a source-pinned capability/evidence envelope,
cost projection and explicit simulated disposition. Operational adoption still
requires the existing owners' exact-source review, their installed adapter and
runtime qualification, real authentication/authorization and revocation checks,
task-matched frontier measurements, current billing/quotas, and separately
authorized deployment and commissioning. The inspected previews do not grant
those capabilities merely because an offline study passes.
