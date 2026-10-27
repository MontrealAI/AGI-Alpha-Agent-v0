# Round 2 opportunity dossier — manufacturing evidence that survives a change of purpose

**Status: pre-selection research; no flagship implementation or performance experiment has been run.**

**Recommendation:** this is a credible candidate for a bounded construction experiment, with actual public industrial artifacts and two useful service missions. It is **not** evidence that digital-thread integration is a new invention, that current engineering tools cannot perform it, or that an enterprise already has paying customers. Select it only with the existing reference graphs, integration research, and expert engineering workflows included in the baseline. If those resources already answer the fresh missions cheaply, the correct result is parity or no additional retained Alpha.

The proposed offering is a **manufacturing evidence-sufficiency and reconciliation service**: determine which design, inspection, and process statements a technical data package actually supports; reconstruct justified links; return inspectable witnesses and unresolved alternatives; and specify the smallest additional evidence needed for a particular customer's decision. This is a digital engineering deliverable. It does not itself authorize machining, release a physical part, or certify measurement accuracy.

## 1. What the bounded search established

Five focused search queries were used: NIST semantic-PMI datasets; STEP File Analyzer capabilities; NIST design/manufacture/inspection integration evidence; CADIQ; and commercial PMI-driven inspection planning. The original three deep-source packages were the NIST artifact collection, the Hedberg et al. integration experiment, and NIST STEP File Analyzer documentation. The parent subsequently supplied two decisive prior-art challenges: the STEP/QIF integrated reference graphs and NIST GCR 24-050. They were examined as an explicit, justified extension of the original source budget; no additional search queries were used. This is a targeted opportunity screen, not a systematic claim that no competing product exists.

The 2021/2022 NIST–MTC study used a real box assembly, CAD, NC programs, machine records, and inspections from different organizations. It reported difficulty aligning feature and characteristic information, despite existing model-based planning tools. Some machine positions were simulated rather than measured. Its published results are historical and already public; reproducing them is not discovery. Its paper also reports that automatic first-article inspection programming took less than ten minutes per part in its chosen system. Therefore, an offer premised on inventing ordinary automated inspection planning would be poorly motivated. [S2]

The 2024 CCAM/NIST report substantially advances beyond that earlier obstruction: it demonstrates standards-based spatial and temporal alignment across STEP, NC, MTConnect, and QIF, including geometry association, simulated NC-to-feature linkage, and execution-time intervals. It also describes a commercial geometry-based alternative. Its findings retain practical limits concerning customization cost, incompatible infrastructure, and sensor synchronization. This establishes strong methods to reuse and challenge; it does not support calling feature association, persistent identifiers, or a digital thread our new algorithm. [S5]

The opportunity is consequently **deployment economics and trustworthy mission-specific evidence**, not the historical absence of an integration method. Whether a retained instrument reduces those costs on unfamiliar missions is an empirical question.

## 2. Actual artifacts now available

Two official ZIP files have been downloaded and inspected. They are real source artifacts, not researcher-generated examples. All paths below are relative to `research_sources/opportunity_dossier/round2_industry_sources/`.

| Artifact | Public source and identity | Local frozen bytes |
|---|---|---|
| NIST–MTC design/manufacture/inspection package | DOI `10.18434/T4/1503154`; dataset identifier `73AE20D288CF02F1E05324570681502B1955`; catalog modified 2018-08-17 | `nist_box_mtc.zip`, 248,727,407 bytes; SHA256 `6bc4693f4b072116329decb0d07ac126eaaac86aa7c09e1276942279fbdb567c` |
| STEP/QIF instance data and reference ontologies, V2 filename | DOI `10.18434/M32146`; `ark:/88434/mds2-2146`; catalog has issued 2021-07-09 and modified 2019-10-21, so these fields should not be simplified into a single release date | `qif-ontology-dataset-V2.zip`, 10,680,120 bytes; SHA256 `9ae303335274645f14d8ceacf56f8defd174271fd645308905f0395d82ef1085` |

