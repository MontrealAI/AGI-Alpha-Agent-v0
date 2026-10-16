# Return Manager work to a fresh Alpha cycle

**Current guided path:** [Open the project journey](../../docs/agent/GUIDED_SUCCESSOR_JOURNEY.md).
It reads the current bundled Manager / Jobs / Fleet transfers in the existing mission workspace.
The CLI described below retains its separately pinned historical Manager receiver; its exact checkout
requirements are intentional, and it does not read newer Manager browser exports.

This optional Node receiver carries an Alpha project through actual local Manager work and back into a new native Alpha cycle. One continuity JSON retains the complete original Manager transfer, its original Alpha dossier, every Manager capsule and every new Alpha project checkpoint. Existing readers and native schemas remain unchanged. The new file is read with the continuity CLI.

The receiver executes the actual Manager validator from the explicitly selected clean checkout, which in turn executes the pinned native Alpha validator. Alpha revalidates its native project and recomputes every allowed cycle/run transition with the native record checker. Hashes alone do not establish validity. Imported reviews, clocks, costs and provenance remain supplied historical statements; no signature, independent review or protected comparative evaluation is inferred.

This is an experimental source candidate, separate from the qualifying preview and deployment work. Pin Manager commit `e5d59f1c8e307193dbb99196a5276eb1fe344fe3`, tree `5136b443f9ef081db7cb5a788f4d49d3f5db2740`, and the original Alpha checkout at `7c410d3d61d5d6bba5354307e1784dba2b3aa177`, tree `e80b1dc06317d939e3dd22d2db063a7f1706ddcb`. These are explicit source identities, not independent review approval. Install trusted software normally; a supplied journal cannot select code, a URL, another source pin or an execution endpoint. Checkouts must be clean. Actual bytes in the complete 19-file Manager execution/builder closure and 18-file original Alpha validator/manifest closure are verified against pinned Git objects. Hidden Git index edits, symlinks and an injected Manager `SOURCE.json` cannot substitute code or provenance.

New Alpha cycles use the native manifest from the published guided source commit
`611a1ae31408f45661430eaf58442dcc78851f96`, tree
`03c3b8e48ae0067c48b9a11154a1178e99b65b58`; its exact manifest SHA-256 is
`5de0c05c5620658dadda8f27c59ce9faeab5ba37150d002a22eb2106beaef4bf`.
The manifest and all 90 local source hashes are checked. The inventory includes
the additive guided history, templates and exact-source receiver closure; the
native discovery and mission-record JavaScript engines remain byte-identical.
The new source identity is recorded in the new cycle. The original Alpha cycle
and original Manager bytes retain their earlier provenance. No old record is
relabeled as having used the new source.

The earlier preview native checkpoint remains `ccad46c561e1b649c77a61d11d405b2ec255e09c`,
tree `e987ff3b748cc56a324239fcc3eb6a018010eeec`, with manifest SHA-256
`908268b06a535a15ad1725deea48fdd160db6816a2af6d643421383826cd6dea`.
Its original 17-file manifest is retained unchanged at
[provenance/mission-sources-ccad46c5.json](provenance/mission-sources-ccad46c5.json)
and its existing evidence remains historical.
The first guided native checkpoint, `875f5a079c9978f744df259b4885f51f96c55727`,
tree `1b54e262009a6696e685910ecb1c6a8e67e5b881`, retains its original 87-file
manifest SHA-256 `1c46d81b4c26d2be6b61d08e33801bb62df6a6d6dd82a016c742e386da11430b`.
Its source identity also remains historical; existing records are not relabeled.
The native input-preflight checkpoint, `ff2a858a5a8b59005c812dc3103108c65156d165`,
tree `2bb20998ffc982b0ff2af9c311ffc674960f34c6`, retains its original 90-file
manifest SHA-256 `6e4ae267273b85028f20f3dbff08a1d845081e1e8a589287cdf871d19a47f20f`.
The current source adds the reviewed Manager C4 receiver and trusted context.

