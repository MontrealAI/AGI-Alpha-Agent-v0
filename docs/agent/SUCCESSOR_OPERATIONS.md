# SUCCESSOR Ω — operator, developer and verifier handbook

[Research notice](../DISCLAIMER_SNIPPET.md) · [Bilingual first session](SUCCESSOR.md) ·
[Architecture](SUCCESSOR_ARCHITECTURE.md) · [Acceptance matrix](SUCCESSOR_ACCEPTANCE.md) ·
[Ascension bindings](SUCCESSOR_ASCENSION.md) · [Distribution packs](SUCCESSOR_PACKAGING.md)

## Supported operating profile

The supported default is a private, single-operator native installation. The shipped mission uses public synthetic
non-personal events and a closed aggregation grammar. No wallet, model download, API key or paid provider is needed.
The static browser workspace and native operator have different evidence scopes. Neither establishes independent
customer Alpha, specialist ASI or production authority.

Install the wheel, matching `requirements-agent.lock`, `SHA256SUMS` and `install_agent.py` from one release, following
[the minimal installation guide](OPERATIONS.md). Use Python 3.11–3.13. The commands below run from any working directory
with that installed environment activated; they do not require a source checkout. Alternatively replace `alpha-agent`
with `.venv-agent/bin/alpha-agent` on macOS/Linux or `.venv-agent\Scripts\alpha-agent.exe` on Windows. Use the matching
virtual environment's `python` for the verifier and Python examples. An offline **installation** additionally needs the
matching dependency wheelhouse; an installed offline **rehearsal** needs no network.

Keep `--home` before the subcommand. It selects private persistent identity, journal and local role-key state. Example
output names below are deliberately new: the CLI refuses existing output files/directories rather than overwriting them.

## One-command native mission

```sh
alpha-agent --home ./successor-state successor-demo --output ./successor-evidence
```

A new home is initialized automatically. The programme underwrites bounded evidence, constructs competing compositions,
freezes a complete release, examines fresh workloads, records the local decision, runs matched memory/control trials,
exercises permission/revocation boundaries and restores portable knowledge into a clean temporary institution.
The command prints the request UUID, public key, local verdict and qualification status. A measured loss is a valid run.

Bounds can be made explicit:

```sh
alpha-agent --home ./bounded-state successor-demo --output ./bounded-evidence --seed 42 --max-events 1000 --max-candidates 4 --formation-trials 2
```

The request allows seed `0..4294967295`, `64..20000` events per workload, `2..12` candidate budget and `1..6` matched
formation trials. Eight unique grammar configurations exist; a larger budget does not create fictitious extra candidates.
The request seed controls development; fresh final workloads use custodian entropy after freeze.

| Output | Meaning |
|---|---|
| `request.json` | Complete normalized version-one request with its UUID. Keep it for resumption and return verification. |
| `result.json` | Request-bound signed native evidence, full study, lifecycle records and explicit local scope. |
| `REPORT.txt` | Readable English or French summary. Machine keys and verdict identifiers remain stable. |
| `portable.json` | Signed public institutional knowledge/history package with empty active proof and grants. |
| `checkpoint.json` | Journal position accompanying that portable snapshot; retain a trusted copy separately. |
| `public-key.txt` | Local journal public key. Pin it through an independent channel before relying on future imports. |

The private home is not an export. It contains the journal identity key, API token, configuration and
`successor-principals/` role keys. Do not publish it or put it on the public site. Public keys copied from the same
untrusted package as a signature do not authenticate that package.

## Interrupt, inspect, resume and export

`Ctrl+C` records an interrupted run. The original request survives in the demo output directory because it is written
before execution. Inspect the request's `request_id` and use it as `REQUEST_UUID` below:

```sh
alpha-agent --home ./successor-state successor-show REQUEST_UUID
alpha-agent --home ./successor-state successor-run ./successor-evidence/request.json --resume --output ./resumed-result.json
alpha-agent --home ./successor-state successor-export REQUEST_UUID --output ./retained-result.json
alpha-agent --home ./successor-state verify
```

