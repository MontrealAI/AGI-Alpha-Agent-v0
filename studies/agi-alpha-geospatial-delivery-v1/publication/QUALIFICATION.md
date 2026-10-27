# Local qualification and publication handoff

This is an additive research study under `studies/agi-alpha-geospatial-delivery-v1/`, inspected against repository baseline `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. It contains executed public-data processing and explicitly modeled commercial scenarios. Local acceptance is the frozen research handoff contract, not a customer receipt or production approval.

## Successfully executed

| Scope | Actual result | Preserved evidence |
|---|---|---|
| Complete study wrapper | Technical, economic and optional existing-TrustRegistry stages all exit 0 | `../reproduction_complete/reproduction_receipt.json` and three logs |
| Economic reproduction | All **10** final economic JSON files match by semantic content **and bytes**; confirmation seed **730552**, **2,400** worlds | `../reproduction_complete/reproduction_receipt.json` |
| Complete geospatial delivery | **2,245** park rows and **3,476** facility rows preserved; **3,175** source-consistent associations; **757** explicit review rows | `../technical/delivery/` |
| Independent package readback | SQLite integrity `ok`; GDAL/GeoPandas reopen, row counts, CRS and exception links pass | `../technical/independent_audit/public_control_results.json` |
| Scoped implementation tests | **16** regression tests pass | `../technical/reproduction/step_1.log` |
| Review-corrected independent regressions | All **15** geometry scenarios and **16** aggregate/package assertions pass | `../technical/independent_audit/results_v1_1_regression.json` |
| Fresh structural confirmation | **48/48** authored cases pass after corrected-instrument freeze | `../technical/independent_audit/fresh_v1_1.json` |
| Competent conventional control | **128/128** sampled nondevelopment decisions match a separate implementation using the same formulation | `../technical/independent_audit/public_control_results.json` |
| Actual retained-recipient application | Frozen version 1.0.0 executes in a separate process on Anjou: **100** assets, **89** associations, **11** reviews; all seven output files tie the identical-information ordinary library | `../technical/recipient_v1_result.json` |
| Optional format confirmation | All **256** rows and extra fields preserved; **29/32** missions have identical association semantics; three boundary divergences remain failures of unrestricted invariance | `../technical/gym/fresh_format_missions/summary.json` |
| Existing TrustRegistry fixture | **10/10** source/manifest/signature/role/tampering/revocation checks pass; replay uses fresh ephemeral keys | `../technical/independent_audit/trust_fixture_results.json` |
| Scoped code checks | Ruff passes for study instruments/tests, audit tools and final wrapper; strict mypy passes for instrument modules, audit tools and wrapper with third-party missing imports ignored and imported modules skipped | Scoped command records and audit README |

The source-consistent association count does not estimate a frontier-model mission success probability. Source truth, geodetic accuracy and customer acceptance are not established by internal consistency or conventional-tool agreement. The conventional control shares mature Shapely/PROJ dependencies. Separate reviewer roles share the same research team and workspace.

## Frozen identities

| Artifact | SHA-256 |
|---|---|
| Original instrument 1.0.0 | `a7246fc53395bc5404d5e031c515b213f091b8153b39be1c3cf059dc0f738529` |
| Corrected instrument 1.1.0 | `f4370f182820fb4a72d95b769b48dbac6d3634e7f32d6a322e6e638aa2541ffa` |
| Explicit-binding CSV/WKT adapter | `3b05081bccc60ba570ba4ac862374d0ce98c1beb48a0ddda7c27beab81dd0599` |
| Capability manifest | `4f46d46ee3b52ee95ca134cf5fbfa4021e689416d6f664c94c33e4b46718edb7` |
| Final economic runner | `0a08f21e30d4fb56cc8d83c1294dcb5ebb2dfdb0682ca40aca388273e3d76c83` |
| Final economic configuration, canonical JSON | `20c1f9deaa7f67f8026669cc5ae03844a7912eafb19ce20c97bdb5eb5114e5f0` |
| Full reproduction wrapper | `4379055568904fc49bec89502e94141e23f8ca9a35b60efce272b2302d44c665` |

The canonical configuration hash is intentionally different from its formatted-file byte hash. Reproduction checks the same canonical representation as the frozen economic engine.

## Preserved failures and limits

Original instrument 1.0.0 had three defect classes: null source properties could crash the workflow; Point/LineString park inputs could be admitted as park polygons; and a shared coordinate-axis swap could pass relative consistency outside the target area. Original source, failing assertions and the additional axis-swap probe remain in `../technical/independent_audit/`. Version 1.1.0 corrects these with explicit property handling, polygon enforcement, target-area checks and source-hash verification. The municipal-source rerun is a **replay**, with unchanged associations; the 48 later structural cases are separately prospective evidence.

The optional adapter's three fresh divergences occur at exact polygon boundary vertices after EPSG:3857 round trips. The affected associations become visible review items. Unrestricted automatic cross-CRS boundary use remains **HOLD**, and optional network retention is separately held on uncertain incremental economics. These outcomes do not erase the completed original-source assurance delivery or turn its conditional commercial model into actual sales.

Earlier economic runs and corrections remain under `../economics/history/`, `../economics/results/`, `../economics/development_failures.json` and `../economics/review/`. An initial wrapper-only raw-versus-canonical hash check stopped before execution; its correction and failed attempt are retained in `../reproduction_complete/attempts.json`. Frozen economic logic, policy and results were not changed to resolve that wrapper defect.

Controlled human/U/E/E+ trials were not run. Actual customer collections are **CAD 0**. Complete actual research cost is unmetered. Wages and API unit rates anchor the cost model; workload, token quantities, buyer behavior, demand, mission reliability and service prices remain explicit assumptions. Broader uncertainty includes losses.

## Scope and publication boundary

Repository status inspection found changes only within this new study directory. Original raw source bytes, prior research and existing runtime/publication files are preserved. The intended publication inventory excludes `__pycache__`, `.pyc`, `.pytest_cache` and other local caches. A bounded scan found no private-key blocks or common credential-token patterns in intended files; this is not a full security certification. Public keys and ephemeral-signature receipts are expected fixture evidence; no private signing key is retained.

The following are **not established by this study's local checks**: full repository test/coverage campaigns; repository-wide pre-commit or hosted CI completion; configured release/security gates; installed wheel/platform qualification; geospatial admission into native production scope; live ENS authorization; customer acceptance or settlement; a canonical Pages deployment; release-asset or served-public-byte acceptance. Those actions and gates remain with existing repository/publication owners. Publication rendering, visual QA and final remote-byte checks must be recorded separately before announcing their corresponding links or claims.

The ordinary source-qualified draft/review path applies. No runtime scope extension, release/version allocation, alternate publisher, wallet action, paid-model call, credential change or customer communication is part of this qualification. The paper's strongest supported commercial conclusion is modeled profitability for the stated complete assurance handoff; the additional capability results and their limits are reported separately.
