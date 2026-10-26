# Server-crash recovery correction

Review [finding4373063467](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4915#discussion_r4373063467)
identified an uncovered case in the otherwise successful a95 isolated campaign:
SIGKILL of the server leaves its separately launched source Node process alive.
Immediate restart previously charged the final recovery attempt before the
canonical writer lock refused dispatch. The old positive child-SIGKILL/browser
results and the negative new test remain preserved; none is relabeled.

The existing worker now inspects its two exact canonical ownership files before
another attempt is charged. It validates the original approval and ordinary file
identity, and waits while that writer remains alive. It neither signals unrelated
processes nor removes/replaces their locks. The existing journal checks source,
approval, CANCEL/STOP and the original lease throughout this bounded wait. It
never renews the envelope. The generic runtime requires this reviewed ownership
boundary before pure-work recovery; the default planning profile remains fenced.

A real test stops the owned Node child after durable preparation, kills the
**server** with SIGKILL, restarts the application, and verifies that waiting consumes
no attempt. It then resumes that same child. The restarted server admits the
independently checked completed output with two charged attempts and unchanged
original lease. This exposed a second defect: canonical completed-run reconnect
returns no `directory` field. The bridge now locates COMPLETE using the already
validated output root/run ID instead of that absent field.

[The server-crash receipt](server-sigkill-recovery.json),
[54 passing source cases](source-tests.txt),
[85 existing worker/transport cases](planning-tests.txt),
[strict types](types.txt), and [Ruff](ruff.txt) are retained. The
[failed pre-repair test](pre-repair-server-test.txt) is retained too.
The new collector requires the actual server-crash receipt in addition to actual
Chromium, original child-SIGKILL and installed planning evidence; no previous
criterion or scanner is removed. The repaired source requires fresh hosted
qualification and review, separately from these local results.

[Prior hosted evidence](prior-hosted-qualification.json) binds run40248069240,
its exact synthetic merge/tree and the downloaded ZIP digest. That campaign
passed real source Chromium closure while active, subsequent real Node/Git/Python
work, reconnect, ZIP verification and signed history. Its artifact was downloaded
and SHA-256 verified. It does not qualify this changed source. The
[previous complete offering/cost record](../completion-v6/README.md) and all60
custody members have also been read back byte-for-byte through ordinary public
HTTP. No earlier release, publication, negative result or held-source body changed.

**Approved operator NOT RUN. Source adoption NOT APPROVED.** The server-crash
case is an isolated fixture, not an approved installation or an OS service grant.
Final distinct Security disposition and full-source integration qualification
remain required. The configured `@codex security review` request on a95 recorded
ordinary Code Review with `security_review:null`; its clear ordinary receipt did
not clear the separate P1 or establish Security authority. Existing #4899 owns
that process and integration. No policy exception, credential, spending, external
transaction, daemon installation or original held-action retry occurs.

The three constructed methods remain inactive/HOLD. Economics remain the shared
schema with unknown observed full monetary cost and explicitly simulated
sensitivity, not measured savings, customer demand or profitable promotion.
The [prepared operator procedure](../completion-v6/OPERATOR_ACCEPTANCE.md) remains
the minimum owner action after exact profile adoption and review.

## Français

Le nouvel essai tue le serveur tout en conservant son véritable processus Node.
Au redémarrage, l’application attend le rédacteur initial sans consommer une
nouvelle tentative, puis vérifie son résultat dans l’autorisation initiale.
La reprise d’un résultat déjà terminé utilisait aussi un champ absent ; cette
recherche de fichier est corrigée. Les échecs sont conservés, les54 essais source
et85 essais existants réussissent localement. Une nouvelle qualification hébergée
et une revue de sécurité distincte restent nécessaires. L’acceptation opérateur
reste NON EXÉCUTÉE et l’adoption du profil NON APPROUVÉE. Aucun coût complet réel,
revenu, surplus ou progrès autonome rentable n’est déduit de ces essais.