Exact downloads:

- https://data.nist.gov/od/ds/73AE20D288CF02F1E05324570681502B1955/mtc.zip
- https://data.nist.gov/od/ds/mds2-2146/qif-ontology-dataset-V2.zip

The original archive contains 443 entries: native SolidWorks models across revisions A–D; six QIF files from two inspection pipelines; 26 NC files; 61 XML files; machine-data transformations and raw/processed records; and a plate setup/tooling workbook. These are inventory observations, not evidence that every file is usable or every revision equivalent. The root confirmed an execution environment with OpenCascade/CadQuery, lxml, and scipy. No CAD importer or flagship algorithm was executed in this screen.

**A consequential correction from inspecting the bytes:** the original archive's only `.STEP` file is **AP203 geometry**, with a SolidWorks 2016 header dated 2017-02-07. It is not a semantic-PMI AP242 file. The separate reference-ontology package contains three AP242 files exported with SolidWorks MBD/HOOPS in 2019, the three incoming-inspection QIF files, and STEP, QIF, and integrated RDF/XML ontologies. The plate QIF in that package is byte-identical to the original incoming-inspection plate QIF. Thus the reference package is a strong supplied answer resource, not a fresh discovery corpus. Never silently treat its 2019 CAD export as the same complete identity as every 2017 manufacturing revision.

The retained inspection record `artifact_inspection.json` contains hashes and limited structural observations for 14 STEP/QIF/tooling files. In particular:

| Part | FAIR characteristic items / actual sets | Incoming characteristic items / feature items / actual sets |
|---|---:|---:|
| Plate | 38 / 20 | 17 / 22 / 20 |
| Cover | 28 / 20 | 12 / 21 / 20 |
| Box | 45 / 19 | 15 / 28 / 19 |

These are counts of XML schema objects, **not** equivalent test counts, independent statistical samples, or numbers of failures. The FAIR files do not contain a top-level `Features` section; the incoming files do. Different aggregation and characteristic semantics can explain different counts. That real asymmetry is relevant to a comparability audit and prevents assuming all measurements can be paired from names or row order.

### Rights and reproducibility

Both official catalog records point to NIST's licensing statement. The ZIP READMEs preserve attribution, modification-notice, warranty, and nonendorsement provisions. NIST's current policy distinguishes employee-created non-SRD works, software, and extramural material; do not collapse all NIST content into an unconditional worldwide public-domain claim. Retain the full notices when redistributing relevant material, identify derived/modified outputs, cite NIST, and do not use its logo or imply endorsement. The CAD/STEP test-collection page separately permits unrestricted use of its test cases. [S1, S4, S6]

Source READMEs and `manifest.json` are retained. Some `www.nist.gov/document` downloads and the local PDF download returned HTTP 403, although the web reader exposed the paper. The public `data.nist.gov` artifact downloads succeeded. The knowledge-graph paper's PMC page showed a browser challenge and an Europe PMC XML mirror returned HTTP 500; its full text was not recovered by this agent. Its actual reference data was recovered and is sufficient to establish that the integrated mappings already exist. No availability limitation is presented as an absence of prior art.

## 3. Two independently useful mission briefs

These are **researcher-authored prospective service requests grounded in different real workflow responsibilities**. They are not observed customer orders, willingness-to-pay data, or two independently sampled industries. The artifacts arose from one assembly experiment. Their useful purposes are independent of our proposed solution.

### Mission A — can a buyer rely on the supplier's inspection evidence?

**Recipient and decision.** A receiving-quality engineer wants to know which incoming-inspection obligations are already supported by a supplier's first-article results, which are not demonstrably comparable, and which discrepancies merit remeasurement. The useful outcome is an auditable evidence-comparability dossier that prevents both redundant work and unjustified acceptance.

**Concrete inputs.** Begin development with:

