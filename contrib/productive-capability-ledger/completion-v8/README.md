# Terminal cancellation after server loss

Review [4373112515](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4915#discussion_r4373112515)
found that cancelling during orphan-writer monitoring could leave a running
journal record and block subsequent approved work. The new test was run against
an isolated copy of exact dc770ee: ordinary server recovery passed, while CANCEL
and STOP cases failed. [That adverse result is retained](before-control-repair.txt).
No held native/browser test, operator session or deployed service was used.

The existing source worker now writes and fsyncs the canonical specialist's
CANCEL marker inside its already-bound run directory. This also reaches a source
child that outlives its server. The journal continues bounded ownership monitoring
without dispatching or consuming another attempt. Once the original writer exits,
it commits terminal cancellation, retains the complete original reservation and
admits no result for that cancelled mission. A separately prepared and approved
next mission can then execute normally. Permanent global STOP propagates the same
source marker and remains permanent; it never becomes a new grant or refund.
Default planning behavior and fixed profiles remain unchanged apart from the
explicitly rebound shared source identity.

The real server-SIGKILL tests now cover resume, CANCEL and permanent STOP. They
verify actual source-child control, original lease, retained reservation, no extra
attempt while monitoring and the next separately approved mission after CANCEL.
The cancellation fixture's two requests are internal regression work, not customer
jobs, demand, revenue or improvement evidence.

[56 source cases](source-tests.txt), [85 existing worker/transport cases](planning-tests.txt),
[strict types](types.txt) and [Ruff](ruff.txt) pass locally. The existing hosted
collector now requires all three server-crash receipts, in addition to real
Chromium/tab closure, original child-crash, clean install, dependency audit and
wheel reproducibility. No previous gate, scanner, rule or adverse record is removed.
The repaired source still needs its own hosted result and review.

Earlier [completion-v6](../completion-v6/README.md) offering/accounting and
[completion-v7](../completion-v7/README.md) ownership repair remain preserved.
Source dc770ee passed hosted202 JUnit cases with no failures/errors/skips; its
actual Chromium156 mission continued after tab closure. Downloaded artifact12619679117
was3951623bytes, SHA256545bcba09fb07b05edb3d5d9ec8c88792f3a94709a876a427077ca199871bf04.
That prior green result does not qualify this changed commit.

**Operator NOT RUN; source adoption NOT APPROVED; distinct Security authority
unestablished; no merge/release/live increment.** The existing #4899 owner retains
integration and Security disposition. This patch grants no credential, persistent
access, spending, exception, financial transaction or original held-action retry.
All three constructed methods remain inactive/HOLD. Actual full monetary costs,
customer price/effort, collections and surplus remain unknown; cost scenarios are
explicitly simulated and use the unchanged shared calculator.

## Français

Après la perte du serveur, ANNULER atteint maintenant le processus source restant.
L’application attend sa sortie sans nouvelle tentative, conserve la réservation,
termine l’annulation puis peut exécuter une autre mission séparément approuvée.
ARRÊT permanent transmet aussi le contrôle et ne se renouvelle pas. Les56 essais
source et85 essais existants réussissent localement ; les échecs de l’ancienne
version sont conservés. Une nouvelle qualification hébergée, la revue finale et
l’adoption par le responsable restent distinctes. L’acceptation opérateur reste
NON EXÉCUTÉE et aucun revenu, surplus ou avantage économique observé n’est déduit.
