# From the white paper to a working Ascension Lab

[Launch Ascension](../ascension/index.html) · [Read the original paper](../assets/whitepaper_v0.1.0-alphav15.pdf)
· [Install your agent](OPERATIONS.md)

The original **META-AGENTIC α–AGI White Paper — v0.1.0-alpha** describes an opportunity-to-value loop:
Insight discovers an opportunity; a Nova-Seed carries its FusionPlan; MARK explores funding; Sovereign
coordinates work; a Council reviews it; a Value Reservoir and Architect inform the next cycle.

Version 1.5.0 makes that loop directly usable in a browser. The paper, original flywheels, all 26 catalog
entries and previous releases remain available. The new lab adds three substantial, editable scenarios:
city resilience, research prioritization and enterprise automation. It also accepts your own scenario JSON.

The paper is preserved byte-for-byte. Its SHA-256 is
`fd14d444d51e9f6ebaec13387fc8d2170615d1bbfab13edc7e84ea1f655d20aa`.
The site build copies that canonical repository file; there is no separately edited PDF.

## Start with a useful mission

1. Choose **The resilient city**. Inspect the seven opportunities and change cost, benefit or risk assumptions.
2. Select **Discover the portfolio**. Every subset is compared; the selected work receives a capacity-aware schedule.
3. Open **Nova-Seed**. Inspect the full genome, choose a private passphrase of at least 12 characters and seal it.
   Download the capsule. Keep the passphrase separately; it cannot be recovered from the file.
4. Open **MARK**. Funding 25 lots deposits exactly 100 modeled tokens in the default city scenario.
   Try redeeming before settlement to inspect the inverse curve. Funding is a simulation with no wallet transaction.
5. Open **Sovereign**. Inspect research, delivery and verification lanes. Download native missions for your local agent.
6. Open **Council**. Inspect both checks, explicitly accept the plan and model settlement. The default mint is zero.
   Download the evidence JSON and readable mission brief.
7. Open **Architect**. Compare 20 budget/risk policies and deliberately start a new cycle with one of them.

With the unchanged city inputs, the selected portfolio has cost **100**, risk **9** and assumed benefit
**210**; 12 operations finish in **30 scenario time units**. These are computed scenario results, not
measurements of city infrastructure. Projected benefit is never automatically treated as certified value.

## Implementation map

| White-paper component | What runs in this release | Scope and boundary |
|---|---|---|
| Ascension | Connected, editable six-stage workflow, worker cancellation, downloadable evidence and recovery | Human-directed research lab; no autonomous economy |
| Insight | Exhaustive bounded portfolio search, exact source quotations and a visible opportunity landscape | Up to seven supplied opportunities; source notes are not independently verified |
| Nova-Seed / FusionPlan | Complete scenario, source notes, selected work, schedule and native mission inputs; real authenticated encryption and recovery | Portable encrypted capsule; no claim that a browser file is an ERC-721 token |
| MARK | Exact discrete linear bonding-curve quotes, funding reserve and inverse redemption before execution | One modeled funder; no live DEX, oracle, purchase or investment return |
| Sovereign | Exhaustive job-priority schedule search and resource lanes for research, delivery and verification | Best within this scheduling policy; no claim of global job-shop optimality or physical execution |
| Marketplace / identity | Native signed agent identity and the existing local EVM payment acceptance; browser stake/attestation/slash controls | Browser identity is an explicit assumption, not ENS resolution or wallet authentication |
| Validator Council | Separate budget/risk and sequence/capacity checks, plus explicit operator acceptance | Two mechanical checks within one runtime; not independent people, formal proofs or real-world outcome certification |
| Payout burn | Exact 1% integer burn of gross modeled payouts, atomic settlement and replay rejection | Protocol simulation; rounding is downward to the token base unit |
| Value minting | Actor and treasury each receive floor(0.94 × explicitly supplied certified value), subject to one combined emission cap | Default zero mint; no mint authority over the canonical deployed token is assumed |
| Value Reservoir | Unspent escrow and treasury balances remain visible and conserved | Workers’ payments are not silently reused; policy selection starts a fresh modeled cycle |
| Architect | Twenty budget/risk policy evaluations; nondominated cost/value/risk/duration frontier | Sensitivity search over fixed assumptions, not learning or evidence of increasing economic performance |
| Governance | Quadratic credit costs; identity/stake/slash model; approval, policy and eight-day upgrade gates | Inspectable mechanisms, not a complete election, Sybil defense or deployed governance system |
| Strategy dynamics | Replicator ODE, positivity-preserving log-coordinate RK4, Hawk–Dove, coordination and zero-sum cycles | Numerical models with explicit payoff matrices; no universal convergence claim |
| Risk controls | Recomputed weighted residual risks, aggregate gate, action-level and system-level risk calculations | Scenario arithmetic; inputs are not empirical safety measurements |
| Nodes / persistent operator | Existing local agent, journals, cancellation, model providers, isolated code evaluation and signed exports | See the separately tested capabilities and setup in [CAPABILITIES](CAPABILITIES.md) |