`successor-show` exposes authenticated phase progress and recorded failure state. Explicit `--resume` permits continuation
of the same frozen request after inspection. Completed phases are retained rather than rerun as new measurements. A
changed request under the same UUID is rejected. Changed release bytes, expired prerequisites, revoked evidence or
uncertain effectful actions require their own recovery decision; `--resume` does not override them.

`successor-export` reproduces the completed retained return and does not remeasure performance. A resumed `successor-run`
writes its signed result file; it does not recreate all six files of a `successor-demo` directory. Do not rerun
`successor-demo` over an existing output folder. Use new request/output identities for a genuinely new experiment.

The existing `pause` control is respected at bounded checkpoints:

```sh
alpha-agent --home ./successor-state pause
alpha-agent --home ./successor-state resume
```

The `resume` control above clears the operator pause condition. It is different from `successor-run --resume`, which
explicitly continues an interrupted request. Neither restores revoked proof, increases a budget or grants authority.

## Verify a file return

For a browser-exported request:

```sh
alpha-agent --home ./browser-run-state successor-run request.json --output result.json
alpha-agent successor-verify result.json --request request.json
alpha-agent successor-verify result.json --request request.json --public-key TRUSTED_RAW_PUBLIC_KEY_HEX
```

The first verification checks exact normalized request/evidence bindings and validates any included signature, but the
included signer remains untrusted. The second additionally authenticates the signer against the separately retained
32-byte raw Ed25519 public key, encoded as 64 hexadecimal characters. `TRUSTED_RAW_PUBLIC_KEY_HEX` is an operator-supplied
placeholder, not a key learned from an incoming document. The browser's optional trust-key field has the same meaning.

This return signs the bytes represented by its evidence digest. It is distinct from the historical plugin wheel
signature, which signs the complete wheel bytes. Neither format may be substituted for the other. Verification checks
record integrity/authenticity; it does not independently establish truthful timings or re-execute the mission.

## Fresh examination: verifier handbook

The installed package contains a separately executable fresh evaluator:

```sh
python -m alpha_factory_v1.core.runtime.successor.evaluation --input freeze.json --output receipt.json
```

`freeze.json` must be the exact native freeze object, not a browser evidence file or an entire native result envelope.
For an already verified native `result.json`, this installed-package Python example extracts it without modifying it:

```python
from pathlib import Path
from alpha_factory_v1.core.runtime.successor.protocol import canonical
from alpha_factory_v1.core.runtime.successor.transport import read_document
result = read_document(Path("result.json"))
frozen = result["evidence"]["study"]["generation_one"]["freeze"]
with Path("freeze.json").open("xb") as output:
    output.write(canonical(frozen))
```

Run the fresh evaluator with the matching installed implementation and declared environment. It verifies the exact
aggregation/evaluation/formation source digests, mission semantics, policy, memory, comparator set, cost rule, protocol
and host fingerprint. A changed Python version, OS fingerprint, implementation or rule refuses the old freeze. Create a
new release and freeze for requalification; do not edit a frozen manifest and present it as the same examined subject.

The evaluator creates a new measurement ID, fresh workload commitment and timings. The output is an **unsigned local
measurement record**. The operator lifecycle binds it into separately signed typed records and a signed result. A fresh
`receipt.json` is not automatically a trusted `ProofReceipt`, an admission or a grant. The process accepts at most 1 MiB
of freeze input. Output must be a new path. `--stdio` exposes the same bounded internal transport for integrators.

The frozen local protocol executes 12 newly generated valid workloads, correctness/rejection checks, paired system
comparisons and separately traced Python peak allocations. It records the actual comparison, failures, uncertainty,
measured effort, exclusions and unknown costs. `tracemalloc` peak is not total resident memory. The workload is the
sampling unit; repeated timings are not extra independent experiments. Current and Beta are complete fixed alternatives,
not a hindsight per-case best-system oracle. Formation, proof and switching assumptions are accounted for explicitly;
unknown money/review costs remain unknown and block economic Alpha.

