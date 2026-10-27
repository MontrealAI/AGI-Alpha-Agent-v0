# Independent acceptance protocol, version 1

## What the delivered service means

The deliverable is a correct, source-traceable audit of a supplied purchasing proposal against explicit functional
obligations. Passing means that the structured report satisfies the frozen research-task contract. It does not mean
customer acceptance, a real transaction, verified nursery inventory, ecological performance, or authority to plant.

The original useful purpose is retained verbatim. The evaluator checks the separately supplied machine-readable
obligations; it does not establish that every implication of free-text mission meaning was extracted correctly. The
researcher supplies that mapping. Any unrepresented requirement requires a new task contract and fresh evaluation.

The hypothesis is that retaining an executable obligation compiler can reduce loss of functional demand when orders
are changed or fulfilled incompletely. Existing mix design, contract growing, forward purchasing, and provenance
tracking are available conventional methods. Their invention is not claimed.

## Frozen scope and data meanings

- `scope` is exactly `documented-source-screen`.
- The catalog is a small, explicitly source-derived factual table. It is not the inaccessible Illinois workbook.
- `catalog.water` lists guide-documented planting contexts, not an exhaustive ecological suitability classification.
- Seasonal coverage means a documented flowering interval and presence on a proposed row. It is not measured bloom
  density, nectar quantity, survival, pollinator nutrition, establishment, or field efficacy.
- `resource_mode=flower` requires the stated habitat context and flowering season. It makes no nectar claim.
- `resource_mode=nectar` additionally requires explicit `nectar=true`. `false` is pollen-only; `null` is unknown.
- A host requirement is separate from flowering coverage. A flowering plant does not qualify as a monarch host unless
  the catalog explicitly lists `monarch` in `hosts`.
- Lot records, provenance status, dates, quantities, prices, and counterparties are fictional research fixtures unless
  independently identified otherwise. `verified` is a fixture condition, not live authentication or certification.
- `quoted_price_cents` is validated as a nonnegative integer. No price cap appears in this task schema, so this checker
  cannot determine affordability, a price-acceptance decision, or commercial profit.

## Input contract

The top-level catalog contains `taxa`, each with a unique `id`, `seasons`, `water`, `nectar`, `hosts`, and nonempty `source`.
Season names are `early`, `mid`, and `late`; habitat values are `dry`, `mesic`, and `wet`.

Each task contains `id`, `purpose`, `habitat`, `resource_mode`, nonempty unique `required_seasons`,
`min_species_per_season`, `region`, `delivery_week`, `rows`, `lots`, and `quoted_price_cents`.
`required_host` is absent/null or `monarch`. Each row contains `taxon`, `quantity`, `unit`, and optional `lot_id`.
Each lot contains unique `id`, `taxon`, `quantity`, `unit`, `evidence_status`, and optional `region` and `available_week`.

Row quantities and seasonal minima must be positive integers; lot quantities, price, and known weeks must be
nonnegative integers. Booleans and floats are not integers for this contract. Missing lot IDs, lot region, and lot
availability dates represent missing evidence and lead to blockers. Missing required task fields and malformed field
types make the input invalid. Unknown taxa and unknown lot identifiers are audit findings, not invalid JSON.

No units are converted. A mass is not converted to pure live seed, seed count, plants, or ecological output. A row and
its referenced lot must have exactly equal unit strings. Region strings must match exactly; the checker has no supplied
permission to treat another provenance region as interchangeable.

## Reference calculation

1. Reject malformed inputs with a nonempty `input_errors` list and `source_screen_pass=false`.
2. For valid inputs, count distinct taxa, never rows or quantities, for each required season.
3. Compute `source_coverage` from rows whose taxon, documented habitat, and requested resource mode qualify, ignoring
   lot constraints. The source catalog is held fixed; no silent botanical inference or catalog extension is allowed.
4. Compute `supply_coverage` from rows that also pass every lot constraint. Aggregate quantities requested from the same
   lot across all rows with that lot's exact unit. If their total exceeds lot quantity, every comparable row receives an
   insufficient-quantity blocker. A mismatched unit remains a separate blocker and is not arithmetically added.
5. Repeated occurrences of the same taxon qualify once. A valid row for that taxon may contribute coverage even when a
   second row is blocked; the blocked second row still prevents the entire proposal passing its source screen.
6. For each required season, report sorted qualifying taxa, count, required minimum, and positive shortfall separately
   for source and supply coverage. List every supply shortfall as an original unmet obligation.
7. A host passes only if an otherwise source- and supply-qualified row names a documented required host. Report source
   and supply host taxa separately. If no host is requested, host pass is true with empty host lists.
8. All independent applicable row blocker codes must be reported. Missing/unknown lot stops further lot checks only;
   unknown taxon stops biological checks only. An empty proposal still has unmet seasonal/host obligations.
