[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed and Ascension: first use and release integration

[First-use and full-cycle guide](ASCENSION_CYCLE.md) ·
[Nova-Seed recovery guide](NOVA_SEED_STUDIO.md) ·
[Native executor guide](SUCCESSOR_ASCENSION.md) ·
[Acceptance and remaining work](ASCENSION_CYCLE_HANDOFF.md)

## First use: English { #first-use-english }

Start with one small project whose inputs and success criteria you can explain. You can prepare and
recover it locally before choosing a wallet or paid service.

1. **Open [Studio](../ascension/mainnet/index.html).** Describe the work and review the committed jobs,
   amounts and deadlines. Preparing a project does not mint an NFT or send a transaction.
2. **Save before continuing.** Encrypt the exact package, check that it reopens and download recovery.
   Keep the capsule passphrase separately. The readable kit exposes its plan; use the private project
   export when you need an encrypted copy of the extended history.
3. **Choose your next step.** You can keep the local project now. Publishing artifacts needs your own
   supported storage access. A funded cycle also needs a qualified deployment and the actual role
   holders; archived Mainnet restrictions remain enforced.
4. **Use the local executor when ready.** Follow [installation](START_HERE.md), then open the installed
   console using `alpha-agent --home ./agent-state serve`. Its Studio desk is
   `http://127.0.0.1:8765/ascension-studio`. The administrator first provisions trusted identities and
   role credentials. Use its setup, pairing, controller approval and execution forms.
5. **Inspect the result and decisions.** Return the exact signed files to the project. Execution,
   acceptance, payment and adoption are separate statuses. Keep failed findings and uncertain outcomes.
6. **Continue deliberately.** Review the source artifact's reuse rights, freeze the comparison and make
   a distinct next mission with fresh inputs and permissions. Save updated recovery after each milestone.

Keep API and role-approval tokens on the local machine; never enter them into the hosted Studio or
include them in project exports. Never use a wallet recovery phrase as a capsule passphrase. If a
transaction is uncertain, reconcile its original intent before another attempt. Recovery preserves
history and does not grant new execution, review, adoption or spending authority.

For the detailed workflow, use the [complete-cycle guide](ASCENSION_CYCLE.md). Use the
[Nova-Seed guide](NOVA_SEED_STUDIO.md) for wallet/publication recovery and the
[native adapter guide](SUCCESSOR_ASCENSION.md) for the operator's exact handoff.

## Première utilisation : français { #premiere-utilisation-francais }

Choisissez d'abord un petit projet dont vous comprenez les données et les critères de réussite.
La préparation et la récupération locales ne demandent ni portefeuille ni service payant.

1. **Ouvrez le [Studio](../ascension/mainnet/index.html).** Décrivez le travail, puis vérifiez les tâches,
   les montants et les échéances. Cette préparation ne crée pas de NFT et n'envoie pas de transaction.
2. **Sauvegardez le projet.** Chiffrez le paquet exact, vérifiez sa réouverture et téléchargez la
   sauvegarde. Gardez le mot de passe séparément. Le kit lisible contient le plan en clair; l'export
   privé chiffre l'historique étendu.
3. **Choisissez la suite.** Vous pouvez conserver le projet local. La publication nécessite votre
   propre accès au stockage. Un cycle financé nécessite aussi un déploiement qualifié et les véritables
   responsables de chaque rôle. Les restrictions du déploiement Mainnet archivé restent appliquées.
4. **Préparez l'exécution locale.** Suivez le [guide d'installation](START_HERE.md), puis les formulaires
   de la console locale. L'administrateur prépare d'abord les identités et les autorisations. La
   signature du contrôleur et le démarrage du travail sont deux confirmations distinctes.
5. **Examinez les preuves.** Importez les fichiers signés d'origine et distinguez l'exécution, la revue,
   le règlement et le choix d'une meilleure méthode. Conservez aussi les résultats négatifs.
6. **Commencez une nouvelle mission explicitement.** Vérifiez les droits de réutilisation, fixez les
   critères de comparaison et utilisez de nouvelles données et autorisations. Mettez la sauvegarde à jour.

Gardez les jetons de la console et des rôles sur la machine locale. Ne les saisissez pas dans le Studio
hébergé et n'utilisez jamais la phrase de récupération de votre portefeuille. Une restauration ne
réactive pas les autorisations. Une transaction incertaine doit être vérifiée avant une nouvelle tentative.

## Release scope and verification

