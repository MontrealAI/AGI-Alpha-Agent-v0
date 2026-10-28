[Project notice](../../../docs/DISCLAIMER_SNIPPET.md)

# Frozen monetary cap and recorded acceptance

The comparison reporter previously checked the signed permit ceiling but omitted
current reconciled A costs from its frozen trial-budget check. An accepted artifact
with 1001 fictional micro-USD of incurred delivery costs could pass the 1000 limit.

The report now reads each trial's original mission from the existing CostLedger.
A known overrun is outside limits even before completeness; an unknown or unsealed
amount cannot establish a budget pass. A complete, currently supported amount at
the exact cap passes. Tokens, actions, time, original acceptance criteria, costs,
failed trials and the full frozen denominator stay in the report. Current monetary
status is explicit on each cell. Receipts and customer refunds are separate from
incurred A costs; negative expenses remain refused by the existing Charge model.
No B/C amount is moved into or out of delivery to improve a contrast.

The current origin validator was separately strengthened to recheck execution
controller trust. Its denial remains authoritative. The report now distinguishes
`accepted` (current origin eligibility) from `historical_acceptance_recorded` and
its separate arm count. The historical flag checks an existing installed
acceptance-role public key, signature and exact Journal/operation/execution/output
bindings, plus the actual finite artifact. It retains a typed EvidenceRef to the
actual acceptance record. Revocation is ignored only for inspecting this narrow
recorded history; no new trust registry is created. A wrong role, absent key,
invalid signature or changed binding does not count. The historical flag is never
used for current acceptance, comparison qualification, accounting or authority.

## Evidence

An isolated original-report overlay fails six behavioral assertions and passes
three exact/below-cap controls. It does not replace installed source files or
waive custody/funding checks. The final complete comparison suite passes **59**
cases, including fresh late reconciliation, all three arms, missing completeness,
refund separation, strict current revocation and eight invalid historical-receipt
conditions. Runtime Python source hashes remain unchanged throughout that run.

Current focused strict typing passes with dependency imports skipped; the parent's
full final native runtime check remains authoritative. Earlier native-config
one-file typing passed before historical metadata was added and is not relabeled
as final whole-runtime evidence. Final owned-file Ruff lint, formatting and
whitespace checks pass. See `QUALIFICATION.json` for exact hashes and commands.

All earlier failures remain: a correct unknown-cost funding refusal from an
initial fixture order, a concurrent source-change refusal, a full-disk abort,
current-check ordering correction, and new test expectations corrected for typed
EvidenceRef schema_version and a deliberately rewritten comparison revision.
The storage-aborted raw4KB log is preserved exactly in compressed/hash-bound JSON.
Only this workstream's failed disposable fixture trees were removed. The successful
retry first passed a real owned64MiB disk write and fsync; no shared-memory retry,
permission change or assertion weakening was used.

## Reproduction

```bash
TMPDIR=/tmp python -m pytest tests/runtime/test_flywheel_comparisons.py --confcutdir=tests/runtime -q
python -m ruff check --no-cache alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py tests/runtime/test_flywheel_comparisons.py
python -m mypy --config-file mypy-runtime.ini alpha_factory_v1/core/runtime/successor/flywheel_comparisons.py
```

The original-report reproduction driver is saved as
`replay-original-report.py.txt`; it uses the exact `ORIGINAL_SOURCE.py.txt` copy.
Its scope is original report logic with current unchanged dependencies, not an
old whole-source release. All calls and monetary amounts in these tests are
explicit protocol fixtures. Actual customer collections and controlled frontier
calls are zero; complete actual monetary costs remain unknown. No new commercial,
retention, foresight or production-authority claim follows from these corrections.
