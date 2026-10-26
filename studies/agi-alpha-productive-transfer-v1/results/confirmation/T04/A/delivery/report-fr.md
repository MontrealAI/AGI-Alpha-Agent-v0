# Votre décision de mise à niveau

scipy 1.10.1 to 1.14.1: sklearn-old source-contract assessment

**Prochaine action:** Suspendez la mise à niveau de cette dépendance seule. Reproduisez ce conflit précis, examinez la correction amont et testez l'ensemble des dépendances.

Liaison des arguments seulement. Vérifiez le comportement et la sécurité avant toute modification d'une dépendance déployée.

**Coût monétaire complet : inconnu**. Inconnu: setup, integration, upkeep, authoring/inference, customer effort.

## Appels sélectionnés

### T04-call-01

La forme de cet appel est acceptée par la déclaration précédente et refusée par la déclaration proposée.

```python
linalg.eigh(
                K, eigvals=(K.shape[0] - n_components, K.shape[0] - 1)
            )
```

La cible de l'appel est déclarée ; son identité à l'exécution reste non démontrée.

- [consumer · L330–L332](https://github.com/scikit-learn/scikit-learn/blob/ffc0f66676b4835eb1bdd3f3ecab025e9c1be9fe/sklearn/decomposition/_kernel_pca.py#L330-L332) · SHA256 `b59f0f8cd73ac2523c5e687a24cb06c49ef4339796ef6b9953592509235c1806`
- [b0 · L270–L620](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/linalg/_decomp.py#L270-L620) · SHA256 `f7ae83c4d6a222bc17cec1c8fb33c35744ceeb39ef4d1bc889b0ad1cf7c82aa1`
- [a0 · L283–L618](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/linalg/_decomp.py#L283-L618) · SHA256 `0f75a0b54a38de1e028dbfbdbcb7a9115b3fec14975f5c182d606d7668513bf3`

### T04-call-02

La forme de cet appel est acceptée par les deux déclarations capturées.

```python
eigsh(
                K, n_components, which="LA", tol=self.tol, maxiter=self.max_iter, v0=v0
            )
```

La cible de l'appel est déclarée ; son identité à l'exécution reste non démontrée.

- [consumer · L335–L337](https://github.com/scikit-learn/scikit-learn/blob/ffc0f66676b4835eb1bdd3f3ecab025e9c1be9fe/sklearn/decomposition/_kernel_pca.py#L335-L337) · SHA256 `b59f0f8cd73ac2523c5e687a24cb06c49ef4339796ef6b9953592509235c1806`
- [b2 · L1357–L1699](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1357-L1699) · SHA256 `a9d851468f5052ad198baea6d499a13fc8793a78f187948ea549e7c1e7cfb916`
- [a2 · L1360–L1702](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/sparse/linalg/_eigen/arpack/arpack.py#L1360-L1702) · SHA256 `052917b5fc2f994b6605e8ee809904d8b38f786b55f8cb3b4f15c72290ff471f`

## Ce qui reste non résolu

- Selected calls and inert argument binding only; not full application, dependency security or release approval.
- A declared target is a conditional source relationship, not proof of runtime dispatch.
- An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.
- Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.

Sources historiques et résultats consignés ; ces versions ne sont pas des recommandations de production actuelles.

Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.
