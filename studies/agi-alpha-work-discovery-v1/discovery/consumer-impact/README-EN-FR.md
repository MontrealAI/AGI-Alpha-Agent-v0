# Legacy Compose and Engine 26: source-bound rollout decision

## English — decision

**Hold approval of an Engine 26 / API 1.45+ rollout for a deployment that still depends on the identified
Docker Compose 1.29.2 container-recreation path.** Plan a move to a maintained Docker Compose implementation,
then qualify the actual deployment configuration and volume-preservation behavior in staging before release.
This packet identifies a concrete compatibility concern; it does not certify that migration or run the user's stack.

The beneficiary is an operator deciding whether a known legacy Compose consumer can accompany an Engine upgrade.
The recurring trigger is a platform/API release combined with an existing consumer that reads affected fields.
No operator commissioned or paid for this study. The supplied consumer and published issue are public evidence of
a relevant use case, not collected demand or an estimate of customer savings.

### What the evidence establishes

The pinned [Compose 1.29.2 source](https://github.com/docker/compose/blob/1.29.2/compose/service.py#L1562-L1622)
defines `get_container_data_volumes` at lines 1562–1622. At line 1579 it directly indexes
`container.image_config['ContainerConfig']`. The caller at lines 1547–1550 invokes this function when a
previous container exists during volume-binding reconciliation.

The executed diagnostic extracts that complete, unmodified function from the actual source using Python's AST.
It imports neither Compose nor its full service module. Two explicit empty-volume fixtures isolate the field:

| Input to the extracted function | Executed result |
|---|---|
| `ContainerConfig` present, with empty `Volumes` | Returns empty bindings and `updated_mounts = false` |
| `ContainerConfig` absent, with `Config` still present | Raises `KeyError('ContainerConfig')` |

The source file is SHA-256 `f2af8cb4a401d892f5d668122803b7e67d93c0be17f03c6f988cd4b74c22dcbb`.
Its Apache 2.0 license is preserved. The test uses labeled fixtures, not captured Docker responses.
The output binds the extracted function's hash, exact line locations and both observed outcomes.

Docker's [26.0 release notes](https://docs.docker.com/engine/release-notes/26.0/) identify the removal of
`Container` and `ContainerConfig` from image inspection. The more precise
[deprecation entry](https://docs.docker.com/engine/deprecated/#container-and-containerconfig-fields-in-image-inspect)
limits omission to Engine 26 with API 1.45 and later. This makes the negotiated API and actual call path material.
A public [Compose issue](https://github.com/docker/compose/issues/11742) also records the legacy failure after
an Engine update and the maintainer's move-to-supported-Compose guidance; that report was not reproduced end to end here.

### A useful limitation of the structural inventory

Both exact Swagger snapshots used in discovery, v25.0.0 and v26.0.0, still declare
`#/definitions/ImageInspect/properties/ContainerConfig`. Their property declarations are identical, including
the description that anticipates removal in API 1.45. Therefore the frozen structural-fact inventory **does not
report this field as removed**. Its image-inspection change is the separate `Created` format/nullable declaration.

This is a documented runtime/version condition that a structural-only difference cannot establish. The appendix
adds publisher-documentation review and consumer-source evidence; it is not a schema-diff success, a change to
primary results, or a third retained capability. A broader customer promise must pay for these additional checks.

### Remaining release work

The deployment owner must establish the invoked Compose version and negotiated API, determine whether the
identified recreation path is used, validate the intended supported replacement, and inspect preservation of the
deployment's actual volumes. No installed Compose, Docker daemon, live API negotiation, image pull, container
recreation, application test or customer acceptance was executed here. No EOL consumer patch was proposed.

Reproduce the bounded source probe from the repository root:

```sh
python studies/agi-alpha-work-discovery-v1/discovery/consumer-impact/probe_consumer.py
```

See `outputs/consumer-probe.json`, `outputs/schema-documentation-boundary.json`, `probe-receipt.json` and
`delivery-record.json`. Command execution, acquisition and research effort are separate. Model billing and
residual deployment attention remain unknown; no human-duration or commercial advantage is inferred.

## Français — décision

**Suspendre l'approbation du passage à Engine 26 / API 1.45+ si le déploiement dépend encore du chemin de
recréation identifié dans Docker Compose 1.29.2.** Préparer le passage à une implémentation Compose maintenue,
puis vérifier en préproduction la configuration réelle et la préservation des volumes avant la mise en service.
Ce dossier établit un risque précis ; il ne valide pas la migration et n'exécute pas le système du client.

La fonction authentique `get_container_data_volumes`, extraite sans modification du fichier public
`compose/service.py`, lit directement `ContainerConfig` à la ligne 1579. Avec une fixture où ce champ est
présent et les volumes sont vides, elle renvoie des associations vides. Lorsque le champ est absent, même si
`Config` est présent, elle déclenche `KeyError('ContainerConfig')`. Ce sont des fixtures explicitement étiquetées,
pas des réponses capturées auprès d'un serveur Docker.

La documentation officielle annonce l'omission de ces champs à partir d'Engine 26 avec l'API 1.45.
La version d'API négociée et le chemin effectivement exécuté restent donc à vérifier. Le dossier ne prouve pas
que toutes les opérations de Compose échouent : l'appel identifié dépend notamment d'un conteneur précédent.

Les deux schémas Swagger exacts v25.0.0 et v26.0.0 conservent pourtant la même déclaration de `ContainerConfig`,
avec la même description annonçant sa suppression. **L'inventaire structurel figé ne détecte donc pas cette
suppression d'exécution conditionnée par la version.** La revue de la documentation et du consommateur constitue
une preuve supplémentaire, distincte des résultats primaires. Elle n'est pas présentée comme un succès du
différentiel de schéma ni comme une troisième capacité acquise.

L'exploitant doit vérifier la version réellement invoquée, la négociation d'API, le comportement du remplacement
maintenu et la préservation de ses volumes. Aucun moteur Docker, aucune migration en production et aucune
acceptation client n'ont été exécutés. Aucun revenu n'a été encaissé. Le temps humain résiduel et le coût complet
restent inconnus. Les sources, licences, hashes, résultats des fixtures et coûts de commandes sont conservés.