A verifier operating outside candidate control must retain the frozen release/protocol before generating final evidence,
keep final workloads, labels, entropy and credentials inaccessible to formation, record all examinations and failures,
and prevent feedback from being used to continue the same candidate trial. Changes require a new candidate identity.
Record organizational/control independence, custody, funding/conflicts, protocol control, replication and validity.
The shipped local process reports same-operator custody honestly; another local process, role name or key does not change
that fact. A genuinely external qualification needs independently configured trust, external examination and the
additional mission-designation requirements. It is not established by running this command on another terminal.

## Developer API and schema contract

Generate the machine-readable schema from an installed package:

```sh
alpha-agent successor-schemas --output successor-schemas.json
```

`alpha_factory_v1.core.runtime.successor` is an additive module of the existing runtime. Version one requires strict
records, UTF-8, sorted printable ASCII object keys, unique keys, scalar Unicode strings and exact safe integers. There
are no committed floating-point values. General JSON is bounded to 2 MB, 32 nesting levels and 100,000 nodes; individual
entry points may impose smaller bounds. Unknown fields, unsupported versions, nonfinite numbers, negative zero and
malformed Unicode are rejected. Requests normalize their declared defaults before hashing and returning all fields.

New commitments are SHA-256 over `successor-omega/v1:` + ASCII domain + NUL + canonical bytes. Time/resource units belong
to their named fields; atomic token values remain explicit decimal strings. UTC validity is separate from measurement
nanoseconds. `canonical-vectors.json` and `schemas.json` are package data available via `importlib.resources` without a
checkout. Historical journal serialization, signatures and Solidity ABI/double-keccak commitments retain their original
formats. See [the exact Ascension boundary](SUCCESSOR_ASCENSION.md).

| Installed Python interface | Responsibility and caller obligation |
|---|---|
| `protocol.RehearsalRequest`, `canonical`, `digest`, `safe_json_loads` | Validate/normalize requests and bounded records. Preserve domain and exact bytes. |
| `orchestration.rehearse(home, request, resume=False)` | Durable complete local lifecycle and signed result; use explicit retry semantics. |
| `transport.request_from_file`, `verify_result` | Bounded file intake and exact request/result verification. Supply trust separately. |
| `mission.run_study`, `GrammarSupplier`, `OpenAICompatibleSupplier` | Measured research study and replaceable bounded generation. A study alone creates no authority. |
| `evaluation.evaluate_frozen` | Fresh exact-release local examination. Prefer the separate process for custody separation. |
| `trust.TrustRegistry`, `TrustAnchor`, `SignedEnvelope`, `sign_record` | Operator-installed principal roles and attributable signatures. Incoming records cannot install roots. |
| `state.SuccessorStore` | Journal-backed institution, release, proof, admission, grant, evidence, memory and lineage transitions. |
| `state.ActionGateway` | Only explicitly installed fixed tool/action handlers. Integrator must enforce the real execution boundary. |
| `jobs.compile_jobs`, `JobDispatcher` | Typed graph validation, sealing, dispatch, action-time checks, acceptance and bounded recovery. |

State mutation methods include `register_release`, `record_proof`, `admit`, `grant`, `dispatch_action`, `execute_action`,
`revoke`, `impair`, `cutover`, `recover`, `descendant`, `record_evidence`, `admit_memory` and `revoke_evidence`. They enforce
exact subject, current dependencies, principal roles and applicable resource/validity restrictions. Mutating workflows
use idempotency identities and the journal's serialized transactions. `execute_action` rechecks authority at execution;
a dispatch receipt does not preserve a revoked permission. No permission is synthesized from fragments of separate grants.

