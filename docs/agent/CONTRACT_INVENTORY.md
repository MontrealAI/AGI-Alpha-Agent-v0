[Project notice](../DISCLAIMER_SNIPPET.md)

# Smart-contract development and deployment inventory — 1.33.0 candidate

This inventory covers every checked-in Solidity source in this candidate, including
legacy, optional, mock, adversarial and archived code. Inclusion is a development
classification, not a claim that every component was deployed, externally audited
or explorer-verified. The [second-deployment runbook](SECOND_MAINNET_DEPLOYMENT.md)
limits the pending mainnet campaign to five new Ascension addresses.

## Qualification boundaries

- `compile:production` compiles all 15 production Solidity source files under
  `contracts/`, including legacy modules absent from Hardhat fixtures. Compilation
  alone does not establish legacy integration, exhaustive behavioral coverage or
  permission to deploy them.
- `compile:strict` also forces the fixture build; matching production mirrors must
  remain byte-identical. Run the complete locked contract test suite and retain
  individual test evidence. Mocks and adversarial harnesses support those tests;
  they do not replace real AGIALPHA/ENS in the required new-candidate fork.
- AscensionToken, Constants, interfaces and imported OpenZeppelin helpers/libraries
  belong in each applicable exact Standard JSON source closure. No separately
  deployed linked library is permitted by the current planner. Any nonempty link
  reference expands scope and requires its own address, deployment receipt,
  runtime/source verification and independent review before signing.
- The October 11 archive preserves its own solc 0.8.24/OpenZeppelin 5.4.0/Paris
  profile. Do not replace it with current solc 0.8.37/OpenZeppelin 5.6.1/Cancun
  output. The historical read-only report does not qualify any new address.
- Existing AGIALPHA, ENS registry, Name Wrapper and registrar are reused external
  contracts. Verify their exact sources/runtime, proxy implementations and upgrade
  authorities separately against fresh finalized evidence. The selected Ledger
  EOA has no contract source to publish. A Safe governor is an optional alternative
  requiring implementation/module/guard/fallback and control checks if selected.
- Separate AGI Jobs/USDC AGIJobManager deployments are not qualified by this
  repository's five-address Ascension campaign.

## Complete checked-in Solidity source coverage

Names include contracts, libraries and interfaces declared in each file. Repeated
names are deliberate mirrors or archived profiles, not additional live addresses.

