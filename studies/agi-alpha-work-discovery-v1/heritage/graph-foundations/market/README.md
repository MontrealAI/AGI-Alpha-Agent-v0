# Evidence-bound economics adapter

This directory extends the existing strategic buyer/competitor simulator and canonical monetary ledger. The inherited sources are byte-identical to their exact PR4940 identities. The extension grants no operational, identity, payment or investment authority. Live identity enforcement is **NOT RUN**; actual customer collections and transactions are **zero**.

## Comparison and finite design

The inherited first-asset B enterprise is the new strong A incumbent. The new B profile represents the actual searchable-registry composition; new C represents the actual graph-guided composition. All three retain the same initial52-week horizon, USD1000 seed, USD200 reserve, heterogeneous buyers, competitors, invoicing, refunds, liabilities and original first-asset history. The graph receives no assumed price, trust, quality or human-time premium.

The preregistered design has48cells: six market conditions, two financing policies and four cost profiles, each with24new paired seeds9101–9124. This yields1152paired worlds and3456enterprise histories. The fixed conditions retain lower demand, no demand, nonzero buyer integration, an upkeep shock and stronger competing AI. These are conditional simulated markets, not customer observations or equilibrium estimates. Frequencies across designed cells are not market probabilities.

Production has15primary unseen paired compositions and three separately labeled designed root-scope stresses. CPU calibration uses the15primary records only. All18technical outcomes are still required to admit an economically tested candidate. Cache confirmations do not enter the fresh-mission denominator. The conventional direct D alternative is reported separately through matched CPU/elapsed time and assumed-tariff arithmetic. The native-history A/B/C comparison does not establish global graph superiority or adoption over D.

## Minimal measured-input contract

The root runner provides `evidence/production-summary.json`:

```json
{
  "arms": {
    "A": {
      "mission_count": 18,
      "primary_count": 15,
      "stress_count": 3,
      "accepted_count": 18,
      "elapsed_seconds_total": 0,
      "cpu_seconds_total": 0,
      "tools_total": 0,
      "cache_confirmations": 0,
      "per_mission": [
        {
          "id": "exact-registered-mission-id",
          "cohort": "primary",
          "accepted": true,
          "decision": "CONSISTENT",
          "elapsed_seconds": 0,
          "cpu_seconds": 0,
          "asset_id": "exact-actually-used-composition-id"
        }
      ]
    }
  }
}
```

The illustrative zero values above are schema examples, not measurements. Supply all four arms A/B/C/D, all18records, matched mission identities/cohort labels and actual quantities. B/C accepted rows must identify the actual composition used. Inclusive totals cannot omit per-mission CPU or elapsed time. Any measured shared recurring overhead beyond individual records is allocated uniformly across18fresh outcomes before the15primary mean is computed. Known calls, tools and confirmations remain counts; authoring inference and human minutes remain unknown unless separately metered. Equivalent accepted outputs are checked by exact decision per matched mission before any CPU saving is credited.

The root produces `market/asset-bindings.json`:

```json
{
  "schema": "agi-alpha-verified-capability-asset-bindings/v1",
  "assets": {
    "B": {
      "id": "exact-registry-composition-id",
      "files": [{"path": "src/actual-file.mjs", "sha256": "actual-64-digit-hash"}],
      "admission_evidence_path": "evidence/asset-admission.json",
      "admission_evidence_sha256": "actual-64-digit-hash"
    },
    "C": {
      "id": "exact-graph-composition-id",
      "files": [{"path": "src/actual-file.mjs", "sha256": "actual-64-digit-hash"}],
      "admission_evidence_path": "evidence/asset-admission.json",
      "admission_evidence_sha256": "actual-64-digit-hash"
    }
  }
}
```

Include the complete source/dependency closure and an exact composition descriptor distinguishing the selected method. `sourceManifestHash(files)` hashes the sorted path/hash records with the adapter's canonical JSON. The source-bound admission evidence is a projection of actual admission results:

```json
{
  "admissions": [
    {"asset_id": "exact-graph-composition-id", "decision": "ADMIT",
     "mode": "FIXTURE_ONLY", "source_manifest_sha256": "actual-manifest-hash"}
  ]
}
```

