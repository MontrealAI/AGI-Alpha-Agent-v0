# Contract deployment and migration guide

This is the supported **local Hardhat rehearsal** for $AGIALPHA Agent 1.28.1. It deploys the Ascension
contracts, verifies their bindings and writes inspectable evidence. It needs no wallet, secret, RPC URL
or real funds. Contract state exists only inside that command's process and disappears when it exits.

For the **existing October 11 Ethereum deployment**, use the [owner and verification guide](../../docs/agent/MAINNET_DEPLOYMENT.md).
`mainnet:record-check` validates its archive; `mainnet:record-verify -- NEW_OUTPUT` checks finalized live state.
It uses the archived compiler profile, while current sources include later settlement fixes.

For a **new** Ethereum deployment preparation, use the separate [mainnet commissioning guide](../../docs/agent/MAINNET_READINESS.md).
It provides unsigned plans and read-only preflight/post-deployment checks; the local fixture below stays isolated.
A mainnet-fork rehearsal, independent review and operator configuration are still required before funding.

| Your goal | Command / guide | Result |
| --- | --- | --- |
| Review what would be deployed | `npm run deploy:plan` | Read-only JSON plan; no EVM or transactions |
| Deploy and verify a fresh local protocol | `npm run deploy:local` | Local transactions, verified graph, JSON manifest |
| Test contracts and failure paths | `npm test` | Existing v2/Ascension/SUCCESSOR tests plus deployment checks |
| Enforce clean Solidity diagnostics | `npm run compile:strict` | Compile every production source, then force all Hardhat fixtures; any Solidity warning or error fails |
| Inspect production source coverage and sizes | `npm run compile:production` | Full production compilation report, source hashes and creation/runtime byte sizes |
| Execute a funded local mission lifecycle | `npm run ascension:demo` | Mock funding, review, job settlement and evidence |
| Compile a mission's indexed commitments | `node scripts/plan.js /absolute/path/jobs.json` | FusionPlan, separate from deployment planning |
| Replace the historical Truffle workflow | [Migration below](#migration-and-rollback) | Fresh local state; no automatic balance or identity import |
| Prepare an unsigned Ethereum deployment | `npm run mainnet:plan -- CONFIG NEW_OUTPUT` | Exact compiled deployment data; requires a clean reviewed checkout |
| Check reviewed live dependencies | `npm run mainnet:preflight -- CONFIG NEW_OUTPUT` | Read-only, finalized-block configuration evidence |
| Check recorded mainnet evidence | `npm run mainnet:record-check` | Offline file, source, transaction and cost integrity |
| Verify existing October 11 contracts | `npm run mainnet:record-verify -- NEW_OUTPUT` | Read-only finalized receipts, full runtime, ownership and bindings; no signer |
| Verify fresh deployed contracts | `npm run mainnet:verify -- PLAN NEW_OUTPUT` | Read-only bytecode, ownership and binding checks |
| Export explorer inputs for existing addresses | `npm run mainnet:verification-package -- record NEW_DIRECTORY` | Exact archived Standard JSON, compiler and ABI constructor arguments |
| Export explorer inputs for a new deployment plan | `npm run mainnet:verification-package -- plan PLAN NEW_DIRECTORY` | Current build inputs; rejects a plan that differs from compiled sources |

## First run

Start in the repository root. Use the repository's Node.js **22.17.1** (`nvm use` if available), then install
the locked JavaScript dependencies. Do not run `npm update` as part of deployment.

```sh
nvm use
cd tests/contracts
npm ci
npm run deploy:plan
npm run compile:strict
npm run deploy:local
```

On Windows, install/select the version in `.nvmrc` with your Node version manager, then run the same
`cd`, `npm ci` and `npm run` commands in PowerShell. The initial `npm ci` requires network access;
the exact Solidity compiler is included in the locked npm dependencies. Compilation needs no separate
compiler download. Offline execution requires those installed dependencies and uses an in-process EVM.

The source profile is Solidity **0.8.37**, optimizer **200**, **via IR**, **Cancun** and OpenZeppelin
**5.6.1**. `npm run compile:strict` first discovers and compiles every `contracts/**/*.sol` production
source, then forces the Hardhat fixture build. It fails on every Solidity warning, including dependency
warnings. The production gate covers all 15 shipped source files and their 30 OpenZeppelin dependencies,
including `DisputeModule`, `ReputationEngine` and `TokenUtils`, which have no Hardhat fixture copies.
It embeds the complete dependency closure under normalized source names and checks all 12 existing
production/fixture mirrors. Its JSON report records source hashes and creation/runtime byte sizes.
Ordinary incremental fixture compilation enforces the same diagnostic policy. Deployment tools also
reject previously cached build outputs containing warnings. Compilation coverage does not establish
legacy v2 integration compatibility or commissioning.

Hardhat 2.29.1 separately reports that its Solidity 0.8.37 stack-trace support is incomplete. This is a
debugger compatibility notice, not a Solidity compiler diagnostic. The retained Hardhat dependency
tree also reports upstream npm deprecations for `lodash.isequal` and `glob`; `npm run audit` separately
checks security advisories. These notices are not hidden or counted as compiler errors. Do not change
the reviewed compiler or dependency versions merely to silence an unrelated notice.

## Explorer verification without guesswork

For the five October 11 addresses, run:

```sh
npm run mainnet:record-check
npm run mainnet:verification-package -- record /absolute/path/new-verification-package
```

This works offline after `npm ci`. Each contract folder contains `standard-input.json`,
`constructor-arguments.txt` (ABI-encoded hex without `0x`) and `etherscan-request.json`. The top-level
`manifest.json` identifies Ethereum mainnet, each exact address, the fully qualified source name,
compiler release, all compiler settings, constructor values and file hashes. `README.txt` explains the
manual Standard JSON and API V2 workflows. Existing output directories are refused.

The existing addresses require their original **0.8.24 / Paris / OpenZeppelin 5.4.0** archive, including
its `project/` and `npm/` source names and remappings. The exporter copies that compiler input byte for
byte and checks every constructor against the recorded creation transaction. Do not flatten it or use
current sources to verify those addresses. Their code is immutable; a source release does not patch it.

For a reviewed new deployment plan, use
`npm run mainnet:verification-package -- plan /absolute/path/plan.json /absolute/path/new-package`.
The exporter reconstructs the plan from current compiled sources and rejects changed addresses,
constructors, chain or compiler data. Planned addresses remain predictions until deployment and
`mainnet:verify` succeed. Keep operator files outside the repository so the plan checkout stays clean.

Exporting makes **no network request**, submits no explorer verification and needs no API key. When
submitting through Etherscan, add the API key separately, retain the final `checkverifystatus` response,
and check the published address and source match. An accepted submission GUID is only a pending
request. Compiler-version advisories on an immutable address cannot be removed by uploading changed
source. Follow the [mainnet guide](../../docs/agent/MAINNET_DEPLOYMENT.md) for deployment limits.

The `contracts/v2` fixtures are legacy component tests. Interface gaps between their registry and
validation modules remain outside the commissioned Ascension graph; passing component tests does not
establish an end-to-end v2 deployment. The five recorded Ethereum addresses are Ascension contracts.
The legacy NFT completion-bonus path is explicitly disabled: `addAGIType` rejects every registration,
including a zero percentage,
until a separately reviewed funding mechanism exists. This avoids promising bonus payouts from the
same escrow that must already fund the job reward, fee and burn.

Success prints a JSON manifest with `verified: true`, `scope: "disposable-local-fixture"`, chain ID
`"31337"`, eight contract/fixture addresses and their runtime-code hashes. This command does not mint
funds, register identities, grant admission, fund a campaign or import native authority. It verifies
empty token supply, seed and job counters, owners, ENS roots, staking parameters and one-time bindings.
Every invocation starts fresh; a repeated address does not mean a previous chain was restored.

For clean JSON redirected to a file, use npm's silent mode:

```sh
npm run --silent deploy:plan > deployment-plan.json
```

Prefer exclusive evidence-file output for deployment, which refuses to overwrite a previous run:

```sh
ASCENSION_DEPLOY_OUTPUT=/absolute/path/new-local-deployment.json npm run deploy:local
```

PowerShell:

```powershell
$env:ASCENSION_DEPLOY_OUTPUT = 'C:\evidence\new-local-deployment.json'
npm run deploy:local
Remove-Item Env:ASCENSION_DEPLOY_OUTPUT
```

The output path is optional; default output is stdout. If saving fails, the command exits nonzero.
Choose a new filename and rerun; no external transaction needs recovery. All failures exit nonzero.

## What is fixed and verified

| Setting | Supported value |
| --- | --- |
| Provider | Newly created, unforked, in-process Hardhat; `localhost` and URL providers are refused |
| Chain ID | `31337`; a matching ID alone does not authorize fixture writes |
| Settlement token | `$AGIALPHA`, `0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`, 18 decimals |
| Local token behavior | Mock runtime installed at the canonical address with `hardhat_setCode`; no real token contract is deployed |
| Governance | First disposable Hardhat signer; no environment key is read or imported |
| Validator / agent minimum stake | 10 / 10 mock $AGIALPHA, expressed as integer base units |
| Risk quorum / maximum risk | 2 / 2,000 basis points |
| ENS role roots | `alpha.agi.eth`, `alpha.agent.agi.eth`, `alpha.club.agi.eth` with mock ENS and wrapper |
| Contract graph | Access → NovaSeed → oracle → marketplace → MARK; oracle/marketplace links are bound once and read back |

`AGIALPHA_ADDRESS` and `AGIALPHA_DECIMALS`, when present, must agree with the canonical configuration.
Leave both unset for local work, or set both canonical values together: the repository-wide token
checker requires the pair. They cannot switch tokens. `DEPLOYER_KEY`, `MAINNET_RPC_URL`, `GOVERNANCE_ADDRESS`, `GAS_PRICE` and
`ETHERSCAN_API_KEY` are not used by this workflow. No secrets are needed in `.env`.

The manifest includes the source-file SHA-256 digests, git commit/tree plus dirty-worktree flag when
git is available, compiler-input SHA-256, settings and dependency source digests, Hardhat/compiler versions,
Hardhat instance ID, mined transaction references, final block hash and observed runtime-code hashes.
Compiled source must match current files before the first deployment transaction; stale artifacts
produce an actionable error. A dirty checkout's file digests describe the run, not its base commit alone.
The auxiliary mock-token deployment receipt and address are included; copying its runtime to the
canonical address is explicitly distinguished from a deployment transaction at that address.
Verification occurs during this process. Saved JSON is a record of that check; this workflow provides
no independent saved-manifest verification/import command and makes no later or live validity claim.

This evidence is suitable for public inspection after review: it contains local addresses, source
identifiers and transaction metadata, not signing keys, RPC credentials or native journal contents.
Keep native signing keys, private mission data, backups and real provider credentials outside public
manifests. A local manifest neither establishes an external-chain deployment nor grants production authority.

## Migration and rollback

| Starting point | Supported transition | What does not transfer |
| --- | --- | --- |
| Historical `truffle/` entrypoint | Use this Hardhat guide from a reviewed checkout | No missing `Deployer` contract is synthesized; no mainnet migration runs |
| Previous local contract rehearsal | Preserve its receipt, then run a fresh local deployment | Balances, allowances, jobs, names, admissions, stakes and proof state |
| Changed Solidity source or dependencies | Run `npm ci` when the lock changed, compile, test, deploy into a fresh process | Existing contract addresses or one-time bindings cannot be upgraded in place |
| Existing native agent home | Follow [native operations](../../docs/agent/SUCCESSOR_OPERATIONS.md) and its backup/restore rules | A contract receipt never imports authority or re-signs old evidence |
| Any external-chain deployment | Separate deployment design and review required | No automated external-chain migration or rollback is provided by this release |

These contracts are not upgradeable proxies. One-time oracle/marketplace/MARK bindings cannot be rebound.
For a local rollback, stop the process, retain its evidence and rerun the selected earlier reviewed source
and its matching lockfile in a new checkout. Never point a fixture reset or mock installation at a funded
node. If interrupted before a verified receipt, rerun from a fresh process; do not label partial output verified.

The legacy migration path now fails before artifact loading or transaction submission and directs you
here. Its former `Deployer` artifact was absent; the former environment token override did not change
Solidity's canonical token. The legacy config exposes no networks and loads no wallet provider.

The separate mainnet tools use `MAINNET_RPC_URL` for read-only HTTPS queries. They never read `DEPLOYER_KEY`.

## Tests and troubleshooting

```sh
# From tests/contracts, with dependencies installed:
npm test -- test/deployment.test.js
npm test
```

The wider native-handoff and SUCCESSOR tests also require the Python environment documented in
[SUCCESSOR Ascension](../../docs/agent/SUCCESSOR_ASCENSION.md). Set `ALPHA_PYTHON` to that interpreter's
absolute path when the default `python3` is unsuitable. For a funded lifecycle and accounting explanations,
use [Ascension protocol](../../docs/agent/ASCENSION_PROTOCOL.md).

| Message / symptom | Next action |
| --- | --- |
| Missing Hardhat/package/compiler | Run `npm ci` and `npm run compile` in `tests/contracts` with Node 22.17.1 |
| Canonical token conflict | Remove conflicting token overrides; rerun `python scripts/check_agialpha_config.py` from the repository root |
| Fixture differs from source | Reconcile the reviewed production/fixture Solidity copies, compile and test; do not bypass the check |
| Compiled source is stale | Run `npm run compile`; avoid `--no-compile` after changes |
| Requires in-process, unforked Hardhat | Use `npm run deploy:local` without an alternate network or RPC URL |
| Existing chain state will not be reset | Start a new CLI process; the deployment helper deliberately refuses to erase a used provider |
| Output already exists | Select a new evidence filename; previous evidence stays intact |
| Truffle migration unsupported | Follow the migration table above; do not add keys to revive the obsolete path |

The repository-wide token checker requires Python and Node, but no installed npm packages. It checks
canonical constants and workflow settings and exercises the provider-free plan and disabled legacy path.

## Démarrage rapide

Depuis `tests/contracts`, exécutez `npm ci`, `npm run deploy:plan`, puis `npm run deploy:local`.
Le déploiement est limité à une chaîne Hardhat locale jetable (31337); aucun portefeuille, secret ou
capital réel n'est requis. Le manifeste confirme les contrats et leurs liens, puis l'état disparaît à
la fin du processus. Conservez un nouveau fichier de preuve par essai. Il n'y a aucune conversion de
jeton, migration de fonds, importation d'autorité ou qualification de production implicite.
