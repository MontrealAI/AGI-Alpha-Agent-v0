[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed and Ascension stack: start here for integration and release

[First-use and full-cycle guide](ASCENSION_CYCLE.md) ·
[Nova-Seed recovery guide](NOVA_SEED_STUDIO.md) ·
[Native executor guide](SUCCESSOR_ASCENSION.md) ·
[Acceptance and remaining work](ASCENSION_CYCLE_HANDOFF.md)

## What a user should open

For the complete project journey, start with the **first-use and full-cycle guide** above.
It explains project creation, encrypted recovery, exact work, separately authorized execution,
review, settlement, evaluation and the deliberate next mission. Use the Nova-Seed guide for
wallet and recovery details, and the native executor guide for the local machine.

The hosted Studio and local operator console are different surfaces. The hosted Studio's
`/ascension/mainnet/` path does not certify production readiness. After installing the native
runtime, `alpha-agent --home ./agent-state serve` serves the private operator console at
`http://127.0.0.1:8765/ascension-studio`. Keep its API and role-approval tokens on that machine;
do not enter them into the hosted Studio or put them in recovery exports.

Local preparation needs no wallet or paid provider. New exposure on the October 11 archived
Mainnet deployment remains blocked, and the production replacement-profile registry is empty.
A pending or uncertain transaction must be reconciled, not blindly resubmitted. Restoring a
project does not grant fresh execution, review, adoption or spending authority.

## The four changes are a stack, not four independent releases

The following is the inspected implementation snapshot from **October 14, 2026**. The commit
IDs identify the submitted implementations; subsequent integration fixes need fresh evidence.

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

## Close the missing regression coverage before final integration

At the inspected cycle head, the passing workflow was **MARK wallet acceptance**. The
`agent-release.yml` push allowlist did not include the native-cycle or inspectable-cycle
branches. A passing wallet workflow therefore did not establish a complete repository pass.

The additive **Ascension stack regression** workflow covers pushes to those two missing
branches when the workflow is present on the source revision. It also supports explicit
manual runs. It does not run a second copy on every pull-request event. The existing Nova
release workflow and all normal main-branch acceptance and publication gates remain in place.

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

## Français : par où commencer ?

Commencez par le **guide de première utilisation et du cycle complet** en haut de cette page.
Il relie le projet, la sauvegarde chiffrée, le travail autorisé, les résultats, la revue, le
règlement et le choix explicite de la mission suivante. Le guide Nova-Seed explique les
opérations du portefeuille; le guide de l'exécuteur décrit la machine locale.

Le Studio hébergé n'est pas la console privée de l'opérateur. Gardez les jetons d'accès et
d'approbation sur la machine locale. N'entrez jamais la phrase de récupération de votre
portefeuille dans le Studio. Une restauration ne réactive pas les anciennes autorisations.
Lorsqu'une transaction reste incertaine, vérifiez son résultat avant toute nouvelle tentative.

Les quatre PR forment un ensemble à intégrer et à tester. Le nouveau contrôle de régression
est en lecture seule : il n'effectue ni fusion, ni publication, ni transaction Mainnet.
Un résultat CI positif ne remplace pas une revue indépendante ni la qualification
opérationnelle. Les restrictions du déploiement archivé et les contrôles de récupération
restent inchangés.
