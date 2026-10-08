# Contract deployment and migration guide

This is the supported **local Hardhat rehearsal** for $AGIALPHA Agent 1.24.0. It deploys the Ascension
contracts, verifies their bindings and writes inspectable evidence. It needs no wallet, secret, RPC URL
or real funds. Contract state exists only inside that command's process and disappears when it exits.

| Your goal | Command / guide | Result |
| --- | --- | --- |
| Review what would be deployed | `npm run deploy:plan` | Read-only JSON plan; no EVM or transactions |
| Deploy and verify a fresh local protocol | `npm run deploy:local` | Local transactions, verified graph, JSON manifest |
| Test contracts and failure paths | `npm test` | Existing v2/Ascension/SUCCESSOR tests plus deployment checks |
| Execute a funded local mission lifecycle | `npm run ascension:demo` | Mock funding, review, job settlement and evidence |
| Compile a mission's indexed commitments | `node scripts/plan.js /absolute/path/jobs.json` | FusionPlan, separate from deployment planning |
| Replace the historical Truffle workflow | [Migration below](#migration-and-rollback) | Fresh local state; no automatic balance or identity import |

## First run

Start in the repository root. Use the repository's Node.js **22.17.1** (`nvm use` if available), then install
the locked JavaScript dependencies. Do not run `npm update` as part of deployment.

```sh
nvm use
cd tests/contracts
npm ci
npm run deploy:plan
npm run compile
npm run deploy:local
```

On Windows, install/select the version in `.nvmrc` with your Node version manager, then run the same
`cd`, `npm ci` and `npm run` commands in PowerShell. The initial `npm ci` and compiler download require
network access; execution uses an in-process EVM. Offline execution requires the previously installed
locked dependencies and Solidity compiler cache.

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
