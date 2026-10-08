[See the project disclaimer](../DISCLAIMER_SNIPPET.md)

# SUCCESSOR Ω · exact Ascension adapter

The adapter adds attributable, sealed work contracts to the existing Ascension lifecycle. It does not change
Solidity, the token, ENS rules, auctions, collateral, committee quorum, payouts or refunds. Existing native
`alpha-agent ascension-*` commands and their legacy local review scope remain supported.

The implementation is `alpha_factory_v1/core/runtime/successor/ascension.py`. The executable contract tests are
`tests/contracts/test/ascension/successor-adapter.test.js`. The contract project runs only against its own
unforked, in-process Hardhat instance. It refuses `localhost`, URL-backed and forked providers before fixture
mutation. Its token balances, ENS ownership and validators are local fixtures. They establish neither live
commissioning nor independent organizations.

## Preserved protocol identity

| Binding | Existing meaning |
|---|---|
| Token | `$AGIALPHA`, 18 decimals, `0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA` |
| Business | `*.alpha.agi.eth` |
| Agent | `*.alpha.agent.agi.eth` |
| Validator | `*.alpha.club.agi.eth` |
| Indexed plan leaf | `hashSpec(actualPlanIndex, spec)` verified by MARK |
| Stored market specification | `hashSpec(0, spec)` stored by the job market |
| Paid work | Two approving committee votes over the exact delivered result |
| Missing review quorum | Full bounty refund and collateral unlock; no invented failure/slash |
| Rejected delivered work | Existing negative-quorum failure and bond-slash accounting |
| Burn | `floor(gross / 100)` separately for each actual payout |

The indexed leaf is the exact legacy double Keccak-256 of the six ABI words: `uint32 index`, goal hash,
success-metric hash, `uint96 bounty`, `uint32 duration`, `uint16 priceWeight`. Identical specifications at two
indices have different plan leaves but the same stored market hash. Neither legacy commitment includes the
new terms, release, environment or authority. The adapter never retroactively claims otherwise.

## Two-stage work binding

1. `seal_terms` validates a richer `JobContract`, its exact legacy `JobSpec`, and either an explicit standalone
   relationship or a verified MARK/seed/FusionPlan relationship. It observes the current block, code identities
   and marketplace next ID, then saves a signed immutable seal in the existing journal. The future market job ID
   and auction winner remain unresolved. Set `JobContract.worker=None` for an open auction.
2. Post/assign through the existing authorized protocol. This adapter never posts, approves, bids, deploys or
   sends a transaction. Local tests perform those operations only inside their disposable fixture.
3. `bind_assignment` checks actual posting and assignment receipts, the preposting checkpoint, selected worker,
   plan index, route, seed, stored market hash, exact release/environment and bounded authorization expiry.
   Historical or already completed jobs cannot acquire these obligations through a late seal. Authorization
   must expire no later than the contract's delivery deadline or the work terms.
4. The institution controller separately signs the runtime `ExecutionAuthorization`, attaching
   `market_binding_digest=binding["digest"]`. The runtime verifies the market observer's separately pinned key,
   its own controller trust, exact authorization, dependencies, resources and action-time authority. An adapter
   signature is a binding record, not an operational grant.
5. `bind_delivery` commits exact artifact bytes and the candidate verdict. `import_settlement` checks fetched
   bytes, successful canonical receipts, configured confirmation depth, contract state, approving/rejecting
   review evidence and integer payout/refund/burn accounting. URI text alone never validates an artifact.

`MarketContext` binds the chain ID, market address and runtime-code hash, canonical token runtime-code hash,
protocol version, evidence scope and confirmation requirement. MARK jobs additionally require MARK/seed
addresses, code hashes and seed ID; partial relationships are rejected. `MarketReader(context, rpc)` accepts
an operator-supplied authenticated, bounded read-only JSON-RPC transport. It uses `eth_chainId`, `eth_getCode`,
`eth_call`, `eth_getBlockByNumber`, `eth_getTransactionReceipt` and `eth_getLogs` only.

Code hashes, node trust and finality policy must come from the operator's trust configuration, not an imported
receipt. The adapter is not a consensus light client; a trusted transport authenticates the node's statements.
A self-consistent local journal does not independently timestamp a preregistration. Use the institution's
independently retained checkpoint workflow when stronger preregistration or rollback protection is required.

## Developer integration

