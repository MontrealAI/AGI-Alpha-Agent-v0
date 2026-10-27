# Manufacturing evidence instrument — independent evaluation design

**Status:** pre-selection design, 2026-10-27. No new manufacturing instrument or confirmation experiment implemented. The reviewer inspected only Plate development inputs and inventories; Box/Cover contents remain unopened by this reviewer. This note extends `round2_industry.md` and preserves the stopped runtime pilot and thermal no-go.

## 1. The useful deliverable and the restriction

An engineering customer needs an auditable answer to a bounded question: which statements in an inspection packet support the customer's current obligation, which contradict a proposed substitution, and exactly what additional evidence is required? The deliverable is an **evidence qualification**, not certification of a physical part, CMM accuracy, manufacturing causality, or permission to release a part.

The difficult restriction is not an absence of graph technology. NIST supplies STEP/QIF integrated graphs, and the 2024 feature-association method is available. It is the cost and fallibility of reconstructing *mission-specific* relationships when providers use different schemas, identities, semantics, coordinate frames, standards, and revisions. A retained executable instrument could reduce repeated reconstruction while exposing irreducible uncertainty. That advantage remains to be tested against an expert who has all those methods and files.

The proposed instrument must therefore produce a **typed, replayable chain of claims**, not a table of apparently matching labels. Its transformation witness is the replacement of unexamined report substitution by executable evidence qualification while preserving the original engineering decision and its requirements.

## 2. What the actual development bytes establish

The Plate AP242 geometry receipt reports one valid solid, 261 faces, 722 edges and 34 cylindrical faces. These are actual importer observations, not a complete proof that PMI, geometry and inspected specimens correspond. Inputs are pinned in `cad_evidence_pilot/input_manifest.json`.

Plate-only XML inspection finds these consequential hazards:

- FAIR declares `FormalStandardEnum=COMPANY`; incoming declares `ASME-Y14.5-2009`. A standard declaration difference is a semantic prerequisite to resolve, not proof that every requirement differs.
- FAIR has no top-level `FileUnits`; incoming has one. Defaults require an applicable pinned schema/standard rule. Do not silently assume units or treat missing as dimensionless.
- Incoming perpendicularity definition `id=25` contains `ToleranceValue=-0.13`; FAIR's corresponding-looking class contains positive `0.13`. Preserve the literal value and investigate its meaning; applying `abs()` would erase source evidence.
- FAIR specimen serials are integers; incoming serials are strings such as `PLATE_RESULTS_A01_NIST_MTC_CRADA_PLATE_ORIGIN_NIKON_SCAN`. A numerical suffix is not a verified cross-provider specimen map.
- FAIR has no top-level feature geometry. Incoming does. Numeric nominal, name and row order alone cannot establish the absent geometry relationship.

These observations motivate checks; they are not a set of supplied correct answers for a confirmation task. The independent reference graph covers design-to-incoming relationships and must be available to E. Its 5,991,185 bytes exceed the inherited bridge's two-million-byte artifact bound: transfer code and a manifest, while mounting separately authorized source data, rather than silently dropping the bound.

Inventory-only caution: original Cover incoming QIF SHA256 is `de1bd5f538fecc5c7fed0884da2a89f548b0efeb56ba9c0581bb8160a926da24`; reference-package Cover QIF SHA256 is `a513cf188d40ed83332fb47f8fcfbfe40cf2c342cbd28149256146836ac07ffa`. Reuse must not infer complete identity from the shared part name or counts. This reviewer has not opened either Cover file.

## 3. Core architecture and admissible claims

Use six small modules with an explicit contract; this is a design, not permission to implement before selection.