Typed signed record domains include `proof`/verifier, `admission`/admission, `authority`/authority,
`execution`/controller and `job-acceptance`/acceptance. `TrustRegistry.verify` requires the domain and expected role.
Principal trust is supplied out of band for each process. `TrustRegistry.revoke(principal)` changes that in-memory
registry only: persist the revocation in the external trust configuration, omit the principal on restart, or record a
durable institutional impairment. Grant, evidence and admission status changes are journal-backed. Do not mistake an
in-memory trust mutation for a persistent revocation.

Local role credentials have local provenance. Installing an independent anchor requires a separately supplied attestation;
that declaration still needs real-world evidence of independence. A producer cannot certify or admit its own release.

Graph version one rejects all cycles. Each job has finite attempts/repair routes and required evidence, control,
challenge and rollback obligations. `JobDispatcher.execute_tool` revalidates a previously dispatched job before invoking
its installed handler. A crash leaving an uncertain effect is not automatically replayed; the accountable controller
must inspect and recover it. Work acceptance, negative candidate verdict, settlement, memory admission and production
admission remain distinct. Do not translate an accepted negative evaluation into a passing candidate.

The maintained OpenAI-compatible supplier is an explicit Python adapter using the existing bounded provider transport.
There is no implicit live provider or `successor-run --provider` option. An integrator deliberately supplies a
`RuntimeConfig` to `OpenAICompatibleSupplier` and supplies that adapter to `run_study`. Record configuration, usage,
errors, costs and pinning limits. Deterministic adapters remain labelled deterministic; errors do not trigger a
fixture-as-model fallback. Default release evidence tests deterministic substitution, not real-model replacement.

These Python integration interfaces do not expose a public production-control server. The default local operator server
retains its existing authentication/origin/body limits. Any effectful handler must enforce filesystem, network,
credential and subprocess restrictions at the actual boundary. Arbitrary generated code uses the existing explicit
Docker path; a Python policy check does not sandbox arbitrary host code. No unavailable Docker fallback runs on the host.

## Threat model and residual limits

| Actor / event | Asset at risk | Implemented control | Residual limit / operator responsibility |
|---|---|---|---|
| Candidate or malicious supplied evidence | Final evidence, policy, credentials | Closed grammar, strict records, no candidate effects; evidence stays data; separate final process | The local OS owner can inspect or modify processes. Local custody is not external independence. |
| Forged receipt or attacker-selected signing key | Proof/admission/authority | Domain-bound signatures and separately configured principal registry; browser keys never self-install | Authenticate roots through an independent channel; a correct signature does not prove a measurement truthful. |
| Changed model, prompt, source, memory or comparator | Exact proof subject | Complete release commitments; frozen validation and claim-specific impairment | Remote model weights cannot be pinned by a request log. Requalify observed supplier changes. |
| Concurrent jobs, retries or queued revocation | Shared budgets and permitted effects | Atomic reservation, cumulative grant limits, idempotent effects and action-time revalidation | Unknown external billing or human effort is not controllable expenditure; dependent claims remain blocked. |
| Power loss during an effect | Journal, accounting, duplicate external effect | Durable intent/result records; uncertain effects require explicit recovery | Some real effects cannot be rolled back; the installed handler and principal must supply a valid recovery contract. |
| Replayed old but correctly signed history | Later revocations and lineage | Separately retained journal checkpoint and exact portable snapshot binding | A checkpoint stored only with its package cannot detect rollback; retain and update an independent anchor. |
| Corrupt, oversized or hostile import | Availability and state integrity | Byte/depth/node limits, strict integer/Unicode rules, duplicate-key rejection, regular-file checks | Parser validation is not a general document malware scanner; no imported code is executed. |
| Descendant or restored institution | Predecessor proof and privileges | Historical attribution preserved; new active proof/grants empty; explicit admission/cutover | Never treat ancestry, an ENS name, token ownership or settlement as permission. |
| Compromised local account or copied private backup | Journal identity, role keys, API token | Private file permissions; public exports omit secrets; private workflows kept separate | The same OS administrator controls local roots. Protect the host and maintain independently retained evidence. |
| Browser status edits or compromised client state | Scientific interpretation | Browser scope permanently local; native request/evidence verification; UI issues no grant | Static UI integrity is not an authority service; validate at the native action gateway. |
| Faster but incorrect candidate or stronger Beta | Mission utility | Correctness/rejection/resource hard gates and best fixed comparator | Small, noisy local experiments are descriptive; no forced Alpha or ASI designation. |

