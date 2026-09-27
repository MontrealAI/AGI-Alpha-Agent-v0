# α-AGI Ascension — executable protocol

[Open the Protocol Desk](../ascension-protocol/index.html) · [Ascension Lab](../ascension/index.html)
· [Proof Bloom](../bloom/index.html) · [Local EVM evidence](../assets/ascension-protocol/receipt.json)

**Powered by $AGIALPHA.** Ascension connects Insight → cryptosealed Nova-Seeds → MARK → Sovereign
businesses → reputation-weighted α-AGI Jobs → validator-gated settlement → evidence-bound successors.
Version 1.11.0 adds executable Solidity to the existing native agent and browser experiences.
The new suite is additive: all historical contracts, demos, manuscripts and flywheels remain available.

The Protocol Desk displays actual **local EVM** transaction receipts from the shipped contracts. It also
runs editable funding and auction calculations. Its token and ENS contracts are local fixtures; its
validators are distinct test signers. No mainnet deployment, external investment, independent organization,
realized economic gain or autonomous AGI capability is represented by that run.

## Requirement-to-implementation map

| Ascension requirement | Executable implementation | Evidence and boundary |
|---|---|---|
| α-AGI Insight: identify disruption opportunities | Existing Insight Atlas, allocation/search, research missions and source evidence produce the genome and native job | Reproducible bounded analysis of supplied inputs; “beyond-human foresight” and “pinpoint accuracy” remain research ambitions, not measured performance |
| α-AGI Nova-Seeds: cryptosealed ERC-721 venture spores | `NovaSeed.sol`, existing AES-256-GCM capsule, immutable capsule hash, double-hashed Merkle FusionPlan root, metadata URI and parent lineage | Actual ERC-721 ownership and transfer; no plaintext secret in the NFT; commitments establish byte identity, not confidentiality of public job descriptions or availability of external storage |
| α-AGI MARK: algorithmic market maker and bonding-curve issuance | `AscensionMark.sol` implements exact discrete linear buy/sell pricing and transferable funding lots | A bounded curve AMM and funding market; no order book, derivatives engine, guaranteed liquidity after bloom, or investment-return promise |
| Validator-driven risk oracle and green-flame gate | `AscensionRiskOracle.sol`: staked, currently eligible validators, evidence hashes, risk ceiling, policy approval, quorum and seven-day expiry | An attributable assessment, not an objective financial or legal oracle; transfer, expiry or approving-validator revocation removes green status |
| Compliance-aware admission | `AscensionAccess.sol`: expiring, evidence-bound admission, controlled by a two-step governance owner | Denied by default; an operator must supply lawful jurisdiction-specific policy and actual review. No claim of automatic regulatory compliance |
| α-AGI Sovereign / Business (`name.alpha.agi.eth`) | Bloom fixes the originating business node and opens a plan-restricted treasury inside MARK | No general treasury withdrawal. New missions require current green approval, original business ownership and Merkle membership |
| FusionPlan → α-AGI Jobs → marketplace | `route` verifies each indexed specification once, checks its budget/horizon, escrows its bounty and reserves three opted-in reviewers | Goal, success metric, bounty, delivery bound and price/time weight cannot be substituted; up to 128 missions per seed |
| Reputation-weighted auctions | `AscensionJobMarket.sol`: up to 32 staked eligible bidders, price/time/reputation score, deterministic ties | The best admissible bid under the published rule wins; this does not guarantee the cheapest and fastest offer simultaneously or global market optimality |
| Only `*.alpha.agent.agi.eth` agents execute | Live canonical ENS ownership, strict single-label registration, admission and individually locked collateral | No resolver-only or administrator allowlist identity bypass. Wrapped names must be unexpired. Root-domain lifecycle still depends on the ENS operator |
| `*.alpha.club.agi.eth` validators approve | Three distinct selected validators; two matching result-bound approvals settle; explicit business availability and per-validator concurrency budget | Addresses must differ from business and worker. Address separation cannot establish independent beneficial ownership or resistance to collusion |
| All settlement uses $AGIALPHA; 1% burn per payout | Canonical `0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`, 18 decimals; exact ERC-20 deposits and verified total-supply destruction | No USDC substitution, mint authority or alternative token. Deployment requires the real token to support these operations |
| Contract pays the winner or slashes failed work | Two approvals pay; two rejections or missed delivery slash the locked agent bond | Missing review quorum is not failure proof: escrow is refunded and the bond unlocked. There is no arbitration/dispute appeal in this new suite |
| Adaptive, self-evolving enterprise constellation | Existing Proof Bloom and Compounding Lab evaluate reuse; successor NFTs bind parent and new evidence | Successors start unapproved; there is no inherited authorization or claim that a minted successor improves intelligence. Live autonomous business operation requires an external operator/runtime integration |

