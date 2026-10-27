> **Conceptual research prototype.** This draft contains an offline research implementation and conditional
> simulated commercial results. It is not a deployed service or evidence of realized sales. See the
> [repository disclaimer](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md).

# Summary

**PROFITABLE WORK FIRST. COMPOUNDING CAPABILITY WHEN WORTHWHILE.**

Add an independent coordination-mechanism foundry study under
`studies/network-invented-economy-v1/`, coordinated through #4850. The study asks whether competent frontier
delivery can earn complete-cost operating surplus against a matched human-service reference, and separately
whether retaining and sharing learning from useful paid jobs improves subsequent work enough to justify
its additional costs. Keeping those decisions separate prevents an unproved Alpha claim from becoming a
prerequisite for an otherwise profitable modeled delivery business.

The completed experiment contains **6,048 simulated histories**: 2,304 training, 768 primary confirmation,
2,736 sensitivity and 240 ablation histories. Primary results cover 104 operating weeks plus 16 run-off
weeks, with $60,000 seed capital and 64 confirmation worlds per scenario.

| Scenario | Mean modeled Beta operating surplus | Mean closing resources after seed comparison and planning buffer |
| --- | ---: | ---: |
| Conservative | $411,421 | $408,312 |
| Central | $3,702,395 | $3,698,570 |
| Favorable | $6,763,479 | $6,758,482 |

Operating surplus deducts all accrued expenses and unexpensed closing obligations; it excludes seed capital
and future receivables. The final column is the reporting-only, per-world calculation
`max(0, min(profit, available_cash - initial_seed) - operating_floor)`, with a $2,640 operating floor.
It is a closing comparison, not a historically locked seed reserve or an investment commitment.

A stricter reporting sensitivity retains only receipts tied to correct, on-time modeled outcomes while
charging every enterprise expense and closing obligation. Mean surplus remains $343,435 / $3,522,731 /
$6,527,982; the conservative minimum is -$30,129. No empirically qualified service-quality floor or measured
customer willingness to pay is claimed. Prices were selected on the network policy family in training and
then applied unchanged to Beta; this is not an independent Beta-specific price optimization.

**Optional Alpha remains unestablished in primary confirmation.** The paired network-minus-Beta increments
are -$13,947 / -$12,063 / -$8,766; the favorable 95% conditional Monte Carlo interval spans zero. No selected
primary policy funds separate C R&D. The positive deterministic retention example remains a modeled cost
surface, and the actual known-method witness preserves mixed construction/checking results without claiming
a net dollar benefit or previously infeasible frontier work.

Evidence for these statements is retained in `results/summary.json`, `results/commercial_core.json`,
`results/recipient_ablation.json` and `evidence/mechanism_witness.json` within the study directory.

## What this adds

- A source-bound protocol and executable simulator with heterogeneous competent Beta agents, human-service
  buyer alternatives, pricing, optional retention/R&D, quotas, queues, errors, complete costs and finite cash.
  A delivery cost, B incremental retention and C separate invention are charged distinctly; paid-job
  construction is not charged a second time to retention.
- A tested research graph lifecycle: candidate, evidence, scoped Alpha assessment against versioned Beta,
  eligible signed validation, separate admission, all-member discovery/retrieval and authorized reuse.
  Revocation, stale evidence, moving baselines, direct-label authority, complementary bundles and separate
  failure memory have explicit implementation and rejection tests.
- A bounded executable coordination witness and heterogeneous recipient counterfactuals, with positive,
  redundant and negative cases retained. Component-mask ablations are reported as total intervention
  effects, including policy and queue responses, rather than clean marginal capability effects.
- Source-linked calibration, a source-pinned unchanged native accounting dependency closure, a 12-sample
  confirmed-data accounting projection, full-ledger audit code and a source-bound modeled graph adapter.
- An English/French offline evidence explorer, LaTeX paper, scientific figures, evidence companion,
  reproducibility instructions and a separately delivered complete raw-evidence archive.

This is an additive draft contribution. Existing owners, studies, publications, code, AGI Jobs
`*.club.agi.eth` roles, contracts, governance and settlement remain unchanged. `$AGIALPHA` utility is separate
from operating earnings; token issuance or appreciation contributes zero modeled revenue.

## Reporting amendment and preserved scientific record

