# H1 — The passing Box family does not establish the narrower obligation

**Both aggregate universal claims are refuted.** In `Box_incoming.qif`, item **33 → nominal 32 → definition 31** specifies target 3.3 with deviations −0.2/+0.2 (`DefinedAsLimit=false`), giving **[3.1, 3.5] mm**, or [0.0031, 0.0035] m. Its primary linear unit is mm, conversion factor 0.001.

`Box_FAIR.qif` items **14/20/26/32** point respectively to nominals **13/19/25/31** and definitions **12/18/24/30**. Each has raw target 3.3 and absolute limits **[2.8, 3.8]** (`DefinedAsLimit=true`). There are **76 actual values**, 19 per item, all labelled PASS.

**Formal units:** FAIR has neither primary linear units nor local unit overrides. The supplied `QIF_2_1_Units.xsd`, `LinearValueType` and `ActualLinearValueType`, therefore assigns metres. The recorded range is **3.246–3.536 m**, or **3246–3536 mm**: **0/76** meet the incoming interval. Concrete counterexample: FAIR actual **142**, item **14**, is **3.315 m**, despite PASS.

**Explicit millimetre hypothesis:** interpreting the source numbers and limits as mm gives **73/76** within the incoming interval, range **3.246–3.536 mm**. All exceptions are:

| FAIR actual | FAIR item | Hypothetical value | Excess above 3.5 mm |
|---|---|---:|---:|
| 238 | 20 | 3.511 mm | 0.011 mm |
| 988 | 14 | 3.506 mm | 0.006 mm |
| 994 | 32 | 3.536 mm | 0.036 mm |

Per-item hypothetical conformity is **18/19, 18/19, 19/19, 18/19**, respectively. The recorded item-26 family passes this numerical comparison; the combined family does not.

PASS against [2.8, 3.8] cannot certify the narrower [3.1, 3.5]. Before physical substitution, obtain the supplier's authoritative unit interpretation/export, specimen correspondence, feature/CAD and revision mapping, measurement-method and uncertainty evidence, destination coverage, and receiving approval. Preserve the originals; this calculation does not authorize their repair. Investigate the three source exceptions once those identities are established.

# H2 — A conditional family result survives permutations

**All 400 selected values satisfy the incoming interval under the millimetre hypothesis.** `Cover_incoming.qif` item **23 → nominal 22 → definition 21** specifies 4.5 ±0.3 mm, hence **[4.2, 4.8] mm**.

Selecting every `Cover_FAIR.qif` `DiameterCharacteristicItem` with raw nominal target exactly `4.5` gives **20 items**: **14, 23, 26, 29, 32, 35, 38, 41, 44, 47, 50, 53, 56, 59, 62, 65, 68, 71, 74, 83**. Each has 20 recorded actuals, giving **400**, range **4.523–4.537 mm** under the hypothesis. Minimum clearance to the nearest interval boundary is **0.263 mm**. Source limits are absolute 4.2–4.8 and all 400 statuses are PASS; the conclusion follows from checking the values.

An unknown permutation changes labels, not the multiset, its extrema, or whether every value lies in the same interval: **[4.523, 4.537] ⊂ [4.2, 4.8]**. Thus every bijective relabelling of these selected records preserves this family-wide numerical statement. It establishes neither an individual record-to-hole assignment nor coverage of additional destination holes.

**It identifies no particular hole for rework.** No selected diameter is numerically outside this interval under the hypothesis, and identity remains unresolved. Obtain authorized source unit clarification, specimen/lot crosswalks, complete source-to-destination feature coverage and cardinality evidence, coordinate-frame/CAD/PMI and revision mapping, comparable measurement definitions and uncertainty/decision rules, and current receiving authorization. Assess other obligations and parent statuses separately. Without unit clarification, the FAIR numbers formally denote metres, so the hypothetical result cannot support physical release.

# H3 — Acquire provenance, semantic impact, and current authority separately

**The incoming files are not byte-identical; that fact alone does not invalidate the graph.** Computed identities agree with the supplied manifest:

| File | Bytes | SHA-256 |
|---|---:|---|
| `Cover_incoming.qif` | 418590 | `de1bd5f538fecc5c7fed0884da2a89f548b0efeb56ba9c0581bb8160a926da24` |
| `Cover_reference_incoming.qif` | 418565 | `a513cf188d40ed83332fb47f8fcfbfe40cf2c342cbd28149256146836ac07ffa` |
| `Cover_FAIR.qif` | 303966 | `ccb67423f6f4a917ef9e92820e5f4a47be6b7e5137a193d94d4ba9fd2a17c124` |
| `Cover_integrated.owl` | 6494247 | `7fe7a7b0df19c7a863b987328117c8cb54d10ae46f9677c4aa3baa879091df0d` |