This projection does not replace native admission or authority rules. The adapter independently verifies every bound file, the admission evidence hash, its exact manifest binding, and each accepted production invocation. A `production_used` flag alone establishes nothing.

## Complete costs and unknowns

`cost-assumptions.json` covers discovery, rejected candidates, executable construction, validation, identity verification, indexing, proof generation/checking, retrieval, composition, revalidation, storage, maintenance and authoring/research contribution. Both B and C pay identical authenticated catalogue/root and inclusion costs and receive the same freshness/validation policy. The reference scenarios differ only in additional graph adjacency construction and recurring graph-index maintenance.

Every row maps into the unchanged canonical categories. No new monetary ledger is introduced. Reference incremental one-off allocations are USD88.50 for B and USD90.50 for C; low and high are separately rounded quarter/fourfold scenarios. Reference upkeep is USD0.25/week for B and USD0.40/week for C. **These numbers are illustrative complete-category allocations, neither invoices nor empirical lower/upper bounds.** The actual-unknown profile retains null for every complete cost category, including under an upkeep shock. The original first-asset history is charged once by inherited accounting; existing source construction is not silently charged again as new composition work.

Inclusive measured primary CPU differences receive only an explicitly assumed USD1/core-hour conversion. USD0.1/1/10 deterministic sensitivities are also reported. No elapsed wall time is treated as human work, and no unmeasured provider/customer attention saving is credited. Signed subcent costs remain visible even when the inherited cent ledger rounds the marginal effect to zero. The separate break-even attention calculation reports what additional *unmeasured* saving would be required; it never assigns that saving to a treatment or alters campaign decisions.

## Second-investment and alternatives

The actual constructed, fixture-admitted and fresh-work-used composition is the candidate asset. `adaptive` pays declared discovery costs, then chooses whether justified investment can be funded from already generated resources. `completed-research-replay` asks whether the already constructed research could have been paid from those resources at the fixed checkpoint. An affordable unprofitable attempt remains explicitly unqualified.

Retaining the incumbent, maintaining its existing asset and preserving reserves remain real no-construction alternatives. Registry and graph adoption carry complete declared new costs. Outside research not financed by the enterprise is deducted exactly once from project-inclusive profit and never increases cash. Positive graph financial admission additionally requires actual modeled uses, direct repayment and positive paired profit. Any conditional native result remains separate from global choice against D and from actual market success.

## Freeze and commands

Before production input is available, validate the static design and original source custody without executing market outcomes:

```sh
node market/run-campaign.mjs --design-only
node tests/market.test.mjs
```

Once measured production and actual asset bindings exist:

```sh
node market/run-campaign.mjs --validate-only
```

The root freezes `protocol/market-design.json` with `status: FROZEN_BEFORE_MARKET_OUTCOMES`, the actual registration UTC and issue4850registration URL. It creates a separate freeze manifest:

```json
{
  "schema": "agi-alpha-verified-capability-market-freeze/v1",
  "marketOutcomesInspected": false,
  "files": [{"path": "market/adapter.mjs", "sha256": "actual-hash", "bytes": 123}]
}
```

The manifest must bind the protocol, adapter, runner, cost assumptions, production summary, asset bindings, actual source closures, admission evidence and all inherited provenance/source files. Execution refuses missing or changed required files:

```sh
node market/run-campaign.mjs --run --freeze protocol/market-freeze.json --output evidence/market-primary
```

The output directory must be new. The campaign has an immutable180second wall/CPU envelope and retains partial results on failure. It does not automatically restart, alter prices, change seeds or extend the horizon. Outputs include complete compressed paired histories, compact per-world ledgers, representative histories, CPU effect calibration, direct-D comparison, conditional cell summaries and source/resource execution receipts. Unknowns, losses and failed investments remain visible.

The19enumerated economic controls test source integrity, denominator and cohort handling, shared-overhead accounting, fair evidence costs, null propagation, candidate source/usage binding, direct alternative visibility, subcent penalties, cash-accounting semantics and the freeze gate. They are synthetic software controls and execute zero primary market outcomes. Code and these development controls share an author; independent review is separately recorded.
