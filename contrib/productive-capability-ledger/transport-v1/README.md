# Source-assurance transport candidate — candidat de transport

This additive adapter implements the missing source-assurance worker interface for
Alpha's **existing** `StrategyExecutor`, `Journal`, authentication boundary and
HTTP routes. It imports the existing source runner and invokes the separately
implemented Python verifier before returning a checked downloadable ZIP. It adds
no server, scheduler, credential, payment route or deployed profile.

**Operational adoption: NOT APPROVED. Approved-operator acceptance: NOT RUN.**
The current installed planning profile, method inventory and candidate wheel are
unchanged. This source-checkout candidate is not in that wheel. Its isolated tests
do not qualify an operator installation, unattended recovery, the website or the
complete Flywheel. The existing planning UI remains unchanged. This candidate supplies its own
English/French view through the same transport static-file mechanism, with prepared
input import, exact approval, execution, durable history/export and verified ZIP
download. It creates no additional API or scheduler.

## Permitted input and bounded execution

An operator-selected inert registry declares 1–32 public scopes, each an exact
local Git commit and committed manifest path. `scopes.example.json` demonstrates
the schema with already public e250 source. Public origin/permission is an
operator assertion to review before adoption. A browser cannot provide a host
path, command, endpoint, repository URL or unlisted scope. The manifest's source
paths still pass the existing 1–128 ordinary-Git-file restrictions.

`SourceAssuranceWorker.prepare_input(scope_id, run_id, created_at=..., expires_at=...)`
prepares the exact existing v3 plan. The returned JSON becomes the input of the
existing transport's `run-mission` plan. The exact outer plan must receive the
existing explicit approval; `prepare_input` grants none. Only fixed comparison,
packaging and verification code executes. Inspected source remains inert.

The candidate policy supports only `run-mission`, with one conservative service
unit per attempt, zero construction/native allowance, at most four outer requests
by default, one source attempt per run identity, 1–60 seconds of runner time and
an equally bounded independent-verifier invocation. Source expiry remains part
of the approval digest. The outer request lease includes these two time limits
plus five seconds. The source runner retains its existing per-Git-call time and
4 MB child-output ceilings, offline `--no-lazy-fetch`, replacement refusal and
ordinary-file limits. Missing objects refuse; this adapter never clones/fetches.

The fixed children use operator-selected absolute Node/Python/Git interpreters,
a minimal child environment, a 256 MB Node heap ceiling, a one-megabyte stdout
ceiling and 64 KB stderr ceiling. These are elapsed/output/heap bounds, not a
claim of an OS memory sandbox or measured full process cost. The package contains
at most 512 KB of selected uncompressed customer files. Oversize, unknown,
changed, expired or incomplete output refuses; retained evidence is not deleted.

The helper `candidate_policy(journal, worker)` reuses the existing installed
engineering environment/child checks: Ubuntu 24.04 x86_64, glibc 2.39, CPython
3.12.14, Node 24.22.1, the exact 26 dependencies and public Alpha 1.42.0. It checks
all 505 declared runtime Python sources, binds the four existing runtime
enforcement files, and additionally requires the selected Git 2.51.1 executable.
Unknown hosts/versions, wrong selected interpreters and changed public runtime
source refuse. Matching this engineering profile still grants no operator
adoption. Pure worker tests remain separate from these installed profile checks.

The same helper binds the registry and every
adapter/runner/checker/comparison source hash using the existing policy's
`SourceFile` inventory. It requires the output root to be exactly
`journal.root / "source-assurance"`, without linked ancestors. It creates no
journal. An existing journal already bound to a different transport policy
refuses this candidate; there is no automatic migration, policy replacement or
permission expansion.

## Journey and usable result

1. The owner makes an explicitly permitted, already local public checkout and
   immutable scope registry available to an eligible existing operator profile.
2. `prepare_input` returns the exact source plan; existing prepare/approve binds
   its public scope, run identity, expiry, limits and installed source identity.
3. The existing `run` action reserves one service unit before fixed work. Its
   checkpoint callback is polled while each child runs; checkpoint failure kills
   the child's process group and retains uncertain work.
