[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

## Disclaimer

# DGM Operations Runbook

This guide outlines day-to-day operational tasks for the **Distributed Governance Module (DGM)**.

## Scheduler Flags

The orchestrator exposes flags controlling job order and concurrency:

| Flag | Purpose |
|------|---------|
| `--priority` | Adjust agent queue weighting. |
| `--max-jobs` | Limit concurrent job count. |
| `--pause` | Temporarily halt scheduling without stopping workers. |

Use these options to throttle or pause workloads during maintenance windows.

## Rollback Steps

1. Tag the current stable commit with `git tag stable`.
2. If a deployment fails, check out the previous tag:
   ```bash
   git checkout stable
   docker compose up -d --build
   ```
3. Verify services recover before promoting new changes.

## Cost Caps

Set `MAX_COST_USD` in the environment to bound cumulative API spend per cycle.
Exceeding this value stops new jobs until the cap resets.

## Sandbox Tuning

The policy runbook describes CPU and memory limits. Update `.env` with
`sandbox_cpu_sec` and `sandbox_mem_mb` to tune runtime safety. Use
`firejail` where available for additional isolation.

## Lineage Audit

Run `alpha-agi-insight-v1 lineage-dashboard` to review archived agent activity.
The dashboard visualises provenance data so you can verify each job's origin
and decision path.
