# AGI ALPHA · Maintenance decision — call contract

**F03 · NetworkX eigenvector centrality across the SciPy transition**

Scope: `eigenvector_centrality_numpy`; scipy 1.10.1 → 1.14.1.

## Recommended action

**REVIEW_UNRESOLVED_SCOPE**

This review identifies calls to revise or test. It is not behavioral validation, a security assessment or deployment approval. Complete scope acceptance is audited separately.

## Evidence and limits

### `sp.sparse.linalg.eigs` · L336 · BINDING_PRESERVED

These two signatures require no argument change for `sp.sparse.linalg.eigs`. Confirm the imported target and test this consumer path under both versions; binding alone does not justify production approval.

[Consumer source](https://github.com/networkx/networkx/blob/9c1ee6392311d056760714d4126cd6382f75a96f/networkx/algorithms/centrality/eigenvector.py#L336) · SHA-256 `a34aa658e88c7f5f07a1f770d0009a00edd30127890bcf51d66782af720b262d`

```python
sp.sparse.linalg.eigs(
        M.T, k=1, which="LR", maxiter=max_iter, tol=tol
    )
```

Retained qualification: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`eigs`](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/sparse/linalg/_eigen/arpack/arpack.py) · SHA-256 `a9d851468f5052ad198baea6d499a13fc8793a78f187948ea549e7c1e7cfb916`
- after: [`eigs`](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/sparse/linalg/_eigen/arpack/arpack.py) · SHA-256 `052917b5fc2f994b6605e8ee809904d8b38f786b55f8cb3b4f15c72290ff471f`

After signature: `A (POSITIONAL_OR_KEYWORD, required), k (POSITIONAL_OR_KEYWORD, optional), M (POSITIONAL_OR_KEYWORD, optional), sigma (POSITIONAL_OR_KEYWORD, optional), which (POSITIONAL_OR_KEYWORD, optional), v0 (POSITIONAL_OR_KEYWORD, optional), ncv (POSITIONAL_OR_KEYWORD, optional), maxiter (POSITIONAL_OR_KEYWORD, optional), tol (POSITIONAL_OR_KEYWORD, optional), return_eigenvectors (POSITIONAL_OR_KEYWORD, optional), Minv (POSITIONAL_OR_KEYWORD, optional), OPinv (POSITIONAL_OR_KEYWORD, optional), OPpart (POSITIONAL_OR_KEYWORD, optional)`

### `sp.linalg.norm` · L340 · BINDING_PRESERVED

These two signatures require no argument change for `sp.linalg.norm`. Confirm the imported target and test this consumer path under both versions; binding alone does not justify production approval.

[Consumer source](https://github.com/networkx/networkx/blob/9c1ee6392311d056760714d4126cd6382f75a96f/networkx/algorithms/centrality/eigenvector.py#L340) · SHA-256 `a34aa658e88c7f5f07a1f770d0009a00edd30127890bcf51d66782af720b262d`

```python
sp.linalg.norm(largest)
```

Retained qualification: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`norm`](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/linalg/_misc.py) · SHA-256 `dc83eaf8b21073157b10b6ed72064af118bad1859b86937fcbb5187ba04a1200`
- after: [`norm`](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/linalg/_misc.py) · SHA-256 `dc83eaf8b21073157b10b6ed72064af118bad1859b86937fcbb5187ba04a1200`

After signature: `a (POSITIONAL_OR_KEYWORD, required), ord (POSITIONAL_OR_KEYWORD, optional), axis (POSITIONAL_OR_KEYWORD, optional), keepdims (POSITIONAL_OR_KEYWORD, optional), check_finite (POSITIONAL_OR_KEYWORD, optional)`

## Complete cost not identified

Measured local resources are in the receipt. Inference, preparation, human review, integration and upkeep charges are not all available; complete cost remains unknown. Actual collections are zero.

[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · [Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)

Authority: HOLD; no operator authority; settlement disconnected. Recommendations require the maintainer’s decision.
