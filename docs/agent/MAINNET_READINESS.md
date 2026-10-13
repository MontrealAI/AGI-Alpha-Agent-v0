[Project notice](../DISCLAIMER_SNIPPET.md)

# Prepare a new Ethereum mainnet deployment — 1.28.1

For the **already deployed October 11 contracts**, use the [deployed addresses and owner guide](MAINNET_DEPLOYMENT.md).
Those contracts have completed ownership transfer but predate this guide's current source and compiler profile.
The commands below prepare a **separate new deployment** with a configured multisignature governor.
They do not upgrade, replace, or verify the existing Ledger-owned deployment.

**Release status: preparation tooling implemented and locally tested; mainnet commissioning is pending.**
A passing software release is not an independent contract audit or evidence of a live deployment.
This guide gives operators an exact, inspectable path from reviewed source to unsigned deployment,
read-only preflight and post-deployment verification. No command here imports a key or broadcasts a transaction.
The [first-use page](../start/index.html) continues to work without a wallet or payment.

## What is ready, and what is still needed?

| Item | Evidence in this release | Required before public funding |
| --- | --- | --- |
| Source, compiler and dependencies | Locked Hardhat 2.29.1, ethers 6.17.0, OpenZeppelin 5.6.1; Solidity 0.8.37, via IR, optimizer 200, explicit Cancun target | Independent review of the exact commit, dependency implementations and economics |
| Deployment data | Five CREATE transactions with explicit deployer nonces, predicted addresses and constructor arguments; two separate governance calls | Reviewed operator addresses, fresh nonces, current gas limits/fees and simulation in the signing interface |
| Token and identities | Canonical $AGIALPHA address/18 decimals; Ethereum ENS registry and Name Wrapper; expected ENS role-root owners | Finalized RPC evidence and a real-token mainnet-fork lifecycle, including deposits, withdrawals, burn and settlement |
| Governance | Direct ownership by the configured multisignature; owners and threshold (at least two) checked | Independent confirmation of the Safe implementation, modules, guards, fallback handler and signer control |
| Settlement | Exact sender/recipient payout deltas, own-balance and total-supply burn checks, current rejection quorum before slashing | Adversarial review, operating limits and an incident response exercise |
| Published contracts | Read-only verifier compares compiler runtime, immutable bindings, owners, token, parameters and empty seed/job counters | Explorer source verification, receipts, finality, admission review and go-live decision |
| Web access and capacity | Guided bilingual, accessible browser journey; static hosting | Measured capacity and service operations for any future public multi-tenant service; no billion-user claim |

The scripts intentionally never emit `readyToBroadcast: true` or authorize public funding. The live-chain
items above cannot be inferred from mock EVM tests. For this current-source candidate, a selected production multisignature and exact-build fork/audit evidence
remain required. The archived earlier deployment's Ledger address and fork results do not satisfy those
requirements for different bytecode. Do not reuse the example placeholders as live configuration.

## 1. Prepare an exact release checkout

Use a clean checkout of the **release tag**, Node.js 22.17.1 and the committed lockfile. Put configuration,
plans and provider credentials outside the repository. A plan or verification from a dirty checkout is refused.

```sh
git checkout v1.28.1
nvm use
cd tests/contracts
npm ci
npm run audit
npm run compile:strict
npm test
```

`compile:strict` forces a complete build with the exact npm-locked Solidity compiler. The compiler gate
rejects every Solidity warning; it does not hide or downgrade diagnostics. This release review found no
Solidity warnings in the baseline compilation: the new gate prevents later regressions. A normal cached
build is insufficient evidence for that check.

The contract dependency audit includes development dependencies: this is the compilation toolchain.
Publication fails on moderate, high or critical advisories. Hardhat 2 retains the low-severity elliptic
advisory in its legacy ABI dependency graph; it is not represented as zero findings. Imported production
keys and signing are absent from these scripts. The compatibility overrides in `package.json` replace
vulnerable archive, HTTP, serialization, temporary-file and UUID dependencies; the complete suite tests
the resulting lock. Reassess advisories and compatibility whenever that lock changes.
Hardhat may warn that stack traces for Solidity 0.8.37 are not fully supported; compilation and receipt/assertion
checks still run. Do not downgrade the compiler to remove a diagnostic warning.

