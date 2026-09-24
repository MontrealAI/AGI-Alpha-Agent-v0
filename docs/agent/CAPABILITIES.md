[Project notice](../DISCLAIMER_SNIPPET.md)

# Vision, implementation and evidence

The original README, including every flywheel, remains verbatim beneath the release-status introduction.
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

Version 1.2.0 connects a usable bounded agent around the original roles and algorithms. The supported
entry point is `alpha-agent` (also `alpha-factory mission`). Its state, policy, identity, evidence,
operator review, memory and payment receipts share one signed persistent journal. Existing launchers,
interfaces, experiments, assets and documentation remain available.

| Area | Working release behavior | Boundary / evidence |
| --- | --- | --- |
| Planning | Validated immutable goal, bounded inputs, input digest, explicit tool selection | Five supported mission kinds; no unrestricted goal decomposition |
| Research | Extractive evidence or an explicitly configured OpenAI-compatible model; exact source quotations checked | Six exact citations verified with a real pinned local Qwen3 4B model; quotation validity does not prove interpretation |
| Strategy | Existing MATS/NSGA-II optimizes feasible allocations and job priorities | Exhaustive allocation oracle only when the bounded instance fits; otherwise no global-optimum claim |
| Forecasting | Train-only policy selection, separate temporal holdout, measured error and future estimates | Simple last/mean/drift/seasonal policies; not economic prediction or guaranteed returns |
| Code generation | Model-generated or supplied Python `solve` candidate, isolated evaluation, host-owned expected outputs, all cases required | Explicit opt-in and sandbox required; no host fallback, package installation, automatic merge or deployment |
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
