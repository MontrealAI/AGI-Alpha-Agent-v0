# SUCCESSOR Ω: current Ascension references

[Project notice](../DISCLAIMER_SNIPPET.md) · [Flagship guide](SUCCESSOR_ALPHA.md) ·
[Current deployment and evidence](CURRENT_MAINNET_DEPLOYMENT.md) ·
[Public address directory](../deployments/2026-10-18/index.html)

The flagship uses the **October 18, 2026 deployment record** for Ethereum mainnet (`chainId: 1`).
Retained explorer reports record five **EXACT_MATCH** results. The scoped five-contract authority graph
and two finalized bindings were observed at block **26220072**
(`0x8a3357d17a61a8f37c99dc836ac1176c6ee44b6261a81c41893527046c88a088`).
These are point-in-time trusted-provider observations retained in the public record; this flagship does
not perform a fresh live RPC or explorer verification.

**Activation and public funding remain unapproved.** The local flagship needs no contract interaction.
Its machine-readable snapshot is
[`examples/successor-alpha/deployment.json`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/examples/successor-alpha/deployment.json).

| Contract | Address and code page |
| --- | --- |
| AscensionAccess | [0x9ee41df6d076fa4f89b102b76def1c503a1e7c3a](https://etherscan.io/address/0x9ee41df6d076fa4f89b102b76def1c503a1e7c3a#code) |
| NovaSeed | [0x31bd0736dcd55da2f9a2bb586c8a98695f86f19e](https://etherscan.io/address/0x31bd0736dcd55da2f9a2bb586c8a98695f86f19e#code) |
| AscensionRiskOracle | [0x198fc6ebee21c6a0b34e4d055afd6d811aa6de58](https://etherscan.io/address/0x198fc6ebee21c6a0b34e4d055afd6d811aa6de58#code) |
| AscensionJobMarket | [0xc1d3d7fb064c23c46c4eb20d24ab6ea650ff0cee](https://etherscan.io/address/0xc1d3d7fb064c23c46c4eb20d24ab6ea650ff0cee#code) |
| AscensionMark | [0x6d5323b2609e36fdc4db3b2501b7bcf0e131033c](https://etherscan.io/address/0x6d5323b2609e36fdc4db3b2501b7bcf0e131033c#code) |

## What has been established

The deployment source is commit
[`c0fc5217e364a39a4cd123d17a8317c06b80f820`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/c0fc5217e364a39a4cd123d17a8317c06b80f820),
source tree `6c0ed7b1a5d40662bcd3e124a6d2aedd6447fcf2`. Later release or website changes do not replace
that deployed-source identity.

The [retained public projection](../deployments/2026-10-18/manifest.json) contains runtime hashes,
creation receipts, finalized binding transactions, observed getters, explorer input/ABI digests and
SHA-256 provenance for the original verification evidence. The flagship snapshot pins that record's
bytes and preserves those distinct proof digests; an original report digest is not the digest of the
sanitized projection. It does not include private operator paths, keys, signed capabilities or journals.

At the recorded block, the three owner-bearing contracts identify governor
`0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99` and zero pending owners. This is transferable Ownable2Step
storage, not immutable ownership. The scoped graph records constructor dependency immutables and
governor-only one-time bindings; it does not establish external token, proxy, ENS, controller or off-chain
authority. There is no global pause. Consult the current guide for the post-hoc manual-binding deviations,
external closeout and the historically incomplete original session; observed execution is not retroactive approval.

## How the flagship uses this record

Local capability development and comparison require no wallet. The addresses are displayed as transparent
references for the optional Ascension route. The reference record does not grant contract permissions,
activate a paid work cycle or authorize signing. Preparing and exporting a local project sends no transaction.

Funded execution still requires the outstanding independent security review, external-authority inventory,
exact-candidate real-dependency fork evidence and separate operator, economic and participant commissioning.
Validate the matching client ABI, configured token route and current state before any authorized operation.
A retained source-verification result and historical authority observation are not present permission to act.

USDC commissioning and `$AGIALPHA` commissioning retain their distinct budgets, interfaces, acceptance and
settlement requirements. This Ascension reference record does not update another work route automatically.

Historical deployment manifests and their qualification boundaries remain intact. Existing operator tools
continue to enforce their own qualified deployment requirements; this reference file is not an override.

## Références actuelles

Le dossier conservé du 18 octobre 2026 répertorie cinq résultats **EXACT_MATCH**, les créations et les deux
liaisons finalisées. Le graphe d'autorité limité aux cinq contrats a été observé au bloc **26220072** par
un fournisseur de confiance. Ce parcours présente ce dossier daté; il n'effectue aucune nouvelle vérification
RPC ou de l'explorateur en direct. Le code déployé reste lié au commit `c0fc5217e364a39a4cd123d17a8317c06b80f820`.

Le parcours local reste utilisable sans portefeuille. Ces références ne confèrent aucun droit de signature,
d'exécution ou de dépense. Toute exécution financée exige la configuration qualifiée correspondante et une
autorisation distincte. Les routes USDC et `$AGIALPHA` restent séparées.
