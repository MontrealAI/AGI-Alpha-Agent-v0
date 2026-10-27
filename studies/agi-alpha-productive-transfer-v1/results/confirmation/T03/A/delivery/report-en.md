# Your upgrade decision

scipy 1.9.3 to 1.10.1: sklearn-old source-contract assessment

**Next action:** Resolve the stated source or dispatch gap and run the relevant integration check before deciding.

Argument binding only. Review behavior and security before changing a deployed dependency.

**Complete monetary cost: unknown**. Unknown: setup, integration, upkeep, authoring/inference, customer effort.

## Selected calls

### T03-call-01

The selected call shape binds to both captured declarations.

```python
linalg.eigh(
                K, eigvals=(K.shape[0] - n_components, K.shape[0] - 1)
            )
```

The call-to-declaration target is supplied, and its runtime identity remains unproved.

- [consumer · L330–L332](https://github.com/scikit-learn/scikit-learn/blob/ffc0f66676b4835eb1bdd3f3ecab025e9c1be9fe/sklearn/decomposition/_kernel_pca.py#L330-L332) · SHA256 `b59f0f8cd73ac2523c5e687a24cb06c49ef4339796ef6b9953592509235c1806`
- [b0 · L267–L606](https://github.com/scipy/scipy/blob/de80faf9d3480b9dbb9b888568b64499e0e70c19/scipy/linalg/_decomp.py#L267-L606) · SHA256 `077bfbbf8d610c122b1d4c5ddc90ce8217604aa95b2949c00086521ae201dc1d`
- [a0 · L270–L620](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/linalg/_decomp.py#L270-L620) · SHA256 `f7ae83c4d6a222bc17cec1c8fb33c35744ceeb39ef4d1bc889b0ad1cf7c82aa1`

### T03-call-02

The selected call shape binds to both captured declarations.

```python
eigsh(
                K, n_components, which="LA", tol=self.tol, maxiter=self.max_iter, v0=v0
            )
```

The call-to-declaration target is supplied, and its runtime identity remains unproved.

- [consumer · L335–L337](https://github.com/scikit-learn/scikit-learn/blob/ffc0f66676b4835eb1bdd3f3ecab025e9c1be9fe/sklearn/decomposition/_kernel_pca.py#L335-L337) · SHA256 `b59f0f8cd73ac2523c5e687a24cb06c49ef4339796ef6b9953592509235c1806`
- [b2 · L1350–L1691](https://github.com/scipy/scipy/blob/de80faf9d3480b9dbb9b888568b64499e0e70c19/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1350-L1691) · SHA256 `5be43c7dee4ad8e7410368c6a10195e5ee03326a364c4d17d9a66c86cc01aa2f`
- [a2 · L1357–L1699](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1357-L1699) · SHA256 `a9d851468f5052ad198baea6d499a13fc8793a78f187948ea549e7c1e7cfb916`

## What remains unresolved

- Selected calls and inert argument binding only; not full application, dependency security or release approval.
- A declared target is a conditional source relationship, not proof of runtime dispatch.
- An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.
- Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.

Historical sources and recorded evidence; these pins are not current production recommendations.

Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.
