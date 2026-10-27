## H1

**Decision: both universal destination-conformance claims are refuted.** This is a receiving-evidence comparison, not authorization for physical substitution. IDs below are local to their named files.

In `Box_incoming.qif`, item **33 → nominal 32 → definition 31** specifies target 3.3 and deviations −0.2/+0.2 (`DefinedAsLimit=false`): **[3.1, 3.5] mm**, or [0.0031, 0.0035] m. Incoming `PrimaryUnits` declares mm with conversion factor 0.001.

In `Box_FAIR.qif`, the item→nominal→definition chains are **14→13→12, 20→19→18, 26→25→24, 32→31→30**. Each target is 3.3; each definition specifies absolute limits **[2.8, 3.8]** (`DefinedAsLimit=true`). There are **76 values, 19 per item**, raw range **3.246–3.536**, all labelled PASS.

The supplied QIF 2.1 `LinearValueType` and `ActualLinearValueType` rules use a value's explicit unit, otherwise the primary linear unit, otherwise **metres**. FAIR has neither a unit override nor `FileUnits`. Consequently:

- **Formal interpretation:** source values span **3246–3536 mm; 0/76** meet the destination interval. Counterexample: FAIR actual **142**, item **14**, result **138**, serial **13**, records **3.315 m = 3315 mm**, despite PASS.
- **Explicit millimetre hypothesis:** reinterpret both source values and source limits as mm, without modifying the source. **73/76** meet [3.1, 3.5] mm. The three failures are actual **238/item 20 = 3.511** (serial 4), **988/item 14 = 3.506**, and **994/item 32 = 3.536** (both serial 5). Each is source-PASS because it remains inside the wider [2.8, 3.8] source interval.

PASS therefore cannot transfer the narrower obligation. Next obtain an authorized unit clarification/export, controlled design revisions, specimen and feature correspondence, measurement capability/uncertainty and the receiving decision rule. Reconcile FAIR's recorded **COMPANY** standard with incoming **ASME-Y14.5-2009**. The Box FAIR header says `nist_mtc_crada_box_rev-D`; incoming placeholder version fields do not establish revision equivalence. Reassess all applicable requirements and obtain current disposition authority before substitution.

## H2

**Decision: the fixed recorded family passes the scalar test under the stated millimetre hypothesis; a particular physical hole is not identified.**

The qualifying `Cover_FAIR.qif` items are **14, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62, 65, 68, 71, 74, 83**. Each item's nominal ID is item−1, definition ID item−2, with raw target 4.5 and absolute limits [4.2, 4.8]. All **400 recorded values**—20 per item across 20 result sets—are source-PASS and fall in **[4.523, 4.537] mm** under the hypothesis. Minimum: actual **337/item 32**; maximum: **361/item 14**.

Incoming **23→22→21** specifies **4.5±0.3 mm**, hence **[4.2, 4.8] mm**. Every recorded value meets it. Decimal comparisons and an independent integer-micrometre calculation agree. Any permutation of this fixed multiset preserves its extrema, so unknown labels cannot change this universal scalar result. This argument requires the same obligation for every selected member; it does not establish membership in a destination physical set.

The incoming file also contains 20 nominal 4.5-mm cylinder feature items. Equal counts do not prove a bijection, coverage, or specimen identity. No failing diameter has been established here to allocate for rework, and these records cannot select a physical hole. Obtain the provider's feature/inspection-program map and specimen crosswalk, controlled revision/standard reconciliation, authorized unit correction, calibrated measurement evidence and applicable acceptance rule, then verify complete destination coverage and current reuse authority. As written, FAIR units remain metres; physical reuse is unresolved.

## H3

**Decision: preserve the numerical hypothesis and usable local evidence, but requalify the intended reuse.** All nine supplied originals match their manifest SHA-256 values; complete identities are saved in `source_inventory.json`. Relevant exact identities are:

| File | Bytes | SHA-256 |
|---|---:|---|
| `Cover_incoming.qif` | 418590 | `de1bd5f538fecc5c7fed0884da2a89f548b0efeb56ba9c0581bb8160a926da24` |
| `Cover_reference_incoming.qif` | 418565 | `a513cf188d40ed83332fb47f8fcfbfe40cf2c342cbd28149256146836ac07ffa` |
| `Cover_integrated.owl` | 6494247 | `7fe7a7b0df19c7a863b987328117c8cb54d10ae46f9677c4aa3baa879091df0d` |
| `Cover_FAIR.qif` | 303966 | `ccb67423f6f4a917ef9e92820e5f4a47be6b7e5137a193d94d4ba9fd2a17c124` |