4. The existing source runner delivers both inventories, complete differences and
   follow-up CSVs, portable workspace and report. The Python verifier separately
   checks the Git/CSV/hash result. ZIP assembly checks the exact independently
   accepted COMPLETE hash and each selected artifact hash, rejects file identity
   changes during reads, and rechecks COMPLETE after packaging. Its statement still says "local Node only":
   this is its intentionally narrow component scope, not a transport receipt.
5. The candidate English/French view imports the owner-prepared JSON. It shows
   the exact finite plan before approval, then the existing run and signed
   mission-history actions. Pause and permanent STOP remain available while a
   request is active. A successful adapter outcome includes `result.download`: ZIP filename, MIME
   type, byte length, SHA-256 and base64 bytes. The ZIP contains the approved
   plan, six useful customer files, final acceptance and independent acceptance.
   Existing signed mission export durably includes that outcome. The candidate
   view checks decoded length and SHA-256 before offering the ZIP download.

A checkpoint, export, reconnect or each verifier assertion is not another job.
`service_work: 1` is an attempt-accounting unit, not seconds, currency or profit.
Full monetary cost, maintenance, failed construction, customer attention,
customer acceptance and revenues remain unknown. There are no token operations.

## Persistence, cancellation and recovery limits

The adapter reuses the existing transport's exact-input idempotency and signed
history. A completed outer duplicate returns the committed outcome without
starting a source child. The inner one-attempt source plan refuses a second
execution even if submitted under a new outer request; neither allowance renews.

Browser disconnection during active source work is **not yet qualified**. Keep
the local executor process running and reconnect to inspect durable history.
This adapter's active browser-closure/network behavior is not established by
worker or ASGI tests. The separately qualified planning active-tab-closure result
does not establish that behavior for this source candidate. The authenticated ASGI campaign separately verifies exact
approval, durable app reopen, duplicate returns, concurrent-request refusal,
missing-artifact refusal and uncertain-result fencing. Worker/process interruption leaves the
existing outer reservation unknown and the inner reservation/checkpoints intact.
The existing transport refuses replay and requires inspected reconciliation.
A new mission needs a new identity and explicit approval. No code here resumes an
uncertain request unattended or converts safe crash shutdown into completion.

Existing transport pause/STOP is checked during each child and before completion.
STOP remains permanent for that installed envelope. The source runner's existing
`CANCEL` signal file records durable cancellation at its next bounded stage;
removing that file cannot reopen a cancelled run. This is an operator-local
control, not a new remote cancel endpoint. The adapter does not remove STOP,
CANCEL, locks, failed artifacts, reservations or uncertain history. An interrupted
recovery lock requires operator inspection under the unchanged runner procedure.

## Ready acceptance procedure and precise owner action

The existing runtime/profile owner must first approve the **source-specific
candidate and source inventory**, choose an eligible already-authorized journal
and finite envelope, and make that exact installation/session available. A token
or home directory by itself does not approve this profile. If the chosen home is
bound to planning, its existing refusal remains; a legitimate adoption/migration
decision must come through the responsible owner. Do not initialize another home
or create credentials to get around it.

After that decision, use the exact reviewed checkout in its qualified environment:

```python
from pathlib import Path
import importlib.util
from alpha_factory_v1.core.runtime.store import Journal

spec = importlib.util.spec_from_file_location("source_worker", "contrib/productive-capability-ledger/transport-v1/source_worker.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
journal = Journal(APPROVED_EXISTING_HOME)
worker = module.SourceAssuranceWorker(Path(APPROVED_SCOPE_REGISTRY), journal.root / "source-assurance",
    node=Path(APPROVED_NODE), git=Path(APPROVED_GIT), python=Path(APPROVED_PYTHON))
policy = module.candidate_policy(journal, worker)
executor = module.load_transport().StrategyExecutor(journal, worker, policy)
```

The fixed candidate launcher opens an existing home only; it does not call
`Journal.initialize`. After the owner adoption decision, prepare input with:

```sh
python contrib/productive-capability-ledger/transport-v1/serve_candidate.py \
  --existing-home APPROVED_HOME --registry APPROVED_REGISTRY \
  --node ABSOLUTE_NODE --git ABSOLUTE_GIT --python ABSOLUTE_PYTHON \
  --prepare-scope APPROVED_SCOPE --run-id FRESH_RUN_ID \
  --created-at EXACT_ISO_UTC --expires-at EXACT_ISO_UTC
```

