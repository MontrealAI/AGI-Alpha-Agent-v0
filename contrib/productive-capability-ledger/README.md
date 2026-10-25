# Productive capability: mission economics increment

This additive product increment adds economic planning to the existing
`successor/alpha/` project workspace. Complete a catalogue mission, choose
**Keep this capability**, then open **What did this delivery cost?** The result,
retained project cycles and planning assumptions stay together in the portable
HTML workspace. The existing `/try/` planning-owner lane is untouched.

The new feature is an implementation candidate, not a deployed release. Existing
accepted versions, scientific results, public papers and the original Harness/Fleet
decisions remain intact. The integration owner coordinates through
[issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850).

## Useful behavior

- Price assumptions, self-reported collected proceeds, complete costs, reserves,
  unpaid obligations and potential capability investment remain separate.
- Blank inputs and incomplete operating-cost inventories remain unknown. Reinvestment
  defaults to zero; explicit conditional accepted-work scenarios permit other fractions.
- Costs include failed construction. Finite reuse and maintenance can make an
  investment lose money. Customer savings are never enterprise revenue.
- Every plan references an existing project cycle and its implementation identity.
  Recalculating identical inputs is idempotent. Revisions remain; only the latest
  record for each mission is selected. Different currencies are never summed.
- Fresh cycles start with blank assumptions. Separate planning JSON imports cannot
  replace or remove already retained history. The existing strict project and
  learning formats remain unchanged; planning is a separately bounded inert sidecar.
- The downloadable HTML includes the project, original learning history and planning
  sidecar. Closing the page stops local computation. Nothing schedules future work,
  executes payments or continues as an unattended service.

All UI amounts are entered assumptions or unauthenticated self-reports. Local
catalogue correctness does not establish commercial acceptance. The user must
explicitly select an accepted-work *scenario*. No measured full-cost saving,
collected payment or improvement is inferred from browser timing.

The pure API is documented in
[`examples/successor-alpha/SHADOW_LEDGER.md`](../../examples/successor-alpha/SHADOW_LEDGER.md).
The [token boundary map](TOKEN_BOUNDARIES.md) distinguishes actual protocol burns,
fee rewards, funding and return of principal from hypothetical enterprise surplus.
Manager's USDC route does not create an AGIALPHA purchase or burn.

## Delivered mission evidence

[Two fresh source-assurance packages](evidence/README.md) compare actual declared
and committed source inventories with the unchanged released catalogue method.
They contain both CSV inputs, complete results, action plans, recomputable
workspaces, executable dependency identities and separately implemented acceptance.
The second mission invokes the same method on different actual inputs.

Both inventories match. Empty action plans are honest checked deliverables, not
evidence that behavior is defect-free. Ordinary executable reuse is demonstrated;
new strategy discovery, superiority, autonomous capability expansion and acceleration
are not. The new accounting feature is an externally engineered product extension.

## Scope and dependencies

| Capability | Status and exact limit |
| --- | --- |
| Fresh local catalogue comparison and exports | Supported existing deterministic engine; public/permitted nonpersonal CSV only |
| Mission-linked economic planning | Implemented; hosted Chromium accepted d12e955 predecessor. Review corrections require fresh checks; release remains pending |
| Retained tool on a second source-assurance mission | Executed in local Node; ordinary reuse, no improvement claim |
| Finite reinvestment/reuse planning | Tested conditional arithmetic; no treasury or spending API |
| Planning → changed planning → repair companion | Existing owner candidate; this increment does not qualify or replace it |
| Browser-to-approved-executor execution | NOT RUN by this team; requires an already approved operator home and exact supported installed profile |
| Public repository repair executor | Unavailable in the inspected capability matrix; isolated reviewed snapshot/patch adapter still required |
| General desktop execution or remote Fleet | Unqualified/unavailable under the existing scope and restrictions |

The public baseline entry points returned HTTP 200 during this work. Their served
bytes do **not** contain this new panel. The pending implementation must pass its
own existing-owner integration, source-bound browser/hosted qualification and normal
publication before an updated public experience can be claimed.

## Reproduce

```sh
node --test examples/successor-alpha/*.test.mjs
python -m unittest tests.test_successor_alpha_delivery
python -m pytest -q tests/test_successor_alpha_release.py
python contrib/productive-capability-ledger/evidence/verify-source-missions.py
python tests/browser/test_shadow_ledger_browser.py --report /tmp/shadow-browser.json
```

Regenerate with `python scripts/generate_successor_alpha.py`, then
`python scripts/build_service_worker.py`. The existing release acceptance now invokes
the new browser journey and requires `mission-shadow-ledger-and-offline-recovery`;
the full source validator includes both new economic implementation modules.

Browser acceptance is explicitly **NOT RUN locally**: Chromium is absent and ordinary
Playwright downloads were truncated. The separate cloud browser could not reach the
local preview. The checked-in blocked receipt records zero browser passes. The new
browser test subsequently passed in the hosted browser-capable environment at
`d12e955909cb5b52a5225c39d4f7fab4a5f93d50`
([run40209883107](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40209883107)).
The local blocked receipt remains historical. The report-publication and currency
review corrections require fresh hosted checks. No unperformed installation or
public acceptance is claimed.


## Automated-configuration continuation

The additive [automation-v1 evidence and software](automation-v1/README.md)
implements the source-assurance delivery path and the shared
`alpha-automated-costs/v1` record. It separates marginal, recurring and fully
loaded cost, prices software replacement of routine handling, and preserves
one-time/shared work, failed construction and residual decisions. The
[completed conditional economics](automation-v1/AUTOMATED_ECONOMICS.md) use
measured execution components, sourced compensation and explicit assumptions;
actual complete monetary cost remains unknown. Neither the old staffed scenario
nor a token component is promoted into an established Agent cost.

The previous hosted mission-recovery run found a real null-project startup bug.
That source and outcome remain recorded. The repaired source now has an actual
UI regression, plus new shared-cost controls and separately checked recovery
software. Exact current-head hosted browser acceptance is still required before
this candidate is integrated or described as publicly installed.

Further review reproduced earlier-cycle assumptions entering an unplanned current cycle.
The [current-cycle restoration repair](automation-v1/CYCLE_RESTORATION_VALIDATION.json)
selects only the latest matching plan on workspace restoration and ledger import.
Four actual-source regressions pass; the earlier archive stays intact. Fresh
hosted qualification is required for this source; previous passes remain historical.
