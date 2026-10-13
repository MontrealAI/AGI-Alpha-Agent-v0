[Project notice](../DISCLAIMER_SNIPPET.md)

# Ethereum mainnet: deployed contracts and owner guide

**Five Ascension contracts were deployed on Ethereum mainnet on October 11, 2026.**
The operator reports completed Etherscan source verification. The public archive does not include the
Etherscan API response or transcript; verify that status independently using the explorer links below.
The recorded on-chain bindings and the two ownership acceptances are checked by the read-only verifier.
The operator reports Ledger custody of the final owner address below.
On-chain evidence establishes the address and successful transactions; it cannot identify a hardware device.

**Before admitting participants or funding jobs, review the source difference below.** The deployed
contracts predate the settlement fixes now in this repository. They are not upgradeable. Publishing this
release neither installs those fixes on-chain nor approves live funding.

## Your deployed addresses

Network: **Ethereum Mainnet (chain ID 1)**. Settlement token: **$AGIALPHA**, 18 decimals,
[`0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`](https://etherscan.io/address/0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA#code).
This is separate from the USDC-based AGIJobManager project.

| Contract | Verified source on Etherscan | Administrative ownership |
| --- | --- | --- |
| AscensionAccess | [0x36f8C079fEEBC81c5AF30D71be5017037246a32e](https://etherscan.io/address/0x36f8C079fEEBC81c5AF30D71be5017037246a32e#code) | Final owner |
| NovaSeed | [0xFA4737Ba7cF111EBb0840aA300BC61D84d303449](https://etherscan.io/address/0xFA4737Ba7cF111EBb0840aA300BC61D84d303449#code) | No administrative owner; individual NFTs have owners |
| AscensionRiskOracle | [0x06cb4D684628846B048d88CCf8C03c4Cfb74f149](https://etherscan.io/address/0x06cb4D684628846B048d88CCf8C03c4Cfb74f149#code) | Final owner; acceptance confirmed |
| AscensionJobMarket | [0x86f84E173A7a1a4588f4e757552F20f7C58e61E8](https://etherscan.io/address/0x86f84E173A7a1a4588f4e757552F20f7C58e61E8#code) | Final owner; acceptance confirmed |
| AscensionMark | [0xa28dA507f7F9AFF8910f1F7cB5d5b8238F5Db625](https://etherscan.io/address/0xa28dA507f7F9AFF8910f1F7cB5d5b8238F5Db625#code) | No administrative owner |

**Final owner:** `0xa9eD0539c2fbc5C6BC15a2E168bd9BCd07c01201`.
**Historical deployer:** `0x6c8B8897Fb6b08B4070387233B89b3E9A94eD00E`.
The deployer no longer owns Access, Oracle or JobMarket. Their pending owners are the zero address.
An explorer's permanent contract-creator label does not mean the creator retains administrative ownership.

Ownership acceptance receipts:
[Oracle](https://etherscan.io/tx/0x802630e8e6655d4ee48857e084cd3846a5b345711ea54be3bfa3fb0224c7691e) ·
[JobMarket](https://etherscan.io/tx/0x3753e652c41aa9d177a4c9d637730621ccba4596740d71996fb908b743076661).
Nine deployment/binding/proposal transactions used **0.004333504290001989 ETH** in gas; including
both Ledger acceptances, the recorded total is **0.004464159109075339 ETH**. This is historical cost,
not a quote for another deployment. No further ownership-acceptance transaction is required.

## Which source belongs to which contract?

| Profile | Source and compiler | What it establishes |
| --- | --- | --- |
| Recorded deployment | [Immutable source/build record](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/deployments/ethereum-mainnet/2026-10-11): Solidity 0.8.24, optimizer 200, via IR, Paris, OpenZeppelin 5.4.0 | The five addresses above, exact runtime hashes and eleven transaction records |
| Current candidate | `contracts/ascension/` and matching `tests/contracts/contracts/ascension/`: Solidity 0.8.37, Cancun, OpenZeppelin 5.6.1 | Later settlement hardening; these bytes have not been deployed at the recorded addresses |
| Protocol Desk demonstration | [Local execution](../ascension-protocol/index.html) | An isolated fixture lifecycle with mock ENS/token; its example payments are not mainnet payments |

The newer source verifies both sides of token payouts and the paying contract's balance during burns.
It also rechecks the eligibility of earlier rejecting validators before a negative quorum can slash an agent.
The recorded deployment lacks these additional checks. The test suite reproduces the earlier negative-quorum
behavior using the exact archived deployment bytecode in an isolated EVM, alongside the current-source fix.

Do not compile the current source and present it as the source of the existing addresses. Do not rerun
deployment to update an existing address. If the newer source is chosen, use a separately reviewed fresh
deployment and an explicit transition plan. No proxy upgrade, automatic migration, global pause, or
arbitrary treasury rescue exists. Keep this deployment's receipts, source identity and user obligations.

## Understand a contract warning

First identify where the warning appears and copy its exact text. A successful build, a green explorer
source badge and a complete operational review answer different questions. The warning text from an
explorer is needed to determine its specific cause; this release does not assert that every recorded
address has the same warning.

| What you see | What it means | Next step |
| --- | --- | --- |
| Solidity warning during a fresh build | A diagnostic for the source and compiler being run | Use the locked current-source qualification commands in the [new-deployment guide](MAINNET_READINESS.md); resolve every compiler warning before release |
| Explorer compiler-version or known-bug notice | A notice about the compiler embedded in that deployment's verified metadata | Compare the exact compiler/settings with the [Solidity known-bug list](https://docs.soliditylang.org/en/latest/bugs.html); review each bug's conditions against the archived source |
| Explorer source or constructor mismatch | The submitted input does not reproduce the deployed build | Use that deployment's exact standard JSON, source paths, libraries and encoded constructor arguments; do not flatten or rebuild with the newer compiler |
| Hardhat stack-trace support notice | A limitation of Hardhat's debugging support for that compiler | Retain the notice and test receipt/state assertions; do not downgrade Solidity or suppress diagnostics to obtain a quieter terminal |
| Dependency audit finding | An advisory for a toolchain package | Run the full locked-toolchain audit; compiler checks and dependency audits are separate gates |

The October 11 archive must remain **Solidity 0.8.24, via IR, optimizer 200, Paris, OpenZeppelin 5.4.0**.
Current-source preparation uses **Solidity 0.8.37, via IR, optimizer 200, Cancun, OpenZeppelin 5.6.1**.
Changing a repository file, compiler setting or explorer submission cannot replace an already deployed
contract's runtime. A compiler notice can remain on an immutable historical deployment after a clean
current-source build. A notice alone also does not prove a particular bug affects that contract.

For the five existing addresses, start with `mainnet:record-check`, then use the read-only check below.
For a new deployment, start with the [current-source preparation guide](MAINNET_READINESS.md).
Keep both build profiles and their evidence separate. The canonical $AGIALPHA token is an external
dependency; this maintenance release does not recompile or replace it.

**En français.** Relevez le texte exact de l'avertissement. Les contrats du 11 octobre restent liés à
Solidity 0.8.24 et à leurs sources archivées. La version actuelle utilise Solidity 0.8.37 pour une nouvelle
préparation. Une publication GitHub ne modifie aucun contrat déployé. Utilisez les fichiers de vérification
correspondant exactement à l'adresse, au compilateur et aux paramètres de cette adresse.

## Prepare exact explorer verification files

If an explorer needs verification or a submission must be reproduced, export the historical profile
from the repository root after the locked `npm ci --prefix tests/contracts` installation:

```sh
npm run mainnet:record-check --prefix tests/contracts
npm run mainnet:verification-package --prefix tests/contracts -- record /operator/new-record-verification
```

Use a new directory outside the repository; PowerShell accepts an equivalent absolute Windows path.
The export includes all five addresses. Each named contract folder has its archived `standard-input.json`,
encoded `constructor-arguments.txt` without `0x`, and `etherscan-request.json` with the exact V2 parameters.
The root `manifest.json` records compiler/settings, address bindings and file digests; `README.txt` walks
through the submission. The original archive is unchanged. No wallet, API key or explorer request is used.

Select **Solidity (Standard-Json-Input)** on Etherscan, select the exact compiler in the manifest, then
upload the file for that address and preserve its fully qualified contract name and constructor arguments.
For an API submission, supply your API key separately, retain the returned GUID and check the final status;
a GUID is a pending submission, not successful verification. Retain the final response and independently
check the explorer's address/source/runtime match. Exporting files does not establish explorer acceptance.
Use `plan` mode only for a separately reviewed new deployment, as explained in the
[new-deployment guide](MAINNET_READINESS.md#5-verify-the-deployed-result-before-use).

## Check the existing deployment safely

These commands run from a clean checkout of the matching release. They require Node.js **22.17.1**.
They do not request a private key, import a wallet, send a transaction, change an owner, or charge gas.

First install the locked tools and check the local evidence:

```sh
nvm use
npm ci --prefix tests/contracts
npm run mainnet:record-check --prefix tests/contracts
```

To compare against live mainnet, supply your HTTPS Ethereum RPC URL locally. In Ubuntu Bash, the following
prompt keeps it out of terminal history and hides input. Use a provider whose history you trust.

```bash
set +x
read -r -s -p 'Ethereum mainnet HTTPS RPC URL (hidden): ' MAINNET_RPC_URL
printf '\n'
export MAINNET_RPC_URL
npm run mainnet:record-verify --prefix tests/contracts -- "$HOME/ascension-mainnet-check-$(date +%Y%m%d-%H%M%S).json"
unset MAINNET_RPC_URL
```

Expected success: `governanceComplete: true`, `externalTransactions: false`, and a new report path.
The report records a finalized block, all eleven successful canonical receipts, complete runtime hashes,
constructor/call data, owners, pending owners, immutable bindings, ENS role roots and parameters.
It does not require empty seed/job counters, so legitimate later activity is not mistaken for a bad deployment.
It does not establish current dependency implementation safety, participant eligibility, or operational approval.

If verification fails, retain the output/error and inspect the named mismatch. A changed owner or parameter
can be a legitimate governance action, but it still differs from the registered baseline and needs review.
An unavailable RPC or missing historical transaction is unresolved, never a pass. Wait if the latest
finalized block has not reached the recorded acceptance. The tool refuses an existing report filename.
Compare important results through a second independent provider. Never share RPC credentials or wallet secrets.

## What still needs commissioning?

Deployment and ownership are complete. The report intentionally leaves `participantCommissioning` as
`not-assessed` and `readyForPublicFunding` as `false`. The earlier operator report's
`operationallyCommissioned: false` was a fixed marker, not a live readiness test.

Before admitting participants or funding jobs, resolve the deployed/current-source difference and record
the selected addresses and reviewed code. Then establish namespace controller access, admission rules,
independent reviewers, token/stake limits, evidence storage, deadline monitoring, incident response and
an observed end-to-end settlement. The earlier mainnet-fork rehearsal used impersonation only inside
an isolated development chain; it does not prove real participant consent or controller custody.

Governance does not control the existing $AGIALPHA token or ENS namespace owners merely by owning these
three contracts. Agent identities use `*.alpha.agent.agi.eth`, validators use `*.alpha.club.agi.eth`, and
businesses use `*.alpha.agi.eth`. Preserve those distinctions from the separate AGI Jobs namespaces.

For a **new current-source deployment**, follow [mainnet preparation and commissioning](MAINNET_READINESS.md).
For **this existing deployment**, use `mainnet:record-verify`. The current-source `mainnet:verify` command
expects a different unsigned-plan schema and compiler profile and must not be used with this record.

Back up the original operator directory privately, especially its configuration, journal, artifacts,
rehearsal and verification reports. The public archive contains selected public evidence and compiler
inputs only; it contains no private key, API key, seed phrase, signed pending transaction, or wallet backup.

## En français

Les cinq contrats sont déployés sur **Ethereum mainnet**. La vérification des sources sur Etherscan est
rapportée par l'opérateur; sa réponse API et sa transcription ne figurent pas dans l'archive publique.
Vérifiez ce statut au moyen des liens vers l'explorateur. Les transferts de propriété vers l'adresse finale
sont terminés; sa garde sur Ledger est rapportée par l'opérateur. Aucune nouvelle acceptation n'est nécessaire.
Les contrats déployés précèdent les dernières corrections de règlement du dépôt et ne sont pas modifiables.
Avant toute admission ou tout financement, faites examiner cette différence et décidez d'un déploiement
distinct si les corrections sont requises. `mainnet:record-verify` vérifie les contrats existants en lecture
seule, sans clé privée et sans frais. Un résultat positif ne remplace pas la mise en service des participants.