The supported local run contains no production connection or mainnet action. Ascension tests use disposable local-EVM
fixtures; real assets, ENS changes and externally controlled chains remain separate commissioning decisions.

## Versioning, restoration and rollback policy

Protocol/portable version one is the currently implemented format. Unsupported versions and unknown fields fail
explicitly; there is no automatic conversion of old signed objects into new proof. A future migration must declare its
version mapping, validation and rollback behavior. Keep historical signed bytes and their original domains unchanged;
never re-sign them to make predecessor claims look current.

Install upgrades into a new virtual environment and retain the old installation and exported evidence until the new
version's checks pass. Source/environment changes intentionally invalidate a freeze for re-examination. Never rewrite
an old frozen source hash or grant to make it pass a new build. A software rollback may restore executable bytes, but
must not roll the journal behind a retained revocation/checkpoint or silently reinstate expired authority. If no valid
fallback exists, keep the institution stopped.

Portable restoration requires a separately supplied source public key and an independently retained checkpoint. It
preserves institutional identity and historical attribution, while active proof and grants remain empty. Configure new
principals locally, reassess rights/freshness, obtain new examinations and admissions, and explicitly cut over only when
all current prerequisites hold. Historical receipts remain historical. See the installed restoration commands below.

## Portable export, checkpoint and clean restore

Obtain `INSTITUTION_ID` from `payload.institution.id` in the demo's `portable.json`. Export a current snapshot and its
matching checkpoint from the authenticated source home:

```sh
alpha-agent --home ./successor-state successor-portable INSTITUTION_ID --output ./portable-current.json --checkpoint-output ./snapshot-checkpoint.json
alpha-agent --home ./successor-state successor-checkpoint --output ./latest-checkpoint.json
```

`successor-portable` writes public permitted records and a checkpoint from the same consistent snapshot. Retain a copy
of that checkpoint through an independent channel before trusting later imports. `successor-checkpoint` captures the
current journal head for independent monitoring. A newer checkpoint must not be paired with an older portable package:
export a new consistent snapshot instead. A key/checkpoint supplied only inside the incoming package adds no trust.

Restore into a **new** home with the separately retained source key and matching checkpoint:

```sh
alpha-agent --home ./restored-state successor-restore ./portable-current.json --source-public-key TRUSTED_SOURCE_KEY_HEX --checkpoint ./retained-checkpoint.json
```

The destination must not exist. The command validates version, structure, signature, source identity and the separately
retained checkpoint before creating the destination. It preserves institutional identity and lineage, but the new home
starts stopped, with fresh local rehearsal role keys, no active proof, no admission, no grant and no allocated budget.
It does not import predecessor credentials or automatically trust predecessor verifier keys.

An operator may explicitly allocate new local resources with repeated `--budget UNIT=COUNT` arguments, and may explicitly
provide a separately configured trust file with `--trust trust.json`. Neither resource allocation nor trust configuration
creates a proof or grant. The trust file uses this exact version-one shape:

```json
{
  "schema_version": 1,
  "principals": {
    "operator-owned-principal": {
      "public_key": "REPLACE_WITH_SEPARATELY_AUTHENTICATED_RAW_ED25519_HEX",
      "roles": ["controller"],
      "provenance": "local",
      "independence_attestation": ""
    }
  }
}
```

