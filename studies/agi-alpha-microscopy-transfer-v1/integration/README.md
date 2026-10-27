# Existing-interface microscopy transfer

This is a bounded research caller around the existing AGI Alpha lifecycle,
Journal, TrustRegistry, and A/B/C CostLedger. It carries the actual instrument
bytes through local AES-GCM encryption and fixture-based network access. It
does not add a registry or extend the production capsule's accepted scope.

## Run against a frozen retained instrument

From the study directory:

```sh
python integration/run_integration.py \
  --artifact src/microscopy_transfer.py \
  --out integration/results/frozen-v1
```

Use a new output directory for each attempt. The runner refuses an occupied
destination and preserves earlier source/result pairs. A successful run writes
`received-artifact.py`: the exact decrypted source bytes available to a separate
recipient process. That recipient must use a new declared mission contract and
run the module's actual checks. Retrieval alone is not useful execution, biological
acceptance, or a measure of transfer advantage.

The intended instrument version is `microscopy-moments/v1`. Its native-label and
mapped geometric measurements must remain distinguished in fresh contracts;
the downstream instrument checks source axes, spacing, units, origin, affine
mapping, target axes, support coverage, label meaning, and requested metrics.
Array index `i` denotes a voxel center; its continuous support spans
`[i - 0.5, i + 0.5)` on each source index axis. Source calibration is axis aligned:
physical source coordinates are `origin + spacing * i`, with units converted
axis by axis to micrometers. The affine matrix's columns follow `source_axes`
and rows follow `target_axes`; translation is in target physical micrometers.
This is geometric pushforward of supplied label support, with uniform voxel
occupancy. It makes no claim that registration recovers true biological size.
Nonzero signed label IDs in the exact JSON integer range are supported; zero
is background. Arbitrary connectivity, nonlinear maps, topology, full-cell
coverage, and intensity inference remain different unsupported missions.
The lifecycle's scope-mismatch control demonstrates refusal of a different
declared meaning. It does not prove the correctness of every within-scope metric.

## What the controls establish

The runner checks identical byte retrieval by four declared fictional
`*.agent.agi.eth` members; refusal of unknown and nested names and the separate
Jobs club role; private versus network rights; export refusal; separately required
execution authority; revocation; changed baseline and mission scope; duplicate
version refusal; protected-evaluation-material exclusion; artifact hash mismatch;
AES-GCM ciphertext, key and context tamper; real Ed25519 signed accounting;
duplicate activity refusal across A/B/C; idempotency; wrong-journal and tampered
signature refusal; revoked signer refusal; unknown-cost boundaries; and rejection
of unsupported production microscopy capsule scope.

These are actual local computations with fictional identity and economic inputs.
The research network's membership/root attestations are fixtures, not real ENS
authentication or an independent validator organization. Ed25519 and AES-GCM
are executed locally; no chain transaction, deployed service or wallet action
occurs. Revocation prevents subsequent mediated retrieval; it cannot delete a
copy already obtained.

The frozen-instrument run in `results/frozen-v1/` passes all **32 controls** on
SHA-256 `a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db`.
Recovered source bytes match that original exactly. `VALIDATION.json` binds the
caller sources, receipts, independent 16-probe input review, and runtime versions.
These 32 controls and 16 input probes are separate from scientific confirmation
and the subsequent fresh recipient result.

## Accounting that preserves uncertainty

`native_actual_unknown.json` records unpaid research in bucket C with unknown
attributable authoring/review expense, no observed receipts, and no completeness
seal. Complete profit, total obligations, and available funds remain unknown.
No research activity is relabeled a paid originating job.

`native_synthetic.json` uses wholly artificial amounts only to test the existing
ledger. It has all nine resource categories in each of A, B and C; seeds and
invoices do not become revenue; paid amounts and accrued liabilities remain
separate. These amounts are not the study's commercial forecast. The driver's
positive lifecycle monetary pairs likewise exist only to reach admission/access
branches. They are not measured Operational Alpha, a market sample, or the
study's actual economic admission decision.

## Source and provenance

All 29 unchanged dependency files are checked against `source_manifest.json`
before import/execution. Native files come from immutable main
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`; their bytes and Git objects were
independently compared in this study. The existing research lifecycle is read
from `231834269599d85e49cfe1ca9917a1a874522d44` and byte-compared with that
study's preserved original-source manifest. The earlier origin audit is inherited
provenance, not a newly rerun audit of every historical commit.

The small Python/JavaScript callers are adapted from
`studies/agi-alpha-capability-opportunity-v1/integration/` at that research commit.
Only caller metadata, microscopy scope, and added conformance controls change.
Their underlying lifecycle/accounting implementation is unchanged. Apache 2.0
notices and the upstream manifest remain in the package.

The initial source-pin attempt refused the updated package-version initializer
when compared with the older 80b manifest. `development_source_pin.json` preserves
that failure and the explicit correction to current frozen main identities.
The source model was never imported before correcting its declared identity.

`development/transport-smoke-v1/` tests transport with the earlier bridge module
as the payload; v2 includes two additional signed-record controls with the later
bridge module. Neither smoke is a microscopy result or a fresh technical recipient
test. A later frozen instrument result must remain separately identified.

The independent input review uses tiny synthetic arrays, never the protected
confirmation specimen. Its final v3 receipt passes 16 semantic/input probes on
the exact retained module in that directory. The first v1 probe ran after the
source had already been corrected and did not trigger its obsolete digest hook;
it is preserved as a weak probe, not a reproduced earlier defect. Later probes
actually change the on-disk source just before NumPy loading, check structured
refusals, and stop an oversized header before an allocation sentinel can run.
The original source-binding and NPZ issues were found by source inspection.
See `development/REVIEW_HISTORY.md` for the chronology and limits.

Callers must inspect the instrument's JSON status, rather than treating process
exit alone as measurement acceptance. Its internal `elapsed_seconds` measures
the numerical/contract phase; complete delivery latency also includes the owned
file snapshot, hashing, decoding, and output packaging.

The foundational source synthesis and precise historical limits are retained in
`foundation_audit.md` and `foundation_sources.json`. Local scientific fixture
qualification does not clear any current hosted, release, installed runtime,
production, or canonical website publication gate.

Requirements: Python 3.11-3.13, Pydantic 2, cryptography, and Node.js. Exact versions
used appear in the study's environment record. The recipient instrument separately
requires NumPy; no model provider, credential or external service is needed for
these local controls.
