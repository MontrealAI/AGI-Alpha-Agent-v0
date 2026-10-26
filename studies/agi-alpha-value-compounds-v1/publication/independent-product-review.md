# Independent development product review

**Review date:** 26 October 2026. **Scope:** the exposed development outputs in `results/development/workbench-retained-v2`, `results/development/workbench-conventional-v2`, and the historical integration example. No confirmation source or result was inspected for this review. Frozen code and original outputs were not modified.

**Reviewer relationship:** this is a separate review within the same research session, by the author of the conventional comparator, independent argument-binding evaluator, and historical integration reproduction. It is independent of the retained method's implementation, but is not a blinded external customer study, an unaffiliated audit, or independent re-execution of the reviewer's own integration experiment.

## Decision

The bundle contains a useful, concrete historical dependency decision: the proposed HTTPX update breaks the specified Starlette TestClient, and the known upstream Starlette change restores the exact minimal consumer outcome. Both methods locate the same relevant consumer call. That is useful diagnostic evidence a maintainer can act on.

The **generic generated HTML packet is an assessment aid**, not yet a complete, self-contained upgrade decision service. It locates the suspicious call and gives source-bound argument-binding evidence, but requires the reader to find the separate runtime experiment and known remedy manually. The polished historical demonstration should link those artifacts and explain their relationship. That editorial/integration work must be charged and identified separately from frozen automatic output.

The engineering result does not establish paid demand, measured human time saved, a customer price advantage, or investment repayment. The strong conventional arm reaches the same consumer finding; the historical example therefore supplies no method-superiority evidence.

## What a maintainer can establish

| Need | Observed delivery | Assessment |
| --- | --- | --- |
| Locate the relevant consumer call | Both packets identify `data/development/starlette/0.36.3/starlette/testclient.py:429`, display the `super().__init__(app=self.app, ...)` call, and retain its exact source hash. | Yes. The snippet is concrete and useful. A clickable source reference would improve navigation. |
| Understand why the update is suspect | Both packets retain HTTPX `Client.__init__` before/after argument metadata, a before-valid/after-invalid shape, and the consumer call shape. | Yes for a technically competent reader of the JSON; the HTML does not connect the removed `app` argument to the failing call in plain language. |
| Distinguish possible from observed impact | Static consumer result is explicitly a syntactic candidate whose runtime dispatch is unproved. Separate pinned runtime results reproduce the actual `TypeError`. | Correctly separated. Publication must connect them without retroactively converting all static candidates into runtime proof. |
| Choose an actionable next step | Generic packet says to review an upgrade/pin decision and run integration checks. Separate README identifies the historical working pins and known upstream remedy; the exact requirements diff is retained. | Complete only when the reader combines the artifacts. The generic HTML alone omits the specific historical next action. |
| Reproduce the accepted consumer outcome | Offline runner, eleven hash-locked wheels, three exact dependency configurations, minimal probe, output/error records and timings are present. | Yes for this declared local scenario, subject to the preserved execution-environment limitation. |
| Know what remains unassessed | Full JSON has declaration exclusions, unresolved consumer inventory, native refusals, assumptions and resource unknowns. | Substantial evidence exists, but the short HTML omits the most useful coverage denominators. |
| Download and inspect evidence | Files exist, and referenced full-evidence hashes match their contents. Both generated HTML documents contain zero hyperlinks. | Companion is inspectable manually; the HTML does not itself meet the requested downloadable, navigable experience. |
| Work entirely in French | French headings and some summaries are translated; the main action, candidate qualification and all three limitations remain English. | Incomplete localization. Publication overlay needs complete French prose. |

Evidence: each arm's `upgrade-packet.json`, `report-en.html`, `report-fr.html`, `resource-receipt.json`, `source-identities.json`, and referenced full-evidence JSON; `data/development/integration-example/README.md`; `results/development/integration-example/run-02/summary.json`. Review observations and input hashes are retained in [`independent-product-review.json`](independent-product-review.json).