- Original archive `FAIR/7_11_2017 9_16_18 AM Plate_Results.qif`.
- Original archive `QIF-IncomingInspection/PlateResults_20_samples.QIF`.
- Reference package `1_DesignData/Plate.STP`, `2_InspectionData/Plate.QIF`, and the supplied `5_IntegratedOntology/Plate_integrated.owl`.

The original plate STEP and relevant native revision metadata are provenance checks, not substitute semantic definitions. Use the cover or box files for a later frozen transfer request; their names identify source files, not correct cross-file feature matches.

**Required output.** For each requested obligation, return: the design or inspection source; characteristic type; nominal and tolerance semantics; units; referenced feature geometry and datum frame when available; specimen/part identity support; justified correspondence or competing candidates; and a machine-checkable trail to the exact source objects. Distinguish requirement equivalence from identical measured values. A result in one provider's file does not satisfy another provider's requirement merely because its label or numeric nominal resembles it.

**Acceptance.** Every asserted equivalence must survive an independent semantic and geometric check. Every asserted incomparability must identify the missing or contradictory evidence. Do not force a match where geometry, datum semantics, or specimen identity are absent. Useful partial results are allowed, but a requested complete substitution decision cannot pass through a generic abstention. If essential evidence is genuinely missing, the accepted deliverable is a specifically scoped insufficiency finding and acquisition request, not a claim that inspection work has been eliminated.

**Conventional route.** A quality engineer compares CMM reports, CAD/PMI, datum definitions, and inspection programs using existing metrology software and data tools; the provided reference graphs can answer covered design-to-incoming questions. Existing commercial PMI import and program generation are baseline capabilities. The proposed instrument's possible value is packaging this specific reconciliation reliably with less repeated work, measured against that route.

**Decisive falsifier.** If the retained workflow asserts even one materially wrong substitution, or achieves no useful reduction in complete accepted-work cost relative to the strong expert baseline, its proposed advantage fails. If the actual inputs lack enough identity information for useful reconciliation, do not supply invented labels to make the experiment pass. Stop or sell only the narrower insufficiency audit at an honestly tested price.

### Mission B — what does the process evidence justify investigating?

**Fresh recipient and decision.** A manufacturing/process engineer receiving a quality discrepancy needs a reproducible evidence package: which design feature and requirement are involved, which planned operations could have acted on it, what execution evidence is actually available, and which additional records would distinguish competing explanations. This supports the next investigation or evidence purchase. It does not declare a machining cause from correlation.

**Concrete inputs.** The second mission uses a held-out part/operation or predefined query drawn from the original archive's `NC Code/`, `MTConnect/`, QIF files, and `Plate-Setup-and-Tooling.xlsx`, together with the appropriate design artifact and existing reference mappings. Before execution, establish that a compatible CAD revision is available. The tool/setup workbook is supplied source evidence, not an instrument discovered by the agent. Use the published NC/MTConnect alignment method, and the 2024 feature-association method when their prerequisites hold.

**Required output.** An operation/feature evidence map with source hashes, coordinate and unit assumptions, candidate machining intervals, planned versus observed settings, external tool data, missing channels, and contradictory evidence. The report must distinguish geometric intersection, planned tool motion, sampled execution, inspected result, and causal explanation. It should include an executable reproduction of every derived claim and an evidence request tied to the remaining decision uncertainty.

**Acceptance.** A separate checker reproduces geometry associations and source references; a process reviewer can recover every cited program block, recorded setting, and time interval. If actual tool-path position is absent, a simulated path remains labeled simulated. If tool length or setup differs outside NC, do not infer it from otherwise identical programs. Requirements concerning revision, identity, and causality remain in force.

**Conventional route.** Established CAD/CAM inspection workflows, published STEP/QIF integration, NC interpretation, dynamic time warping, and the 2024 spatiotemporal-feature method. These are allowed building blocks for all expert configurations. A commercial geometry integration service is also a relevant outside option; this screen has not priced or benchmarked it.