Both incoming QIFs share QPId **f2ddc75c-8fc4-40a3-b3c8-5b5d6ed18e79**; that identifier does not establish byte identity. FAIR has QPId **67f6c6b3-392d-4ea5-a491-cbcc9e7e6a64**.

The sole non-whitespace structural difference is on **PerpendicularityCharacteristicItem 571**: incoming adds **`<FeatureItemIds n="1"/>`**, absent in reference. This advertises one entry but supplies no feature ID. It is a reference-completeness issue, not a changed measured diameter, tolerance, or specimen value. Neither absent nor empty supplies the missing association.

In the graph, **`PerpendicularityCharacteristicItem_1`** carries source `_id=571` and links to **`FeatureItemIds_3`**, which has `_n=1` and no `Id`. The graph therefore preserves this empty-reference condition. Its relationship to the reference export needs provenance investigation; unequal bytes alone prove neither erroneous geometry nor invalid diameter arithmetic.

**Ordered cross-provider evidence acquisition:**

1. Ask the graph provider for exact source artifacts/hashes, CAD and inspection revisions, transformation/ontology versions, generation logs, qualification scope, validation records, and any changes since qualification. Bind the qualification to these delivered artifacts and claims.
2. Ask the incoming exporter to explain item 571's absent-versus-empty list and recover its intended association from authoritative inspection/design records. Obtain a versioned corrected export only if the owner authorizes one; retain the originals and diff.
3. Ask the FAIR supplier for declared units, export settings and measurement provenance. Plausible millimetre numbers justify investigation, not automatic rescaling or inherited authority.
4. Jointly establish serial/lot correspondence, feature and CAD/PMI mappings, coordinate registration, revision compatibility, completeness, and measurement uncertainty. Verify the mappings against physical inspection evidence where needed.
5. Reproduce and requalify the relevant graph relationships and numerical obligations for the present receiving mission. Obtain current owner's authorization specifying permitted use, acceptance criteria, limits and responsible sign-off before substitution or release.

Past qualification is evidence about its original scope. It supplies neither a missing specimen map nor permission for this successor's mission.

# H4 — Local diameter conformity, with parent failure retained

**`Box_incoming.qif` actual 534 numerically meets its diameter requirement; it does not establish part acceptance.** The complete local chain is:

| Record | Evidence |
|---|---|
| Characteristic actual **534** | Value **3.314 mm**, status **PASS**; item **33**, feature actual **533** |
| Item **33**, `DIAMETER1` | Nominal **32**, definition **31**: target 3.3 mm, deviations ±0.2, interval **[3.1, 3.5] mm** |
| Cylinder actual **533** | Diameter **3.314 mm**; feature item **29**; axis point **(146.901, 5.556, 69.3) mm** |
| Cylinder item **29**, `SIMPLE_HOLE12` | Nominal **28**, definition **27**; marked measured |
| Nominal **28** / definition **27** | Nominal axis point approximately **(146.9, 5.5, 69.3) mm**, direction approximately **(0,0,−1)**; internal cylinder, diameter **3.3 mm** |
| Measurement result **604** | Inspection status **FAIL**; actual component **528** |
| Component **528** | Serial **`BOXRESULTS_A07_NIST_MTC_CRADA_BOX_ORIGIN_NIKON_TOUCH`**; status **FAIL** |

The local value is 0.214 mm above the lower limit and 0.186 mm below the upper limit. This checks recorded diameter magnitude only; it is not an uncertainty-qualified conformity decision for all requirements.

**Release:** retain the parent/component FAIL. Result 604 has 46 characteristic PASS statuses and one FAIL: position actual **571**, item **86**, `POSITION5`, value **1.063**. Have receiving quality review that requirement, complete the remaining obligations, and record disposition before release.

**FAIR correspondence:** local IDs, similar diameter values, or an integrated incoming graph do not identify a supplier record or specimen. Obtain the verified FAIR-to-incoming specimen and feature crosswalk, with resolved units and revisions, before transferring any source result.

**Physical investigation:** item 29 and its axis provide an inspection-system locator. Register that coordinate frame against the authoritative CAD/PMI and the identified physical specimen to confirm the hole before intervention. This association identifies where to investigate; it establishes no machining cause. Obtain process history and corroborating measurements before attributing one.

**Resources:** 7 local tool calls through `functions.exec`, each with one shell execution, including reading and saving; no delegation or network. All executions succeeded. Two oversized inspection outputs were truncated and corrected with narrower follow-ups; complete logs were saved. Unexecuted: full-schema validation, CAD registration, graph requalification, physical verification, uncertainty assessment and authorization acquisition. No source changes. Token counts and billing telemetry are unknown.
