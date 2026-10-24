[Project notice](../DISCLAIMER_SNIPPET.md)

# Alpha Agent 1.41.1 — immutable workbench submissions

A submitted workbench mission now captures its nested JSON inputs before planning,
identity, lifecycle registration, persistence and execution. A caller changing the original
object after submission cannot change the captured mission or its worker result.

Two deterministic regressions reproduce mutations at the planning and run boundaries,
checking the persisted request/digest, actual result and duplicate-submission behavior.
The same maintained runtime, journal, attempt budget, worker and commands remain in use.
No second scheduler, executor, service or authority mechanism is introduced.

Start with the [installation and first-run guide](START_HERE.md), then inspect the
[workbench operations](SUCCESSOR_WORK.md) and [release readiness](RELEASE_READINESS.md).

## Scope and qualification

This is a patch to released local work. It does not contain the held enterprise Harness
#4863 or bridge #4865, qualify Fleet, authorize transactions, or establish a fresh installed
Alpha/Jobs/Manager/Fleet tuple. USDC and $AGIALPHA routes remain distinct.

Historical releases, original paper bytes, companion archives and all earlier checkout
profiles remain preserved. Synthetic research results and qualification limits retain
exactly their original meaning. Current version headings, generated presentation and
content-versioned caches are refreshed through the maintained generators.

Source review, hosted checks, merged-source acceptance, public publication, website and
installed verification are separate stages. A source candidate is not a public release.
Use the eventual matching release manifest and installer; do not combine assets from
1.41.0 and 1.41.1. No historical asset is overwritten.

## Français

La mission locale conserve désormais une copie JSON indépendante de ses entrées avant
la validation, le calcul de son identité et son exécution. Une modification ultérieure de
l’objet de l’appelant ne change pas la mission soumise. Les restrictions existantes du
Harness et de Fleet restent distinctes; cette correction ne les lève pas.