The public-key placeholder must be replaced; it is not a usable fixture key. Never build this trust file automatically
from an incoming portable package. `provenance: independent` requires an externally supported attestation and appropriate
real-world separation. A local label cannot establish that independence. Imported knowledge remains subject to rights,
freshness and new accountable admission before influence; signed history alone cannot reactivate it. The restored
institution requires current evidence, admission, scoped grants and an explicit valid cutover through the state API
before any consequential action. The default CLI does not expose a shortcut that issues production authority.

## Private disaster recovery: same identity and keys

A private recovery backup is a different artifact from `portable.json`. It contains secret material and is not a public
institutional transfer. Pause the operator and retain a separately stored checkpoint alongside the private recovery
procedure:

```sh
alpha-agent --home ./successor-state pause
alpha-agent --home ./successor-state backup ./private-recovery.zip
alpha-agent --home ./successor-state successor-checkpoint --output ./recovery-checkpoint.json
alpha-agent --home ./private-restored-state restore ./private-recovery.zip
```

The private archive includes the journal, configuration, identity key and API token. When present, it additionally
preserves the complete `successor-principals/` role-key set and separately configured `successor-trust.json`. Partial or
inconsistent role-key sets are refused; historical five-member legacy backups remain supported for their original
contents. An old backup that never contained SUCCESSOR role keys is not a complete role-continuity backup. Restoration
requires a new destination and validates the private archive before promotion. Protect this secret-bearing archive with
your private storage/transport controls; it is not an encrypted public export.

The generic `restore`/`verify` commands check internal journal authenticity, not whether a newer revocation once existed.
Before resuming private restored state, verify the independently retained checkpoint using the installed API:

```python
from pathlib import Path
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads
from alpha_factory_v1.core.runtime.successor.trust import JournalCheckpoint
checkpoint = JournalCheckpoint(**safe_json_loads(Path("retained-recovery-checkpoint.json").read_bytes()))
checkpoint.verify(Journal(Path("private-restored-state")))
```

The checkpoint must have been retained separately from the incoming archive. A self-consistent older archive cannot
satisfy a later checkpoint. Keep the restored operator paused while checking current trust, expiry, dependency rights,
provider/source changes and uncertain effects. Only then make explicit recovery/resumption decisions. A private backup
preserves recorded identity and history; it does not turn expired or revoked permissions back into current authority.

## Français : exploitation native et vérification

Après l'installation minimale, activez son environnement Python. Ces commandes fonctionnent sans copie du dépôt :

```sh
alpha-agent --home ./etat-successor successor-demo --output ./preuves-successor --language fr
alpha-agent successor-help --language fr
```

`REPORT.txt` est en français; les clés machine et identifiants de verdict restent stables. Le dossier contient la requête,
le résultat signé, le rapport, le paquet portable, le point de contrôle et la clé publique. Le calcul est réel, mais la
qualification reste `HOLD` et aucune autorité de production n'est attribuée. Conservez le point de contrôle et la clé
publique par un canal indépendant, et gardez le dossier privé `--home` confidentiel.

Après `Ctrl+C`, inspectez le UUID de `request.json`, puis utilisez les mêmes paramètres et un nouveau fichier de sortie :

```sh
alpha-agent --home ./etat-successor successor-show UUID_REQUETE
alpha-agent --home ./etat-successor successor-run ./preuves-successor/request.json --resume --output ./resultat-repris.json
alpha-agent --home ./etat-successor successor-export UUID_REQUETE --output ./resultat-conserve.json
alpha-agent successor-verify ./resultat-conserve.json --request ./preuves-successor/request.json --public-key CLE_PUBLIQUE_HEX_FIABLE
```

La reprise réutilise les phases conservées; elle ne contourne ni révocation, ni expiration, ni limite de ressources.
L'export restitue des mesures existantes sans les refaire. Une nouvelle expérience exige une nouvelle identité et de
nouvelles sorties. `pause`/`resume` gère l'arrêt de l'opérateur; `successor-run --resume` reprend explicitement une requête.