| Source file | Declared units | Development/deployment classification |
| --- | --- | --- |
| `contracts/ascension/AscensionAccess.sol` | IAscensionENS, IAscensionWrapper, AscensionAccess | Required new Ascension deployment |
| `contracts/ascension/AscensionJobMarket.sol` | IAscensionMarkBinding, AscensionJobMarket | Required new Ascension deployment |
| `contracts/ascension/AscensionMark.sol` | AscensionMark | Required new Ascension deployment |
| `contracts/ascension/AscensionRiskOracle.sol` | IAscensionJobBinding, AscensionRiskOracle | Required new Ascension deployment |
| `contracts/ascension/AscensionToken.sol` | IAscensionBurn, AscensionToken | Inherited helper, not separately deployed |
| `contracts/ascension/NovaSeed.sol` | NovaSeed | Required new Ascension deployment |
| `contracts/v2/CertificateNFT.sol` | CertificateNFT | Legacy development source; outside five-address campaign |
| `contracts/v2/Constants.sol` | Constants | Embedded canonical-address library; also imported by Ascension |
| `contracts/v2/DisputeModule.sol` | IStakeManager, IJobRegistry, DisputeModule | Legacy development source; outside five-address campaign |
| `contracts/v2/IdentityLib.sol` | INameWrapper, IENS, IResolver, IdentityLib | Legacy development source; outside five-address campaign |
| `contracts/v2/JobRegistry.sol` | IValidationModule, IStakeManager, IReputationEngine, IDisputeModule, ICertificateNFT, ITaxPolicy, JobRegistry | Legacy development source; outside five-address campaign |
| `contracts/v2/ReputationEngine.sol` | ReputationEngine | Legacy development source; outside five-address campaign |
| `contracts/v2/StakeManager.sol` | IERC20Burnable, StakeManager | Legacy development source; outside five-address campaign |
| `contracts/v2/TokenUtils.sol` | TokenUtils | Legacy development source; outside five-address campaign |
| `contracts/v2/ValidationModule.sol` | IStakeManager, IReputationEngine, IJobRegistry, IValidationModule, ValidationModule | Legacy development source; outside five-address campaign |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/AscensionAccess.sol` | IAscensionENS, IAscensionWrapper, AscensionAccess | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/AscensionJobMarket.sol` | IAscensionMarkBinding, AscensionJobMarket | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/AscensionMark.sol` | AscensionMark | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/AscensionRiskOracle.sol` | IAscensionJobBinding, AscensionRiskOracle | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/AscensionToken.sol` | IAscensionBurn, AscensionToken | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/ascension/NovaSeed.sol` | NovaSeed | Archived October 11 source; original-profile evidence only |
| `deployments/ethereum-mainnet/2026-10-11/sources/contracts/v2/Constants.sol` | Constants | Archived October 11 source; original-profile evidence only |
| `tests/contracts/contracts/ascension/AdversarialSettlement.sol` | SettlementHarness, AdversarialSettlementToken | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/ascension/AscensionAccess.sol` | IAscensionENS, IAscensionWrapper, AscensionAccess | Byte-identical production fixture mirror |
| `tests/contracts/contracts/ascension/AscensionJobMarket.sol` | IAscensionMarkBinding, AscensionJobMarket | Byte-identical production fixture mirror |
| `tests/contracts/contracts/ascension/AscensionMark.sol` | AscensionMark | Byte-identical production fixture mirror |
| `tests/contracts/contracts/ascension/AscensionRiskOracle.sol` | IAscensionJobBinding, AscensionRiskOracle | Byte-identical production fixture mirror |
| `tests/contracts/contracts/ascension/AscensionToken.sol` | IAscensionBurn, AscensionToken | Byte-identical production fixture mirror |
| `tests/contracts/contracts/ascension/MockENS.sol` | MockAscensionENS, MockAscensionWrapper | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/ascension/NovaPlanProofHarness.sol` | NovaPlanProofHarness | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/ascension/NovaSeed.sol` | NovaSeed | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/CertificateNFT.sol` | CertificateNFT | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/Constants.sol` | Constants | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/ConstantsHarness.sol` | ConstantsHarness | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/IdentityHarness.sol` | IdentityHarness | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/IdentityLib.sol` | INameWrapper, IENS, IResolver, IdentityLib | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/JobRegistry.sol` | IValidationModule, IStakeManager, IReputationEngine, IDisputeModule, ICertificateNFT, ITaxPolicy, JobRegistry | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/StakeManager.sol` | IERC20Burnable, StakeManager | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/ValidationModule.sol` | IStakeManager, IReputationEngine, IJobRegistry, IValidationModule, ValidationModule | Byte-identical production fixture mirror |
| `tests/contracts/contracts/v2/mocks/MaliciousCertToken.sol` | MaliciousCertToken | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/mocks/MaliciousToken.sol` | MaliciousToken | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/mocks/MockAGI.sol` | MockAGI | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/mocks/MockReputationEngine.sol` | MockReputationEngine | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/mocks/MockTaxPolicy.sol` | MockTaxPolicy | Local test/mock/adversarial harness only; never a live dependency substitute |
| `tests/contracts/contracts/v2/mocks/MockValidationStakeManager.sol` | MockValidationStakeManager | Local test/mock/adversarial harness only; never a live dependency substitute |

## Exact post-deployment verification for every deployed address

Keep separate status/evidence fields for deployment, runtime and explorer source
verification. All five new Ascension addresses remain PENDING until actual evidence
exists. Record chain ID, exact plan/commit/tree/lock digest, fully qualified source
name, compiler/settings, constructor arguments, sender/nonce/creation transaction,
successful canonical receipt and finalized block/hash. Verify every runtime from
the same reviewed build; separately read every masked immutable through its getter,
then check owner/pending owner, bindings, token, parameters, role roots and fresh
counters. Retain both governor binding-call receipts and the same-plan
`mainnet:verify` report. Reconcile interruptions before any subsequent transaction.

Export `mainnet:verification-package -- plan` from that same clean build for all
five contracts, preserving embedded imports and metadata. Submit exact Standard
JSON, fully qualified contract name, compiler version/settings and ABI constructor
arguments for each actual address. Retain the final explorer response and check
address/source/runtime correspondence. A submission GUID is pending, not success.
Repeat material chain checks through an independent provider. Do not silently mark
optional, legacy, helper or reused external contracts verified by another row's
result. A different optional deployment requires its own reviewed inventory and
complete receipt/runtime/source evidence before use.

Source verification and deployment success do not authorize public funding or
participant admission. Real-token rehearsal, current dependency review and the
operating/go-live decision remain separate. Record unavailable or owner-omitted
checks explicitly; never present them as passed.
