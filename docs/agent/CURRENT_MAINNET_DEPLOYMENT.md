# Current Mainnet deployment: 18 October 2026

[Research-prototype disclaimer](../DISCLAIMER_SNIPPET.md)

Five fresh Ethereum Mainnet contracts (chain ID 1) are deployed and have Etherscan
EXACT_MATCH verification. Both governor-only one-time bindings have finalized receipts.
The scoped five-contract authority graph was verified at block **26220072**
(`0x8a3357d17a61a8f37c99dc836ac1176c6ee44b6261a81c41893527046c88a088`).
These are point-in-time trusted-provider observations, not a global authority audit.

**Activation and public funding are not approved. There is no global pause.**
This record does not establish full production readiness or authorize any transaction.

## Exact contracts and creation transactions

- **AscensionAccess**: [0x9eE41dF6d076Fa4F89b102b76DEf1c503a1e7C3A](https://etherscan.io/address/0x9eE41dF6d076Fa4F89b102b76DEf1c503a1e7C3A#code)
  Creation: [0xbd76213da1ebba1a6844db3049d301adb728d1d5bb0817040105034f2ba83db0](https://etherscan.io/tx/0xbd76213da1ebba1a6844db3049d301adb728d1d5bb0817040105034f2ba83db0)
- **NovaSeed**: [0x31BD0736DcD55DA2f9a2BB586C8a98695F86f19E](https://etherscan.io/address/0x31BD0736DcD55DA2f9a2BB586C8a98695F86f19E#code)
  Creation: [0x8d0cfaf628c5308164b3f6fc78782b6371269ea20a676cdd56d3cefa04ec0513](https://etherscan.io/tx/0x8d0cfaf628c5308164b3f6fc78782b6371269ea20a676cdd56d3cefa04ec0513)
- **AscensionRiskOracle**: [0x198FC6EBee21c6A0B34E4d055AFD6D811AA6dE58](https://etherscan.io/address/0x198FC6EBee21c6A0B34E4d055AFD6D811AA6dE58#code)
  Creation: [0x28854aa99af51722ecadb843f28cfb502e2fb5b69e4c1c328df053a143679a01](https://etherscan.io/tx/0x28854aa99af51722ecadb843f28cfb502e2fb5b69e4c1c328df053a143679a01)
- **AscensionJobMarket**: [0xc1d3d7fb064C23c46C4EB20d24ab6EA650FF0ceE](https://etherscan.io/address/0xc1d3d7fb064C23c46C4EB20d24ab6EA650FF0ceE#code)
  Creation: [0xc74b0146846ad71ad4840de1e2944e59f9c03d41157edce525b73c02bf567be0](https://etherscan.io/tx/0xc74b0146846ad71ad4840de1e2944e59f9c03d41157edce525b73c02bf567be0)
- **AscensionMark**: [0x6D5323b2609E36fDc4dB3B2501B7BcF0E131033c](https://etherscan.io/address/0x6D5323b2609E36fDc4dB3B2501B7BcF0E131033c#code)
  Creation: [0xa85b88ff97fc3f5312bbfc9e33dccae1653aacb85461c943db115ad222ad480d](https://etherscan.io/tx/0xa85b88ff97fc3f5312bbfc9e33dccae1653aacb85461c943db115ad222ad480d)

## Two finalized bindings

- `bindMarketplace(0xc1d3d7fb064C23c46C4EB20d24ab6EA650FF0ceE)`, nonce 813, block 26219975:
  [0xbe9501a1da1d28c0705e43390a61232f3574f8eadd7583398f9cbb7fc388432b](https://etherscan.io/tx/0xbe9501a1da1d28c0705e43390a61232f3574f8eadd7583398f9cbb7fc388432b)
- `bindMark(0x6D5323b2609E36fDc4dB3B2501B7BcF0E131033c)`, nonce 814, block 26220058:
  [0xaa1339ae0fe993445464e617d6bbbe1e193db2164075d5dc0b7958e311750c88](https://etherscan.io/tx/0xaa1339ae0fe993445464e617d6bbbe1e193db2164075d5dc0b7958e311750c88)

## Authority and source

Governor: `0xd76AD27a1Bcf8652e7e46BE603FA742FD1c10A99`.
The owner-bearing AscensionAccess, AscensionRiskOracle and AscensionJobMarket contracts
have this owner and zero pending owners at the authority block. Ownership is
constructor-set Ownable2Step storage, transferable later by the governor, not immutable.
Dependency addresses use constructor immutables and governor-only one-time bindings.
No creator deployment privilege was observed within this exact five-contract graph.
This statement does not cover external token, proxy, ENS, controller or off-chain authority.

Deployed source commit: `c0fc5217e364a39a4cd123d17a8317c06b80f820`.
Source tree: `6c0ed7b1a5d40662bcd3e124a6d2aedd6447fcf2`.
The publication release may include later documentation changes; it does not change the deployed source revision.

## Deviations and external closeout

The manual calls were verified post hoc. The first call differed from its original
intent in gas limit, maximum fee per gas and priority fee. The second call had no
recorded pre-transaction intent. Observation is not retroactive approval.
Combined actual binding gas cost was **0.000221497159466359 ETH**, exceeding the
original combined proposed maximum of **0.00015 ETH**.
External authority closeout completed at **2026-10-18 15:24:15.848 UTC**, and both
original actor leases were released. Original session sequence 20 remains historically
incomplete and its journal is unchanged. Closeout performed no signing and broadcast
no transactions; it does not recreate missing pre-transaction intent or approve activation.

Independent security review, the external-authority inventory, exact-candidate
real-dependency fork evidence, and separate operator, economic and participant
commissioning and activation approval remain outstanding. Explorer acceptance is
satisfied by the five EXACT_MATCH results; it does not satisfy those other gates.

## Evidence and history

The [sanitized machine-readable record](../deployments/2026-10-18/manifest.json)
contains exact contract addresses, runtime code hashes, observed getters, creation and
binding transactions, explorer ABI/input hashes, and original evidence SHA-256 provenance.
It excludes private operator paths, keys, signed capabilities and journals. It is an
allowlisted projection, not a byte-for-byte copy of the source reports. The subsequent closeout report is
identified separately by its file and payload SHA-256 provenance.

The [11 October archive](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/c0fc5217e364a39a4cd123d17a8317c06b80f820/deployments/ethereum-mainnet/2026-10-11/README.md)
and [15 October verification](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/c0fc5217e364a39a4cd123d17a8317c06b80f820/deployments/ethereum-mainnet/2026-10-15/record-verification.json)
remain historical records and are not rewritten or relabeled as this deployment.
