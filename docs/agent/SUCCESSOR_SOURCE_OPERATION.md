# Operate a bounded source-analysis campaign

[Operator handbook](SUCCESSOR_OPERATIONS.md) · [Research notice](../DISCLAIMER_SNIPPET.md)

The maintained `alpha-agent successor-study` path drives the existing `CampaignExperiment`, `DiscoveryLoop`,
fixed selectors and signed transactional Journal. The preserved `backend.agent_manager.AgentManager` research
scheduler is separate; `ALPHA_CYCLE_SECONDS` does not start this operation. Original Harness/Fleet holds remain.

## Delivery and first run

Inspected public base: Alpha **1.41.1**, commit `787bc547f8c44854931b316d7286b8bc9f9c8bba`, Python 3.11–3.13.
These new commands require the focused source change accompanying this guide. Their branch implementation does
not establish their presence in the unchanged public 1.41.1 wheel. Install a release containing the change using
its matching wheel, lock, installer and SHA256SUMS via [the installation guide](OPERATIONS.md). Check
`alpha-agent --version` and `alpha-agent successor-study --help`. Exact source, installation and publication
status belong in the delivery report. Node, an external model, Jobs, Manager and Fleet are not needed here.

Use new paths; `--home` precedes the command and `--output` precedes the study action:

```sh
alpha-agent --home ./source-state init
alpha-agent successor-study --output source-operation.json operation-example
alpha-agent --home ./source-state successor-study --output source-result.json operation-start source-operation.json
```

Review the generated envelope first. Starting approves its exact purpose, operator, sources, tools and resource
limits. The example has one training campaign at time zero and three confirmation arrivals at 4, 8 and 12 seconds,
each comparing three policies. Concurrency is one, with a 60-second absolute deadline and at most three crash
attempts per child. Worst-case search/checking budgets, including retry reservations, must fit the separate totals
before work starts. Routine phases need no further prompt. Empty intervals wait; completed operations stop.

This runs in one foreground Python process on the operator's computer. Closing it stops computation. No unattended
session survives that process. An optional OS service can start the same `operation-run` command, but its machine,
logs, lifecycle and finite deadline must be disclosed; no service is installed by these commands. The separate
browser-first `/try/` experience explores browser-local work and does not keep a persistent executor running.

## Useful mission and evidence

A technical reader uses these notes to retain prerequisite qualifications in concise release notes. An incoming
`CampaignUnit` has annotated public/nonpersonal clauses, provenance, weights and an acyclic prerequisite graph.
Sources are inline; URLs record provenance and are never fetched. The default example is explicitly synthetic.
Acceptance requires at most two exact source clauses, retained references, recomputed supported coverage and visible
unsupported selections. The weighted coverage objective is structural. Incomplete/over-budget checks cannot support
improvement. Source annotations, reader comprehension, physical validity, customer demand and profit remain unproven.

Changed dependencies, weights or valid requirements establish changed tasks; renaming an identical document does
not establish transfer. The example changes graph structure and weights, then includes a task where simple ordering
already works. A changed purpose, tool, budget or privilege needs new approval. The candidate cannot change these
terms, evaluator code or authority controls.

| Stage | Real operation and retained artifact |
|---|---|
| Identify | Select the next due permitted mission; charter and exact input commitment |
| Out-Learn | Inspect its supplied graph and training outcomes; native diagnosis |
| Out-Think | Evaluate competing fixed programs; all attempts and charged search work |
| Out-Design | Construct executable selection packages with representation/production rules |
| Out-Strategise | Freeze the training-selected search policy; study and child freeze digests |
| Out-Execute | Execute installed selectors and conventional controls; exact notes and checks |
| Out-Evolve | Test the frozen policy on changed whole campaigns; retain losses/ties/incumbent |

This retains a reusable sandbox search policy. It installs no production replacement. Comparators also execute and
their checking costs count. The incumbent and controls receive equal inputs, budgets, tool and archive access.
Strong conventional exact search runs on every terminal document. Policy savings against broad enumeration do not
establish advantage over a conventional policy allowed the same reuse. Training costs and changed-task losses count.

