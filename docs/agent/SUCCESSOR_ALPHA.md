# Useful Alpha: a capability worth keeping / un outil utile à conserver

[Research scope](../DISCLAIMER_SNIPPET.md)

**[Open the flagship](../successor/alpha/index.html)** ·
**[Ouvrir en français](../successor/alpha/index.html?lang=fr)** ·
[Implementation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/examples/successor-alpha/)

Start with a useful result: reconcile two catalogs and keep the result and the working tool.
The supplied example uses synthetic data. You can instead select public, synthetic or licensed nonpersonal CSV inputs.
The local browser journey needs no account, installation, model, API key or wallet.

## Your first result

1. Choose **Find my first advantage** to run the supplied catalog example.
2. Inspect the joined catalog, unmatched rows and discrepancies. Check that the selected keys and fields express
   the task you intended.
3. Inspect correctness, operation counts, observed timings and the comparison limits. A strategy can lose;
   that result remains useful evidence.
4. Download the useful files, your project record and the working offline tool. Reopen the saved HTML in a modern
   desktop browser to continue locally. Save a new copy after changes.

Choose **Bring my own catalogs** to paste or select two CSV files. Select each catalog's key; common non-key columns
are compared as exact text. Inspect identifiers and duplicates before relying on the output.
A reconciliation finds the differences expressed by its contract; it does not
establish that either catalog is complete or factually correct.

Keys are exact, case-sensitive, nonempty strings. Whitespace and numeric-looking strings are retained;
`001`, `1` and ` 1` are different keys. Duplicate keys produce every matching left/right pair, rather than
silently deduplicating. The joined catalog contains matching pairs; unmatched rows are exported separately.
Inputs support quoted commas/newlines and a UTF-8 BOM. Each table is bounded to 200,000 UTF-8 bytes,
1,500 data rows, 32 columns and 4,096 characters per cell. Output is capped at 10,000 matching pairs.

CSV downloads prefix formula-like cells with an apostrophe for spreadsheet import. The exact JSON retains
the original strings. Use that JSON when exact original cell values matter.

| File | Use |
| --- | --- |
| `joined.csv` | Every exact matching pair, with left/right column names |
| `unmatched-left.csv`, `unmatched-right.csv` | Input rows with no matching key on the other side |
| `conflicts.csv` | Differences in shared non-key fields for matching pairs |
| `exact-result.json`, `comparison.json` | Original cell strings, task and engineering observations |
| `report.html` | A readable local result and comparison report |
| `project.json` | Retained task history for inspection and continuation |
| `successor-tool.mjs` | The reusable Node tool for another pair of local catalogs |

The browser additionally saves the whole workspace as one self-contained HTML file. This working browser
copy and the standalone Node tool are separate ways to keep the capability.

## What Alpha means here

Alpha is an advantage worth building for a particular mission. A working join and a discrepancy report can be
useful before anyone has measured whether they justify replacing the current workflow. The question is whether
the resulting capability helps its intended user enough to warrant its full costs.

For a different mission, use the opportunity notebook to record the goal, current approach, credible alternative,
measurable target, supplied evidence and budget. Ask what current evidence, expertise and feasible experiments
make achievable now. These records stay typed hypotheses; recording one neither retrieves new sources nor
executes a domain experiment. The catalog capability is the executable first mission.

| Stage | What this flagship provides | What requires further evidence or a separate decision |
| --- | --- | --- |
| Find Alpha | A concrete reconciliation task, usable outputs and explicit alternatives | The user's actual bottleneck, adoption constraints and benefit |
| Develop in a Gym | Execute maintained baselines, construct bounded composite plans and test a different task formulation | Unrestricted code synthesis or scientific certification |
| Examine a frozen candidate | Bound inputs and implementation identity with inspectable local comparisons | Independently administered protected work and a credible external comparator |
| Prepare successor continuity | A portable working tool, project inputs and retained observations | Earned Specialist status, institutional admission and operational authority |

The developmental Gym helps build and inspect capabilities. Specialist qualification requires a frozen candidate
to pass the agreed constraints and outperform Current and the best credible alternative on protected work.
Separate accountable authorization is required before operational use with authority. The local flagship does
not complete those independent steps.

## Read the comparison correctly