## 2. Fill in the operator configuration

Copy `tests/contracts/mainnet.example.json` to a private operator folder. Replace every `REPLACE_...`
value with a reviewed public address/hash. This file contains no signing key or RPC URL.

- `deployer`: dedicated Ethereum EOA with five consecutive nonces available. Do not use a Safe,
  an account with delegated code, a shared operational wallet or a wallet with pending transactions.
- `governor`: deployed multisignature address, runtime-code hash, exact owners and threshold.
  The governor owns all three administrative contracts from their constructors. There is no temporary
  deployer ownership or later handover to forget.
- `block`: finalized Ethereum mainnet block number and hash. Record the provider and retrieval time
  privately. Independently check the block and dependency source deployments through a second provider.
- `dependencies`: reviewed code hashes for the canonical token, ENS registry and Name Wrapper.
  A proxy's runtime hash does **not** bind its implementation. Inspect token/proxy implementation slots,
  upgrade authorities and Safe configuration independently and include them in the audit/fork evidence.
- `rootOwners`: expected effective owners of `alpha.agi.eth`, `alpha.agent.agi.eth`, and
  `alpha.club.agi.eth`. Wrapped roots must have unexpired ownership. This check does not issue names
  or establish your legal/organizational control of their owners.
- `parameters`: minimum stakes in integer token base units, review quorum and risk limit. The example's
  values are local defaults, not an economic recommendation. Have governance explicitly approve them.

The schema rejects unknown fields, zero addresses, placeholder hashes, duplicate governance owners,
unsafe thresholds, wrong token/ENS addresses, noninteger nonces and out-of-range parameters.

## 3. Generate the unsigned plan and inspect mainnet

```sh
npm run mainnet:plan -- /operator/config.json /operator/new-plan.json
# Set MAINNET_RPC_URL through your private environment/secret manager (HTTPS only).
npm run mainnet:preflight -- /operator/config.json /operator/new-preflight.json
```

PowerShell uses the same npm commands with Windows paths; configure `MAINNET_RPC_URL` with your
secret manager or `$env:MAINNET_RPC_URL`. Never paste credentials into an issue or commit them.
The RPC adapter allows only chain/block/code/call/nonce/balance reads, rejects redirects and redacts
provider errors. It has no transaction, wallet, impersonation, fixture-reset or state-override method.
Each output is written exclusively; use a new filename for each attempt. Failed checks exit nonzero.

The plan contains the exact source revision/tree and lock digest, compiler standard JSON inputs,
source digests, deployment bytecode, constructor arguments, predicted addresses and checksum.
The checksum detects accidental modification; it is not an operator signature or independent approval.
Store the preflight with its matching configuration digest. A read-only preflight cannot test fee-on-transfer,
blacklisting, upgrades, burn semantics or whether a transaction will succeed. A failed or unavailable RPC
check is unresolved, never a pass.

## 4. Rehearse, review and sign separately

Have an independent reviewer examine the exact plan and source. Run the complete protocol lifecycle
on a **separate mainnet fork pinned to the reviewed block**, with the real token/ENS implementations.
Do not add a URL or fork to the local fixture config: that config deliberately refuses external networks
and its mock-installation helpers must never touch a funded node. Retain the fork block, script, receipts,
balance/supply invariants and resolved findings. Test expiry, validator removal, timeout refunds,
failed burns, governance compromise response and interrupted deployment recovery.

After review, repeat preflight immediately before signing. In your hardware-wallet or approved signing
system, simulate and send the five `transactions` in order with their exact sender, chain ID 1, nonce,
zero ETH value and data. Select current fees and gas limits in that system; the plan deliberately contains
no stale quote. Confirm each successful receipt and expected creation address before continuing.
Do not send a later transaction after a failed or replaced earlier one without reconciling nonce/address
predictions. The plan is a review document, not a directly importable wallet format.

After all five contracts exist, the governance multisignature executes the two `governanceCalls` as
ordinary **CALL** operations (`operation: 0`, never DELEGATECALL), in order. Both bindings are one-time.
Keep admissions and funding closed until final verification. No script mints a token, replaces the
canonical token, migrates balances, opens a campaign or grants admission.

