[Project notice](../DISCLAIMER_SNIPPET.md)

# Vision, implementation and evidence

The original README, including every flywheel, retains all text beneath the release-status introduction;
CI badge selectors and live Health/Smoke/Integration image sources are maintained. See [badge scope](../CI_STATUS.md).
The preservation release `baseline-2026-09-24` retains the original source and complete Git history.
This project belongs to **$AGIALPHA**. It is separate from AGI Jobs and does not connect this agent to
USDC job settlement or a private OpenClaw installation. Historical job-contract experiments remain present.

## Recovered vision

`docs/DESIGN.md`, the seven original core agent roles, MATS, the evolutionary archive and the README's
flywheels describe the same intended loop: find useful work, plan and research it, search for an improved
solution, check the result, deliver it, retain what worked, and connect earned value to future work.
The design document explicitly calls its forecast a toy model and its architecture a research prototype.
The implementation historically mixed real algorithms and integrations with synthetic fitness, no-op
SDK compatibility classes, random market fixtures and ambitious future claims.

Version 1.5.2 connects a usable bounded agent around the original roles and algorithms. The supported
entry point is `alpha-agent` (also `alpha-factory mission`). Its state, policy, identity, evidence,
operator review, memory and payment receipts share one signed persistent journal. Existing launchers,
interfaces, experiments, assets and documentation remain available.

| Area | Working release behavior | Boundary / evidence |
| --- | --- | --- |
| Planning | Validated immutable goal, bounded inputs, input digest, explicit tool selection | Five supported mission kinds; no unrestricted goal decomposition |
| Research | Extractive evidence or an explicitly configured OpenAI-compatible model; exact source quotations checked | Six exact citations verified with a real pinned local Qwen3 4B model; quotation validity does not prove interpretation |
| Strategy | Existing MATS/NSGA-II optimizes feasible allocations and job priorities | Exhaustive allocation oracle only when the bounded instance fits; otherwise no global-optimum claim |
| Forecasting | Train-only policy selection, separate temporal holdout, measured error and future estimates | Simple last/mean/drift/seasonal policies; not economic prediction or guaranteed returns |
| Code generation | Model-generated or supplied Python `solve` candidate, isolated evaluation, host-owned expected outputs, all cases required | Explicit opt-in and Docker required; no host/Firejail fallback, package installation, automatic merge or deployment |
| Safety | Independent arithmetic/precedence/citation checks; explicit human review bound to revision and artifact hash | Code correctness applies only to supplied cases; no formal verification or security certification |
| Memory | Approved matching allocations/schedules seed later search; parent recorded and constraints checked again | No autonomous model weight training or general self-improvement claim |
| Identity | Ed25519 signatures and a hash-chained journal; optional EIP-191 wallet-control proof | Local-key identity is not ENS ownership, KYC, SPIFFE or reputation attestation |
| $AGIALPHA | Pinned token bytecode/chain/decimals, invoice before payment, confirmed canonical ERC20 receipt, replay protection | Real local EVM tested; mainnet requires configured trusted RPC, independent bytecode pin and finalized blocks |
| Reinvestment | Integer allocation of confirmed receipts to an auditable local earmark | No automatic spending, treasury custody or executed buyback/burn claim |
| Controls | Persistent pause, bounded evaluations/time/output, local bearer-authenticated console, idempotency, compare-and-swap reviews | Single-operator local service; remote exposure requires a separately operated secure access layer |
| Recovery | Consistent SQLite backup plus config/key/token, checksums, signature verification, restore to a new directory | Backup contains secrets; signatures cannot protect against theft of the signing key or rollback without an external checkpoint |
| Original contracts | Preserved Solidity components; exact shipped/test-source comparison and original contract suite | Tests are not an independent security audit; no mainnet deployment or migration performed |
| Original demos | All retained; browser/contract/Python regression checks included | Optional heavy integrations, provider keys, hardware and external services remain conditional |

## Explicit research and integration boundaries

The `openai_agents` package in this repository remains a **legacy demo compatibility stub**, not the
installed OpenAI Agents SDK (`agents`). The new runtime uses an explicit HTTP provider and never counts
stub output as inference. Existing `ModelProvider` fallback and random-market demonstrations do not
establish live market connectivity. Exchange client construction now explicitly selects the Binance
sandbox. Live trading is not a release acceptance criterion and is not activated by mission approval.

The original hash-based fitness is preserved as `simulate_fitness`; `evaluate_agent` now requires real
benchmark cases. The transfer-evaluation command requires a configured model endpoint and held-out
cases; `archived_score_baseline` preserves the old score-only demonstration explicitly. The legacy
`self_improver` metric-file example is not independent evidence of performance improvement, and the
diff-mutation TODO is not an autonomous repair capability. The separate RepoHealer experiments retain
their test-gated patch workflow. The new agent's reviewed memory reuse is a narrower, measurable loop.

Hash-based SNARK placeholders are not zero-knowledge proofs. Demo stakes, simulated revenue, synthetic
benchmarks and predicted objective gains are not token balances or realized profit. Broad AGI/ASI,
SOX/FDA/other compliance, twelve fully deployed industrial businesses, guaranteed returns and unrestricted
self-improvement are **not established by this release**. Those historical ambitions are preserved,
not silently promoted into release guarantees.

See [the operator guide](OPERATIONS.md) for supported installation, configuration, review and recovery,
and [validation](VALIDATION.md) for the exact acceptance surface.

## Browser inference and legacy service completion in 1.3.0

The full Insight build now runs the actual Xenova GPT-2 ONNX model through Transformers.js 3.7.2,
using CPU WASM and a bounded 32-token continuation. Model files are revision-pinned and SHA-256 checked.
The GPU preference remains available for other browser features; the GPT-2 baseline accurately reports
WASM execution. The initial model load requires the full local distribution to be served; after a
successful generation its browser cache supports offline reload. Minimal builds retain the simulation
and explicitly report that model assets are unavailable. The original PyTorch assets are retained.
This completes the browser model integration, not the research aspiration of general intelligence.

AIGA's direct-file service launcher is covered by a required health/startup/shutdown test. Its provider
fallback uses a local HTTP fixture in that test; real-model acceptance is reported separately for the
supported operator runtime and the browser ONNX baseline.


## Browser workspace and complete demo catalog (1.4.0)

The GitHub Pages home now supports four actual bounded workflows with editable inputs, worker
cancellation, disclosed methods, independent constraint/citation checks, human review, portable reports
and optional device-local memory. Native mission JSON imports into the installed agent. The page also
verifies current Ed25519 exports against an independently supplied key using original canonical bytes,
including float results and large nanosecond timestamps. It does not claim to verify current chain state.

Actual local GPT-2 ONNX generation runs in a separate worker and survives an offline reload after
installation. It is an exploratory text-completion model; it does not power the four algorithmic workflows.
The original Insight presentation, its three Plotly charts, tree and logs remain accessible alongside the
modern Insight studio. A complete, pinned same-origin Pyodide runtime powers explicit Python examples.

All 26 demo directories have current guides and one shared launch catalog. Fourteen finite offline launch
contracts, actual CPU AIGA/MuZero, three Streamlit lineage interfaces, offline native GPT-2, 42 shared
browser replay pages and the distinct preserved Insight presentation receive dedicated acceptance checks.
Read [demo evidence and scope](DEMO_VALIDATION.md) before treating any simulation as an integration.
