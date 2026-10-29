# Scoped supplier delta delivery

This is a small local CLI capability, not the full enterprise campaign or a new platform.
Only the byte-pinned PR #5011 catalogue producer and two adapter/checker modules plus a tiny shared identity guard are imported.
No campaign engine, financial logic, dependency change or hosted service is added.
The original source-only increment made no installed-wheel promise; the explicit narrow
wheel closure and its separate qualification are described in [PACKAGING.md](PACKAGING.md).

From the repository root (Python 3.11–3.13, standard library only):

```sh
python -m contrib.enterprise_campaign.delta_delivery \
  --before contrib/enterprise_campaign/examples/catalogue.csv \
  --delta contrib/enterprise_campaign/examples/supplier_delta.csv \
  --keys sku --write-fields price --decimal-fields price \
  --aliases '{"product_code":"sku","new_price":"price"}' --output /tmp/catalogue-review-new
python -m unittest discover -s tests -p 'test_delta*.py' -v
```

The output directory must not exist. Inputs remain untouched. Inspect REPORT.md and safe-preview.csv;
updated.csv preserves machine text, including formula-like cells, and is not a trusted spreadsheet.
Never apply remote catalogue changes without separately scoped authority.

Explicit contract: update existing keys/authorized fields, preserve omitted rows and local fields,
no insertion/deletion or inferred identifiers. Aliases and composite keys must be explicitly declared.
A changed producer fails its exact-source guard and requires requalification, not a pin bypass.

The checker shares the pinned bounded syntax parser, discards its parsed rows, and computes the intended update separately. Integration adds checks for review preview,
change summary, complete native contract metadata, native integrity and actual producer identity. Native apply/rollback separately reconstruct
and validate the complete native package. Neither checker is external certification. Review files
are local artifacts, not customer acceptance, financial settlement or security certification.

## Evidence and limits

`fast_delivery_evidence/original-*` preserves upstream developer evidence, not current-run receipts.
The original ZIP remains unchanged in Library (identity and hash in qualification.json). Original
26 tests were rerun on current Python 3.12; 50 tests pass after the checker repair, including eight
new fixed contract cases. The 64 original development cases tie conventional software. None are
independent customer trials or fresh scientific confirmation. Fixed code only was run with resource
limits and network denial; this does not qualify a generated-program sandbox.

This is designer-supplied transactional semantics, not autonomous analogy discovery. Costs, demand,
competitive advantage and profit remain unestablished. No customer outreach, payments or model calls.
The complete-service commercial probe still needs an actual admitted job, strongest complete
alternative, accepted output, collection and all acquisition/review/support/development costs.
Use the existing Journal/CostLedger when that probe is authorized; this module adds no ledger.

Full locked installation, full repository regression, required hosted checks and release acceptance
remain separate. The original source-only increment was not included in the wheel. The additive wheel
closure in [PACKAGING.md](PACKAGING.md) does not itself establish a published release.
The retained failed full-snapshot interpretation is a counterexample, not a regression in the
upstream producer's correctly declared full-snapshot contract.

## Reconciled contributions

PR #5025 at `c46f16f3872056b171ad02022becf5cddb5c5e18` independently extended the same
original adapter. This integration retains its canonical/type-sensitive packet comparison, exact
envelope contract, exclusive output writes, read-only verifier and development-only transfer sidecar.
It also retains #5022's actual producer-byte guard, shared bounded syntax gate and adversarial regressions.
Neither original branch is overwritten. Exact provenance/disposition is in
`fast_delivery_evidence/reconciliation-5025.json`; prior failures and receipts remain preserved.

After producing a packet, independently invoke the read-only command with trusted inputs/request:

```sh
python -m contrib.enterprise_campaign.delta_acceptance \
  --before contrib/enterprise_campaign/examples/catalogue.csv \
  --delta contrib/enterprise_campaign/examples/supplier_delta.csv \
  --request /tmp/catalogue-review-new/request.json --package /tmp/catalogue-review-new/package.json
```

This second process verifies the JSON packet, not subsequent sibling-file edits or an untrusted host.
The transfer-record.json is an inert sidecar, not a competing registry or ledger. Output uses exclusive
file creation but a failed write may leave a partial new directory; atomic delivery is not claimed.
