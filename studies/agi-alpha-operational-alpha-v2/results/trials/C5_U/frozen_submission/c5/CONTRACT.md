# Supplementary mission C5: campaign recovery and reconciliation packet

A software team operates a small multi-tenant job campaign. Four services record different parts of its outcome:
credit reservation, dependency execution, delivered artifacts and internal credit settlement. The team needs an
inspectable decision packet before it releases the campaign's outputs. Replaying each component successfully does
not by itself establish that their records describe the same completed campaign.

Implement `audit(packet)` in `engine.py`. Preserve the public function and return schema, write regression tests
and `REPAIR.md`, and pass the canonical public smoke plus the independent finite contract checks. The identical
verified `components/` implementations are available to every operating configuration. They expose the APIs from
the four component contracts included in this directory. Use them to replay and inspect the submitted evidence;
do not modify them. No specialist-specific algorithm is required. Any equally valid integration method may win.

## Packet structure

The input is a JSON-compatible dictionary with exactly these keys:

```
version, initial_credits, capacity, jobs, journal_events, schedule_commands, artifacts, settlements
```

Version is integer 1 (not bool). `initial_credits` is a nonempty map of nonempty owner strings to nonnegative
integer credits. The name `__usage__` is reserved and cannot be an owner. Capacity is a positive integer.
Jobs is a nonempty list. Each job has exactly `owner`, `job`, `cap`, `cost`, `deps`, `artifact`: owner must exist,
job and artifact are nonempty strings, cap and cost are positive integers, cost <= capacity, and deps is a list
of distinct earlier job IDs owned by that same owner. Job IDs are globally unique. The pair (owner,artifact)
is unique across jobs. These synthetic campaigns are small; no production concurrency or filesystem guarantee
is claimed.

`journal_events` follows the supplied Journal API. `schedule_commands` is a list of exactly one of:

- `{action: "claim", owner, job, lease}`
- `{action: "finish", owner, job, lease, success}`
- `{action: "cancel", owner, job}`

The scheduler first adds all declared jobs in order, then executes these commands in order. `artifacts` is an
ArtifactStore snapshot. `settlements` is a list of `{request, operations, expected}` batches for AccountBook.
The AccountBook starts with each owner's initial credits and zero credits in `__usage__`.

## Release conditions

Return `release` only when ALL conditions hold:

1. Structure is valid and each component replay succeeds under its own documented API. Component failures cannot
   be waived because another service looks successful. Input and output mutations must not affect future audits.
2. Every declared scheduler job ends succeeded, with zero used capacity. No undeclared job can be introduced.
3. Journal jobs exactly match declared jobs, with matching owner/cap, and every journal job is settled. Its final
   settle event supplies actual consumption, including zero. Exact event-ID retries do not add consumption.
4. Artifact records exactly match the declared (owner,artifact) pairs. Every record is committed, complete and
   SHA-256 verified. The same upload string owned by another tenant is not the required artifact. Two jobs cannot
   claim the same tenant artifact as separate deliveries.
5. Each positive-consumption job has one logical settlement batch with request `settlement:` followed by the
   literal job ID. Its operations list contains exactly one transfer from that job's owner to `__usage__`, with
   amount equal to that job's actual consumption. Exact batch retries are permitted and counted once. Zero-cost
   jobs have no settlement batch. No other batches, routes, or transfers are permitted. Expected revisions must
   satisfy AccountBook's ordinary contract. Swapping amounts between jobs is invalid even if aggregates match.
6. Final per-owner AccountBook balance equals the corresponding Journal available balance; Journal reserved is
   zero; usage-sink credits equal total spent. This redundant reconciliation must be checked, not assumed.

For `release`, return exactly:

```
{
  "schema": "campaign-audit/1",
  "decision": "release",
  "packet_sha256": <canonical hash>,
  "reasons": [],
  "summary": {
    "jobs": <number declared>, "succeeded": <number succeeded>, "running_units": 0,
    "artifact_bytes": <sum bytes of the distinct required artifacts>,
    "wallets": <Journal wallets>, "settled_credits": <map from owner to actual credits settled>,
    "usage_sink": <total credits in __usage__>
  }
}
```

For any malformed or inconsistent JSON-compatible packet return the same top-level keys, with `decision: "hold"`,
a nonempty list of descriptive string reasons and `summary: {}`. Reasons need not use fixed wording. If canonical
JSON encoding is impossible, `packet_sha256` is null; otherwise it is always the SHA-256 of the ENTIRE supplied
packet encoded as `json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`
in UTF-8. Mapping key order must not affect this hash. Lists remain order-sensitive. Evidence with an extra exact
retry therefore has the same financial result but a different packet hash. Do not hash only the derived summary.

All numeric integers exclude bool. Reject/hold behavior must not throw for malformed JSON-compatible input.
The audit is read-only and deterministic. Real ENS identity, signatures, live customer acceptance, real currency,
physical products, confidential data, arbitrary hostile Python objects and remote execution are outside scope.

Run `python test_public.py`. Accepted completion is a bounded executable audit prototype, not an operating business
or independent proof of demand. `offerings.json` contains the same synthetic buyer brief and proposal alternatives
for all configurations; participants may propose alternatives but cannot replace executable acceptance with prose.