9. `source_screen_pass=true` exactly when input is valid, no row is blocked, and no original obligation remains unmet.
   Every report has `field_outcomes_verified=false`, `customer_acceptance_verified=false`, and
   `production_authorized=false`.

## Critical output contract

The reference output has these fields: `task_id`, `scope`, `original_purpose`, `input_errors`, `source_coverage`,
`supply_coverage`, `host`, `blockers`, `original_unmet_obligations`, `source_screen_pass`, `field_outcomes_verified`,
`customer_acceptance_verified`, and `production_authorized`.

Each season entry is `{taxa: [canonical IDs], count: integer, required: integer, gap: integer}`. Host is
`{required: string/null, source_taxa: [IDs], supply_taxa: [IDs], pass: boolean}`. A blocker is
`{row: zero-based index, code: string, lot_id: string/null}`. A seasonal unmet obligation is
`{kind: "seasonal", season: string, required: integer, qualified: integer, gap: integer}`; an unmet host obligation is
`{kind: "host", host: "monarch"}`. Empty-string or missing lot identifiers are reported as null in blocker records.

For valid inputs every critical field must match. Array order is immaterial; duplicates are not silently discarded.
For invalid inputs, error wording need not match, but at least one error must be present, task and scope identity must
be preserved, the pass flag must be false, and all three authority/outcome flags must be false. Extra suggested plans
are outside this exact structured comparison and require separate review. No ungraded narrative is thereby accepted.

### Blocker codes

| Code | Meaning |
| --- | --- |
| `unknown_taxon` | The supplied catalog has no canonical taxon ID. |
| `habitat_not_documented` | The guide-derived catalog does not document the requested context for this taxon. |
| `nectar_unknown` | Nectar is required but the supplied evidence does not establish it. |
| `pollen_only` | Nectar is required but the catalog identifies this species as pollen-only. |
| `missing_lot` | The proposed row does not identify a lot. |
| `unknown_lot` | The row names a lot absent from the supplied lot records. |
| `lot_taxon_mismatch` | The row and its referenced lot name different taxa. |
| `unit_mismatch` | The row and lot use different units; no conversion is authorized. |
| `lot_evidence_unknown` | Supplied lot status is unknown. |
| `lot_evidence_failed` | Supplied lot status failed. |
| `region_unknown` | The lot's provenance region is absent or empty. |
| `region_mismatch` | The lot's region differs from the task's required region. |
| `availability_unknown` | The lot's availability week is absent. |
| `unavailable_by_deadline` | The known availability week is later than the required delivery week. |
| `insufficient_lot_quantity` | Aggregate comparable demand exceeds this lot's supplied quantity. |

## Independent implementation and protected confirmation

`oracle.py` uses Python standard library only and imports no production compiler. Its author has not inspected the
core compiler. It evaluates reports against this stated contract, not against production-code output.

The parent supplies one openly available development task. No confirmation cases or answer files are created before
the parent freezes core artifact bytes, policies, source versions, and comparison procedures. After that freeze, this
evaluation owner creates twenty-four deliberately varied research fixtures, twelve for each mission. They are not sampled ecological
observations. The set includes valid positives, valid negatives, malformed inputs, mission changes, and combined
failure conditions. A blanket refusal cannot pass because correct positives and precise positive coverage within
negative cases are required.

Recipient A concerns mesic seasonal floral provision. Recipient B changes habitat, adds a monarch host requirement,
and changes provenance. The actual frozen artifact must be used on B; no refitting on B's protected answers is allowed.
Task packets may be shared with workflow agents. Answer files remain with the evaluator and parent until outputs are
sealed. Hashes and creation order are recorded. Subsequent repairs require new artifact versions and newly generated
confirmation cases; old failures remain in the evidence history.

The same catalog, task evidence, permission boundaries, and resource ceilings must be supplied to compared workflows.
The established expert may use existing tables, scripts, validation, and contract-growing practices. An ordinary-use
condition must be representative and must not be instructed to ignore evidence. Measurements of human service, ordinary
model use, expert operation, and retained-artifact use require observed executions or explicit simulation labels.

Passing this oracle establishes a narrow software property under supplied rules. It does not establish independent
botanical validation, buyer value, demand, autonomous discovery, model improvement, superhuman ability, or ecological
transformation. Results on constructed fixtures have no population confidence interpretation. Useful accepted research
delivery and unproven live commercial/ecological acceptance are reported separately.

## Reproduction interface

Run `python evaluation/oracle.py expected --catalog data/catalog.json --tasks TASKS.json --out EXPECTED.json` to produce
reference reports after confirmation is authorized. Run `python evaluation/oracle.py check --catalog data/catalog.json
--tasks TASKS.json --reports REPORTS.json --out CHECKS.json` to verify sealed submitted reports. Each input file may wrap
its list as `tasks` or `reports` respectively. Exit status is nonzero when check mode finds a rejected or missing report.