1. **Source envelope.** Archive/member and byte hash; schema version; source namespace and object locator; supplied identity/revision; license/provenance. Source and provider identifiers remain separate. Prevent external-entity/network resolution during XML ingestion.
2. **Typed extraction.** Preserve literal fields beside normalized forms, with each conversion's rule and unit source. Distinguish absent, explicit `NONE`, unsupported, contradictory, and resolved. Parse characteristic definition, nominal, item, actual, feature, datum and specimen relationships separately.
3. **Candidate construction.** Use existing graph links and geometry/semantic constraints to enumerate candidates. Graph links are supplied assertions to validate, not fresh discoveries. Geometric equality needs a justified transform, units, identity and tolerance; circular cylinders can occupy multiple faces of one bore. Do not equate face count with feature count.
4. **Claim evaluator.** Separate design-feature correspondence, requirement equivalence, measurement comparability, specimen identity and permission. An unknown prerequisite blocks that stronger claim without erasing independently supported weaker claims. A source's own PASS/status is observed data, not our independent engineering acceptance.
5. **Mission compiler.** Translate an explicit customer decision into obligations and evidence prerequisites; return per-obligation dispositions, exact witnesses, unresolved alternatives and acquisition requests. Do not change the scope to improve the score.
6. **Independent receipt checker.** Reopen pinned sources and reproduce references, literals, numerical conversions and admissible inferences; check that every output is tied to the actual mission. Keep the checker out of the candidate update loop after freeze.

No new capability registry is needed. A local claim DAG is a derived artifact. An ordinary library/index with identical documents, links and permissions is the graph-control arm.

## 4. Acceptance and counterexamples

Each scoped obligation must receive one of three substantive dispositions:

| Disposition | Required evidence | What it does not establish |
|---|---|---|
| Supported | All required prerequisites, exact-source path, reproducible checks and declared inference scope | General validity on other revisions, specimens or missions |
| Contradicted | A specific proposed claim and a reproducible incompatible field/constraint | The true alternative mapping when it is unknown |
| Indeterminate | Missing prerequisite or explicit surviving alternatives, plus a precise acquisition request | Physical failure or an automatic waiver of the customer's requirement |

A **contradiction witness** can invalidate proposed requirement equality without asserting the true feature match. A **bounded ambiguity witness** may show that two assignments among actual source candidates both satisfy the available checks but imply different conclusions. It must identify the bounded candidate universe; sampling a few candidates does not prove exhaustive ambiguity or a global countermodel. Missing geometry is often an insufficiency witness, not a manufactured alternative geometry.

A useful audit passes only if it covers every declared obligation, contains no materially unsupported equivalence, correctly reproduces cited evidence, and supplies actionable resolution for unresolved obligations. Blanket abstention fails. A full-substitution mission additionally requires every substitution prerequisite; a correct insufficiency audit cannot be relabeled as successful substitution. Thresholds and any maximum acceptable customer clarification must be frozen before confirmation.

The independent checker should use different parsing/control logic from the builder. Reusing OpenCascade in both arms is acceptable engineering, but cannot be reported as independent geometric ground truth. Cross-check kernel outputs against exact STEP/QIF relations, supplied reference links and explicit invariants where possible. An unresolved standards interpretation requires a flagged review condition; an AI checker alone does not become a licensed metrology authority.

## 5. Fair experiment and protected transfer

**Stage 0 gate:** demonstrate one complete Plate requirement-to-geometry-to-result trace using source evidence, and one valuable mission obligation beyond simply querying supplied links. If all useful work is already answered cheaply by E, report parity. If every substantive obligation lacks essential source evidence, stop the broader service and evaluate only the narrower, explicitly priced insufficiency audit.

**Freeze:** source closure, supported semantic classes, instruments, rule provenance, mission rubric, budgets, verifier and stopping rule. Preserve all failed candidates. Develop on Plate. An independent curator may inspect Box/Cover only after the split is assigned and must freeze missions and answer evidence before candidate execution; disclose public-source familiarity and historical reuse. This reviewer has so far preserved that separation.

**Configurations:** H is equivalent quality-engineering service (actual quote or disclosed hours/rate estimate). U gets competent same-model use and the same files/tools. E gets the complete reference graphs, 2024 method, established geometry/QIF tooling and expert scripting. E+ gets that plus the retained instrument. If live frontier operation or human timing is not executed, do not call deterministic scripts measured U/E or inferred labor measured savings. Measure actual executable outcomes and model any unobserved service economics separately.