The comparison uses the same bounded reconciliation semantics and inputs for each maintained strategy.
The four strategies are a nested scan, hashing the right table, hashing the smaller table and sort/merge.
Hashing the smaller table is an established heuristic; this example does not invent a new join algorithm.
Operation counts describe those implementations. Observed browser timings describe one device and run;
browser optimization, load and measurement order can affect them. A strategy with fewer counted operations can
take longer. Inspect both results and correctness before drawing a conclusion.
The reported indexed-row counts are not measurements of memory consumption.

These are engineering comparisons against the implemented strategies, not a demonstrated advantage over every
spreadsheet, database or existing commercial product. Selecting the fastest observed strategy after seeing the
same workload is development evidence. Fresh protected evaluation under a frozen protocol is a separate stage.

Any user-supplied time, volume, price or cost assumptions are estimates. They do not become measured human time
savings, realized revenue or accepted customer value. Count setup, integration, review, repair, maintenance and
unwind when deciding whether to adopt the capability. Unknown costs and burdens remain unknown.

## Construct a strategy, then test a different question

After the first result, the optional research experiment constructs executable join plans from a finite,
validated grammar. Plans combine key partitioning, conditional small-product scanning, bounded hashing and
an exact uniform-key shortcut. This is composition of known primitives, not unrestricted algorithm invention.
The search executes the constructed plans; it does not merely rename the four initial comparison methods.

Set an explicit auxiliary-row budget and inspect the metered work. Auxiliary rows count retained row references,
not bytes or process memory. The comparison includes competitive bounded block-hash alternatives as well as
the original approaches. Infeasible alternatives are identified. Construction, checking and validation have
costs of their own; the work metric is an inspectable proxy rather than an adoption or economic measurement.

The candidate is frozen before a fresh local synthetic check. Its inputs and generator remain inspectable and
under local control, so this check is **not protected evaluation**. If a candidate does not establish the declared
improvement, the incumbent remains. Save the research record to retain its plan, source identity, comparisons
and rejection or improvement evidence. An included duplicate-heavy example makes the shortcut's narrow scope
concrete; it does not establish improvement on arbitrary catalogs.

The executable reframing asks a different question: **which product keys need a corrective decision?** It groups
unmatched occurrences and conflicting pairs into a per-key action queue, preserving references to every original
exception. A coverage check verifies those references against the original reconciliation. Compare the number of
exceptions with the number of grouped actions, and download the queue. Grouping changes the output contract;
it neither repairs the source catalogs nor measures human review time. It can reduce repeated decisions when
several occurrences concern the same key, and can correctly show no reduction.

These are bounded working examples of strategy construction and task reframing. A general ability to discover
better scientific methods or fundamentally new business opportunities requires its own environment and evidence.
The retained [synthetic research example](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/examples/successor-alpha/research-evidence.json) contains an exact
mission, frozen plan, fresh confirmation and all 131 exception references grouped into two proposed actions.
This is a deliberately constructed local example, with a changed review contract and no human time-saving claim.

## Continue through the native workbench

The catalog adapter uses the existing SUCCESSOR workbench runtime and native Jobs compiler. It binds the exact
catalog project and cycle to the work specification, executes the installed adapter locally, and independently
rechecks the returned catalog outputs before accepting a continuity record. The record retains the original
project identity and historical cycles. The learning archive and offline workspace preserve the associated
research, action queue and native return evidence.

This is an unfunded native workbench path. Existing Manager/Fleet project receivers do not install this catalog
executor; a native workbench result is not a completed Fleet execution or paid settlement. Separate USDC and
AGIALPHA work briefs remain available with their own readiness boundaries. See the
[native continuity guide](SUCCESSOR_ALPHA_CONTINUITY.md) for the supported formats and exact limits.

## Keep and continue your work

The downloadable project retains the task, inputs and observations. Imported historical observations are
unverified history; rerunning produces new local evidence. A saved file or checksum establishes neither
independent trust nor current permission. Keep the exported files before clearing browser data.
Project and learning imports are bounded to 2 MB, including retained evidence. A full archive is refused rather
than silently pruned; keep the existing downloads before beginning another separate project.

The retained tool preserves the mission and its working method as material for an eventual authorized SUCCESSOR Ω.
Saving it does not establish that status. It does not require a particular model provider.
A future implementation can replace models or methods while retaining permitted evidence, skills and operating
memory. A changed capability needs fresh applicable proof and a separate authorization; predecessor proof or
authority does not transfer automatically.