## Method parity and interpretation

The retained and conventional development packets both report 16 changed modules, eight unchanged modules, 31 declarations with a lost accepted call shape, 66 without a lost shape, one added declaration, and five unresolved declarations. The consumer result is identical: one syntactic loss candidate and seven syntactic preserved-binding candidates. All 16 changed-module reports are marked accepted by the independent argument-binding validation. These counts describe one exposed historical development assessment, not 31 independently recurring defects, 16 customer missions, or eight further delivered jobs.

The conventional full evidence also preserves **52 Griffe alerts**. Those alerts include broader API considerations outside the narrow call-shape endpoint; they must not be discarded as false positives solely because they differ from the selected endpoint. The two arm-specific evidence files are approximately 16.17 MB and 17.28 MB, respectively. A short front page with direct evidence downloads is appropriate; a reader should not need to search those large payloads for the primary action.

The consumer census covers 57 files and 10,350 call nodes. It conservatively reports zero runtime-proven dependency resolutions. Triage identifies ten declared dependency import references, 2,783 other-import references, and 7,557 unattributed calls. The eight syntactic candidates are a separately qualified subset. These totals must not be presented as complete application coverage, as 10,350 dependency calls, or as a demonstrated recall percentage. Likewise, static top-level non-underscore names can occur inside internal modules; the 31 declaration losses are not automatically 31 supported public API regressions.

Across the 32 native before/after inventory slots, there are 15 accepted scoped inventories, 16 native-policy refusals, and one absent source. The new local compatibility result does not turn these refusals into native admission. The generic HTML correctly states that boundary, but giving the actual refusal/unknown totals would help the maintainer interpret coverage.

The single observed development runtimes are 11.506 seconds for retained and 12.704 seconds for conventional, including the pipeline represented in each receipt. They are not a replicated causal speed result or a monetary saving. Both report zero runtime model calls, which says nothing about unpriced construction inference. The `inspection.json` spec includes `reviewMinutes: 1`; this is a template/configuration field, **not an observed human review duration** and must not become a charged wage input or assumed customer time saving.

## Historical whole-outcome evidence

The actual local probe returns these results:

| Declared versions | Actual result |
| --- | --- |
| Starlette 0.36.3 / HTTPX 0.27.2 | TestClient constructed, lifespan context completed, in-process `GET /` returned HTTP 200 and the exact expected JSON. The `app` deprecation warning was retained. |
| Starlette 0.36.3 / HTTPX 0.28.1 | TestClient construction failed with `TypeError: Client.__init__() got an unexpected keyword argument 'app'`. Exit code 1 and the original traceback identify `starlette/testclient.py:429`. |
| Starlette 0.37.2 / HTTPX 0.28.1 | The known upstream remedy restored the same TestClient lifecycle and exact HTTP 200/JSON outcome. |

All three environments report the exact nine declared dependency versions, successful dependency checks, and zero attempted network operations. The result is one historical incident exercised in three configurations, with two completed in-process HTTP requests. The public incident concerned HTTPX 0.28.0; this reproduction uses the predeclared 0.28.1 patch release. Publication must retain that distinction.

This supports a narrowly useful action: reject the tested historical failing combination, then assess the known Starlette remedy with the project's own integration checks. It does not recommend these old versions as a current production dependency set. The upstream fix was already known and selected by the researchers. No autonomous repair invention is shown.

The successful replay's 6.039 wall seconds and 5.888 child CPU seconds include fresh local venv creation, offline installation, dependency checks and the probes. They exclude acquisition, research, development, prior failures and some diagnostic work. `resource-accounting.json` explicitly retains those exclusions and unknowns. The default-sandbox timeout and missing initial timeout output remain recorded; the later ordinary authorized local execution completed with the same network-denial hook and stripped test environment. Do not generalize this to reliable operation in all environments or to approved-operator execution.

