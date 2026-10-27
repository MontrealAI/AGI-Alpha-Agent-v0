# H1

**Decision: both universal incoming-compliance claims are refuted.** Scope is all recorded values for Box FAIR items 14, 20, 26 and 32, not all physical holes or part release.

All QIF files declare version 2.1.0. File-local item→nominal→definition chains in `Box_FAIR.qif` are 14→13→12, 20→19→18, 26→25→24 and 32→31→30. Each target is 3.3; definitions specify absolute limits [2.8, 3.8], `DefinedAsLimit=true`. In `Box_incoming.qif`, 33→32→31 specifies target 3.3 with signed deviations −0.2/+0.2, `DefinedAsLimit=false`: **[3.1, 3.5] mm**, equivalently [0.0031, 0.0035] m. Incoming `PrimaryUnits/LinearUnit` declares mm, factor 0.001; omitted conversion offset defaults to zero.

The supplied QIF 2.1 `LinearValueType` and `ActualLinearValueType` use explicit `linearUnit`, otherwise primary length units, otherwise **metres**. FAIR has neither FileUnits nor length overrides. Thus all **76 values (four items × 19 results)**, range **3.246–3.536 m**, fail the incoming interval formally. For example FAIR actual 142, item 14, is 3.315 m = 3315 mm. All 76 recorded PASS labels concern the wider source limits, not the incoming obligation.

Under the separate hypothesis that FAIR targets, limits and measurements meant millimetres, the range becomes **3.246–3.536 mm**: **73 pass, three fail**:

| FAIR actual | Item | Result; specimen serial | Value, mm |
|---|---:|---|---:|
| 238 | 20 | 232; 4 | 3.511 |
| 988 | 14 | 984; 5 | 3.506 |
| 994 | 32 | 984; 5 | 3.536 |

Each still records PASS against [2.8, 3.8]. Item 26 has 19/19 within the incoming interval under the hypothesis; each other selected item has one violation. These are complete finite checks, independently recomputed with rational arithmetic; `H1_witness.csv` records every actual and parent.

**Next action:** obtain the FAIR exporter’s signed unit clarification or controlled re-export, the design authority’s applicable revision/requirement, supplier-to-receiver specimen and feature crosswalk, and measurement uncertainty/decision-rule evidence. Reconcile the three violating records before substitution. The hypothetical reinterpretation changes no source and grants no physical acceptance.

# H2

**Decision: the selected recorded family passes numerically under the millimetre hypothesis; individual physical identity remains unresolved.** In `Cover_FAIR.qif`, the qualifying diameter items are **14, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62, 65, 68, 71, 74, 83**. For each item n, nominal n−1 has raw target 4.5 and definition n−2 has absolute limits [4.2, 4.8]. Incoming 23→22→21 has target 4.5 and deviations −0.3/+0.3, giving **[4.2, 4.8] mm**.

There are **400 values: 20 per item across 20 results**, all recorded PASS, with hypothetical range **4.523–4.537 mm** and **zero interval violations**. Minimum witness: actual 337, item 32, result 327, serial 9, 4.523. Maximum: actual 361, item 14, result 357, serial 10, 4.537. `H2_witness.csv` exhaustively enumerates them.

Every value lies inside the same interval; any permutation of the selected records preserves that predicate. Unknown labels therefore cannot change this family-wide numerical statement. This does **not** prove a bijection onto the destination’s physical feature set. It identifies no particular hole for rework, and supplies no diameter-based rework reason among these records. Formal FAIR units remain metres absent correction.

**Next action:** request an authorized unit resolution, complete feature-family membership and coverage evidence, a specimen/lot crosswalk, feature/coordinate/datum registration, applicable design revision and standard interpretation, comparable measurement methods with calibration/uncertainty and acceptance rule, other required characteristic results, and current reuse authorization from the receiving authority. Each condition is needed before translating this finite numerical result into physical reuse.

# H3

**Decision: a past qualification and plausible numbers do not authorize current reuse.** Exact identities were recomputed and match the supplied manifest:

| File | Bytes | SHA-256 |
|---|---:|---|
| Cover_incoming.qif | 418590 | de1bd5f538fecc5c7fed0884da2a89f548b0efeb56ba9c0581bb8160a926da24 |
| Cover_reference_incoming.qif | 418565 | a513cf188d40ed83332fb47f8fcfbfe40cf2c342cbd28149256146836ac07ffa |
| Cover_integrated.owl | 6494247 | 7fe7a7b0df19c7a863b987328117c8cb54d10ae46f9677c4aa3baa879091df0d |
| Cover_FAIR.qif | 303966 | ccb67423f6f4a917ef9e92820e5f4a47be6b7e5137a193d94d4ba9fd2a17c124 |