**Decisive falsifier.** A package that supplies already published conclusions, invents an unmeasured channel, or conflates a planned interval with actual contact fails. If the existing method plus ordinary engineering scripts produces the complete accepted package within the same resource limit, there is no demonstrated E+ advantage. Both configurations may still deliver a commercially useful service.

## 4. Strong-incumbent challenge

| Available method | What must be conceded | What could still be tested |
|---|---|---|
| NIST STEP File Analyzer / Viewer | Geometry, entity/attribute inspection, semantic-PMI analysis, validation properties, and conformance checks already exist. Its site redirects new releases to GitHub from January 2026; the old page's 5.41 label is not a verified latest version. | Whether a mission-specific cross-provider dossier needs substantial additional integration and review. Do not score syntax checks or PMI extraction as a discovery. |
| Supplied STEP/QIF integrated ontologies | Integrated design-to-incoming graphs are supplied for all three assembly parts; their complete coverage and correctness were not independently verified in this screen. A graph representation and their existing links are not our inventions. | Independent validation, coverage limits, new inspection-provider reconciliation, and changed mission semantics. All arms receive the same public reference material. |
| NIST GCR 24-050 and cited commercial geometry method | Geometry association, NC-to-feature linkage, execution timing, and QIF linkage have been demonstrated. | Whether adapting these methods to the actual older packet and a new purpose is useful and economical; whether the retained adapter reduces later construction costs. |
| Commercial CAD validation and PMI-driven metrology tools | CADIQ-style geometry/PMI comparison and commercial inspection planning are real alternatives. This screen did not establish their current complete feature coverage or prices. | A prospective deployment benchmark or human-service quote, including licenses and setup actually required by the recipient. |
| Manual expert service | A skilled engineer can often reconcile evidence with CAD viewers, spreadsheets, scripts, and experience. | Accepted quality, complete labor/resource cost, turnaround, and customer effort. Manual competence is not set to zero or hidden inside a free baseline. |

The technical gap is therefore a **hypothesis of expensive, repeated adaptation and insufficiently explicit evidence boundaries**, not a proven missing universal capability. The latest source examined actually supports this narrower economic interpretation. General novelty is unnecessary for legitimate Operational Alpha, but the experiment must measure added value rather than merely rename established methods.

## 5. The construction that would deserve retention

The retained object should be a substantive executable workflow: schema-aware readers; geometry and coordinate-frame adapters; typed characteristic equivalence checks; provenance-preserving evidence links; independently reproducible checks; and a mission-specific query/report layer. A table of hand-entered correct feature pairs would not qualify. Neither would a prose summary of the papers.

Its proposed transformation witness is:

1. **Original useful purpose:** make a justified receiving or investigation decision from the available design, quality, and process evidence.
2. **Binding restriction:** repeated manual reconciliation, incompatible identity conventions, and incomplete source semantics prevent economical reuse of an otherwise useful technical data package.
3. **Removable portion:** some identity can be established by existing geometry/semantic methods and explicit evidence constraints; some missing information is irreducible and must remain unresolved.
4. **Replacement:** a reusable, checked evidence-construction workflow with explicit alternatives and mission-specific acceptance, assembled from strong established components.
5. **Realization:** accepted source-grounded dossiers on the frozen public packet, followed by a fresh recipient performing a different mission with the retained workflow.
6. **Falsifier:** no useful accepted output, incorrect equivalence, unrecognized revision/authority mismatch, equal or worse complete cost than E, or no independently demonstrated transfer.

This is not a claim of inventing geometry registration, QIF, graph integration, or digital-thread standards. It is a proposed **enterprise capability construction**. Whether it is sufficiently consequential to be the edition's flagship depends on the actual breadth and usefulness of the constructed outputs. A tiny parser extracting a known failure count would be a no-go result.

## 6. Minimal decisive experiment before an ambitious campaign

