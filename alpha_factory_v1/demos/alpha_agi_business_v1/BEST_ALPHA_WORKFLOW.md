[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Best Alpha Opportunity Workflow

This short note summarises the highest ranked alpha signal included with the demo and how to act on it using the
  provided multi‑agent stack. The goal is to show a concrete starting point for experimentation.

## 1. Identified Alpha

Using `examples/find_best_alpha.py` (run from the root of the project directory) the top opportunity from
  `examples/alpha_opportunities.json` is:

```
gene therapy patent undervalued by market
```
with a score of **88**.

## 2. Launch the Orchestrator

Run the one‑click launcher which automatically installs any missing dependencies and starts the local orchestrator with
  the OpenAI Agents bridge enabled:

```bash
python start_alpha_business.py
```

Open the REST docs at `http://localhost:8000/docs` to verify the service is running. The core agents (discovery,
  opportunity, execution, risk, compliance, portfolio) start automatically.

## 3. Evaluate supplied assumptions

The score-only ranking above is a historical example, not a cost/benefit or
risk assessment. It cannot be submitted for execution. Supply a complete
business state instead; all amounts must use the same caller-selected currency.
The example below is deliberately illustrative and unverified.

```bash
# API_TOKEN must match the configured orchestrator token.
./scripts/post_alpha_job.sh examples/job_evaluate_business.json
```

The helper sends only the `state` object to the authenticated
`POST /agent/alpha_execution/evaluate` endpoint. It requires budget, max_loss
and opportunities containing id, cost, benefit and worst_loss. The immediate
response reports ranked proposals, supplied-loss checks, unverified position
arithmetic and pending legal/compliance review, with an input hash. It never
places orders, forms a company or certifies compliance.

The bridge `submit_job` tool accepts the same outer `{agent, state}` object.
Its old `trigger_best_alpha` helper now rejects score-only submissions with a
clear missing-input error. It never reports them queued.

## 4. Interpret the result

Inspect the immediate `evaluation` response. No periodic state is changed or
reused, and no event is written to the dashboard/memory by this endpoint.
Malformed, incomplete or unauthenticated requests fail without returning an old
result. To schedule the separate file-driven periodic evaluation, call
`POST /agent/alpha_execution/trigger` without a body and with authentication.
That response only acknowledges rescheduling; it is not proof of evaluation.
Request bodies on a trigger are explicitly rejected.

The original research architecture and diagrams remain context for future
integrations; this supported path is bounded supplied-assumption evaluation.