The broader [guided project journey](GUIDED_SUCCESSOR_JOURNEY.md) and [five-family workbench](SUCCESSOR_WORK.md)
remain available. Their native formats and execution boundaries are unchanged. A flagship project export is
not automatically a Jobs/Manager/Fleet execution request or native backup. USDC and $AGIALPHA commissioning
retain their separate configuration, budgets, acceptance and settlement requirements.

## Premier résultat en français

Ouvrez le parcours français, puis lancez l'exemple synthétique. Examinez le catalogue rapproché, les lignes sans
correspondance et les différences. Pour utiliser vos propres catalogues autorisés, sélectionnez deux fichiers CSV
et leurs clés; les champs communs sont comparés comme du texte exact. Téléchargez les résultats, le projet et
l'outil autonome pour les conserver.

Après ce premier résultat, construisez et testez une stratégie dans la grammaire proposée, ou exécutez le
regroupement des divergences en décisions par clé. La candidate reste soumise au budget déclaré et aux
alternatives implémentées. Une absence d'amélioration conserve la méthode actuelle. Le contrôle synthétique
nouveau reste public et local, et le regroupement change le contrat de sortie. L'archive d'apprentissage
conserve ces éléments avec le même projet. Le relais natif utilise le workbench et le compilateur Jobs;
il reste non financé et n'installe pas un exécuteur de catalogues dans Manager ou Fleet.

Les comparaisons locales décrivent les méthodes exécutées et les mesures de votre appareil. Les hypothèses
économiques restent des estimations; elles ne prouvent ni économies réalisées ni valeur client acceptée.
Le Gym sert au développement. Une qualification Specialist exige une évaluation protégée indépendante du
candidat figé contre la méthode actuelle et la meilleure alternative crédible. L'autorisation opérationnelle
reste une décision distincte. Conserver l'outil et son historique ne transfère aucune permission.

## Development and verification

With Node 22.17.1 or later, run the example from the repository root:

```sh
node examples/successor-alpha/cli.mjs --example --out alpha-example
```

To use your own permitted local catalogs, explicitly choose both key columns:

```sh
node examples/successor-alpha/cli.mjs --left left.csv --right right.csv --left-key id --right-key id --out alpha-result
```

Run the focused engine checks with:

```sh
node --test examples/successor-alpha/*.test.mjs
```

Keep the output directory and inspect its artifacts before integrating the result. The CLI runs the same
maintained reconciliation engine without a provider or blockchain request. It does not produce an independent
qualification or a production grant.

Run the exported Node tool from any directory with another pair of permitted inputs:

```sh
node successor-tool.mjs left.csv right.csv id id new-result
```

The tool reruns all four maintained methods and exact checks. It writes new artifacts; it does not reuse
historical timings as proof of the new run.

The separate **retained plan** download exports the strategy selected by the optional research experiment.
Import it as an ESM module to apply that exact plan to fresh CSV strings:

```javascript
import { reconcileCatalogs } from './successor-retained-plan.mjs';

const result = reconcileCatalogs({ leftCsv, rightCsv, leftKey: 'id', rightKey: 'id' });
console.log(result.joinedCsv, result.conflictsCsv);
```

It rechecks exact output and the declared resource budget on the new inputs. It refuses inputs the retained
plan cannot process within that budget. The module performs no file, network or wallet operations; its caller
decides how to read and save data. A held experiment exports the incumbent rather than the rejected candidate.

The maintained implementation is in [`examples/successor-alpha/`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/examples/successor-alpha/).
Its generated browser entrypoint is [`docs/successor/alpha/index.html`](../successor/alpha/index.html).
Keep source changes, the generated page and its source manifest together; do not edit bundled JavaScript
inside the generated HTML. Follow the example's reproduction instructions and run its focused checks,
browser/accessibility checks and the repository's required exact-source checks before publication.

Source availability, a local passing check and a published Pages deployment are separate facts. The route
becomes public only after the relevant source has passed its required checks and Pages has deployed it.

## Supplied visual reference

The flagship uses the owner-supplied purple and gold institution illustration, encoded as WebP for delivery.
`examples/successor-alpha/artwork.json` records source and delivered-byte identities. The binary gate admits
only this exact asset hash; the general restriction is preserved.
