# Economic evidence mapping

`analysis/economics.mjs` is an additive mapping into the unchanged project `automated-costs.mjs`, `shadow-ledger.mjs`, and v1 economics adapter. Their exact hashes are checked; local byte-identical copies and upstream/source-candidate status are recorded in `canonical/SOURCE.json`. It does not introduce another transaction system or ledger implementation.

The initial template is a schema fixture, not an experimental result. Populate it only after observing final outcomes. All prices, full monetary costs, capital and approved allocations remain unknown in this study; actual collections are zero. No arbitrary horizon, utilization, amortization, reserve or reinvestment assumption is supplied. The canonical replay API's inert default `reinvestmentBps: 0` is not an investment policy or earned allocation.

## Invoke

```sh
node research/useful-work-v2/analysis/economics.mjs \
  --input /path/to/completed-economic-evidence.json \
  --root /absolute/path/to/useful-work-v2 \
  --out /path/to/new-economics-edition
```

The output directory must not already exist. All evidence paths below resolve against `--root`. Optional `evidence_sha256` fields pin the expected bytes; otherwise the actual hash is recorded. The script refuses duplicate mission IDs, duplicate substantive triggers, duplicate additive receipt paths, and failed receipts relabeled successful.

## Unique mission record

Each entry of `missions` has this shape; replace placeholders with actual evidence:

```json
{
  "mission_id": "upgrade-001",
  "phase": "confirmation",
  "freshness_status": "untouched_before_protocol_freeze",
  "trigger": {
    "kind": "dependency_bundle",
    "before_identity": "exact before lock/source identity",
    "after_identity": "different exact proposed lock/source identity",
    "reference": "protocol and trigger evidence reference"
  },
  "outcomes": [
    {
      "arm": "retained",
      "accepted": true,
      "independently_verified": true,
      "decision": "SCOPED_COMPONENT_PRESERVED",
      "evidence_path": "results/path/to/decision.json"
    }
  ]
}
```

Arms are `manual`, `retained`, and `conventional`; include the actually observed outcomes for each. Phases are `development`, `confirmation`, and `control`. Supported decisions are `SCOPED_COMPONENT_PRESERVED`, `COMPONENT_REGRESSION`, `INCOMPLETE_HOLD`, and `NOT_EXECUTED`. An accepted regression package can be useful if it independently establishes a bounded hold decision; an incomplete package is not an accepted outcome merely because a JSON file exists. `accepted` may be null when unestablished. Acceptance is an explicit mapping tied to immutable evidence, not something this economics script infers from a producer's assertion count.

Equal before/after identities are no-ops and contribute no substantive mission count. Controls never count as missions. Different arms and repeated evaluations do not multiply the number of underlying triggers. The canonical mission acceptance follows the explicitly selected `primary_arm`; separate per-arm counts retain comparator outcomes. Changed historical dependencies against the same consumer are representative assessments, not actual historical customer requests. Freshness is an explicit provenance assertion requiring the protocol evidence; a confirmation label alone does not qualify an operational pair for the fresh-work comparison.

The manual arm is the actual first manual probe/package assembled in this study. Its construction belongs in this study's investment account. It is not a recruited or observed non-AI human professional. The competent-human comparison remains a separate wage-and-duration counterfactual with unknown duration.

## Resource records and ownership

Each `resource_entries` row declares one evidence record and its cost ownership:

```json
{
  "id": "upgrade-001-retained-command",
  "ownership": "delivery",
  "arm": "retained",
  "mission_id": "upgrade-001",
  "outcome": "succeeded",
  "accounting_role": "additive",
  "stages": ["execution"],
  "evidence_path": "results/path/to/execution-receipt.json"
}
```

Ownership is exactly one of `discovery`, `shared_investment`, `manual_construction`, `retained_construction`, `conventional_construction`, `delivery`, or `maintenance`. `arm` is one of the three arms or `shared`. Failed work retains its actual owner and uses `outcome: "failed"`; it does not move to a cost-free excluded category. Known prelaunch errors whose exact subprocess metrics were not captured should retain documentary evidence and null resource amounts.

`accounting_role` is `additive`, `nested_evidence`, or `documentary`. A nested row must give `covered_by` naming an additive record; its measurements are not added again. JSONL metering logs use `format: "jsonl"` and must be documentary. Their timestamps and entries are retained without monetizing assistant elapsed time or pretending that event counts are inference-token bills.

Known receipt quantities include command wall time, child CPU, controller CPU, network requests/bytes, model calls/tokens, human/customer minutes, peak RSS and logical storage snapshots. A generic meter's own zero model calls never substitutes for the child's unknown runtime activity. Resource totals expose both measured subtotals and missing-record counts; a missing quantity makes the complete total null. Memory peaks are maxima, not sums. Logical storage remains per-record snapshot evidence, since adding overlapping cached snapshots would double-count storage. Currency amounts remain null.

## Complete delivery envelopes

For each measured arm/mission pair, reference the actual additive receipts and nested evidence:

```json
{
  "mission_id": "upgrade-001",
  "arm": "retained",
  "scope_complete": true,
  "resource_ids": ["upgrade-001-retained-command"]
}
```

`scope_complete: true` requires at least one additive record and explicit coverage of all canonical stages: preparation, planning, execution, verification, correction, packaging, reporting and recovery. A single complete enclosing command may cover all stages if that is its actual boundary; do not mark an isolated 15-second probe as complete delivery. An unchanged stage with zero activity must be supported by the measured enclosing scope, not silently omitted. Shared environment construction and retained assets remain separately charged to the finite investment inventory.

Operational differences are calculated only for fresh, equivalent accepted packages with complete declared scope on both sides. All failed attempts remain in campaign resources. A physical resource difference does not establish dollar repayment, extra eventual output, or financeable expansion.

## One finite capability account

The canonical `study-investment` container receives separate unknown cost events for discovery, common evaluation/integration, the actual manual incumbent, the retained builder, and the conventional builder, with failed attempts separated within each owner. It describes the same tested capability, not five hypothetical reinvestments. Per-mission delivery accounts and explicit ownership prevent duplicate resource attribution. Every actual construction bill remains unknown until billing evidence is available.

The output answers all six investment questions separately. It reports marginal, recurring and fully loaded costs through the existing canonical API, retaining unknown inputs. Symbolic low-utilization, failure, maintenance and demand equations are provided without selecting favorable numerical assumptions. Monetary repayment and financeable expansion remain unestablished; actual collections remain zero.