Official historical evidence is linked in `source-evidence.json`: [Starlette discussion 2770](https://github.com/Kludex/starlette/discussions/2770), [HTTPX 0.28.0 release](https://github.com/encode/httpx/releases/tag/0.28.0), and [Starlette 0.37.2 release notes](https://www.starlette.io/release-notes/#0372-march-5-2024). The public reporter is not an AGI ALPHA customer.

## Publication-layer requirements

These additions can be made in a separate demonstration overlay without changing the frozen engine, evaluation method or historical raw outputs:

1. Lead with the actual failing and restored historical consumer outcome, exact versions, and a one-sentence explanation of `app` forwarding. Place 31 upstream declaration changes below the relevant consumer result.
2. Link the consumer source and precise line, both upstream source revisions, the minimal test, original traceback, runtime summary, exact requirements, known-remedy diff and full arm-specific evidence. Provide a portable offline replay command and downloadable files.
3. Explicitly label the static finding, the separate runtime reproduction, and the known upstream remedy. Say that the overlay connects existing evidence through researcher/editorial work; do not claim the frozen packet automatically executed or selected the remedy.
4. Display coverage limits close to the result: qualified candidate, eight static candidates, unresolved calls, restricted callable scope, and preserved native refusals. Explain that passing a binding check is not passing an application test.
5. Present the conventional arm's equal consumer finding and retained broader Griffe alerts. Do not imply that this useful result requires an algorithmic breakthrough.
6. Provide complete French action and limitations, and use readable call examples or labels instead of making raw JSON the only explanation of a witness. API names and machine keys may remain unchanged.
7. Keep exact money costs and customer price explicitly unknown. Link the complete resource record and preserved failed attempts; do not display a tiny execution time as the service's complete cost or claim a fabricated payback.

Two small source-document issues should also be recorded rather than hidden: the integration README still calls `known-remedy-review.patch` an "illustrative two-line" patch, whereas the actual current patch is the exact unified diff between the two hash-locked requirements files; and the French sentence "le client de test construit" should read "le client de test est instancié". No existing file was rewritten during this review.

## Suggested French decision copy

> **Le changement de dépendance proposé casse le client de test utilisé par ce projet.** Avec Starlette 0.36.3 et HTTPX 0.27.2, le client est instancié et renvoie la réponse attendue. Avec HTTPX 0.28.1, la même instanciation échoue parce que l'argument `app` n'est plus accepté. Le correctif amont connu, Starlette 0.37.2 avec HTTPX 0.28.1, rétablit la réponse HTTP 200 et le contenu JSON attendu dans notre essai minimal. Examinez le correctif et relancez les tests d'intégration de votre projet avant de décider de la mise à jour.

For the generic static result, use "Appel signalé par l'analyse statique — comportement à l'exécution non vérifié" instead of the untranslated "candidate / runtime unproved". Translate the action as "Examinez les changements d'arguments acceptés et les appels potentiellement touchés. Exécutez les tests d'intégration du projet avant de choisir une mise à jour ou de conserver une version précise." Use "Encaissements clients réels" for actual customer receipts. Keep the historical runtime proof separate from the generic static qualification.

## Value and residual work

The supported nonprice value is a traceable connection from a dependency change to a specific consumer call, an inspectable counterexample, a reproduced failure, and a reproduced known alternative. That can support a real maintainer decision. It is stronger than an isolated checksum timing result and more concrete than a package-wide list of changed symbols.

The remaining commercial question is substantial: intake must capture the customer's actual dependency graph and constraints; uncertain dispatch and behavior need targeted tests; the customer still owns application acceptance and responsibility for rollout. This one example does not measure the cost of that residual work, willingness to pay, demand frequency, or a human baseline duration. A free conventional tool plus competent maintenance work remains a strong alternative. The appropriate supported claim is an executable, bounded assessment offering demonstrated on an exposed historical need, with comparable conventional capability and economics still unresolved.
