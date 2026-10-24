# Reproduce Writer 10's contract evidence

This directory preserves a focused, exact-source subset of Alpha revision
`197147ffd22c5ae13113162afffaf3ce9c10aa2e`. `source-manifest.json` identifies all
five contracts and their verified equality to deployed-source reference
`c0fc5217e364a39a4cd123d17a8317c06b80f820`. The original source retains its license.
The study adds only `writer10-*.js`, this guide and its audit/evidence files.

## Local only

Use a disposable local environment, Node 22.17.1 as requested by the upstream
guide (this execution used Node 24.19.0), and the supplied exact npm lockfile.
The original Hardhat configuration and disposable-network helper explicitly
reject an external endpoint or fork. Do not configure a live wallet or RPC.

From the extracted source package's root:

```sh
cd contracts-audit/tests/contracts
npm ci --ignore-scripts --no-audit --no-fund
node node_modules/hardhat/internal/cli/cli.js compile --concurrency 1
node node_modules/hardhat/internal/cli/cli.js test --no-compile test/ascension/lifecycle.test.js
NOVA_LEDGER_PATH=/absolute/path/to/public-or-synthetic-ledger.json NOVA_CONTRACT_OUTPUT=evidence/my-contract-results.json node scripts/writer10-demo.js
```

The caller supplies the exact final public or synthetic evidence JSON; no
private key or real funds are required. Maximum input size is 20 MiB. The script
does not claim to establish the input's physical truth. It commits exact input
bytes and checks the stated protocol behavior. Default output is
`tests/contracts/evidence/writer10-contract-results.json`; the command above sets
`NOVA_CONTRACT_OUTPUT` to a fresh destination and preserves the canonical record.
A portable, clearly labeled
`evidence/binding-fixture.json` permits checking the software before the full
study's ledger is available. Results on that fixture are not study outcomes.

The final retained contract run binds actual development `pilot-03`, not a
placeholder or the holdout matrix. Return to the extracted package's root before
recreating the exact 2,646-byte binding summary from the retained 42-row,
six-world development ledger with `python contracts-audit/summarize_pilot.py`.
Then return to `contracts-audit/tests/contracts` and run the command above with
`NOVA_LEDGER_PATH=evidence/pilot-03-binding-summary.json`. The summary commits
the entire 203,897-byte JSONL file by SHA-256 and includes all seven method
outcomes. Its SHA-256 is
`1d0a79fc3f5f7f63a76e6bbf6e6f3b9a8de9b4eb752782f54d19aaf0843e2113`.
Both the NFT registry and signed-registry alternative bind these exact bytes.

The final run passed 21 checks, recorded 113 local-chain transactions including
fixtures and negative cases, used 20,701,896 total simulated gas and 4,546,309
gas across explicitly tracked calls, and measured 2.220 seconds wall time /
2.085 seconds process CPU. This includes the 1,000-signature-verification loop.
Registry construction including key generation took 4.110 milliseconds; the
1,000 complete six-record verifications took 958.908 milliseconds. Those times
are one local execution, not population performance estimates. The record set
occupies 3,619 JSON bytes. Actual deployed bytecode source was not queried.

After this final run, task-owned dependency installations and disposable
compiler caches were removed to free space; sources and exact lockfile remain.
`evidence/compiled-five-contracts.json` retains the exact compiler outputs for
the five contracts and their compiler profile. `npm ci` reinstalls dependencies
for a new reproduction; the small stand-alone signature verifier needs no npm
dependencies.

The compiler is the pinned Solidity 0.8.37 package with the repository's actual
SOL-2026-7 workaround profile, viaIR, Cancun and 200 optimization runs. The
existing compiler policy removes only L/E passes from the stated Yul sequence.
Hardhat prints that this compiler is not fully supported for some diagnostics;
the demonstration additionally decodes standard `Error(string)` revert bytes
when the debugger cannot infer a reason. No compiler restriction is disabled.
In this hosted environment, compiler child-process execution required an
approved sandbox escalation; compilation did not work under the initial
subprocess restriction. No network is used by the EVM fixture itself.

## What executes

The unchanged upstream fixture constructs all five contracts and their fixed
bindings with mock ENS and a mock canonical-address token. The study then seals
the supplied digest, obtains two attributable local risk attestations, funds a
two-leaf plan with mock tokens, blooms, routes each specification once, executes
local bid/award/submit/review/settlement calls, collects refunds and reclaims
unused principal. It tests altered metrics, duplicate routes/votes/collection,
wrong result hash, job bounds, post-bloom trade restrictions, fresh successor
review, and strict funding deadline. Distinct local signers do not establish
independent organizations or real-world reviewer judgment.

The off-chain counterfactual signs the same evidence and plan with an ephemeral
Ed25519 key generated only in memory, checks the base-seed parent commitment, a scoped authority and
route-once membership, and records the identical delivered byte digest. It
preserves that evidence interface and workload binding, not decentralized
escrow custody or shared consensus. Its full records and public key are in the
output. Tampering and internal record omission fail verification; a valid
truncated prefix remains acceptable to a party with no independently pinned
terminal checkpoint. The paper must retain that negative result.

## Independently check the signed records

Export the emitted public key to a PEM file and pin it through a trusted channel
before relying on authorship. This stand-alone verifier uses only Node's
standard cryptographic implementation:

From `contracts-audit/tests/contracts`, verifying the fresh reproduction output:

```sh
node scripts/writer10-verify.js evidence/my-contract-results.json /absolute/path/to/the-exact-ledger.json /absolute/path/to/pinned-registry-key.pem
```

This verifies byte identity and signatures; it does not adjudicate the solver
result. Read the separate workload verifier and its resource-validity checks
for that property. Signing or hashing a physical assertion cannot make it true.

## Costs and limitations

Machine-readable output separates all-chain gas including deployment/fixtures
and negative cases from explicitly tracked lifecycle calls. It reports host
wall/CPU time for this execution, registry construction time, 1,000 registry
verifications and record bytes. Compiler/install work and all research authoring
time are not included in those execution timers. No gas-price or token-price
conversion is made; no live transaction occurred. Mock payment accounting is
not revenue, profit, service price, social value or investment return.

Local transaction hashes, timings and signatures can change across runs. The
fixed assertions, input digest, source identities, final balances and rejection
outcomes are the intended reproducible properties.