## 5. Verify the deployed result before use

From the same clean source checkout with the same lockfile and compiled artifacts:

```sh
npm run mainnet:verify -- /operator/new-plan.json /operator/new-verification.json
```

The verifier validates the plan checksum, regenerates the plan from current source, and requires the
recorded commit/tree/lock to match. It reads the latest finalized block, rechecks dependencies,
ENS/governance configuration, consumed deployment nonces and every deployed runtime. Compiler
immutable positions are masked only for bytecode comparison; each immutable is separately read back
through its getter and checked against the plan. Owners and pending owners, one-time bindings, stakes,
quorum, risk threshold, role roots and fresh seed/job counters must match. Retain the block and observed
runtime-code hashes. This is a **fresh-deployment commissioning check**, not an ongoing health check
for an already active protocol.

Export the matching explorer package from the same reviewed checkout:

```sh
npm run mainnet:verification-package -- plan /operator/new-plan.json /operator/new-verification-package
```

The exporter rebuilds and compares the plan against the current compiled sources. It refuses a different
plan/build or an existing output directory. Each contract folder contains `standard-input.json`,
`constructor-arguments.txt` (ABI hex without `0x`) and `etherscan-request.json` for the Etherscan V2 API.
`manifest.json` lists addresses, exact compiler/settings and file digests. `README.txt` gives the submission steps.
The command only writes local files; it sends no explorer request and needs no API key or signing key.
Planned addresses remain predictions until deployment is independently verified.

Publish each contract's exact Standard JSON using its compiler version, fully qualified source/name and
constructor arguments. Preserve imports and metadata; do not flatten or change optimizer/EVM settings.
If submitting through the API, supply the API key separately and retain the final verification status:
a submission GUID only means pending. Check the explorer's final address/source/runtime comparison and
publish address/chain/block, plan digest, audit/fork reports and multisignature receipts together.
Have governance approve the admission policy, monitoring, support, incident response and initial exposure
limits before first funding.

## Recovery and limits

These contracts are not upgradeable. New bytecode cannot repair an existing deployment in place.
If a CREATE fails, record the consumed nonce and stop: blindly restarting can bind different addresses.
If a governance call fails, inspect actual bindings before retrying the unchanged call. An already-bound
module cannot be rebound. If configuration is wrong, keep the deployment unfunded and prepare a new,
reviewed deployment with fresh nonces. Existing funded deployments require a separately reviewed
exit/migration plan; there is no automatic fund movement or rollback.

Governance can revoke admission; there is no global pause or arbitrary treasury rescue function.
Revocation does not undo transactions and should not be mistaken for instant recovery. Withdrawing
unused funds, timeout refunds and capital reclamation remain part of the tested lifecycle. Define
monitoring for exposure, deadlines, dependency upgrades, name expiry and governance changes before use.

## En français

Cette version prépare des transactions **non signées** et vérifie la configuration et les contrats en
lecture seule. Elle ne déploie rien sur le réseau principal et n'autorise aucun financement public.
Commencez par le tag de version, `npm ci`, `npm run audit`, `npm run compile:strict` et `npm test`.
Faites vérifier les adresses, les paramètres, les propriétaires ENS et le multisig par une personne
indépendante. Un audit des sources exactes et un essai complet sur un fork mainnet avec le vrai jeton
restent nécessaires. Signez ensuite dans votre système habituel, puis exécutez `mainnet:verify` avant
l'admission des utilisateurs. N'inscrivez jamais une clé privée dans les fichiers ou les commandes.

## Upstream references

- [Hardhat deployment](https://v2.hardhat.org/hardhat-runner/docs/guides/deploying)
  and [source verification](https://v2.hardhat.org/hardhat-runner/docs/guides/verifying).
- [ENS deployment addresses](https://docs.ens.domains/learn/deployments/).
- [Solidity known bugs](https://docs.soliditylang.org/en/latest/bugs.html).
- [OpenZeppelin access control](https://docs.openzeppelin.com/contracts/5.x/access-control)
  and [changelog](https://docs.openzeppelin.com/contracts/5.x/changelog).