L'examinateur installé s'exécute avec `python -m alpha_factory_v1.core.runtime.successor.evaluation --input freeze.json
--output receipt.json` sur **une seule ligne**. Le fichier `freeze.json` est l'objet natif exact extrait comme indiqué
plus haut. Il faut la même version et l'environnement déclaré. Un changement exige une nouvelle version figée, jamais
la modification d'une ancienne preuve. L'examen crée de nouvelles mesures, un nouvel engagement de données et un rapport
local non signé. Le cycle opérateur le lie ensuite à des enregistrements signés; ce rapport seul n'accorde aucune
admission ni permission.

La séparation des processus et des clés locales n'établit pas l'indépendance. Une qualification externe exige une vraie
séparation du contrôle et de la garde des données, des racines de confiance fournies séparément, des critères figés et
toutes les preuves requises. Les données finales ne doivent pas revenir à la formation du même candidat.

La restauration portable conserve l'identité et l'histoire, mais laisse preuves actives et permissions vides. Le point de
contrôle conservé séparément détecte un retour à un historique antérieur pourtant bien signé. Les versions inconnues
sont refusées; aucune migration implicite ne réécrit ou ne re-signe les anciens documents. Un retour logiciel en arrière
ne réactive jamais automatiquement une permission expirée ou révoquée. Les limites résiduelles restent celles du tableau :
contrôle de l'hôte par son propriétaire, coûts externes inconnus et mesures locales descriptives.

### Restauration portable et points de contrôle

`successor-portable IDENTITE_INSTITUTION --output portable.json --checkpoint-output point.json` exporte un instantané
et son point de contrôle correspondant. `successor-checkpoint --output dernier-point.json` capture le dernier état
pour conservation indépendante. Ne mélangez pas un ancien paquet avec un point plus récent : exportez un nouvel
instantané cohérent. L'identité de l'institution se trouve dans `payload.institution.id` du paquet de démonstration.

```sh
alpha-agent --home ./etat-restaure successor-restore ./portable.json --source-public-key CLE_SOURCE_HEX_FIABLE --checkpoint ./point-conserve-separement.json
```

Le dossier de destination doit être nouveau. La restauration vérifie les liens, la signature, la clé source et le point
conservé séparément avant sa création. Elle préserve l'identité et l'histoire, mais démarre arrêtée, sans preuve active,
admission, permission ni budget. Les clés locales sont nouvelles. Des options répétées `--budget UNITE=NOMBRE` affectent
explicitement de nouvelles ressources; `--trust confiance.json` fournit des racines configurées séparément selon le schéma
ci-dessus. Ces options ne créent ni preuve ni permission. Les droits et la fraîcheur des connaissances doivent être
réexaminés; une nouvelle admission et une transition autorisée restent nécessaires.

### Sauvegarde privée et continuité des clés

Une sauvegarde `backup` contient des secrets : identité, jeton API, journal, configuration et, lorsqu'ils existent,
ensemble complet de clés `successor-principals/` et fichier `successor-trust.json`. Elle est distincte du paquet portable
public et doit rester dans un stockage privé protégé. Elle n'est pas un export public chiffré. Mettez l'opérateur en
pause, créez la sauvegarde et conservez un point de contrôle séparé. `restore` exige un nouveau dossier. Vérifiez ensuite
le point conservé séparément avec `JournalCheckpoint.verify` comme indiqué plus haut; la seule cohérence des signatures
ne prouve pas l'absence d'une révocation ultérieure. Gardez l'état restauré en pause jusqu'à la vérification des droits,
expirations, dépendances et effets incertains. Une sauvegarde ancienne sans clés de rôle n'assure pas leur continuité.

Les racines de confiance sont fournies séparément à chaque processus. `TrustRegistry.revoke` agit en mémoire seulement :
conservez la révocation dans la configuration externe, retirez le principal au redémarrage ou consignez une altération
institutionnelle durable. Les révocations de permissions, preuves et admissions enregistrées au journal restent durables.