Version **1.31.0** integrates the four-PR stack. [Release notes](RELEASE_NOTES_1.31.0.md) describe its scope and the
[readiness record](RELEASE_READINESS.md) separates integration checks from actual publication.
At the start of this integration, #4780 and #4781 had been merged into the Nova-Seed feature branch;
that was not yet a merge of #4779 into `main`. #4782 then needed reconciliation with that updated branch.
Final combined-source checks, main merge, release/tag identity and public-site acceptance must use the
actual resulting commit. Historical workflow successes remain evidence for their recorded snapshots.

## Historical stack and integration requirements

The following records the earlier inspected implementation snapshot from **October 14, 2026**. These
are historical submitted source identities, not the new integrated release identity. Subsequent fixes
and merge resolutions need fresh evidence.

| PR | Purpose | Submitted source | Base branch at inspection |
| --- | --- | --- | --- |
| #4779 | Recoverable Nova-Seed Studio | `89b6f78b83a6643416649173d7d16b6d1c7a65c1` | `main` |
| #4780 | Authorized native execution | `98ef5a5d510b81048ed32cad06e132d30b166e8f` | Nova-Seed feature branch |
| #4781 | Recovery and release-evidence hardening | `94c48703c8e86597eda54f28a65bc45be5d4a8bb` | Nova-Seed feature branch |
| #4782 | Linked execution, settlement and successor cycles | `c42121a4471ab205d8ad84b0e74c2a8c76616e31` | Native-cycle feature branch |

Preserve both lines of work: #4779 → #4780 → #4782 and #4779 → #4781. In particular, the
hardening and cycle branches both edit Nova browser, recovery, evidence and test files.
Do not select an entire side of a merge merely to remove conflicts. Reconcile the behavior
and retain both sets of assertions. A feature-branch merge is not a merge into `main`.

## Preserve the full regression and publication gates

At the inspected cycle head, the passing workflow was **MARK wallet acceptance**. The
`agent-release.yml` push allowlist did not include the native-cycle or inspectable-cycle
branches. A passing wallet workflow therefore did not establish a complete repository pass.

The additive **Ascension stack regression** workflow covers pushes to those two missing
branches when the workflow is present on the source revision. It also supports explicit
manual runs. It does not run a second copy on every pull-request event. The existing Nova
release workflow and all normal main-branch acceptance and publication gates remain in place.

The 1.31.0 integration also adds the inspectable-cycle branch to **Agent release acceptance** itself,
so that branch can run the full candidate acceptance path before merging. This configuration change is
not a recorded CI result. Publication still requires the resulting integrated `main` commit and its
matching package and public-site evidence.

The added check uses the same locked development setup, full offline regression, unchanged
80% coverage floor, strict type scopes and preservation commands as the existing release
regression job. Checkout is pinned to the triggering SHA, credentials are not persisted,
and the commit, tree and run identifiers are retained before dependency installation.
Reports upload even after a failure. The workflow has only `contents: read`; it cannot merge,
create a release, deploy Pages, sign a wallet transaction or authorize a provider.

The five tests in `tests/test_ascension_stack_ci.py` check trigger coverage, exact-source and
read-only execution, the full-suite/coverage boundary, type/preservation checks and retained
failure evidence. Those configuration tests are not a substitute for running the repository.

**After any code, dependency, generated-asset or merge-resolution change, qualify the new
commit.** Previous successful runs and their artifacts remain historical evidence; they do
not automatically qualify the changed tree. Inspect failure logs rather than converting
failed whole-suite runs into passes by adding together selected retries.

## Final publication checklist

Keep final integration blocked until the combined exact source has resolved review findings
and the required acceptance results. Preserve the independent-review requirements recorded
in the engineering handoffs. The added regression check is not an external security audit.

Use the existing full release workflow for the combined candidate and integrated `main`.
Require its preservation, browser, contract, platform, regression, type, packaging and public
site checks. Reserve an unused version, keep existing tags/assets immutable, and verify that
the tag, package manifest, checksums, tested source and published routes agree. Do not mistake
a successful candidate package, source-version label or deployed page for a published release.

Keep the [80-case acceptance index](ascension-cycle-acceptance.json) and the
[operational handoff](ASCENSION_CYCLE_HANDOFF.md) truthful. Their submitted decisions include
partial and blocked requirements. Actual storage-account trials, physical wallets, independent
real actors, live paid providers and a separately authorized Mainnet canary are not supplied
by this CI correction. New funding or other public exposure remains subject to its existing
qualification and explicit authorization requirements.

## Français : limites de la publication

Les quatre PR forment un ensemble à intégrer et à vérifier. Les contrôles de régression ne fusionnent
pas le code et n'autorisent aucune transaction. Le manifeste, les sommes de contrôle et les résultats
liés au commit publié identifient la livraison réelle. Une publication logicielle ne remplace ni la
revue indépendante, ni les essais de portefeuilles physiques, ni la qualification opérationnelle Mainnet.