Both incoming versions share QPId **f2ddc75c-8fc4-40a3-b3c8-5b5d6ed18e79** and creation time **2017-03-20T11:40:15**, yet are not byte-identical. The only substantive XML addition is **`<FeatureItemIds n="1"/>`** under **PerpendicularityCharacteristicItem 571**, alongside whitespace change. It declares one member but supplies no `Id`; neither version provides a usable feature link there. Measurements, tolerances and units are unchanged, so H2's arithmetic is unaffected. Parser/schema and association consequences still require examination.

The graph itself contains **PerpendicularityCharacteristicItem_1**, stored `_id=571`, pointing to **FeatureItemIds_3**, with `_n=1` and no `Id`. It thus already reflects this empty-container structure. Different source bytes alone do not establish that the graph is wrong, nor does this local agreement establish complete graph qualification. The manifest places the reference QIF and graph in `qif-ontology-dataset-V2.zip`, and incoming QIF in `nist_box_mtc.zip`; archive provenance does not reconstruct the transformation history.

Ordered acquisition plan:

1. Ask the present receiving owner to specify mission, acceptance obligations, controlled revision, permitted cross-provider disclosure/reuse and decision authority. This task permits analysis; past qualification does not confer present release authority.
2. Obtain provider-controlled original exports, hashes, revision records and the previous qualification's exact input set, converter/ontology/rule versions, queries, checks, exclusions and approval scope. Preserve both incoming versions and this diff.
3. Ask the exporter to explain item 571's empty list and FAIR's missing units; obtain documented unit intent and, if warranted, a formally issued corrected export with lineage. Plausible mm numbers alone authorize neither repair nor reuse. Resolve COMPANY versus ASME semantics and the FAIR header `nist_mtc_crada_cover_reb` against controlled design evidence.
4. Acquire cross-provider specimen/lot histories, feature/program maps, coordinate registrations and complete requirement coverage; verify candidate correspondences against AP242 geometry and inspection records. Obtain calibration, method and uncertainty evidence.
5. Replay the relevant conversion and mission queries against exact versions, compare affected triples/results, independently check conclusions, and have the current owner approve the specified use. Retain unresolved conditions explicitly.

## H4

**Decision: actual 534 numerically meets its local diameter requirement; the enclosing inspection is FAIL.** In `Box_incoming.qif`:

- **DiameterCharacteristicActual 534:** **3.314 mm**, recorded **PASS**; item **33** (`DIAMETER1`) → nominal **32** (3.3) → definition **31** (−0.2/+0.2). Thus **3.1≤3.314≤3.5 mm**, deviation **+0.014 mm**.
- Its `FeatureActualIds` references **CylinderFeatureActual 533**, diameter **3.314 mm**, axis point **(146.901, 5.556, 69.3)**. This points to feature item **29**, `SIMPLE_HOLE12` → feature nominal **28**, nominal axis point **(146.9, 5.5, 69.3)** and direction approximately **(0,0,−1)** → feature definition **27**, **INTERNAL**, nominal diameter **3.3 mm**. Item 33 names measurement device **15**, `CMM`.
- Containing **MeasurementResults 604** has **InspectionStatus FAIL** and references **ActualComponent 528**, also **FAIL**, serial **`BOXRESULTS_A07_NIST_MTC_CRADA_BOX_ORIGIN_NIKON_TOUCH`**. Its position actual **571**, item **86**, value **1.063**, is recorded FAIL and references feature actual **569**.

The graph corroborates 534 through stored `_id=534` on `DiameterCharacteristicActual_82`; generated graph suffixes are not QIF IDs. Independently, AP242 contains a radius-1.65 cylinder on nominal axis x=146.9, y=5.5, supporting a geometric candidate, subject to frame/revision registration.

For **whole-part release**, obtain and resolve the parent failure, remaining requirements and authorized disposition; local PASS cannot override them. For **FAIR correspondence**, obtain an explicit specimen/feature crosswalk and resolve units/revisions; common numbers or IDs do not establish it. For **physical investigation**, verify A07's identity and obtain the CMM alignment, fixture transformation and program-feature locator before locating or remeasuring `SIMPLE_HOLE12`. Inspection association identifies an investigation target, not a machining cause; causal attribution needs process/tooling evidence.

**Resources:** Six tool-call turns, each with one local execution; no delegation, network or input mutation. Four analysis scripts and logs retain extraction, complete value lists, hashes, diff, graph checks and CAD corroboration. Corrections: overly broad/truncated diagnostics; exact nominal-pointer and plural result-container names; graph lookup by stored `_id`. No command failed. Full QIF-schema validation, graph-pipeline qualification, authoritative specimen/frame reconciliation, physical remeasurement and uncertainty-based release were not executed. Token usage and billing telemetry are unknown.