The separate **AGIJobManager / AGI Jobs** project is not modified by this suite. Its USDC policy and
`*.agent.agi.eth` / `*.club.agi.eth` identities do not replace Ascension’s explicitly requested
$AGIALPHA and `*.alpha.agent.agi.eth` / `*.alpha.club.agi.eth` namespaces.

## A concrete end-to-end run

The native agent solves the supplied city allocation mission. An independently coded enumeration in the
acceptance runner checks the returned selected items, their costs/risks/value and the optimal objective.
The result is four projects, cost **100 planning credits**, risk score **9**, assumed benefit **210 modeled
resilience points**. These scenario units are not tokens, measured savings or a forecast.

The runner then seals and reopens the real encrypted genome and commits its capsule digest and job root
in an ERC-721. Two local validators approve the seed. Forty curve lots fund **158 $AGIALPHA**. The
business blooms, escrows a **100-token maximum bounty**, and compares two bids:

| Bid | Gross price | Promised delivery | Prior reputation | Outcome |
|---|---:|---:|---:|---|
| `researcher.alpha.agent.agi.eth` | 70 | 86,000 seconds | 0 | Loses under the selected time/price rule; bond unlocked |
| `fast-researcher.alpha.agent.agi.eth` | 80 | 1,000 seconds | 0 | Selected; delivered native result hash reviewed |

After two approvals of that exact delivered artifact:

| Token destination | $AGIALPHA |
|---|---:|
| Executor after its burn | 75.24 |
| Two approving reviewers after their burns | 3.96 |
| Destroyed token supply | 0.80 |
| Returned unused funding | 78.00 |
| Remaining treasury | 0.00 |
| **Total accounted for** | **158.00** |

A successor NFT then records the delivered evidence and parent seed; its risk approval remains false.
The downloadable snapshot contains the encrypted capsule, actual native result, verified journal summary,
plan/proofs, contract source hashes, transaction hashes, blocks, gas, decoded events and accounting.
The native journal identity is ephemeral local evidence, not independently trusted reviewer identity.

## Reproduce the end-to-end run

Use the repository’s supported Python environment and Node **22.17.1**. The canonical runtime is installed
from `requirements-agent.lock`; the test contract dependencies are pinned by `tests/contracts/package-lock.json`.

```bash
python -m pip install --require-hashes -r requirements-agent.lock
npm ci --prefix tests/contracts
npm test --prefix tests/contracts
npm run ascension:demo --prefix tests/contracts
python -m scripts.check_ascension_protocol
python -m scripts.validate_ascension_protocol --site docs --output evidence/ascension-protocol/browser
```

The demo requires a local Hardhat EVM with chain ID **31337**. It explicitly resets that development chain
and installs mock ENS/token fixtures. Never point it at a live/funded node. It makes no live provider,
wallet, payment or storage-publication request. Set `ALPHA_PYTHON` to an absolute Python interpreter path
when needed. `ASCENSION_DEMO_OUTPUT` can select the evidence JSON destination; by default it writes
`evidence/ascension-protocol/receipt.json`. The checked-in public snapshot is a recorded run, not a fresh
execution in each visitor’s browser. CI reruns the lifecycle and retains its new evidence separately.