## Status, STOP and restart

Read `operation_id` from the configuration and substitute it for `OPERATION_UUID`:

```sh
alpha-agent --home ./source-state successor-study --output current-status.json operation-status OPERATION_UUID
alpha-agent --home ./source-state pause
alpha-agent --home ./source-state successor-study --output stopped.json operation-stop OPERATION_UUID
alpha-agent --home ./source-state verify
alpha-agent --home ./source-state successor-study --output history.json operation-export OPERATION_UUID
```

Status separates authorization state from the executor lock being held. It shows latest notes, frozen policy,
comparison evidence, costs, failures, interventions and attention needed. A running authorization without an active
process is not an unattended-running claim. `pause` is the reversible global stop and persists across restarts.
`operation-stop` permanently cancels the campaign, clears study approval and fences stale worker handoffs.
A canceled operation cannot resume. STOP is checked inside native phase transactions; bounded pure work already
holding the journal lock may finish before a stop writer obtains it. No external effect needs rollback here.

To continue an interrupted, still-authorized operation after inspection:

```sh
alpha-agent --home ./source-state resume
alpha-agent --home ./source-state successor-study --output resumed.json operation-run OPERATION_UUID
```

The existing OS operator lock releases on process death. A committed child is reconciled before replay: its retained
result, costs and measurement identity remain unchanged. Incomplete pure work may repeat within the reserved cap;
unclean-exit CPU is explicitly unknown. Unexpected deterministic errors put the operation on HOLD. Expiry, changed
code/inputs and exhausted allowances require inspection/new approval. Restart never extends the absolute deadline.
Uncertain external effects are outside this adapter and must not use its pure-work retry rule.

## Continuity and recovery

The submission is copied once into private `source-operation-UUID.json` and bound by its complete digest. Future
input commitments enter the journal before construction. The separate file retains immutable submitted bytes;
changing them blocks execution. The study retains its original training/freeze/confirmation order. Closed candidate
selectors receive only their development document before freezing. The local OS operator can inspect all files:
this is local computational separation, with no independent custody claim. Existing exact-exposure checks remain.

`history.json` is inert evidence, including submitted inputs when their commitment verifies, with no private key or
activate/import-operation command. Keep a trusted journal key/checkpoint separately. Existing private `backup` and
`restore` commands preserve Journal history and the private identity. Never publish that backup. The operation input
file is separate: preserve it or the verified public history export too. Restoration to a new home cannot continue
the old operation, even with the input copied; authority remains bound to the original home and absolute deadline.
Malformed submissions fail before work reservation without blocking other valid operations. A corrupt authoritative
signed journal requires trusted recovery; corruption is not skipped. Inconclusive child checks remain visible while
other planned comparisons continue. No lost/failed task is silently converted into accepted evidence.

Search/checking logical units include training ancestors and committed pending-child work. Measured process CPU and
session wall time remain separate. Human minutes and engineering/review labor are unmeasured; process starts,
recovery and stop interventions are disclosed. Unknown full costs prevent a full-cost capability-growth claim.
Capability, sustained operational throughput and commercial growth are distinct. Load evidence applies only to its
declared sample; maximum concurrency remains one. No unrestricted-scale, real-demand or realized-revenue claim follows.

## Existing adapter boundaries

| Interface | This operation's actual use |
|---|---|
| Alpha | Installed Journal, CampaignExperiment, DiscoveryLoop, schemas and fixed selectors |
| Jobs / `$AGIALPHA` | No service, wallet, payment or settlement; no new compatibility qualification |
| Manager / USDC | No service, wallet, payment or settlement; separate currency route |
| Fleet | No provisioning or original held native/review operation |
| Five Alpha contracts | No function is needed or called; no wallet, local EVM or settlement claim |

The historical accepted API tuple and pending native integration remain in
[issue 4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850). Source inspection, installed local execution,
local EVM testing and real settlement remain separate. This source operation clears no original Harness/Fleet decision.
