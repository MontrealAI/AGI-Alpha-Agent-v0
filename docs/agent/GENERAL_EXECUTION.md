[Project notice](../DISCLAIMER_SNIPPET.md)

# General execution protocol / Protocole d’exécution générale

The additive `flywheel-execution/v1` executor uses the existing signed Journal, protected deployment,
controller trust, high-water checkpoint and A/B/C CostLedger. It creates no second skills registry,
publisher, credential store, settlement role or governance path. The old source-selection connector
and every previous route remain available with their original scope.

## Implemented boundaries

`ExecutionMission` binds beneficiary, difficult assumption, useful deliverable, acceptance criteria,
inputs and sharing rights, stop conditions, component labels and finite budgets. `ExecutionProfile`
binds the exact model and optional served revision, standard reasoning mode, requested effort,
explicitly supported efforts, strict named tools, context and output limits and qualification evidence.
There is no Pro-mode fallback or inference of capabilities from a marketing name.

`ExecutionPermit` is a separate controller-signed record for the exact journal, mission, profile,
execution environment, runtime configuration, quota and pricing evidence, A/B/C bucket, expiration
and maximum authorized envelope. Membership alone does not authorize execution.

The concrete Responses transport sends `reasoning.effort`, preserves output/reasoning items and tool
results in the next request, and uses strict function-call or native computer-call output records.
An explicitly reported different reasoning effort refuses; an omitted report remains unverified.
Supported empty pointer modifiers are normalized only on execution copies; raw history is preserved.
Computer calls execute the validated existing primitives and return the resulting screenshot.
A computer observation must be a bounded inline PNG; it cannot make the provider fetch an arbitrary image URL.
A call marked completed by the provider still must execute through the actuator.

Wire data uses the existing canonical protocol: exact integers, decimal strings, text and structured
JSON, with no floating-point JSON numbers. Scientific tools must use exact units/decimal strings or
an explicitly qualified conversion adapter. This version does not claim arbitrary API compatibility.

The optional `HTTPToolEnvironment` targets an **application-owned, already approved sandbox service**;
its protocol is not an OpenAI-hosted endpoint. That service must implement its own isolation,
argument schemas, artifact permissions, session custody, quotas and request-ID deduplication.
No dynamic host import, eval or shell fallback is provided. Code execution, research and document
creation are possible through separately qualified named sandbox tools; they are not established
merely by declaring a tool name. The Docker adapter reuses the existing immutable-image,
networkless browser worker and exact approved public-read allowlist. No host browser fallback exists.
The enclosing mission must fit the independently approved ComputerTask's turn, action and time limits
before any paid reservation. The adapter also enforces the task's own action/time limits during execution.

Each provider/tool attempt is checkpointed before I/O. Full returned observations have individual
immutable Journal records. Mission checkpoints preserve history and all usage events. Expired
permits, stops, model substitution, unsupported tools, safety checks, replay, context/action/time
limits and changed environment identities refuse. A competing mission record cannot be overwritten.
Interrupted attempts stay uncertain and are never automatically retried. The operator can inspect
the prior record and reconcile costs before explicitly authorizing a fresh operation; this version
does not implement automatic continuation of an uncertain environment.

Transport I/O has total deadlines and cancellation. Trusted tool implementations must also provide
bounded cooperative cancellation; an arbitrary in-process callback is not an isolation boundary.
The concrete HTTP and Docker adapters enforce their own bounded operations.

The initial model liability remains unknown until attributed billing reconciliation. Other resource
categories must be charged separately and sealed under the existing ledger before complete-cost
profit is available. Usage is not an invoice. The signed envelope is spending authorization, not
an enforceable provider-side dollar meter: live qualification must establish the account's quota,
tariff, output/context/tool limits and external hard limit. Unreconciled liabilities conservatively
block further funded intake. Multi-mission live throughput has not been qualified.

Live models and tools require separately qualified per-request liability caps in the signed profile.
The loop reserves each cap before the corresponding call and refuses a call whose cumulative caps
would exceed the whole mission allowance. These caps require real tariff/quota/hard-limit evidence;
supplying an arbitrary number does not establish a provider guarantee. Actual charges remain unknown
until reconciled. Scripted/local fixtures may have no provider fee while complete research cost stays unknown.

General operation IDs are hashed into a separate namespace so an ID containing `/event/` cannot
collide with another mission's observation records. The execution identity also binds the reused
computer adapter, worker, public reader and dependency-capture implementations.

## Explicit modes and observed evidence

All modes use the same `MissionExecutor.run` and lifecycle records. `live` requires all declared
material components to be live; the declaration and signature do **not** establish that fact.
Every returned record still has `live_network_qualified: false` until deployment-specific evidence
has been assembled and independently assessed outside this production conversation.
`hybrid` permits real tools with a scripted model or modeled identity. `simulation` requires a
modeled production model. Imports do not install an executor, signers or resource access.

The recorded systems-R&D demonstration uses real orchestration and an executable exact placement
prototype: two replicas per service in distinct failure domains, finite host capacities and
service-specific costs. Branch-and-bound outputs are checked against an independently written
exhaustive enumerator on affordable instances. Search exhaustion remains incomplete.

The model is **`scripted-protocol-fixture/v1`**, not Astra, Terra or another frontier model. Requested
high effort exercises protocol preservation; no reasoning occurs in that script. Identities,
funding, market and prospective customers are fictional. Local computational acceptance is not
customer acceptance or a paid delivery. No actual frontier calls or computer clicks occurred.

