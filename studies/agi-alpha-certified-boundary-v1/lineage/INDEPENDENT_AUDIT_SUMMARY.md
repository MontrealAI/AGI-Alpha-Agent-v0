# Independent audit: accepted internal research result

## Result

For every integer n>=2, every exact partition of {1,...,n} into complete
truncated residue classes, with at least two interval elements in every class,
has

    h=sum_i 1/m_i > 1891871140656049/1929687500000000
                 = approximately 0.9804028583156853 > 0.98.

This implies a negative answer to the below-0.98 question as defined in
Myerson's inspected author post. The proof does not require distinct moduli,
but preserves the exact-partition and at-least-two-elements requirements.

This is an executed, exact, computer-assisted proof with independently
recomputed mathematical obligations in the same session. It is not external
peer review, a proof-assistant formalization, a controlled model benchmark,
or commercial demand evidence. Literature priority is bounded by the scoped
primary-source search.

Frozen polynomial file: `scout/revised_polynomial.json`.
SHA-256: `c92bc1977bbb6804af862d52c82507793ff57e2355c501477f609e7a1dd22633`.

## Independent obligations

| Obligation | Independent method | Executed result | Last wall time |
| --- | --- | --- | --- |
| Every class of length 2 through 40 | Direct sparse Horner expansion of every summand; factorial Bernstein transform; binomial subdivision with opposite initial axis | 78/78 patches pass; 95 certificate leaves; maximum depth 6 | 3.8083s |
| Every class of length >= 41 | Rational univariate Bernstein bounds on derivative variation and exact quadrature inequality | Global upper bound0.9825010361292407<1 | 0.1737s, including original finite-n confirmation |
| Every interval length n>=2 | Explicit Chebyshev coefficients; telescoping centered-moment recurrence; 16 positive Bernstein intervals; direct n=2,3 | Uniform midpoint average strictly greater than exact integral | 0.0812s |

Wall times include launching a separate Python process and writing a report.
The 3.8083s result is a later independent rerun; the first full audit was 3.17s.
No timing advantage over a competitor is inferred.

Commands, from the package root:

```bash
python lineage/myerson_independent_bivariate.py
python lineage/myerson_independent_bounds.py scout/revised_polynomial.json lineage/myerson_revised_independent_bounds.json
python lineage/myerson_independent_uniform.py
```

The full argument is in `MYERSON_INDEPENDENT_AUDIT.md`. The execution log is
`INDEPENDENT_AUDIT_EXECUTION.json`. Acceptance uses rational/integer comparisons;
decimal values are explanatory only.

## Correction preserved

The initial coarse-grid polynomial had integral 0.9855824689586415 but was
infeasible. An independent exact finite-class counterexample at n=26, m=15,
residue 11 has normalized constraint value 1.0464113181398584>1. It was rejected
before publication. `myerson_original_counterexample.json` preserves this
and four other exact failures. No claimed lower bound derives from that witness.

## Existing ecosystem execution

The unchanged adapter from archive-study artifact commit
`979f50024ddbf3d6eff6c49d3271898c64b240f8` executed the unchanged 44-file native
source closure pinned at `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`.
All preserved source byte digests passed. New study metadata and outputs are:

- `native/myerson_metadata.json`;
- `native/results_myerson/insight/`;
- `native/results_myerson/research-nova-seed.json`;
- `native/results_myerson/fusion-plan.json`;
- `native/results_myerson/research-sidecar.json`;
- `native/results_myerson/native-controls.json`;
- `native/results_myerson/MANIFEST.json`.

Insight produced a neutral single-candidate review dossier; this is provenance
execution, not a comparative discovery score. Nova-Seed remains an unminted,
unfunded research draft. FusionPlan contains four verified job commitments;
its integrity is not proof that downstream jobs were executed. The production
capsule correctly refuses the unsupported scientific scope. The native ledger
records four local fixture journal events and refuses a complete-cost seal
when authoring costs are unknown; complete profit remains null. Plan and
dossier tampering controls are refused. Temporary fixture identities were not
live ENS authentication. No MARK activation or external financial operation
occurred.

To reproduce the bridge, choose a fresh output path; it intentionally refuses
to overwrite preserved evidence:

```bash
python lineage/native/integration/native_bridge.py --input lineage/native/myerson_metadata.json --output lineage/native/results_myerson_reproduction
```

The metadata and output manifest contain artifact hashes. Some research reports
include run durations and will have new hashes if rerun; retain the original
metadata snapshot when reproducing the bridge instead of silently replacing it.

## Prior-art cross-check

The separate conventional-challenge audit subsequently inspected Emanuel's 2011 dissertation and located the stronger prior general lower bound h>sqrt(8)-2 (Appendix C, Theorem C.1, printed page 215). This is the appropriate prior general bound, rather than the weaker main-text asymptotic 0.75. See `challenge/heft_audit/PRIOR_ART_AND_DEFINITION_AUDIT.md`. Full copyrighted thesis/article working copies must be excluded from the public deliverable.
