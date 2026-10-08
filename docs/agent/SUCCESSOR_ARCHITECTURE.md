# SUCCESSOR Ω: architecture decision 001

Status: implementation candidate; no external qualification or production grant.

## Base and preservation

The inspected main revision is `aab4995ee87f7fb575180931c79b8bf86e26d50d` (1.23.2).
This additive candidate is stacked on reviewed PR #4758 head
`d1fb99e629ec1627e7d3876a330797bde79d5ee6`; neither that PR nor this candidate is automatically merged.
Its repair preservation, release identity and browser corrections remain intact.
The proposed feature version is 1.24.0. Existing journal bytes, five native mission kinds,
research assets, diagrams, contracts and routes retain their meanings and compatibility.

## Decision and dependency order

Extend `alpha_factory_v1.core.runtime` with one `successor` package, using the existing private
single-operator deployment, Ed25519 journal, Pydantic and explicit Docker execution boundary.
No new service stack, wallet, paid provider or model download is needed for the default rehearsal.

1. Protocol: strict versioned records, bounded imports and domain-separated canonical commitments.
2. State: signed durable transactions, principal decisions, shared reservations and action-time authority.
3. Mission: fixed bounded aggregation engines, constructed challengers, WORLD predictions and fresh evaluation.
4. Jobs/Ascension: sealed work, typed dependency dispatch and exact legacy settlement commitments.
5. Chronicle: scoped knowledge admission, independent checkpoints, empty-authority successors and clean restoration.
6. Interfaces: CLI orchestration and equivalent bilingual browser request/evidence transport.
7. Release: adversarial gates, installed-artifact execution, preservation and bounded distribution packs.

The default candidate representation is non-general-purpose configuration of maintained fixed aggregation engines.
It cannot name host operations or execute supplied code. Arbitrary code retains the existing explicit Docker opt-in;
unavailable isolation is a refusal. The browser is a local rehearsal, never a protected final verifier.

## Accountable implementation owners

| Area | Owner | Implementation boundary |
|---|---|---|
| Architecture and integration | Root | CLI, lifecycle wiring, guides, integration review |
| Protocol and schema | Protocol engineer | `successor/protocol.py`, schemas and canonical vectors |
| Runtime and authorization | Runtime engineer | Durable state, trust, job dispatch, grants and recovery |
| Search and evaluation | Mission engineer | Aggregation, formation, WORLD, comparative proof and memory study |
| Ascension and economics | Adapter engineer | Exact chain bindings, work acceptance and settlements |
| Frontend and accessibility | UX engineer | Bilingual rehearsal, handoff, responsive and keyboard workflows |
| Release and operations | Release engineer | Packaging, preservation, source identity and existing CI gates |

Internal engineering review does not establish independent verifier or customer evidence.

## Protocol choices

New canonical objects use compact sorted-key UTF-8 JSON, safe integers and no floating-point commitment values.
Times and measurements use declared integer units; modeled decimals use explicit decimal strings.
Hash domain: `successor-omega/v1:` + ASCII domain + NUL + canonical bytes, SHA-256.
Existing signed formats and Solidity ABI/double-keccak commitments remain unchanged.
Imported keys cannot establish trust. Work acceptance, candidate verdict, settlement, memory admission,
institutional admission and authority are separate records and decisions.

## Initial requirement-to-code-to-test allocation

| Mandate | Implementation | Required verification |
|---|---|---|
| §§4–6 strict objects and authority | protocol/state/trust | Malformed imports, forgery, revocation, grant mixing, budget races |
| §7 sealed jobs | jobs | Missing functions, cycles, typed edges, revoked evidence and exact authorization |
| §8 Ascension | successor adapter + preserved Solidity | Nonzero index, zero-index market hash, negative report, quorum and replay |
| §§9–11 measured mission | mission/evaluation | Constructed challengers, wrong-result rejection, stronger Beta, freeze mutation |
| §§12–13 continuity and economics | state + study + integration | Memory/control trials, empty successor grants, checkpoints and supplier changes |
| §14 user journeys | CLI + browser | EN/FR, cancellation, stale inputs, request-bound round trip and offline cache |
| §§15–17 release | existing acceptance workflow + packaging | Runtime matrix, browser/EVM/Docker, wheel, preservation and file-size gates |

The final validation matrix records actual outcomes and unavailable gates. Software acceptance, local evidence,
external qualification and authorized operation must remain separately visible.
