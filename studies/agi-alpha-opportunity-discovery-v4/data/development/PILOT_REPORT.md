# Plate-only evidence-viability pilot

## Decision

**Go for a bounded service-construction study of cross-provider inspection evidence comparability and requalification.** The pilot produced concrete geometric traces, a source-grounded rejection of naive correspondence, an exact-schema unit obstruction, and a conditional repair route. It did not establish customer demand, a cost advantage over expert engineering, a new algorithm, or a presently admissible cross-provider inspection substitution.

The useful deliverable is an **audit of what evidence supports**, with the specific extra identity, unit, and measurement evidence needed for a recipient's decision. It is not automatic part acceptance. The pilot is development on one actual public part, with researcher-selected example assertions after inspection. No Box or Cover result was used during this session.

## Reproduction and evidence

Run from this directory:

```sh
python pilot.py
```

The runner consumes four frozen Plate artifacts in `inputs/`, verifies their hashes, imports actual AP242 geometry using CadQuery/OpenCascade, reads QIF and the supplied integrated reference ontology, and writes `pilot_receipt.json`. The exact QIF 2.1 unit schema is retained as `QIF_2_1_Units.xsd`. `input_manifest.json` records source archive members. The supplied reference is an E building block, not a newly invented mapping or evidence that this pilot outperforms expert use of it.

Runtime versions: Python 3.12.14, CadQuery 2.7.0, OCP 7.8.1.1. The import is a valid single solid with 261 faces, 722 edges, 34 cylindrical surfaces and approximate dimensions 120 × 71.16 × 5 mm. All 18 incoming cylindrical feature definitions have at least one geometry candidate under explicit coordinate/axis/radius checks. Split cylindrical faces can legitimately produce multiple face candidates. This is a numerical correspondence test on the actual imported solid, not a general proof of complete manufacturing-feature equivalence.

The original archive's 2017 AP203 geometry and the reference package's 2019 AP242 export are different complete artifacts. This pilot uses the latter; it does not grant equivalence to every manufacturing revision or silently reuse evidence across them.

## 1. Complete, independently inspectable incoming trace

The selected chain is fully reproduced in the JSON receipt:

| Stage | Exact source object | Observed content |
|---|---|---|
| Incoming requirement | QIF definition `99`, nominal `100`, item `101` | `DIAMETER7`; target 3; offsets −0.254/+0.254; interval [2.746, 3.254] mm |
| Feature | QIF item `97`, nominal `96`, definition `95` | `SIMPLE_HOLE10`; diameter 3; axis point approximately (45.606601718, 25.606601718, 4.5); axis parallel to z |
| Design geometry | Imported face index `93`; STEP advanced face `#7281`, cylindrical surface `#7269`, placement `#7268`, point `#7265` | Radius 1.5 mm; matching axis line; extent z=0…5 mm |
| Actual feature | QIF feature actual `98` | References feature item `97`; diameter 3.017 mm |
| Actual characteristic | QIF actual `102` | References item `101` and feature actual `98`; value 3.017; recorded `PASS` |
| Specimen record | Measurement result `183`, component `4` | Serial `PLATE_RESULTS_A01_NIST_MTC_CRADA_PLATE_ORIGIN_NIKON_SCAN`; overall inspection `FAIL` |

The diameter result satisfies its encoded interval, and its value agrees with the feature-actual diameter. **The part still has overall status FAIL.** Reusing one valid diameter assertion cannot turn that into a passed part.

Independent check criteria are explicit: resolve the stated QIF IDs; verify both directions of the characteristic/feature references; interpret the declared incoming mm conversion; reproduce the interval and numeric comparison; inspect the exact STEP records and actual imported cylindrical surface; preserve overall inspection status. The supplied ontology independently contains the corresponding QIF individuals and their encoded IDs. The pilot's checker is self-authored and mechanical; a separate reviewer has not yet adjudicated the service deliverable.

## 2. A concrete counterexample to label-only joining

After whitespace/case normalization, FAIR `Diameter 4` means nominal **10**, while incoming `DIAMETER4` means nominal **4.5**. FAIR `Diameter 5` and incoming `DIAMETER5` both have nominal **4**. Therefore, a label-join rule that tries to reconcile these definitions with a single unit scale would require both a scale of **0.45** and **1**. No single uniform unit conversion satisfies both. This is a source-grounded rejection of that joining rule; it does not identify the intended replacement mapping or prove a physical part defect.

The candidate distance comparison provides a second, expressly **constructed** counterexample. Under separately established common units and same-distance identity, FAIR item `110` permits [71.0, 71.4], whereas incoming item `169` permits [70.96, 71.36]. A value of **71.38** passes the former and fails the latter. Thus a historical PASS flag cannot be substituted merely because both descriptions appear to refer to a roughly 71.2-unit distance. This value is a falsifying example, not a measured NIST observation. The actual FAIR values for that item happen to lie in both numeric intervals; even that does not prove feature or specimen identity.

The position and perpendicularity records also carry differing literals (`NONE`/`MAXIMUM`, and +0.13/−0.13 respectively). Those differences are preserved as issues for authoritative semantic adjudication. The pilot neither infers an acceptance relation from those labels nor silently changes the sign of a tolerance.

