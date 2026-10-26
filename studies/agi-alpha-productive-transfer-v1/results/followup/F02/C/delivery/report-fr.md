# AGI ALPHA · Décision de maintenance — contrat d’appel

**F02 · Black output and error formatting across the Click transition**

Périmètre: `_out, _err`; click 8.1.7 → 8.2.1.

## Action proposée

**REVIEW_UNRESOLVED_SCOPE**

Cette revue délimite les appels à corriger ou à tester. Elle ne constitue ni une validation comportementale, ni une approbation de sécurité ou de déploiement. L’acceptation du périmètre complet est évaluée séparément.

## Preuves et limites

### `style` · L20 · UNRESOLVED

Décision suspendue pour `style`. Identifier la cible effective et les arguments développés ou liés, puis exécuter un test isolé de ce chemin avec les versions avant et après; conserver les valeurs, types et exceptions observés. Le motif ci-dessous précise la preuve manquante.

[Source consommateur](https://github.com/psf/black/blob/3702ba224ecffbcec30af640c149f231d90aebdb/src/black/output.py#L20) · SHA-256 `86193aef8ea564131b1ae27554b82397f26b9fb62f6f6e190456827e93bf8a33`

```python
style(message, **styles)
```

Limite conservée: expanded arguments require runtime verification


### `echo` · L21 · BINDING_PRESERVED

Aucun changement d’arguments n’est exigé par ces deux signatures pour `echo`. Confirmer la cible importée et tester ce chemin du consommateur avec les deux versions; la liaison seule ne justifie pas une mise en production.

[Source consommateur](https://github.com/psf/black/blob/3702ba224ecffbcec30af640c149f231d90aebdb/src/black/output.py#L21) · SHA-256 `86193aef8ea564131b1ae27554b82397f26b9fb62f6f6e190456827e93bf8a33`

```python
echo(message, nl=nl, err=True)
```

Limite conservée: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`echo`](https://github.com/pallets/click/blob/874ca2bc1c30d93a4ac6e36a15ed685eafe89097/src/click/utils.py) · SHA-256 `d78efa51db94358e9478f194e26d7cbb35472edd6c28cd8f3f7c96b1085b22d3`
- after: [`echo`](https://github.com/pallets/click/blob/fd183b2ced1cb5857784fe7fb22f4982f671f098/src/click/utils.py) · SHA-256 `6f5326faeb040c11ed13070f96d3c89f7cd22b89f0d8a4e9e460bbfe849394ba`

Signature après: `message (POSITIONAL_OR_KEYWORD, optional), file (POSITIONAL_OR_KEYWORD, optional), nl (POSITIONAL_OR_KEYWORD, optional), err (POSITIONAL_OR_KEYWORD, optional), color (POSITIONAL_OR_KEYWORD, optional)`

### `style` · L29 · UNRESOLVED

Décision suspendue pour `style`. Identifier la cible effective et les arguments développés ou liés, puis exécuter un test isolé de ce chemin avec les versions avant et après; conserver les valeurs, types et exceptions observés. Le motif ci-dessous précise la preuve manquante.

[Source consommateur](https://github.com/psf/black/blob/3702ba224ecffbcec30af640c149f231d90aebdb/src/black/output.py#L29) · SHA-256 `86193aef8ea564131b1ae27554b82397f26b9fb62f6f6e190456827e93bf8a33`

```python
style(message, **styles)
```

Limite conservée: expanded arguments require runtime verification


### `echo` · L30 · BINDING_PRESERVED

Aucun changement d’arguments n’est exigé par ces deux signatures pour `echo`. Confirmer la cible importée et tester ce chemin du consommateur avec les deux versions; la liaison seule ne justifie pas une mise en production.

[Source consommateur](https://github.com/psf/black/blob/3702ba224ecffbcec30af640c149f231d90aebdb/src/black/output.py#L30) · SHA-256 `86193aef8ea564131b1ae27554b82397f26b9fb62f6f6e190456827e93bf8a33`

```python
echo(message, nl=nl, err=True)
```

Limite conservée: Conditional on the declared target; runtime dispatch/import identity is unproved.

- before: [`echo`](https://github.com/pallets/click/blob/874ca2bc1c30d93a4ac6e36a15ed685eafe89097/src/click/utils.py) · SHA-256 `d78efa51db94358e9478f194e26d7cbb35472edd6c28cd8f3f7c96b1085b22d3`
- after: [`echo`](https://github.com/pallets/click/blob/fd183b2ced1cb5857784fe7fb22f4982f671f098/src/click/utils.py) · SHA-256 `6f5326faeb040c11ed13070f96d3c89f7cd22b89f0d8a4e9e460bbfe849394ba`

Signature après: `message (POSITIONAL_OR_KEYWORD, optional), file (POSITIONAL_OR_KEYWORD, optional), nl (POSITIONAL_OR_KEYWORD, optional), err (POSITIONAL_OR_KEYWORD, optional), color (POSITIONAL_OR_KEYWORD, optional)`

## Coût complet non identifié

Les ressources locales mesurées figurent dans le reçu. Les frais d’inférence, de préparation, de vérification humaine, d’intégration et d’entretien ne sont pas tous disponibles; le coût complet demeure inconnu. Aucun encaissement réel.

[Captured input](raw-task.json) · [Decision record](decision-record.json) · [Call inventory](call-inventory.json) · [Cost record](costs.json) · [Execution result](result.json) · [Receipt](receipt.json)

Autorité : HOLD; aucune autorité opérateur; règlement non connecté. Les recommandations exigent la décision du mainteneur.