The browser computes allocations and schedules with real algorithms. Its cryptography is real Web Crypto.
Its economics and governance are explicitly labeled protocol simulations. The existing GPT-2 browser model
remains available in the homepage AI studio as an actual local text-completion baseline. None of these
components demonstrates general intelligence or turns simulated activity into real token settlement.

## Mathematical corrections that affect an implementation

The lab implements the specified arithmetic and dynamics, rather than reproducing inconsistent printed outputs.
The original paper remains unchanged so the comparison is inspectable.

### Table 4 residual risk

For each row, the paper’s stated rule is
`coverage = 0.4 × staking + 0.4 × formal + 0.2 × fuzz` and
`residual = probability × impact × (1 − coverage)`.

| Row | Calculated coverage | Calculated residual | Printed residual |
|---|---:|---:|---:|
| R0 | 0.38 | 0.109120 | 0.073 |
| R1 | 0.39 | 0.082350 | 0.027 |
| R2 | 0.60 | 0.036000 | 0.012 |
| R3 | 0.37 | 0.102375 | 0.056 |
| R4 | 0.21 | 0.063200 | 0.047 |
| **Sum** | | **0.393045** | **0.215** |

The calculated sum exceeds the proposed **0.3** admission gate. Increasing mitigation in the observatory
changes the actual formula. Adding heterogeneous normalized risk scores does not make their sum a catastrophe probability.

### A trillion actions

For `N = 10^12` actions and per-action failure probability `p = 10^-9`, the expected number of failures is
`Np = 1000`. The union bound is `min(1, Np) = 1`, not `10^-3`. Under independence,
`P(at least one failure) = 1 − (1 − p)^N`, which is effectively one at these values.

A sufficient per-action budget under the union bound for total risk at most `10^-3` is
`p ≤ 10^-3 / 10^12 = 10^-15`. Establishing that bound for an actual system would require evidence not supplied
by this numerical example. The implementation uses `expm1`/`log1p` to avoid cancellation at small probabilities.

### Hawk–Dove and convergence

For the displayed payoff matrix `[[ (V−C)/2, V ], [ 0, V/2 ]]`, the hawk share obeys
`dx/dt = x(1−x)(V−Cx)/2`. When `0 < V < C`, the interior equilibrium is **V/C**.
The printed alternative `(V−C)/V` is not the equilibrium of that matrix.

A zero-sum Rock–Paper–Scissors example cycles; a coordination game has two attracting boundaries.
They illustrate why a unique globally attracting equilibrium, rising welfare, or antifragility cannot be
concluded for arbitrary agents from a discount factor and positive stake alone. Those claims need explicit
payoffs, dynamics, assumptions and proofs. Changing noise or iteration count does not establish them.

### Proofs, emission and physical claims

The repository does not supply the referenced `lip_proof.v` proof corpus, all claimed invariants, or the
large experiment traces needed to reproduce the paper’s strongest proof and convergence claims.
The demo therefore does not display invented proof certificates or passing formal-verification badges.