**Fresh recipient:** use a new operator/process and untouched part source set. Merely changing Plate to Cover tests instance transfer, not necessarily a new purpose. A stronger changed-purpose mission asks for the evidence and acquisition plan needed to combine provider results for a specified process-investigation decision, rather than substituting a report for receiving inspection. Pooling requires specimen/measurement comparability and additional statistical assumptions; do not claim process capability from a small correlated historical batch. If NC/MTConnect investigation is chosen instead, compatible revision and observed-versus-simulated motion must pass its own Stage 0 before promising that scope.

Transfer actual executable modules, rule/schema files and manifest, then re-run the new mission checks. A summary or cache of known correspondences is not transfer of the instrument. Protected evaluation answers stay outside the bundle. A receiving environment with identical already installed dependencies should be described accurately; no claim that the dependency intelligence was transferred.

**Measurements:** accepted dossiers and obligations; dangerous false substitutions; specific unresolved conditions; complete resource/correction/customer effort; elapsed time and resource peaks; recipient adaptation; source coverage. Report both correctness and decision usefulness. Aggregate by part/provider/mission family; 20 specimens sharing a design are not 20 independent invention trials. A fixed-budget feasibility crossing requires E to miss a predeclared useful quality/budget/deadline constraint and E+ to satisfy it. If both satisfy, report better economics.

**Controls:** rename/reorder IDs without changing meaning; duplicate labels on distinct features; remove required unit/identity evidence; change revision/nominal/material condition; stale or mismatched graph; source-sign corruption; fresh mission purpose; revoked/expired authority; same-content ordinary library. Synthetic perturbations test robustness and must be labeled as such, not independent demand or historical incidents. A benchmark that consists mostly of these perturbations cannot establish a broad commercial service.

## 6. Existing integration reuse without scope expansion

The immutable parent `studies/agi-alpha-capability-opportunity-v1/integration/bridge.py` offers:

- `verify_sources()`: pinned closure validation before importing native/research interfaces.
- `run_lifecycle(...)`: actual artifact bytes through the existing protected, fixture-only lifecycle, with a two-million-byte bound. Keep retrieval and execution separate; no live ENS claim.
- `replay_native(...)`: actual native signed journal, trust-role and CostLedger conformance. Native currency is USD; any CAD projection needs an explicitly assumed conversion and authoritative separate CAD timing ledger.

The parked study's `QualificationCache` and `LocalMissionAuthority` can test exact generic qualification reuse, fresh mission hashing, expiry, nonce reuse, rights and revocation. Complete generic identity includes code, artifact, schema, dependencies, evaluator, supported scope, reuse policy and test bank. Reusing a generic receipt never validates the new mission. The old microgrid bundle's fixed five-file closure cannot package this new instrument unchanged; use a new research manifest and safe extraction contract while preserving the parent bridge.

Native production capsule scope remains the literal `bounded-public-source-selection/v1`. Manufacturing evidence is **not** thereby admitted. Demonstrate rejection, not relabeling. Artifact access, local simulated execution authority, research qualification, scientific acceptance and production admission remain distinct outputs.

No publication mutation, live customer transaction, external message or production permission is proposed by this design.

### Evidence pointers

Local evidence: `round2_industry.md`; `round2_industry_sources/{manifest.json,artifact_inspection.json,qif_ontology_README.md,nist_mtc_README.md}`; `cad_evidence_pilot/{input_manifest.json,geometry_import_receipt.json,inputs/Plate_FAIR.qif,inputs/Plate_incoming.qif,inputs/Plate_AP242.STP,inputs/Plate_integrated.owl}`. Primary public packages: DOI [10.18434/T4/1503154](https://doi.org/10.18434/T4/1503154) and [10.18434/M32146](https://doi.org/10.18434/M32146). Established alignment method: [NIST GCR 24-050](https://doi.org/10.6028/NIST.GCR.24-050). Preserve the source license notices and modification attribution. Prepared with AI assistance; design recommendations are reasoned proposals, not executed results.
