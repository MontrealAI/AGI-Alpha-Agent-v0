# Source-assurance reviewed corrections

This continues the same #4907 owner line and preserves the complete
[v1](../completion-v1/README.md) and [v2](../completion-v2/README.md) records.
Three actual review findings on the earlier source were reproduced before repair:

| Finding | Repair and regression |
| --- | --- |
| Expiry did not constrain the plan rebuild's reads | The original invocation deadline reaches `makePlan` and installed-source validation; every read checks the same ceiling. The regression uses controlled clocks around actual Git reads. |
| A remaining recovery guard was bypassed if the writer file was absent | Every writer acquisition now holds the same recovery guard. Both interrupted states refuse pending operator inspection. |
| The verifier accepted truncated reservation history | Unique reservations must cover every retained execution/stage and the completing verification. Omitted, duplicated, substituted and coordinately rehashed histories refuse in the separate Python verifier and runner. |

The original reviewer comments, predecessor code snapshots and before-fix failures
are retained. The current code bodies pass **209 local tests**: 177 Node tests,
including 21 source-assurance controls, plus 32 page/source/release-boundary tests.
Ruff, Black and strict mypy pass on the changed Python verifier. These are local
component results; fresh final-source hosted checks and review remain required.
Earlier green checks did not establish the three repaired boundaries.

## Prospective useful request

The [protocol](PROTOCOL.json) and [baseline inventory](previous-published-source.json)
freeze one source-change assurance request before confirmation. Five declared
source identities come from public predecessor `2c5c393c`; the corrected candidate
is expected to differ in the runner, its tests and the independent verifier while
preserving the common cost and mission-ledger implementations. These are intended
version changes, not invented vulnerabilities. The accepted deliverable must
report exactly those differences in complete CSVs, action exports, portable
workspace and report, with separate Python verification.

At this code freeze the new request is NOT RUN. This record does not rewrite the
earlier five local requests or count their rechecks/artifacts as new jobs. Input
acquisition and source publication are separate from the offline execution.

## Exact operating scope and gaps

The existing Git specialist performs the useful comparison. v3 approval fixes
expiry, lifetime invocation count and total conservative execution reservations.
Interrupted attempts and reconnects retain their allowances; STOP pauses, CANCEL
is durable. Missing local source bodies refuse without lazy fetching, object
replacement or inherited Git routing. Git 2.51.1 was tested. No repository/global
configuration, scanner rule, exception map or protected criterion is changed.

Source assurance is still a **local Node offering**. The current installed
strategy executor's closed methods support bounded planning, construction and
planning journeys. It has no source-assurance transport adapter or approved Git
profile; a credential alone cannot make this source route work. That adapter and
profile adoption remain unimplemented/unapproved. The existing planning path is
the eligible connected offering; its exact approved operator home/profile is
unavailable in this session. Neither route is claimed as an actual authenticated
operator mission here. Browser closure, persistent worker/network recovery and
clean approved-profile installation remain NOT RUN for this increment.

Original Harness/Fleet restrictions retain their original task operators and
supported decision controls. Existing #4899 retains runtime/scanner/release
ownership; its exact2645 official scan has56 unapproved findings/exit1 and no
distinct Security clearance. Fresh combined-source qualification cannot inherit
that result or an ordinary Code Review receipt. No new credentials, persistent
access, paid infrastructure, financial action or deployed-contract change occurs.

## Economics and improvement

The canonical `alpha-automated-costs/v1`, nontransactional mission ledger and
USDC/AGIALPHA role map are preserved. Actual full currency cost, attributable
development/upkeep, customer attention, matched human duration, collections and
available surplus remain unknown. Process counters and reservation ceilings are
not money. This is human-authored repair; conventional comparison remains the
incumbent. No autonomous discovery, economic promotion, realized reinvestment or
self-acceleration is established.

## Français

Les trois défauts constatés en revue sont reproduits puis corrigés : échéance
pendant la revalidation, verrou de reprise interrompu et couverture de chaque
tentative par sa réserve. Les résultats antérieurs restent accessibles. Le
nouveau protocole doit vérifier cinq identités et trois changements de version
réels; cette demande est encore NON EXÉCUTÉE à ce gel du code. L’offre Git demeure
locale; son adaptateur connecté et son profil approuvé restent à livrer. Aucun
coût complet, bénéfice commercial ou accroissement autonome n’est présumé.