Counting smooth/piecewise components alone does not bound the full Jacobian’s spectral norm. Shared treasury
couplings require a bound for the joint system. A mint coefficient of 0.94 also does not establish a 3%
annual emission bound without a value flow and explicit cap. The lab enforces a **combined token cap**;
it makes no annual inflation claim. A thermodynamic lower bound, a conservation analogy or an illustrative
Hamiltonian does not establish the paper’s proposed physical behavior for deployed software.

## Exact accounting

Amounts are unsigned decimal strings with at most 18 fractional places, converted to `BigInt` base units.
They are never converted to JavaScript floating-point values for settlement. One million funding lots and
uint256-sized token amounts are explicit bounds. The market’s discrete batch sum equals the independent
sum of individual lot prices; redemption reverses that sum at the current supply.

Each job can settle once. Both checks must pass. The escrow must cover the payout. All inputs and bounds
are validated before a ledger mutation. A payout burns floor(gross / 100); minting is capped across both
actor and treasury. After every accepted settlement:

`escrow + workers + treasury = initial deposit + minted − burned = current modeled supply`.

Funding closes after settlement so an already-spent reserve cannot be redeemed. Unspent escrow is shown
separately. This lab does not promise liquidity, transferable shares, stable prices or mainnet minting rights.

## Encryption, export and recovery

Nova-Seeds use **AES-256-GCM**, a fresh 96-bit IV, a fresh 128-bit salt and **PBKDF2-HMAC-SHA256 with 600,000
iterations**. A random 256-bit blind is encrypted with the genome before its public SHA-256 commitment is
computed. Identical low-entropy plans consequently do not expose an identical unsalted plaintext hash.
All capsule header fields are authenticated as additional data. Strict field, version and size checks bound
the work performed by an imported file. The key is nonextractable; the passphrase is not written to storage
or sent to a server. Use a strong unique passphrase; encryption cannot compensate for an easily guessed one.

These choices follow the [OWASP password derivation guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
and the [Web Crypto AES-GCM interface](https://developer.mozilla.org/en-US/docs/Web/API/AesGcmParams).
They are tested interoperability choices, not a claim of an independent security audit.

- **Continue later:** download the scenario, sealed capsule, evidence JSON and mission brief. The lab keeps
  mission state in memory only; a reload starts a fresh mission.
- **Recover:** open Nova-Seed → Recover, select the capsule, enter the passphrase and inspect the decrypted
  genome. Restore recomputes the scenario; it does not trust imported totals or revive spent simulated funding.
- **Wrong passphrase or altered file:** decryption fails visibly and exposes no recovered plan.
- **Changed inputs:** prior results, seed, reserve, settlement and policy comparisons are invalidated.
- **Offline:** after the page’s service worker finishes installing, the lab and scenario library work after
  an offline reload. Download the PDF separately if you need it offline; it is not in the lightweight cache.
- **Native execution:** download allocation, research or schedule mission JSON and import it into your local
  agent console. Use its journal, signature and payment verification, documented in [OPERATIONS](OPERATIONS.md).

Evidence JSON includes an integrity digest; it is not a trusted signature. Never use an untrusted report’s
own asserted public key to establish identity. The existing homepage verifier accepts an independently
trusted agent public key for native signed results.

## Reproduce the checks

From a source checkout, use Node **22.17.1**, Python **3.12** and Playwright **1.54.0**:

```bash
node --test tests/browser/portal_engine.test.mjs tests/browser/ascension_engine.test.mjs
python scripts/generate_gallery_html.py
python scripts/build_service_worker.py
python -m scripts.validate_ascension --site docs --output evidence/ascension
```

The browser validator exercises actual controls, file downloads, authenticated encryption/recovery,
native mission handoff, redemption, underfunding gates, settlement, policy changes, governance controls,
hostile scenario text, mobile layout and offline reload. The release workflow repeats it against both
site builds and the public deployed URL. Release validation assets contain the recorded outputs and screenshots.

Core tests compare arithmetic against independent per-lot sums, analytic differential equations, exact
known balances and invariants. Existing agent, local model, isolated code, local EVM, contract, Python,
cross-platform, signature and original-demo gates remain required. Claims that need external data,
independent validators, formal proof artifacts or deployed authority remain outside these test results.
