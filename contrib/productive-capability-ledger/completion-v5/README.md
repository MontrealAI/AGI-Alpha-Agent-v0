# Independent CSV acceptance repair

PR #4899 finding 4372481324 identified a genuine independent-verifier defect.
On the preserved completion-v4 delivery, changing a `differences.csv` source hash
and recomputing the packaging and completion hashes still passed the exact e250
verifier with 353 checks. The original delivery is unchanged. The
[reproduction](csv-integrity-reproduction.json) records that accepted corruption;
[the original verifier](pre-repair-verifier.txt) retains the actual pre-fix source.

The corrected Python verifier reconstructs every difference field from the two
independently checked source inventories: exact path/hash values, difference and
occurrence IDs, original data-row numbers and action IDs. It independently
reconstructs complete action objects, row references, conflict fields and follow-up
text. It compares both downloadable CSV byte streams and the embedded action CSV
against these reconstructions, including the existing CSV formula protection.
JSON evidence comparison retains type distinctions. It imports no comparison
JavaScript. This strengthens the existing exact source-delivery acceptance; it
changes no runner, budget, permission, source profile or old evidence.

Run the focused regression from the repository root:

```sh
python contrib/productive-capability-ledger/automation-v1/test_csv_integrity.py
```

The regression reads the retained public Git source at
`443246db37b30b83f4b9c8a854ceb226601e0155`, which must already exist locally. It
never fetches source during verification. Five unittest groups check the original
valid deliverable, all ten difference-export fields, all seven action-export
fields, four forged result-evidence references and the embedded action CSV.
They exercise 23 cases on copied evidence, not 23 customer jobs. The unchanged
original passes 351 grouped checks in the corrected verifier; changed check
count is not a weaker acceptance threshold. Every corrupt variant refuses.

Local validation uses Python 3.12.14, Node 24.22.1 and the already available
Python packages (`scripts/check_python_deps.py` passed). Black check, Ruff and
strict standalone mypy pass on the two changed Python files. Full locked
installation, full hooks, final exact-source hosted checks, eligible Code Review
and Security disposition are separate requirements. This repair establishes no
approved-operator execution, commercial acceptance or economic improvement.

## Français

La correction empêche qu'un CSV faux soit accepté après le recalcul de ses
empreintes. Le vérificateur reconstruit chaque valeur, référence de ligne et
association d'action à partir des inventaires contrôlés, puis compare les CSV
complets. Les cinq groupes de régression comprennent 23 cas sur des copies du
même dossier; ce ne sont pas de nouveaux travaux clients. L'ancien résultat et
sa preuve de défaillance sont conservés. Aucune permission, limite de ressources
ou qualification d'exploitation n'est modifiée.

## Current Security source evidence and lock-tool correction

[Source-specific Security evidence](security-source-review-e250.json) covers all
57 original e250 findings with source hashes, code paths, exposure and controls.
It contains operator-authored analysis, not an eligible Security disposition. The
captured E3C25 rule bodies are unavailable here; an actual call through the unchanged
repository registry retrieval returned the different historical DE5 pack. No
current-rule applicability opinion or old clearance is transferred. A changed
source needs its own complete mandatory scan and owner review.

Seven lock-verification tools now enforce their documented local-wheel-cache
boundary: a nonempty WHEELHOUSE must resolve to an existing local directory and
is one absolute argv operand. The fixed compiler invocation has a 600-second
timeout. A URL passed to --find-links could previously contradict the offline
contract even with --no-index. The inert before/after probes launch no resolver
and make no network request. Five unittest methods cover 70 behavioral cases,
including rejection, literal path handling, timeout, return-code propagation and
unchanged byte-equality checks. Locks and scanner policies are unchanged.

These fixes do not promise zero scanner findings. The existing Security
maintainer/process must review the exact current rule definitions and final
source, disposition findings and assign further validated repairs. No scanner
suppression, exception map, permission change or acceptance waiver is introduced.

## Verified existing public journey

The existing public /try/ interface was opened in an ordinary Chromium browser,
completed in English, then inspected in French. Its four-row action plan was
actually downloaded: 832 bytes, SHA256
`af76ece3748df265c3bc2f04837dd768c0869616a68ec74dbcb4e7f0bfde8639`.
This is current public-demo verification, not the pending source candidate,
approved-operator acceptance or a new customer job. The older live interface and
its operating boundaries remain preserved.