The inputs below are validated operator/job records and previously observed transactions; the example issues
no transaction. Supply `job`, `spec`, `context`, `rpc`, `plan`, `plan_index`, `job_id`, transaction hashes and
`proposed_authorization` from the application's controlled workflow.

```python
from alpha_factory_v1.core.runtime.successor.ascension import (
    MarketReader, seal_terms, bind_assignment, bind_delivery, import_settlement,
)

reader = MarketReader(context, rpc)
seal = seal_terms(journal, job, spec, reader, plan=plan, index=plan_index)
binding = bind_assignment(
    journal, seal, reader, market_job_id=job_id, posting_tx=posting_tx,
    assignment_tx=assignment_tx, execution_authorization=proposed_authorization,
)
authorization = {**proposed_authorization, "market_binding_digest": binding["digest"]}
```

The controller must sign `authorization` through the existing runtime trust interface before dispatch. The
selected worker needs its separately configured runtime identity and permitted capabilities. After authorized
work and the existing market's artifact review:

```python
delivery = bind_delivery(journal, binding, artifact_bytes, candidate_verdict="FAIL")
settlement = import_settlement(
    journal, binding, delivery, artifact_bytes, reader, settlement_tx=closing_tx,
)
```

A correct negative evaluation can have `job_acceptance="accepted"`, `candidate_verdict="FAIL"`, and
`settlement_status="paid"` together. Memory admission, institutional admission and authority remain
`"not_granted"`; customer realized value remains unmeasured. Final-proof compensation does not depend on a
favorable candidate verdict. The import path covers authorized, delivered jobs; the unchanged legacy contract
also retains its unawarded-auction and missed-delivery recovery paths.

Imports serialize through the journal's transaction and use one attribution key per chain/market/job. Identical
retries return the same receipt. Different institutions, missions, artifacts or authorizations cannot reuse an
already attributed payment. `list_settlements(journal, institution_id, cx)` supplies the portable export with
signed settlement records from the caller's consistent snapshot. Historical signed bodies remain exact strings;
private keys are excluded. `validate_historical_settlement(record)` authenticates the original signed bytes,
identity and attribution before a restore retains them as historical records. Embedded keys establish historical
provenance only; the separately trusted export supplies custody. Restore and replay never reissue authority.

## Reproduce the local engineering evidence

From the unpacked source distribution or repository, use the supported Python operator/development environment
and Node version in `.nvmrc`. No wallet, paid provider or real assets are required. `npm ci` and first compilation
need the normal development dependency/compiler downloads; they are not part of the dependency-free rehearsal.

```sh
python -m pytest tests/runtime/test_successor_ascension.py tests/runtime/test_ascension_handoff.py -q
cd tests/contracts
npm ci
ALPHA_PYTHON=python npx hardhat test test/ascension/successor-adapter.test.js
npm test
```

`ALPHA_PYTHON` selects the installed Python environment; an absolute interpreter path is supported. Optionally set
`SUCCESSOR_EVM_EVIDENCE_DIR` to a **new empty output directory** to retain the seals, exact artifact, execution and
delivery bindings, reviews and settlement receipts. Existing evidence files are never overwritten.

The integration test executes a bounded arithmetic candidate, records its wrong answer, produces an accurate
FAIL report, settles that report through two fixture validators, and verifies the real chain receipts in Python.
It also tests a nonzero plan index with identical specs, duplicate import, artifact tampering, no-quorum refund
and unlock, and refusal of non-disposable fixture environments. Additional Python tests cover chain/contract/
worker/release/environment mismatches, rich-term mutation, expiry, concurrency, burn rounding and signed export.

## Français · fonctionnement et limites

L'adaptateur conserve les contrats, le jeton `$AGIALPHA`, les espaces ENS et les règles économiques existantes.
Les conditions complètes sont scellées **avant** la publication. Après l'attribution réellement observée,
l'autorisation d'exécution lie le travailleur, la mission, la version exacte et l'environnement. Le contrôleur
accorde séparément les permissions; une signature, un paiement ou un nom ENS ne les remplace pas.

Un rapport d'évaluation exact peut conclure « FAIL » et être accepté puis payé. Le candidat reste non admis,
sans permission opérationnelle nouvelle. L'absence de quorum entraîne le remboursement et le déverrouillage
prévus; elle ne constitue pas une preuve d'échec du travail. Les imports répétés n'attribuent aucun paiement deux
fois. Les essais Hardhat utilisent uniquement des actifs et identités de test, dans un processus local jetable;
ils ne démontrent aucune validation indépendante ni autorisation de production.