Save the returned input JSON. The same launcher without preparation arguments
serves the existing transport application on loopback port 8788 (or an explicit
port 1024–65535), using the existing journal token. In that local candidate view,
connect, import the JSON, choose an exact request ID, inspect/approve the plan,
run, inspect history and download/export. No token is put into URLs, browser
storage or exports.

Prepare a fresh scoped input with explicit ISO UTC `created_at`/`expires_at` and
run ID. Submit that JSON through the existing authenticated prepare route,
inspect/approve its exact outer plan digest and execute it. Retain versions,
checkout SHA/tree, registry/source hashes, policy binding, input, actual signed
output, verifier result, ZIP bytes/hash and public-source provenance. Decode and
independently inspect the ZIP. Check same-ID duplicate returns without another
source reservation. Then qualify pause, permanent STOP, source CANCEL, expiry,
exhaustion, missing artifacts, concurrent writers, worker restart and network
interruption in separately approved finite fixtures. Record every failure and
unknown outcome. These live/operator checks are **NOT RUN here**.

The isolated component campaign is reproducible without any operator profile:

```sh
python scripts/check_python_deps.py
python check_env.py
python -m pytest -q contrib/productive-capability-ledger/transport-v1/test_source_worker.py --noconftest -p no:cacheprovider
python -m ruff check contrib/productive-capability-ledger/transport-v1
python -m black --check --line-length 120 contrib/productive-capability-ledger/transport-v1
python -m mypy --strict --follow-imports=skip contrib/productive-capability-ledger/transport-v1/source_worker.py contrib/productive-capability-ledger/transport-v1/serve_candidate.py
node --test contrib/productive-capability-ledger/transport-v1/strategy.test.mjs
```

The worker-only campaign passes 23 cases using actual Git/Node and the
independent Python verifier; three Node groups check input, download validation and the bilingual plan summary.
The separate nine-case authenticated ASGI campaign runs outside the checkout with `-I`,
asserts actual installed public Alpha 1.42.0 rather than checkout imports, and uses
its exact core dependency profile. Its transient isolated journals are test
fixtures, not operator credentials or profile adoption. The component environment
is CPython 3.12.14, Node 24.22.1 and Git 2.51.1. Full software qualification, official
Security, actual browser and approved-operator acceptance remain separate.
Run `test_source_api.py` only in that installed environment from outside the
checkout with `python -I -m pytest ABSOLUTE_TEST_PATH --noconftest
--import-mode=importlib -p no:cacheprovider`. Test counts are cases/groups, not jobs.

## Français — périmètre et adoption

Ce candidat réutilise le transport, le journal durable et les contrôles existants.
Il vérifie uniquement des fichiers Git publics déjà présents, selon un inventaire
et une révision explicitement autorisés. Il produit les deux inventaires, les
écarts complets, les actions proposées, un espace de travail portable et un
rapport dans une archive ZIP vérifiée. Il n'exécute pas le code inspecté.

**Adoption opérationnelle NON APPROUVÉE; essai dans l'installation de l'opérateur
approuvé NON EXÉCUTÉ.** Les essais isolés ne prouvent pas une reprise autonome ni
une livraison par le site public. Le profil de planification actuel et son
interface restent inchangés. La vue candidate FR/EN utilise le transport existant
pour importer l’entrée, approuver le plan exact, exécuter, consulter l’historique
et télécharger le ZIP après vérification de sa taille et de son SHA-256. L'autorité responsable doit adopter ce profil exact
et fournir son installation/session autorisée avant l'essai connecté.

Les limites, l'expiration et les réservations ne se renouvellent jamais en
silence. La déconnexion du navigateur pendant un travail source actif n'est pas encore
qualifiée. Gardez l'exécuteur local actif et reconnectez-vous pour consulter
l'historique durable. Une interruption du processus conserve un résultat incertain et ses coûts réservés; elle ne crée
aucune réussite. STOP reste permanent, CANCEL est durable, et la reprise d'un
travail incertain exige l'inspection prévue par le transport existant. Aucune
recette, économie complète ou accélération autonome n'est établie par ce candidat.