**Stage 0: evidence viability, one bounded engineering session.** Import one actual AP242 model; inspect the supplied integrated ontology; trace at least one complete requirement-to-geometry-to-result path; and identify whether any nontrivial receiving-comparability or process question remains outside the supplied answers. Preserve negative findings. If all proposed tasks are already directly answered, or the missing inputs make every useful task indeterminate, stop this candidate. Do not manufacture missing mappings.

**Stage 1: freeze development and confirmation purposes.** Use one part/mission for development. Before confirmation, freeze the different-purpose request, allowed files and tools, acceptance rubric, resource budget, and reference baseline. Independent adjudication must establish which assertions are checkable, which are legitimately ambiguous, and which require source evidence absent from the packet. That is evaluator work and has a recorded cost. It is not an excuse to weaken the original useful purpose.

**Stage 2: fair configurations.** H is an equivalent quality/process engineering service, priced by a scoped quote or disclosed hours/rates. U is competent ordinary use of the same frontier model and available files. E includes the published methods, supplied integrated ontologies, expert scripting/CAD tools, and normal verification. E+ adds only the newly retained construction. Give all configurations the same underlying evidence and permission to propose alternatives. If commercial software is unavailable to an executed arm, disclose the limitation and avoid claiming superiority over it.

**Stage 3: fresh recipient and changed purpose.** Transfer the executable instrument to a separate operator for Mission B, or reverse the lineage if the evidence viability test favors process work first. Recheck data meaning, revision, geometry, units, feature and characteristic scope, acceptance, and access authority. A cached link to a past source object grants no acceptance of a new purpose. Separate the benefit of a stronger inherited artifact from any improvement in discovering instruments.

**Primary measurements.** Accepted useful obligations and dossiers; unsupported-equivalence errors; justified ambiguity coverage; complete cost and retries at matched accepted quality; turnaround; customer clarification effort; and recipient adaptation cost. If exact billed tokens or equivalent human timing are unavailable, report observed quantities and estimates separately. Do not turn a public benchmark into a field reliability estimate.

The 20 manufactured instances are clustered observations from a shared design and process study. They are not 20 independent task families. The public papers and reference graphs create contamination risk; all agents may already know them. Freshness can attach to frozen request construction and operator transfer, not to a claim that this public corpus is protected from model training.

**Feasibility crossing.** Define a complete dossier, budget ceiling, deadline, and permissible residual customer effort before the confirmation jobs. A new feasible service is demonstrated only if E fails that original threshold and E+ satisfies it. If both qualify, report improved economics or reliability. If neither does, report the obstruction and stop. No numerical threshold or positive crossing is asserted in this dossier.

## 7. Offering and coordination hypothesis

The two prospective buyers have different benefits: a receiving team values justified use or rejection of supplier evidence; a process team values a focused, reproducible investigation package. They may share a fixed-cost schema/geometry/verification core, while their part data, acceptance obligations, and operational authorities remain separate.

A testable arrangement is a conditional development pool for that common core plus separately accepted customer dossiers. A buyer can decline, use its existing metrology/digital-thread provider, perform the task internally, or purchase missing evidence. Participation must be attractive against that buyer's actual outside option. A common-development contribution is refundable or convertible according to explicit milestones; no deposit is counted as earned service revenue before its contractual earning condition. There is no assumption that two buyers automatically appear or that their requests are technically compatible.

Test the instrument alone, coordination alone using existing tools, and their combination. Include withdrawals, scope disagreement, incompatible data rights, common technical failure, adaptation cost, refund obligations, payment delay, serving capacity, and upkeep. Compute cash required before deliveries separately from expected contribution. A useful instrument may be uneconomic to build for one buyer; a pool may still fail if data or acceptance cannot share meaningful work. All numbers would initially be assumptions or measured research costs, not observed demand or profit.

Retain only rights-cleared generic code, schemas, verifiers, and operating knowledge. Customer parts, proprietary programs, and protected adjudication material do not enter the shared network. Integrate any admitted capability into the existing enterprise interfaces and authorization system rather than creating a new registry. A successor gets eligible access to the versioned artifact; execution permission and mission acceptance remain separate.