Prepare a separate public-data mission JSON using the native mission schema; the example is `examples/successor-workbench/missions/public-data.json`. Explicitly choose the next dataset, its rights, integer units, language (`en` or `fr`), new cycle ID and new mission ID. The prior rejected record remains historical. The new cycle starts as a draft, with no result or current review.

```sh
node examples/successor-project/continuity-cli.mjs import manager-transfer.json /ABSOLUTE/MANAGER_CHECKOUT /ABSOLUTE/ALPHA_BASELINE next-mission.json cycle-2 mission-2 --new-public-data-cycle continued.json
node examples/successor-project/continuity-cli.mjs inspect continued.json /ABSOLUTE/MANAGER_CHECKOUT /ABSOLUTE/ALPHA_BASELINE
node examples/successor-project/continuity-cli.mjs run continued.json /ABSOLUTE/MANAGER_CHECKOUT /ABSOLUTE/ALPHA_BASELINE executed.json
```

Import performs validation and creates a draft; it does not run the next task. The separate `run` action executes the selected local Alpha task and preserves its actual result pack, timestamp and measured elapsed time. Later inspection checks semantic outputs and bindings with the native checker while retaining the original supplied timing metadata. It never replaces old measurements with a fresh replay clock. Recovered records cannot prove the original runtime or author. The CLI saves exclusively and refuses overwrites. Inspect displays identity, cycle/checkpoint counts and explicit authority/qualification/settlement status.

The complete continuity file is bounded to **2 MB and eight new Alpha checkpoints**. This can be narrower than either native input format. At capacity it rejects the operation, retaining the old file; it never truncates rows or prunes history. Inputs, source checkouts and output paths are explicit. No wallet, provider, model service or host privilege is used. USDC proposals stay unfunded Manager proposals. Alpha allowances and $AGIALPHA are not converted into USDC.

Implemented: receiver validation, retained prior rejection and complete Manager history, explicit fresh cycle, English/French native task and actual local execution. The separate current guided workspace adds hosted file handoffs, the native Jobs receiver and Fleet local execution/internal-check history. Frozen candidate/incumbent/alternative manifests, protected evaluation, eligible independent review and separately authorized production commissioning remain open. This adapter does not complete the four-repository flagship or certify training, operational permission, funding or a deployment.

## Français

Cet adaptateur conserve un seul fichier d'historique contenant le dossier Alpha original, toutes les étapes Manager et chaque nouvelle étape Alpha. Les validateurs natifs des deux dépôts sont réellement exécutés depuis les sources explicitement choisies. Les examens, coûts, dates et mesures importés restent des déclarations historiques non authentifiées. Aucune autorité, revue indépendante, conversion monétaire ou évaluation protégée n'est créée.

Choisissez explicitement le nouveau CSV public, synthétique ou sous licence non personnelle, ses unités entières, ses droits et de nouveaux identifiants de mission et de cycle. Utilisez `language: "fr"` dans la prochaine mission. L'importation prépare un brouillon; `run` exécute séparément la tâche locale. L'ancien rejet reste visible et n'est pas transféré comme approbation du nouveau cycle. Les fichiers existants ne sont jamais remplacés. La limite est de 2 Mo et huit étapes Alpha; les données ne sont jamais tronquées.

Le parcours guidé actuel ajoute les transferts de fichiers dans l’interface hébergée, le lecteur Jobs et l’historique local Fleet. Le présent CLI conserve son lecteur Manager historique épinglé. L’évaluation protégée, la revue indépendante admissible et la mise en service restent à qualifier.

Les fichiers réellement chargés sont vérifiés contre Git, même si des
indicateurs d’index masquent une modification. Le cycle original garde ses
sources Alpha `7c410d3...`; le nouveau cycle utilise le manifeste `611a1ae...`
après vérification exacte de ses 90 fichiers. Le manifeste historique
`ccad46c...` et ses reçus sont conservés sans modification. Le changement du manifeste est
consigné sans réécrire la provenance ancienne. L’ancien reçu de 40 tests reste
un point de contrôle historique; le reçu de correction est distinct.
