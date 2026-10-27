# Reproduce the paid-job Alpha study

This is an offline research simulation and a tested lifecycle/access adapter. It makes no model, identity, customer, payment or settlement requests. Actual revenue is zero; actual complete research cost is unknown. Simulated dollar values are never observations of a business.

## Layout

Keep the companion directory structure intact. BeyondBeta reuses only generic primitives at these sibling paths:

- `venture_creation/src/finance_capacity.py`: finite cash bookkeeping, not historical economics.
- `venture_creation/src/authority_fixture.py`: the parity-tested direct-agent fixture predicate.
- `venture_creation/src/native_integration.mjs`: inert cash/authority adapter; its historical admission routines are not called by this study.
- `human_market/validation/skill_admission.mjs`: unchanged native direct-agent authority foundation.
- `native_snapshot/canonical/shadow-ledger.mjs`: existing `planMission` reconciliation.

The pinned upstream provenance is in `native_snapshot/manifest.json` and `canonical/provenance.json`. Live contracts, club roles and production security are unchanged.

## Dependencies and checks

Use the Python/package versions recorded in `validation/execution-environment.json`; `requirements.txt` gives exact package pins. Node is required for the existing-system adapter. A TeX installation and Poppler are required only to compile/inspect the paper. No API credential or paid access is needed.

From the companion root:

```bash
python3 beyond_beta/src/freeze_study.py --verify beyond_beta/protocol/source-freeze.json
python3 beyond_beta/tests/test_graph_lifecycle.py
python3 beyond_beta/validation/engine_controls.py
python3 beyond_beta/tests/test_native_smoke.py
python3 beyond_beta/run_experiment.py
```

The last command reports the campaign definition without generating a world. Controls use explicitly fictional budgets and are not the economic results.

## Re-run the frozen campaign

Use a new empty output directory; the runner refuses to overwrite results. It preserves failures and partial histories. The original run's exact outcome and resource envelope are recorded beside its results.

```bash
python3 beyond_beta/run_experiment.py --run --max-seconds 7200 --output beyond_beta/results/reproduction
```

The original campaign declared a 1,800-second operational envelope, then encountered an explicit storage-capacity interruption. Its original bytes, unfinished tail, 1,289 complete records and recovery metadata are preserved. Continuation was separately authorized and recorded without changing scientific inputs. The 7,200-second allowance above is for a clean reproduction on another machine; reproducing the storage interruption or using the continuation script is not a prerequisite for a clean rerun. Complete original CPU time and actual complete study cost remain unknown.

Training and confirmation are sequential. The runner records all policy scores, selects best Beta, best optional Alpha and the overall winner, then writes a selection freeze before fresh confirmation. No selected policy is allowed to inspect confirmation outcomes. The seed/condition draw scheme fixes economic outcomes. Ephemeral cryptographic keys are regenerated, so signature bytes and roots can differ without changing economic outcomes.

## Analyze without executing new worlds

```bash
python3 beyond_beta/src/analyze_results.py --results beyond_beta/results/primary
python3 beyond_beta/publication/reporting_supplement.py --results beyond_beta/results/primary
```

`publication/REPORTING_CLARIFICATIONS.md` explains two mechanical reporting issues in the frozen first analyzer. The supplement reads the final explicit funding fields and separates initial retention from ongoing reuse. It changes no economic history, policy, price, cost or acceptance result. Complete profit remains authoritative.

The frozen independent auditor at `foundations/audit_economic_trace.py` reads recorded histories without importing the simulator. Its original confirmation PASS and original training FAIL (51 temporal-epoch flags) are preserved. The post-freeze `validation/audit_epoch_diagnostic.py` adds the Beta/policy increments omitted by that auditor's temporal replay; its separate training and confirmation reports pass all 6,288 unchanged histories. Use its documented CLI and retain the frozen auditor and original reports.

The native extractor actually used is `validation/extract_native_confirmation.py --run-native`. Its recovery-aware guard requires COMPLETE, explicit completed operational continuation, unchanged frozen inputs, original interrupted/tail hashes, exact recovered gzip-prefix bytes and all 1,289 original record hashes. The initial no-failure-file refusal and original extractor are preserved separately. It checks the fixed 24-history selection through 48 native planning calls and 264 fixture-authority predicates, and writes no new economic worlds. Run it only after restoring the raw streams to their documented paths and in a fresh audit-output copy, because it refuses to overwrite its evidence.

`validation/semantic_reproduction.py` performs exactly two separately labeled verification replays: reference/1001/trained-beta, and the first recorded network-alpha confirmation history with an admitted asset. Both reproduced their economic outcomes despite fresh ephemeral keys. They add no primary samples. It also refuses to overwrite its report. Actual complete verification cost remains unknown.

All diagnostic result files state their executed coverage and limits. Paths in old execution records identify the original environment; the scripts derive current workspace paths from their own locations.

## Paper and demonstration

The LaTeX source, generated tables, figures and English/French self-contained HTML are in `publication/`. Compile the paper from that directory with two runs of `pdflatex -interaction=nonstopmode -halt-on-error paper.tex`. The demonstration opens as a local HTML file; its selectors inspect registered results rather than inventing new outcomes. Its default example was chosen before results. It includes a downloadable record and labels assumed, externally reported, calibrated and locally observed material.

## Claims and costs

Ledger A contains every paid-job delivery resource, including learning already undertaken. B contains only additional retention and reuse work. C contains optional separate research. Shared operations and financial adjustments remain explicit. A is recorded in a retained skill's provenance but is not charged again to prospective Alpha. Complete enterprise economics always include all accounts and failures.

The human-service reference is a task-level effort estimate combined with sourced United States wages and an explicit business allowance. Buyer values, acceptance, retention yield, future Beta progress and transfer are assumptions. A modeled Alpha admission is not an operational certification. A larger graph, more agents, node counts or job volume do not prove value, exclusivity or self-acceleration.