The two incoming files share QPId `f2ddc75c-8fc4-40a3-b3c8-5b5d6ed18e79`, QIF 2.1.0 and creation time 2017-03-20T11:40:15, but differ in bytes. The incoming archive member is `QIF-IncomingInspection/CoverResults_20_samples.QIF`; the reference is `qif-ontology-dataset/2_InspectionData/Cover.QIF` from the separate ontology archive.

The complete text diff shows one substantive XML difference: **PerpendicularityCharacteristicItem 571**, nominal 570, contains `<FeatureItemIds n="1"/>` in incoming and omits that element in reference; there is also whitespace variation. No diameter measurement or tolerance changed. Empty-with-declared-count and absent are distinct representations, neither supplying a feature Id. Their validation/translation consequences need checking.

Graph `PerpendicularityCharacteristicItem_1` has `_id=571` and links to `FeatureItemIds_3`, which records `_n=1` but no Id. That observation warrants a lineage/translation check; different source bytes alone do not establish a wrong graph or identify a missing feature. The graph is not a unit correction or mission permission.

**Ordered acquisition plan:**

1. Obtain the current mission owner’s purpose, decisions, scope, participating providers, permitted data/actions and release authority; obtain the earlier qualification’s exact scope and limitations.
2. Ask the graph custodian for input hashes, archive/revision identity, ontology and converter versions, mapping rules and validation evidence. Reproduce item 571’s empty/absent handling against both exact inputs.
3. Ask the FAIR exporter/metrology owner for authoritative unit evidence and any controlled replacement, preserving originals and recording changes; rerun the conditional calculations afterward.
4. Obtain provider-approved specimen/lot and feature mappings, coordinate transforms/datums, complete coverage, and current design/inspection requirements. Incoming records cite ASME-Y14.5-2009; confirm applicability rather than assuming it transfers.
5. Obtain measurement comparability, uncertainty and decision-rule evidence; resolve discrepancies and rerun mission-specific checks. Present those results to the current acceptance authority before physical reuse.

`identities.json` also inventories both STEP and OWL assets. STEP headers name Box Rev-D and Cover Rev-B; generic incoming version 1.0.0 does not establish design-revision equivalence.

# H4

**Decision: actual 534 passes its local recorded diameter interval; it does not support whole-part release.** In `Box_incoming.qif`:

- Diameter actual **534**: **3.314 mm**, status **PASS** → item **33**, `DIAMETER1` → nominal **32**, target 3.3 → definition **31**, deviations −0.2/+0.2. Therefore 3.1 ≤ 3.314 ≤ 3.5 mm.
- Its `FeatureActualIds` links cylinder actual **533**, diameter 3.314 → feature item **29**, `SIMPLE_HOLE12`, determination mode Measured → feature nominal **28** → definition **27**, INTERNAL cylinder, nominal diameter 3.3. Nominal axis point is (146.9, 5.50000000000002, 69.3); actual axis point is (146.901, 5.556, 69.3), in declared mm coordinates.
- Containing measurement result **604** has inspection status **FAIL** and references actual component **528**, also **FAIL**, serial **BOXRESULTS_A07_NIST_MTC_CRADA_BOX_ORIGIN_NIKON_TOUCH**, assembly path 3. Within this result, position actual **571** records FAIL, value 1.063, item 86, linked feature actual 569; that is a separate association from actual 534.

The graph contains corresponding local objects, but their duplication is not independent physical verification. No standalone feature acceptance follows from “Measured.”

**Next actions:** for release, obtain the complete applicable inspection/disposition and acceptance owner’s resolution of the parent failure, including actual 571. For FAIR correspondence, obtain a verified specimen and characteristic/feature crosswalk; matching numbers or labels do not supply it. To locate the physical feature, have the operator verify serial 528’s specimen, CMM program feature 29 and datum registration against the controlled model; then inspect the relevant hole. Obtain raw measurement and process evidence before attributing a machining cause.

## Resource statement

Used **8 functions.exec calls**, each dispatching one local exec_command; no delegation/network or input mutation. One calculation execution failed on a nested tolerance path and was corrected once. Three exploratory outputs were truncated; decisive calculations and full initial inspection are saved. Graph lookup was refined from Id to _id. Unexecuted: full-schema validation, CAD topology/registration, metrology qualification, physical inspection and permission verification. Token counts and billing telemetry are unknown. Scripts, source identities, complete finite witnesses and logs accompany this response; no self-score.
