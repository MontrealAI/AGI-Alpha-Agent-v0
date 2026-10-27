# Independent technical audit

This audit was authored in a separate agent role within the same research team and shared workspace. It is not an outside assessor's certification, a frontier-model comparison, a customer acceptance receipt or live ENS authorization.

## Results

| Scope | Result | Evidence |
|---|---|---|
| Frozen original core 1.0.0 | All 15 finite geometry scenarios pass, but four additional assertions fail: null properties in either source crash; a Point is admitted as a park polygon and can falsely confirm a facility | `results_v1.json`, `instrument_v1.py.txt`, `audit_v1.py.txt` |
| Additional original-core scope probe | Shared latitude/longitude swap passes internal acceptance and returns a false source-consistent confirmation outside the Montreal area | `additional_v1_failure.json` |
| Corrected core 1.1.0 regression | All 15 original geometry scenarios and all 16 aggregate/package/audit assertions pass | `results_v1_1_regression.json` |
| Fresh constructed missions | 48/48 cases pass after the corrected source freeze; seed 2026102751 | `fresh_v1_1.json`, `fresh_freeze_v1_1.json`, `fresh_fixtures_v1_1.json` |
| Competent conventional control | Same candidate and disposition decisions for 128/128 sampled nondevelopment public-source rows; seed 2026102752 | `public_control_results.json` |
| Actual final GeoPackage reopened | 2,245 park records; 3,476 facility records; 757 exception rows; CRS EPSG:32188; SQLite integrity `ok`; no missing facility exception link or contradictory confirmed ID | `public_control_results.json` |
| Existing TrustRegistry fixture | 10/10 checks pass, binding signature checks to the real manifest, source code and input hashes | `trust_fixture_results.json` |

The corrected source hash is `f4370f182820fb4a72d95b769b48dbac6d3634e7f32d6a322e6e638aa2541ffa`. The frozen capability manifest hash is `4f46d46ee3b52ee95ca134cf5fbfa4021e689416d6f664c94c33e4b46718edb7`. Original source and unfavorable results remain preserved.

Fresh cases include interior agreement, shared boundaries, overlapping parks, unknown IDs, polygon holes, invalid park geometry type, null properties and shared coordinate-axis mistakes. These are authored structural cases within the scoped Montreal workflow. The 128-row conventional comparison uses native GeoPandas/GDAL source reading and linear vectorized polygon coverage; it does not import the study's reconciliation function. It shares Shapely and PROJ dependencies, so the comparison is an implementation control, not independent geodesy or source truth.

The trust fixture uses the repository's existing `TrustRegistry`, `TrustAnchor`, `sign_record` and `ti-library-review` domain. Fresh ephemeral keys authenticate a local `*.agent.agi.eth`-shaped fixture identity. No private key is persisted. Unknown trust, wrong role/domain, tampering and revocation are rejected. Signature verification does not admit this geospatial workflow into unsupported native capability scope or grant execution authority. Historical version 1.0.0 recipient use remains distinct from current 1.1.0 qualification.

## Reproduction

From the study directory, using its pinned dependency environment:

```bash
python technical/independent_audit/audit.py --label replay_v1_1 --expected-hash f4370f182820fb4a72d95b769b48dbac6d3634e7f32d6a322e6e638aa2541ffa
python technical/independent_audit/fresh_confirmation.py --label replay_v1_1 --expected-hash f4370f182820fb4a72d95b769b48dbac6d3634e7f32d6a322e6e638aa2541ffa
python technical/independent_audit/public_control.py
python technical/independent_audit/trust_fixture.py
```

New labels preserve the original outcomes. Re-running the fixed seed replays the same fixtures; it does not create fresh scientific evidence. The original defects can be reproduced with `audit.py --source technical/versions/v1/geodelivery.py --label replay_original --expected-hash a7246fc53395bc5404d5e031c515b213f091b8153b39be1c3cf059dc0f738529`. That replay is expected to report `passed: false`. The shared-axis-swap case is fully specified in its saved JSON.

`public_control.py` expects the final full delivery under `technical/delivery/`. Trust fixture replay uses new ephemeral keys, so signatures change while the ten semantic outcomes should remain the same. Its manifest hash pin must not be silently relaxed if the retained capability changes.

## Scope of local code checks

Ruff passed on the four authored Python audit tools. Scoped strict mypy passed with third-party missing imports ignored and imported modules skipped. Black formatted these audit tools. An initial three-error typing check on an unchecked dynamic-import specification was corrected in the audit harness; it did not change the instrument. These scoped results do not imply full repository, production, release or publication qualification.