Twelve predeclared seeds 7300–7311 exercise fresh engineering variation. No additional frontier
advantage is measured, so the candidate decision is **do not admit**. There is no positive general
capsule admission, authenticated peer result, retention-program return or growing-Alpha finding.
Complete actual research costs are unknown and actual receipts are zero. This is an executed
engineering/protocol fixture, not a calibrated frontier-performance or commercial simulation.

Reproduce without overwriting evidence:

```sh
PYTHONPATH=. python scripts/record_general_flywheel.py --output /private/new-general-evidence.json
python -m pytest tests/runtime/test_flywheel_execution.py -q --no-cov
```

The public Flywheel embeds a screened copy of this report, with code source identities and explicit
labels. Exporting it restores no live authority. Its results remain separate from the preserved
commercial teaching simulation and prior research findings.

## Operator path

Only after the existing protected deployment and execution resources are separately approved:

```sh
alpha-agent --home /private/agent flywheel --deployment /private/deployment.json \
  --output /private/new-attempt.json mission-run /private/mission.json \
  /private/profile.json /private/controller-signed-permit.json \
  --tool-endpoint /private/approved-sandbox-contract.json
```

For the existing browser actuator, replace `--tool-endpoint` with `--computer-task TASK.json
--computer-image IMMUTABLE_DIGEST`. Starting the browser is lazy: no container is created before
the signed mission reservation. It uses the existing ComputerTask permissions, whose contents and
worker/image identities must match the signed environment contract. The native CLI never runs
scripted simulation as a live provider; credential-free reproduction uses the explicit recorder.

The sandbox request contains schema_name `flywheel-sandbox-call/v1`, session_id, sequence,
operation_digest, sandbox_revision, tool, arguments and a domain-separated request_id. The operation
digest binds the exact signed permit and Journal identity. Sequence/deduplication scope is that
operation, so a fresh mission cannot receive an older mission's cached result. A client environment
cannot be rebound to another operation. The response must contain
exactly request_id and result, with the same request_id and a bounded JSON object. A timeout
cannot establish nonexecution, zero cost or permission to retry.

After interruption, use the same private operator's `execution-receipt OPERATION_ID` command with
a new output path. Add `--event model/0` or the exact recorded tool-attempt label to inspect a full
durable observation. Inspection does not replay an action, reconcile a bill or restore a stopped
environment. Historical records and the original uncertain obligation remain intact.

## Qualification record and remaining work

| Capability | Current scope |
| --- | --- |
| General versioned reasoning/tool loop, structured deliverables, durable observations and CAS | Implemented; fixture tests only |
| Concrete Responses and application-owned sandbox HTTPS protocols | Mock-transport tests; no actual account/service call |
| Existing Docker computer adapter | Validated-action adapter tests; no new real browser/desktop execution |
| Actual finite systems-R&D tool and independent checker | Executed on 12 fresh synthetic cases |
| General protected transferable capsules | Still requires a reviewed extension of the existing closed selector scope; no parallel registry created |
| Fresh competent frontier Beta, second live identity and invoked skill | Not executed; no positive claim |
| Repeated net advantage and complete commercial economics | Not established; costs unknown, receipts zero |
| English/French evidence addition | Generated source; complete local browser and released/public journey qualification pending |
| Release | Additive proposal, separate from the held v1.46 lease; no merge/release/public acceptance inferred |

Live dependencies are the approved model/account, quota/tariff/hard budget and billing evidence;
approved sandbox/tools or immutable local browser image; HTTPS service and durable checkpoint,
storage and key custody; two separately approved mainnet RPC readers and independently checked
ENS implementation pins; two owner-controlled eligible names **and distinct wallets**; rights-cleared
work and independent acceptance. No new credentials, persistence, paid infrastructure, financial
transactions or live wallet actions were provisioned by this change.

General capsule admission and transfer evaluation also require further engineering and exact-source
review; they are not merely resource dependencies. The existing protected selector's qualification
does not transfer to those future scopes. Preserve its identity/revocation/copying limitations and
all Jobs validator, currency, settlement and governance boundaries.

Rollback uses the existing paused-runtime recovery procedure and a previously qualified release.
Preserve the latest high-water custody and private journal; do not roll both stores back to revive
an uncertain permit, stale authority or revoked candidate. Reconcile outstanding liabilities first.

Official API interfaces checked 2026-10-27:
[computer use](https://developers.openai.com/api/docs/guides/tools-computer-use),
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra).
These pages establish published interfaces, not this account's entitlement or task performance.

## Français

Ce parcours ajoute une interface générale et versionnée au Journal, aux autorisations signées,
au point de contrôle durable et aux registres A/B/C existants. Aucun registre concurrent ni
nouveau rôle de règlement n’est créé. Les appels Responses conservent l’effort demandé,
les appels d’outil, leurs résultats et l’historique borné. Les actions visuelles utilisent
l’actionneur Docker existant. Un plan ou un JSON décrivant un clic ne constitue pas une exécution.

Les douze cas R&D exécutent réellement un prototype de placement résilient et une vérification
exhaustive indépendante. Le modèle est un script explicite ; identités, financement et marché
sont fictifs. Aucun appel frontière, clic réel, client ni revenu n’est établi. Le coût réel
complet reste inconnu. La candidate n’est pas admise faute de comparaison avec un Beta frontière
compétent. La réutilisation authentifiée et la croissance d’Alpha restent non qualifiées.

La qualification réelle exige les ressources approuvées décrites ci-dessus. L’admission de
capsules générales exige aussi une extension examinée du périmètre existant et des essais
nouveaux. Ce travail logiciel ne remplace ni cette ingénierie restante ni les contrôles de
publication, l’acceptation du navigateur ou la preuve d’un avantage économique réel.