## 3. Exact-schema unit finding: no cross-provider reuse is currently admitted

Incoming QIF explicitly declares millimeters, including an SI conversion factor of 0.001. The FAIR file contains neither `FileUnits` nor any per-value unit attribute. Inspection covered all its element and attribute names.

The standards owner's exact QIF 2.1 archive was retrieved from:

https://qifstandards.org/wp-content/uploads/2015/03/QIF-2.1.zip

The owner links it at https://qifstandards.org/qif-2-1/ . The complete archive is 106,776,144 bytes, SHA256 `d9e8b5f1333f2c8827a1c5ff7fa08dc2839be8f9d84dcc3607145dc1f816df14`. Its nested `QIF_2.1_XMLSchemaFiles.zip/QIFLibrary/Units.xsd` is 54,740 bytes, SHA256 `2d46993e49300841e66fc05c35dafbcb63ac8085e9c9c8cbc8670e97c13a5fbd`.

Both `LinearValueType` and `ActualLinearValueType` document **meters** as the fallback when no per-value unit or primary linear unit is supplied. Consequently, the candidate FAIR values 3.026–3.065 formally represent meters, or 3026–3065 mm. They cannot be interpreted as millimeters merely because that looks plausible for the part. A confirmed intended-unit correction must come from an authorized source and be retained as a new derived artifact with provenance; the original bytes remain unchanged.

This ruling strengthens the audit's concrete value: the recipient receives a precise reason why apparently matching raw numbers and PASS flags are insufficient, and an actionable request for a corrected export or signed unit declaration. It does not establish what the original exporter intended or blame the physical measurements.

## 4. A useful conditional repair route with less identity work

After a separately authorized FAIR-to-mm metadata repair, three FAIR diameter characteristics are numerical candidates for the incoming nominal-3 family: item IDs **71, 89, 92**. Their three encoded intervals are [2.75, 3.25], a subset of incoming [2.746, 3.254]. Their 60 recorded raw values range from 3.026 to 3.065 and lie in that destination interval. Actual CAD inspection finds three radius-1.5 cylindrical faces, indices 92, 93 and 95.

For the narrow question **“does every feature in this verified family satisfy this common diameter criterion?”**, the numeric conclusion is invariant under all six permutations of the three candidate characteristics. The recipient need not resolve which particular candidate maps to which particular hole to establish this family-wide statement.

This is a **conditional numerical certificate after repair**, not verified physical reuse. Its prerequisites are:

- An authorized unit correction confirming intended millimeters despite the formal meter default.
- Accepted requirement identity or explicit requalification against the receiving criterion.
- Set identity and completeness: these three source characteristics cover the intended three-feature family.
- Specimen/lot identity and coverage, since the two providers' serial conventions differ.
- Adequate measurement provenance and current permission for the intended acceptance decision.

The useful distinction is between **set identity** and a complete individual permutation. The certificate can reduce the required identity evidence for this one aggregate purpose. A request about one named hole, a positional tolerance, or a particular specimen may still require the finer mapping. The method does not inherit acceptance for those different purposes.

## 5. What the pilot did and did not demonstrate

It executed useful audit work on unchanged public engineering artifacts: real geometry import; all incoming cylindrical-feature candidates; one complete source trace; a false-label-join witness; a conditional interval counterexample; exact-version unit adjudication; and an explicitly gated family-wide reuse certificate. These are substantive objects a later reviewer can inspect and reproduce.

It did not benchmark H/U/E/E+, run a fresh recipient, obtain customers, estimate willingness to pay, or demonstrate new feasibility. The runner's approximately one-to-two-second rerun time excludes development, discovery, source access, correction, evaluator construction, and review. It is not a complete delivery cost or an advantage over the supplied methods. A fair E can use the reference ontologies, NIST/CCAM methods, CAD tools, and ordinary expert scripts.

The next study can freeze the constructed method and test a different part and receiving purpose with a separate recipient. Relevant prospective acceptance is whether the audit correctly supports reuse, requests requalification, or rejects an unjustified inference while producing an actionable, source-grounded result. All-unknown answers or a generic warning do not constitute a complete useful dossier. The current unit obstruction must remain visible rather than being patched away to manufacture a favorable transfer.

## Development record and limitations

Only Plate was developed. One direct low-level STEP reader experiment terminated with a segmentation fault while exploring entity-to-shape retrieval; this route was abandoned. The stable CadQuery import and OpenCascade surface adaptor provided actual geometry. Text indexing is used only to cite the corresponding STEP source records. One preliminary RDF inspection encountered a null attribute; it was corrected by handling non-individual XML nodes. These failures are part of development cost, not hidden successes.

The first standards download was bounded at 80 MB and was incomplete; its public HTTP range tail was subsequently retrieved, and the complete ZIP opened successfully. The complete checksum above supersedes that incomplete download. The first positive numeric certificate was already conditional on units; the parent's unit challenge triggered exact-schema verification and the stronger explicit formal-meter/no-admission ruling. No physical-reuse result was retroactively recovered.

Full QIF schema validity, the complete GD&T meaning of every characteristic, source calibration adequacy, CAD revision equivalence, and customer authority remain outside this pilot. AI assistance performed research, code construction, and inspection; all example selection was development, not autonomous discovery from an unseen commercial request.