## 8. Ranked decision

1. **Best next bounded test: cross-provider and cross-purpose evidence service using actual NIST artifacts.** Conditional go for Stage 0 and, if it passes, construction. This is consequential engineering work with real geometry, semantics, revisions, and source limitations. Its advantage must be discovered in execution and costed against strong E. No field demand, new algorithm, or compounding gain has been established.
2. **Fallback: productized expert deployment of the existing integration methods.** Legitimate service and Operational Alpha experiment if useful customers can be served better, but a weaker flagship for transformational construction. A profitable result here should remain visible even if optional learning or sharing is rejected.
3. **No-go: reimplement the supplied three-part knowledge graph or reproduce published quality findings and call it autonomous invention.** Also no-go for relabeling old CAD/PMI export defects as current vendor deficiencies, or manufacturing a complete correspondence where the original evidence is missing.

This candidate is stronger than the thermal proposal on immediate executable evidence availability. It is still conditional on proving a useful fresh mission beyond supplied answers. The honest next question is not whether digital threads can exist; they do. It is whether expertly constructing and retaining a bounded, evidence-preserving service makes the next useful engineering job less costly or newly feasible for the recipient.

## Sources and exact provenance

**S1. NIST test artifact collection and official alternate index.**

- https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0
- https://www.mbx-if.org/home/cax/resources/
- Original MTC metadata: https://catalog.data.gov/dataset/design-manufacturing-and-inspection-data-for-a-box-assembly-d0c80

The original FTC/CTC tests concluded in 2015; simplified cases were added in 2023 and a hole test case in 2024. Their historical validation failures must not be attributed automatically to current products. This dossier uses the downloaded MTC bytes rather than claiming that every broader catalog artifact was accessed.

**S2. Hedberg et al., _Defining requirements for integrating information between design, manufacturing, and inspection_.** DOI https://doi.org/10.1080/00207543.2021.1920057 . NIST publication page dated May 11, 2021; retrieved PDF draft header September 22, 2021; final journal volume 60(11), 2022. Thirty-page PDF read through the web tool, including methods and results; local PDF download failed.

- https://www.nist.gov/publications/defining-requirements-integrating-information-between-design-manufacturing-and
- https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=928791

**S3. NIST STEP File Analyzer and Viewer.** Official documentation and current release routing; software not installed or benchmarked in this screen.

- https://www.nist.gov/services-resources/software/step-file-analyzer-and-viewer
- https://github.com/usnistgov/SFA

**S4. Reference Knowledge Graphs of STEP and QIF Data for a Three-Part Box Assembly.** DOI https://doi.org/10.18434/M32146 . Complete ZIP and README inspected; exact hashes above.

- https://catalog.data.gov/dataset/reference-knowledge-graphs-of-step-and-qif-data-for-a-three-part-box-assembly-071c8
- Related paper supplied by parent: https://pmc.ncbi.nlm.nih.gov/articles/PMC13189002/ ; full text unavailable to this agent, so no unverified method details are attributed to it.

**S5. Standfield, Holterman, Waddell (2024), _Spatial and Temporal Data Alignment from Disparate Sources for Feature Association_, NIST GCR 24-050.** DOI https://doi.org/10.6028/NIST.GCR.24-050 . Twenty-nine-page report, substantive methodology, findings, and conclusions examined via web tool; no runtime replication.

- https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957946

**S6. Current NIST licensing statement.**

- https://www.nist.gov/open/license

Commercial-tool search results were used to challenge the opportunity rather than establish absence: CADIQ validation, ZEISS CAD/PMI inspection planning, and Hexagon PC-DMIS automation. Their latest configurations, license terms, and complete task performance remain to be verified before a commercial superiority claim.

**Investigation date:** 2026-10-27. Research notes prepared with AI assistance. Source files, artifact inventories, and proposed mission briefs are explicitly separated from executed capability construction and experimental results.
