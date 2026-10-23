# Alpha five-suite local EVM evidence — 2026-10-23 UTC

**38 unchanged source tests, the unchanged native-allocation demo, and nine separately frozen integer-boundary cases passed in an isolated, unforked Hardhat EVM.** Funds, ENS, admission and actors are fixtures. This is not a thermal or complete SUCCESSOR Ω Harness integration claim, a present-mainnet readiness observation, or an independent organizational review.

## Source and runtime

The copy began from HEAD `30021f8659c1ecdf483dd07bd8154b7fb8362a42` with explicitly recorded worktree changes. Every one of the 1,334 copied tracked files plus one restored unchanged demo import was subsequently verified byte-for-byte against public commit `f1ac7df95d802b12bf194b3fa7be6f4c30a62ef4`. `source-copy.json`, `source-supplement-demo.json` and `source-integrity-final.json` retain that sequence; HEAD alone was not used as a substitute for byte identity. No copied source changed during execution. The new supplemental test is separately identified below.

`selected-source.json` records production/mirror SHA-256 equality for AscensionAccess, NovaSeed, AscensionRiskOracle, AscensionJobMarket, AscensionMark and their AscensionToken base, plus the selected tests, config, fixture, demo and native Python interfaces. This is the Alpha suite, not AGIJobsv0 or AGIJobManager.

Runtime: Node **22.17.1**, Python **3.12.14**, Hardhat **2.29.1**, ethers **6.17.0**, local solc **0.8.37+commit.f401782d**, OpenZeppelin **5.6.1**. Full resolved versions and module paths are in `dependencies-*-1.stdout.txt`. The existing compiler policy was used unchanged. No Solidity compiler download was needed.

## Results and preserved failures

`ATTEMPTS.json` indexes every phase with actual UTC times, exit codes, full stdout/stderr and hashes. It retains all five failed attempts: the initial npm config collision, two registry DNS failures, a sandbox solcjs `HH506`/`write EPIPE` failure before tests, and the first demo's missing transitive import. The successful retries changed runner/environment or the isolated copy's completeness, not contract source, dependency versions, existing tests or demo logic.

| Execution | Evidence | Result |
|---|---|---|
| Five existing test files | `tests-2.*` | 38 passing; 00:09:55–00:11:03 UTC |
| Existing demo | `demo-2.*`, `demo-receipt.json` | Exit 0; 00:14:51–00:14:54 UTC |
| Independent integer test | `small-integers-1.*`, `small-integers/small-integers-1/` | 9 passing; 00:17:24–00:17:28 UTC |

The unchanged demo **executes the native allocation first**, verifies its signed journal and checks the delivered result, then performs its local seed/risk/funding/job/delivery/settlement/refund/successor sequence. It records 18 transaction summaries. Its scenario reaches value 210, tying the baseline; it does not establish a gain over the expert alternative. Funding is 158 simulated AGIALPHA, job price 80, worker net 75.24, two validators' combined net 3.96, total burn 0.8 and unused-reserve refund 78. The successor token records lineage and requires a new risk review; it does not demonstrate improved capability. The report retains actual native result bytes and summarized transaction provenance, not a full persistent chain database or every raw receipt.

The existing native-adapter tests separately retain `native-adapter/accepted-negative-evaluation.json` and `missing-review-quorum.json`. A correct report that its evaluated candidate failed can be paid as an accepted reporting job; no quorum instead produces a refund. Their release/environment identifiers and local roles are fixtures. Memory, institutional and production authority remain ungranted.

## Literal integer boundary

The frozen protocol is `payout-small-integers-protocol.json`, SHA-256 `d72950970e93bec2d8cfd58323c2cb2ca1789e6ea018a44bc8604cb619b57a01`, frozen before execution at 00:15:58 UTC. All values below are token **base units**.

| p | Worker net | Each qualifying validator net | Total burn | Actual contract outcome |
|---:|---:|---:|---:|---|
| 1 | 1 | 0 | 0 | Post and bid rejected; payout columns arithmetic only |
| 39 | 39 | 0 | 0 | Post and bid rejected; payout columns arithmetic only |
| 40 | 38 | 1 | 0 | Post and bid rejected; payout columns arithmetic only |
| 99 | 95 | 2 | 0 | Post and bid rejected; payout columns arithmetic only |
| 100 | 96 | 2 | 0 | Paid |
| 103 | 99 | 2 | 0 | Paid |
| 104 | 99 | 2 | 1 | Paid |
| 3999 | 3763 | 99 | 38 | Paid |
| 4000 | 3762 | 99 | 40 | Paid |

Actual source requires both bounty and bid price to be at least 100. The four smaller cases check `job bounds` and `bid bounds` reverts and unchanged token balances, supply, stake and locks. They are **not** subminimum payout demonstrations. The five valid cases use price=bounty=p and the existing fixture, post, bid, award, deliver and two-reviewer approval path. Every case retains raw local transaction receipts; valid payouts retain event log indexes and block hashes. Assertions separately verify each recipient, the abstaining third validator, supply burn, escrow conservation, collateral release and zero surplus refund. Arithmetic is `each=floor(p/40)`, then `floor(gross/100)` burned separately for each recipient.

## Reproduction and boundaries

The exact argv, clean environment, working directory and executable identities for every attempt are in its phase JSON. `reproduction/` preserves the runner, dependency checks and new test unchanged; runner snapshots preserve earlier failed-attempt configurations. The supplemental test's candidate destination is:

`tests/contracts/test/ascension/payout-small-integers.local.test.js`

After setup from the source commit and the unchanged lockfiles, use the recorded Node/Python versions. Place the supplemental test at that destination in a disposable copy, set `ALPHA_PYTHON` to the isolated Python executable and `PYTHONPATH` to that copy's root, and invoke the existing local Hardhat entry directly:

```sh
node node_modules/.bin/hardhat --config hardhat.config.js --network hardhat test \
  test/ascension/lifecycle.test.js test/ascension/marketplace.test.js \
  test/ascension/settlement.test.js test/ascension/native-handoff.test.js \
  test/ascension/successor-adapter.test.js
node node_modules/.bin/hardhat --config hardhat.config.js --network hardhat run \
  --no-compile scripts/demo.js
node node_modules/.bin/hardhat --config hardhat.config.js --network hardhat test \
  --no-compile test/ascension/payout-small-integers.local.test.js
```

The last command also requires `ASCENSION_SMALL_INTEGER_PROTOCOL` pointing to the frozen protocol and `ASCENSION_SMALL_INTEGER_OUTPUT` pointing to a new evidence directory. The demo's `ASCENSION_DEMO_OUTPUT` must likewise name a new file. Run from `tests/contracts`. Full environment details and the dependency command (`npm ci --ignore-scripts --no-audit --no-fund`, distinct empty npm configs) are retained in the phase records. This evidence bundle does not ship installed dependencies.

Config and fixtures reject external/forked providers and require an in-process Hardhat instance. Native Python adapter requests traverse the existing six-method read-only bridge to that local instance. No external RPC URL, externally supplied signing key or proxy was supplied to test/demo phases. Dependency acquisition alone used the existing credential-free runtime proxy and public CA after the retained DNS failures. **These application restrictions are not OS-wide egress isolation.** Distinct fixture signers are not independent organizations, legal compliance or live admission. Thermal execution, the held harness façade, real operator/validator independence, physical validity, and the other repositories' live integrations remain separate requirements.

`MEMBERS.json` and `SHA256SUMS` identify the publication bundle's bytes, including empty stderr files. Keep failed attempts and the frozen protocol when publishing or copying it.
