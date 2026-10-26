# Your upgrade decision

scipy 1.10.1 to 1.14.1: sklearn-new source-contract assessment

**Next action:** Resolve the stated source or dispatch gap and run the relevant integration check before deciding.

Argument binding only. Review behavior and security before changing a deployed dependency.

**Complete monetary cost: unknown**. Unknown: setup, integration, upkeep, authoring/inference, customer effort.

## Selected calls

### T05-call-01

The selected call shape binds to both captured declarations.

```python
eigsh(
                M, k + k_skip, sigma=0.0, tol=tol, maxiter=max_iter, v0=v0
            )
```

The call-to-declaration target is supplied, and its runtime identity remains unproved.

- [consumer · L176–L178](https://github.com/scikit-learn/scikit-learn/blob/8721245511de2f225ff5f9aa5f5fadce663cd4a3/sklearn/manifold/_locally_linear.py#L176-L178) · SHA256 `f57eb9cc2a7a9a6b3c411f8634c8e06c95189766437fd8df8658076f3702da40`
- [b2 · L1357–L1699](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1357-L1699) · SHA256 `a9d851468f5052ad198baea6d499a13fc8793a78f187948ea549e7c1e7cfb916`
- [a2 · L1360–L1702](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1360-L1702) · SHA256 `052917b5fc2f994b6605e8ee809904d8b38f786b55f8cb3b4f15c72290ff471f`

### T05-call-02

The selected call shape binds to both captured declarations.

```python
eigh(
            M, subset_by_index=(k_skip, k + k_skip - 1), overwrite_a=True
        )
```

The call-to-declaration target is supplied, and its runtime identity remains unproved.

- [consumer · L192–L194](https://github.com/scikit-learn/scikit-learn/blob/8721245511de2f225ff5f9aa5f5fadce663cd4a3/sklearn/manifold/_locally_linear.py#L192-L194) · SHA256 `f57eb9cc2a7a9a6b3c411f8634c8e06c95189766437fd8df8658076f3702da40`
- [b0 · L270–L620](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/linalg/_decomp.py#L270-L620) · SHA256 `f7ae83c4d6a222bc17cec1c8fb33c35744ceeb39ef4d1bc889b0ad1cf7c82aa1`
- [a0 · L283–L618](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/linalg/_decomp.py#L283-L618) · SHA256 `0f75a0b54a38de1e028dbfbdbcb7a9115b3fec14975f5c182d606d7668513bf3`

## What remains unresolved

- Selected calls and inert argument binding only; not full application, dependency security or release approval.
- A declared target is a conditional source relationship, not proof of runtime dispatch.
- An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.
- Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.

Historical sources and recorded evidence; these pins are not current production recommendations.

Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.
