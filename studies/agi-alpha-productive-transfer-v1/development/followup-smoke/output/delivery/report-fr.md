# AGI ALPHA · Décision de maintenance — contrat d’appel

**synthetic-control · Synthetic development control**

Périmètre: `mission`; provider 1 → 2.

## Action proposée

**HOLD_UPDATE_AND_TEST**

Cette revue délimite les appels à corriger ou à tester. Elle ne constitue ni une validation comportementale, ni une approbation de sécurité ou de déploiement. L’acceptation du périmètre complet est évaluée séparément.

## Preuves et limites

### `execute` · L3 · BINDING_CONFLICT

Suspendre la mise à niveau pour `execute`. Le contrat capturé accepte cet appel avant, mais le refuse après. Vérifier la cible importée, adapter les arguments à la signature ci-dessous, puis exécuter un test de régression du consommateur avec les deux versions. Aucun correctif comportemental n’est validé ici.

[Source consommateur](https://github.com/test-fixture/structural-input/blob/0000000000000000000000000000000000000000/consumer.py#L3) · SHA-256 `5ae5655ec2320adf2c3f0502b31c67e06c988f94bf7faf16f6e07fdfd542b39e`

```python
execute(3, flag=True)
```

Limite conservée: Direct captured import under standard imports, successful argument evaluation and no runtime monkeypatching.

- before: [`work`](https://github.com/test-fixture/structural-input/blob/0000000000000000000000000000000000000000/provider/api.py) · SHA-256 `0a8d660ab630f926eafe85bd07636235714b1dfa66365362ab8c9c959f0bb0f1`
- after: [`work`](https://github.com/test-fixture/structural-input/blob/0000000000000000000000000000000000000000/provider/api.py) · SHA-256 `9a40cabc3b6b72d299181acc4eb2a42f033c0e81cfce232ee8106e8be0b7e6ed`

Signature après: `x (POSITIONAL_OR_KEYWORD, required)`

## Coût complet non identifié

Les ressources locales mesurées figurent dans le reçu. Les frais d’inférence, de préparation, de vérification humaine, d’intégration et d’entretien ne sont pas tous disponibles; le coût complet demeure inconnu. Aucun encaissement réel.

[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · [Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)

Autorité : HOLD; aucune autorité opérateur; règlement non connecté. Les recommandations exigent la décision du mainteneur.
