# Votre décision de mise à niveau

Starlette 0.36.3 + HTTPX 0.27.2 → 0.28.1 · historical example

**Prochaine action:** Suspendez la mise à niveau de cette dépendance seule. Reproduisez ce conflit précis, examinez la correction amont et testez l'ensemble des dépendances.

Liaison des arguments seulement. Vérifiez le comportement et la sécurité avant toute modification d'une dépendance déployée.

**Coût monétaire complet : inconnu**. Inconnu: setup, integration, upkeep, authoring/inference, customer effort.

## Appels sélectionnés

### testclient-constructor

La forme de cet appel est acceptée par la déclaration précédente et refusée par la déclaration proposée.

```python
super().__init__(
            app=self.app,
            base_url=base_url,
            headers=headers,
            transport=transport,
            follow_redirects=follow_redirects,
            cookies=cookies,
        )
```

La cible de l'appel est déclarée ; son identité à l'exécution reste non démontrée.

- [starlette-consumer · L429–L436](https://github.com/Kludex/starlette/blob/be4f3e110ed1172ec9cb47a6209bd899a0d3a604/starlette/testclient.py#L429-L436) · SHA256 `4ad9cf0a44243a5d82e3becfe19d8aad4d7ac5f7298fb35a6ba6273b940dffe8`
- [httpx-before · L628–L724](https://github.com/encode/httpx/blob/609df7ecc0f7cb10a1c998aa9c269bba77337c5f/httpx/_client.py#L628-L724) · SHA256 `c4abf7e3485c2df38f0a78a57b1121da0360e41ac442a212eff3b4641f67c56c`
- [httpx-after · L639–L716](https://github.com/encode/httpx/blob/26d48e0634e6ee9cdc0533996db289ce4b430177/httpx/_client.py#L639-L716) · SHA256 `c43f941baefe58c91e96d00039e1868fe719d91453026d7db1647194563bff8d`

## Preuves d'exécution consignées

Ces vérifications ont été consignées séparément ; cet exécuteur de sources ne les réexécute pas.

historical-integration-01

Actual offline fixed ASGI probe in three hash-pinned upstream wheel environments. One exposed historical job. These stored observations are source-linked imported evidence; the source worker does not rerun them or gain package-execution authority.

Current continuation replay summary SHA256 1f6bbea8d5210789659034d2d1764fda3e43758715fe70d5c1f7ce95932352b3; original writer study f019a1d2d1c1c678c7363bf9cde61dab6ec0de12; probe SHA256 bdbfe5d11587fa81a18a6a05d6bf6e67e99fd0b3d9c375540cbf2410351a6451

```json
{
  "all_dependency_checks_pass": true,
  "all_exact_versions": true,
  "before_accepted": true,
  "known_upstream_remedy_accepted": true,
  "no_network_attempts": true,
  "proposed_update_failed_as_observed_historical_mechanism": true
}
```

## Ce qui reste non résolu

- Selected calls and inert argument binding only; not full application, dependency security or release approval.
- A declared target is a conditional source relationship, not proof of runtime dispatch.
- An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.
- Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.

Sources historiques et résultats consignés ; ces versions ne sont pas des recommandations de production actuelles.

Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.
