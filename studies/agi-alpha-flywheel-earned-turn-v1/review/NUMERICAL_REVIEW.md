# Numerical construction and persistence review

**Status: completed development review before confirmation.** The reviewer used only declared development seeds 27101–27104, with 24×24 and 40×40 grids and additional 4×4 smoke cases. Three standard sparse orderings were checked for correctness; these tests did not choose a winning method or expose confirmation tasks.

## Mathematical result

The updated solver implements the positive low-rank identity

`(A + U Uᵀ)^−1 b = A^−1 b − W (I + Uᵀ W)^−1 Uᵀ A^−1 b`, with `W = A^−1 U`.

For an edge increment `delta`, each direction column has `+sqrt(delta)` and `−sqrt(delta)` at its endpoints. Positive grounding and positive edge increments make the declared operator positive definite. The retained parent solves a block of `k` direction right-hand sides during construction. The recorded count is one parent API block call, not one scalar RHS solve; reports must state the block width separately.

Portable sparse factors use the saved SuperLU row/column permutations and triangular factors. Across **36 development combinations**, the separate edge-balance checker accepted **216 outputs**: native factors, restored portable factors, changed-load Mission B, native and portable low-rank descendants and restored descendants. The maximum relative residual was `6.267356117939566e-15`; the largest descendant-versus-direct coordinate difference was `1.3322676295501878e-14`. These numerical checks establish correctness for these finite inputs, not a speed, adoption or investment claim.

The exact raw records are `NUMERICAL_MATH_REVIEW_RAW.json` for the initial valid-input review and `NUMERICAL_MATH_REVIEW_FIXED.json` after corrections. The second binds the reviewed source and checker hashes. `test_numerical.py --math-review` reproduces the fixed-source review. Temporary factor files are deliberately not durable artifacts; their byte hashes are retained, while their reproducible recipes and generated development inputs are sufficient to rebuild them. NPZ container timestamps can change byte hashes on a subsequent save.

## Reproduced defects and corrections

`pre_fix/numerical.py` preserves the initial implementation; `pre_fix/PROBES.json` preserves the failing probes. Before confirmation, the root authorized validation fixes. They were implemented as follows:

| Reproduced defect | Correction and regression |
|---|---|
| An empty update was accepted, called the parent and left the operator unchanged. | Require at least one valid change and reject unchanged operator identity. |
| A Boolean edge index was accepted as integer1. | Require integer indices excluding Boolean values. |
| A NaN increment reached a parent solve before scope refusal. | Validate finite positive increments, distinct indices and range before constructing direction columns or calling the parent. |
| Negative and out-of-range increments failed with incidental exceptions. | Explicit `UPDATE_SCOPE` refusal before parent execution. |
| A factor file with a newly computed checksum and incoherent recipe identity loaded successfully. | Recompute the factor recipe identity and check explicit persistence schema, current operator, dependencies, dimensions, finite arrays, valid permutations and triangular structure. |
| Update loading lacked sufficient parent/operator and shape checks. | Bind base operator and parent recipe; verify current expected operator when supplied; recompute child identity; check finite direction, response and Schur arrays, shapes, direction form, consistency and positive definiteness. |
| Integer grounding values caused fractional edge additions to truncate in diagonal assembly. | Explicit floating-point diagonal storage. The analytic two-node case with grounding `[1,1]`, edge1.5 and load `[1,0]` now returns `[0.625,0.375]` and passes the independent checker. |

The last defect is a mathematical input-coercion bug in the **new development code**. Generated 0.1 grounding values did not trigger it. It is not a cause of the previous, frozen scheduling study's failure.

Twenty existing checker tests and 23 numerical scope/persistence regressions pass: **43 tests in total**. Their log is `NUMERICAL_SCOPE_TESTS.log`. No numerical algorithm or sparse ordering was changed by these fixes. Expanded persistence validation has a real load cost that the experiment must charge.

## Trusted prevalidated identities

Repeated full operator serialization was found during development to dominate some small constructions. The root requested a narrowly scoped interface correction:

```python
Update(parent, task, changes, preceding_receipt,
       validated_ids=(base_operator_digest, changed_operator_digest))
```

The default interface computes both identities itself. The optional tuple is for the fixed, packaged orchestrator **only**, after it has bound the complete WORLD input and changed operator independently. It is not a field accepted from candidate or public task JSON. The builder still checks tuple shape, hexadecimal digest shape, the base digest against its parent, nonempty valid changes and a changed operator identity before any parent solve. Persisted metadata records whether identities were derived in the builder or prevalidated by the fixed orchestrator.

This interface deliberately trusts the caller's full-input binding. Passing false identities through it is outside its contract; it does not independently authenticate an arbitrarily supplied WORLD. The outer orchestrator must charge common hash/serialization work equally to every arm, bind the loaded full input to the workbench receipt, and check the final output against the actual changed graph.

The preceding accepted receipt is a 64-character digest. It binds lineage to a recorded result, but a digest alone does not prove that the result was accepted. Acceptance and current authority remain controlled by the outer orchestrator and independent checker.

## Integrity and authentication limits

Both persistence loaders verify file bytes against the supplied trusted receipt. This detects altered files when the receipt remains fixed. It is not authentication against an adversary who can replace both file and receipt. Added structural and recipe checks reject incoherent metadata even with a newly computed checksum, but do not grant production authority or institutional proof. A validly reconstructed equivalent factor may have a different byte representation and still implement the same scoped numerical method.

`Update.load(..., expected_oid=current_operator_digest)` should be used when restoring for current work. Without it, the loader checks internal base/parent binding but cannot infer which changed WORLD the user currently intends. Every subsequent solve still needs independent output checking and lifecycle policy.

## Integration and resource observations still owned by the main study

The reviewed workbench bridge limits `payload_json` to120,000 bytes. Full compact generated inputs measure45,038 bytes at24×24,129,664 at40×40 and189,149 at48×48. A fixed small input-reference envelope must bind the full task digest, or the reviewed transport limit must be revised before freeze. The numerical review does not certify that outer integration or its future modifications.

The proposed release of unused accepted-mission CPU quota is an actual resource-allocation feedback mechanism if debited by later construction, but it remains release of **externally endowed capacity**. Equal initial capacity and release rules must be available to all arms. This is not resource creation, cash, or automatically a causal saving against the best comparator. Full Python plus Node costs, startup, persistence, checking and any reference computation remain part of the applicable accounting.

Reviewer-authored development checks and corrections share the commission and hardware. These reviews improve correctness; they do not constitute independent institutional replication. CPU and human effort for the initial exploratory review were not fully measured and must remain unknown in the investment ledger rather than being set to zero.