The 27 October commercial-first presentation is an explicitly disclosed **post-results reporting amendment**.
It changes narrative order and adds derived reporting views, not the frozen hypotheses, selected policies,
prices, seeds, experiments or negative conclusions. The original protocol already treats Beta, Alpha,
sharing and durability as separate hypotheses; no new preregistered priority is asserted.

All 20 frozen scientific source identities still match protocol SHA-256
`7cb1683c08090d68cef5e847438446dda8032b67163c5368c2cbdaddce180dcb`.
Earlier source and paper editions, development amendments and the storage-interruption recovery are
preserved. See `evidence/REPORTING_AMENDMENT_20261027.md` and `results/training_interruption.json`.

# Checks

The following upstream checks are **not claimed as passed** for this isolated draft. The complete upstream
environment was not set up; opening this draft does not waive required hosted merge or release gates.

- [ ] `pre-commit run --files <changed paths>` — not run in the complete upstream hook environment.
- [ ] `pre-commit run --all-files` — not run; no repository-wide hook result is claimed.
- [ ] `python check_env.py --auto-install` — not run; no complete upstream installation is claimed.
- [ ] `pytest --cov --cov-report=xml` — not run for the full repository; study-local unit results are below.
- [ ] PR CI / `Lint (ruff)` — pending the actual PR; no hosted result is claimed here.
- [ ] PR CI / `Smoke tests` — pending the actual PR; no hosted result is claimed here.

# Testing

| Executed check | Result and scope |
| --- | --- |
| `python3 -m unittest discover -s tests` | **113 passed**, run from the study directory on 27 October 2026; 1.766 seconds. Covers the witness, Alpha arithmetic, lifecycle/access refusals and specific accounting regressions. |
| Independent confirmation audit | **768 complete ledgers**, 22,497,355 repeated checks, zero failures; `results/output_audit.json`. Reconstructs policy selection, ledger chronology, cash/reservations, A/B/C partitioning, quotas and summary identities. |
| Independent sensitivity audit | **2,736 rows across 57 conditions**, 8,220 checks, zero failures; `results/sensitivity_audit.json`. |
| Commercial reporting reconciliation | **192 Beta ledgers**, 28,993 checks, zero failures; `results/commercial_core.json`. No new economic seeds or price selection. |
| Native accounting compatibility | 12 fixture checks on Node v24.22.1; confirmed-data projection maps 39,007 expense rows once across 12 alternative worlds, with source/native cost-checksum difference zero. See `evidence/native_accounting_check.json` and `evidence/native_confirmed_projection.json`. |
| Demo interaction QA | **15 JavaScript/DOM-fixture groups** and nine saved Python-oracle cases; `demo/ui_qa.json`. This is not browser visual validation. |
| Scientific identity | All 20 frozen files match the retained protocol before publication; no frozen file changed for this reporting edition. |

Large audit counts are repeated arithmetic/protocol assertions over the same recorded histories, not
independent inventions, customer trials or evidence of market certainty. The native aggregate is a checksum
over alternative simulated worlds, not one enterprise's observed expenditure or receipts.

## Qualification limits

- **No Node 22 native release gate:** the local accounting seam ran on Node v24.22.1. The upstream Node 22.17.1
  release profile, complete native suite and hosted release acceptance were not qualified.
- **No browser visual qualification:** deterministic script checks passed, but Chromium was absent and
  automatic approval review declined downloading its runtime. No browser-rendering pass is claimed.
- **No live frontier task trial, ENS enforcement, on-chain deployment or sales:** production/validation roles,
  commercial outcomes and graph identity/authority are modeled or fixture-bound. Actual local AES-GCM,
  Ed25519 and Merkle operations use public deterministic test keys and confer no production secrecy.
- Graph checks enforce the research API lifecycle; they do not establish a secure multi-tenant service,
  truthful validator evidence, or an operational authorization to execute exported material.
- Supplied manuscripts are cited and hashed, not redistributed. No confidential client material, credentials,
  provider purchase, financial transaction, permission bypass or deployment is included.

`README.md` gives commands for unit checks, witness/graph replay, the frozen simulator, commercial reporting,
native arithmetic and the publication build, including `analysis/build_commercial.py`. Full ledgers remain
in the separate evidence archive; `results/DATA_AVAILABILITY.md` documents restoration and hashes.

This draft is ready for source and research review. Operational adoption requires the exact-source,
task-matched and deployment qualification described in `evidence/OPERATIONAL_VALIDATION_PLAN.md` and
`evidence/IMPLEMENTATION_BOUNDARIES.md`; this PR does not activate a production route.