To compile your own FusionPlan, supply a JSON array of specifications:

```json
[{"goal":"Prepare a reproducible allocation from the supplied public dataset",
  "successMetric":"Independent replay matches all selected IDs, totals and constraints",
  "bounty":"100000000000000000000","duration":86400,"priceWeight":6000}]
```

```bash
node tests/contracts/scripts/plan.js /absolute/path/jobs.json > fusion-plan.json
```

`bounty` is an integer string in **18-decimal base units**; duration is seconds; priceWeight is 0–10,000
basis points. The compiler emits each indexed leaf and inclusion proof, the root and total maximum
bounty. Choose funding, reviewers, deadlines, evidence availability and native mission payloads deliberately;
the compiler does not infer the real-world meaning or sufficiency of a success metric.

## Arithmetic and state rules

For supply `s`, batch `n`, initial price `b` and slope `m`, the AMM charges:

`n*b + m*n*(2*s+n-1)/2`.

Redemption uses the same sum over the last `n` lots. Quotes and token operations use uint256/integer base
units. Slippage bounds are mandatory. Lots are transferable only between admitted participants during
funding; revocation never blocks a holder’s funding withdrawal. Bloom ends trading and redemption.
After all posted jobs close, or after the execution horizon with no active jobs, unused funding is
returned in proportion to remaining lots; the final claim receives residual rounding dust.

Auction score (lower is better):

`(floor(price*weight*10^6/bounty) + floor(seconds*(10000-weight)*10^6/maxSeconds))*10000/(10000+reputation)`.

The final division is floored. Reputation is snapshotted on bid, capped at 10,000, increased by one only
after accepted work and decreased by one on failure. Ties prefer price, then delivery time, then numerical
address. Reputation is a protocol counter, not a demonstrated measure of skill or a Sybil defense.

The agent bond is `max(minimumStake, floor(maximumBounty/10))`, individually reserved for each bid. Losing
bonds unlock on award. Three selected reviewers must have explicitly opted into work for that business,
have enough concurrency capacity, live validator ENS identities and sufficient stake. Capacity is released
on every terminal path. Their stake stays locked to the maximum committed review/risk expiry, even if a
job ends early. Availability can be revoked for future work without cancelling an existing obligation.

The gross job price includes a fixed 5% review pool; each approving reviewer gets
`floor(floor(price*500/10000)/2)`, and the worker gets the remainder. Each actual payout burns
`floor(gross/100)` separately. Agent-slash compensation also burns 1%; returned escrow and returned stake
are principal refunds and are not burned. Tiny base-unit amounts can round the burn to zero.

Anyone may award an ended auction, expire undelivered/unreviewed work, collect a treasury refund and close
an eligible campaign. Only the recorded client/lot holder can claim its funds. An unawarded auction can
be processed even after its horizon; all bids then expire and escrow returns without an agent slash.
No admin key can withdraw a treasury or fabricate validator votes. Governance can still deny new work
through admission decisions; one-time oracle/market bindings must be checked before operation.

## Deployment boundary

The repository now contains a coherent, tested reference protocol, **not an independently audited or
commissioned mainnet system**. Before a live deployment, verify canonical token behavior and ENS roots,
external admission policies, governance custody, independent reviewer recruitment, evidence storage,
monitoring/recovery keepers, dispute policy, adversarial testing and economic incentives. The current
bounds are 32 bidders per auction, 128 plan jobs, three reviewers per job and up to 128 reserved jobs per
validator. Many campaigns can coexist; no global-scale throughput claim follows from that fact.

There is no wallet action in the public desk. Existing native agent provider integrations, proof/reuse
experiments, original demos and browser simulations remain usable with their documented limits.
