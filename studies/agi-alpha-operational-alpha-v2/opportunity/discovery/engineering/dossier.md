# Engineering opportunity discovery dossier

**Prepared:** 27 October 2026. **Status:** exploratory selection evidence, not a completed experiment or validated business. **Owner:** engineering exploration agent, independent candidate generation within the research team. No external customer or independent professional has validated this dossier.

## Research budget and selection discipline

The declared ceiling was 12 targeted search queries and 16 primary-source retrieval attempts, with two serious candidates and no implementation before comparison with the other tracks. Actual use: 12 queries and 16 open/click retrieval attempts; four attempts failed. Search-result evidence is distinguished from full retrieved sources in `sources.json`. No model-call cost telemetry was available. These are research-resource counts, not financial costs.

The candidates were selected for different binding dependencies: geospatial decisions depend on the meaning and uncertainty of heterogeneous measurements; industrial-control qualification depends on executable semantics of protected, time-dependent components. Neither opportunity is presented as a new scientific field. Existing solutions materially narrow the proposed contributions.

| Candidate | Consequence and evidence | Remaining hypothesis | Recommendation |
|---|---|---|---|
| ENG-1: Geospatial transition and decision qualification | Public agencies explicitly require choices among resurvey, readjustment and transformation; public tools and historical data already exist. | A reusable evidence instrument can reduce the cost of deciding which legacy datasets are fit for a particular new use, beyond competent GIS practice. | Conditional shortlist. Conduct a bounded real-data inventory and strong-tool comparison before building a large system. |
| ENG-2: Qualification of protected PLC components for migration | A real CERN–GSI study demonstrates service delivery, reusable component models and remaining manual work. | Authorized active experiments and reusable semantic models can make another component family economical to qualify. | Defer as flagship unless the team obtains an authorized executable vendor oracle and substantially different public tasks. A home-written substitute would not test the claimed opportunity. |

## ENG-1 — A decision-qualification instrument for mixed elevation evidence

### Beneficiary, useful purpose and observed need

The intended beneficiary is an infrastructure owner or engineering consultancy deciding whether existing elevation records are adequate for a defined planning decision, need reprocessing, or require new survey work. The deliverable is a reproducible evidence package for that decision: dataset identity, coordinates and units, horizontal and vertical reference, epoch where relevant, source observations, valid transformation, known uncertainty, unresolved contradictions and the action justified by the requested tolerance.

NGS describes three legitimate transition routes: resurvey, readjust and transform. Its guidance makes accuracy requirements, retained observations and metadata part of that choice [G1]. Thus the useful task is not merely converting a number. A current transition creates a time-specific reason to examine archives: NGS's beta progress page describes expanded NCAT functionality, remaining service gaps and a planned 2027 official transition [G2]. The date is a current plan, not a guaranteed event.

NOAA also publishes limitations directly relevant to acceptance. Its VDatum page flags location-specific uncertainty problems [G3]; the uncertainty documentation distinguishes transformation and source errors, warns about systematic effects, and says regional standard deviations are not maximum error bounds [G4]. A successful API response therefore does not establish that a customer's decision tolerance is met.

### What existing methods already accomplish

Free NOAA NCAT and VDatum already perform major transformations. PROJ already supports area restrictions, requested accuracy, rejection of ballpark operations and failure when the best operation lacks a required grid [G5]. GIS professionals already inspect metadata and commission surveys. Those are competent outside options and must be made available to U and E. Building a wrapper around `only_best` is not a new discovery.

A final adversarial prior-art search further weakened the broad opportunity claim: Safe Software's own FME documentation describes early CRS/metadata validation, explicit vertical transformation, automated attribute/geometry checks and batch workflows [G7]. Esri's Data Reviewer documentation likewise describes automated quality-control workflows and stored review results [G8]. Generic metadata validation and a shared exception ledger are therefore also existing building blocks. The new instrument must demonstrate a useful cross-document, mission-semantic contribution beyond these products, or the opportunity should be rejected.

The proposed gap is narrower: a reproducible, portfolio-level connection between heterogeneous documentary evidence, the available transformation and a mission-specific acceptance requirement. Whether this is underserved or expensive enough to pay for has **not** been established. The possibility is motivated by official preparation requirements, not by measured customer pain or a claim of market absence.

### What frontier intelligence could contribute

Expert operation might read long survey reports and metadata, identify conflicting datum or unit statements, propose an executable evidence schema, prepare appropriate tool calls, and localize the missing information that blocks a decision. The transformation engine remains the authoritative conventional software. An agent must never infer an undocumented datum merely because it is common in the region. The useful outcome may be a well-supported decision to obtain new evidence.

The asset to construct is an instrument that binds every conclusion to a source span, versioned data identity, transformation recipe and acceptance calculation. This is a candidate capability, not an already learned improvement. Its added value could disappear if ordinary frontier use with a well-documented GIS workflow performs equally well.

### Transformation witness

| Required element | Proposed witness |
|---|---|
| Original purpose | Decide which existing elevation evidence can support a frozen infrastructure-planning tolerance and what extra work is required for the rest. |
| Binding restriction | The owner treats a mixed archive as either reusable wholesale or requiring wholesale replacement; data meaning and uncertainty are not linked to the decision. |
| Why potentially removable | Source reports, metadata, conventional transforms and uncertainty information may permit a justified per-item classification. Some items will remain unresolved. |
| Alternative formulation | Construct a provenance-bound decision ledger that separates transformable, reprocessable, resurvey-required and unresolved records. |
| Executable realization | Parse actual public files; run PROJ/NCAT/VDatum where applicable; emit machine-checkable records and source-linked exception reports. |
| Falsifier | The evidence cannot support the distinctions, expert GIS already produces the same package within the same envelope, or the new method produces an unjustified positive qualification. |

The stated original purpose is archive qualification. Do not substitute this artifact for a certified flood map, surveyed elevation, hydrodynamic model, or engineering design. Such a substitution would abandon requirements rather than transform the task.

### Smallest decisive experiment before substantial construction

First inventory twelve real public evidence packages sampled under a fixed rule across at least three datum/region families. The NOAA Portland coastal DEM record is one accessible starting artifact, with public metadata, a stated MHW reference and documented intended use [G6]. It is not evidence that all required raw data or uncertainty records are available. Pin original files and licenses before deciding the final sample; publish exclusions. If almost everything is already unambiguous or almost everything lacks indispensable evidence, stop or reformulate before making an elaborate evaluator.

Freeze one planning purpose and its tolerance, the expected evidence fields, valid reasons to abstain, and a provider-independent review rubric. A meaningful positive result must qualify some useful records correctly while detecting genuine deficiencies; an always-reject strategy cannot pass usefulness. Give U ordinary frontier-model tools plus the same official GIS documentation and software. Give E a frozen contract/evidence/tool/verification procedure. Develop a candidate extractor or qualification method only on the development subset; E+ receives that version on unfamiliar geographic and datum families. A separate recipient records its initial resources and then uses the capsule.

Compare accepted decision packages at matched budget, errors that would incorrectly qualify data, unsupported abstentions, correction effort and complete cost. Include a conventional GIS script and an expert manual workflow. Give the discovered representation to U as a structure-only ablation. A separate information-acquisition ablation distinguishes better reasoning from obtaining additional source material. Review must check citations against original files and numerical operations against independent official outputs. A same-model internal review is not external professional validation.

### Commercial arrangement and its falsifiers

The hypothesized offering is an archive-readiness and decision-evidence service sold per bounded portfolio, with a separate commissioned survey or specialist review when necessary. Price should be compared with a scoped GIS consultant quote or observed hours; no such quote was obtained here. A genuinely new portfolio-sharing service needs buyer-value hypotheses rather than an invented market price.

A regional infrastructure consortium might jointly fund reusable source adapters, while each member pays for mission-specific qualification. This is a hypothesis about complementarity. Test four arms: separate delivery, common instrument only, coordinated purchase only, and both. Allow members to choose their existing consultants, defer, withdraw, or decline because procurement and rights costs exceed savings. Shared geography does not guarantee shared requirements or permission to redistribute source material.

A proposed contract would separate a refundable precommitment threshold from earned milestone payments; source acquisition, construction, adaptation, independent review, support and refunds must be costed once. Required opening cash must be computed from dated obligations before any positive expected contribution is interpreted as feasible. No deposits, counterparties, prices or sales have been observed.

Commercial falsifiers include: buyers already obtain equivalent work cheaply; required metadata is irrecoverable; human professional obligations dominate cost; cross-customer adapters have little reuse; or coordination and prefunding fail despite expected surplus.

### What a successor inherits

A successor can inherit a tested metadata parser, source-resolution procedure and versioned transformation dependency manifest. It must freshly check the new geography, source versions, intended use, tolerance, epoch, authority and permissions. A passed coastal screening mission does not qualify a building survey. Rights to a generic adapter do not grant access to a customer's archive.

## ENG-2 — An experimental instrument for qualifying protected PLC semantics

### Beneficiary and concrete gap

The intended beneficiary is an industrial owner or systems integrator qualifying a control-system migration or new application that depends on vendor-protected, time-dependent function blocks. The useful outcome is evidence that a bounded software behavior meets independently specified requirements under a declared scan-cycle and environment model. It is not unrestricted permission to operate equipment.

The gap is **not** that formal PLC verification or outside expertise is missing. CERN's open PLCverif translates programs and requirements to verification engines [P1]. A CERN–GSI case study already describes independent stakeholder roles, modeling of protected blocks, a real safety-critical application and retained models used by later projects [P2]. This is strong prior art for both service economics and reusable expertise. Repeating its FDBACK example would reproduce an existing demonstration, not discover a new opportunity.

The study identifies manual experiments with a vendor simulator and further automation as a development direction [P2]. PLCverif documentation also identifies specific frontend limits, including some time, addressing and memory semantics [P3]. These documented limits are not universal claims about the newest releases. A search surfaced a newer 2026 ESBMC successor paper, but the primary page could not be retrieved within this budget; no assertion about its current capabilities is made. Any candidate selection must resolve that prior-art uncertainty.

### Potential capability and transformation

The candidate instrument would take authorized access to a black-box component, vendor documentation and frozen requirements; select discriminating input sequences; observe scan-by-scan behavior; infer a scoped model; and generate replayable verification obligations. The known techniques include automata learning, simulation, model checking and requirement formalization. The prospective contribution is economical, reliable orchestration across unfamiliar components, not a new theorem simply because an agent performs the steps.

| Required element | Proposed witness |
|---|---|
| Original purpose | Qualify the actual component behavior needed by a frozen migration or new control application. |
| Binding restriction | Protected implementation and time dependence prevent an ordinary source-based check from establishing relevant semantics. |
| Removable assumption | Full source disclosure may be unnecessary if authorized experiments and documented assumptions yield a sufficiently scoped model. |
| Constructed alternative | An active experiment and verification instrument with explicit counterexamples and coverage limits. |
| Original-setting realization | Execute experiments against the actual authorized vendor simulator or hardware, then verify the original mission with the inferred model. |
| Falsifier | A held-out trace contradicts the model, an important behavior is unidentifiable within budget, or the existing service/toolchain matches cost and quality. |

### Smallest decisive experiment and present blocker

Choose a publicly documented component family not already included in the supplied prior-art models, obtain legitimate access to its executable reference, and freeze six or more mission-relevant requirements before inference. The public PLCverif examples can establish tool installation and semantics, but their absolute-value example and known timer example are only fixtures [P4]. They cannot serve as the flagship.

Give all arms PLCverif, supported model checkers, vendor documentation and ordinary automation APIs. Compare manual or scripted conventional identification, U, frozen E, and E+ with newly learned experiment-selection capability. Hold out components and input sequences; include restart, acknowledgment, timing boundaries and negative transfer between versions. Measure accepted models and mission outcomes, not merely trace fit. Give the inferred model to the original solver to isolate the value of discovered structure.

**Selection blocker:** this exploration has no authorized vendor executable, live controller, customer source or scoped migration acceptance contract. A homemade Python oracle could support a methods fixture, but could not establish successful qualification of the actual engineering dependency. This candidate should be deferred unless those inputs become available. Do not convert missing access into an artificially weak deterministic capability ceiling.

### Commercial and inheritance hypotheses

A fixed-scope qualification service could charge for accepted evidence, while multiple integrators cofund generic component models under explicit redistribution rights. The CERN–GSI work establishes that such collaboration has been done; it supplies neither a market price nor a demand forecast for this enterprise. Use actual scoped human-service quotes when available. Do not infer value from avoided accident costs or broad industrial market size.

Compare private construction, shared models alone, pooled demand alone and their combination. Model simulator licensing, independent engineering review, participant withdrawal, failed identification, support after firmware changes and refunds for undelivered models. Prefunding is separate from expected profit. A software proof cannot remove hardware commissioning, physical safety or independent responsibility where the actual project requires them.

The inherited artifact should contain exact component/firmware identities, scan semantics, assumptions, evidence, counterexamples, executable tests and rights. A successor must recheck its mission requirements, environment and authority; matching a model's name is insufficient. Shared expertise has potential value, but no fresh transfer, profitability or superior invention has been demonstrated in this dossier.

## Selection recommendation

ENG-1 is the stronger **small discovery check** within the currently available public-data environment, conditional on the inventory showing a real gap beyond PROJ, NCAT, FME and competent GIS service. It is not yet a validated flagship or business, and no large simulator is warranted. ENG-2 is consequential and closely fits the desired instrument/arrangement/inheritance mechanism, but its existing prior art and unavailable original-setting oracle make an immediate headline claim inappropriate. Neither candidate currently establishes that ordinary approaches are failing to deliver a useful outcome economically. Other exploration tracks should outrank both if they establish stronger unmet demand and a more decisive executable test.

## Primary sources

- [G1] NGS, [Get Prepared](https://beta.ngs.noaa.gov/new-datums/get-prepared.html).
- [G2] NGS, [Track Our Progress](https://beta.ngs.noaa.gov/new-datums/track-our-progress.html).
- [G3] NOAA, [VDatum](https://vdatum.noaa.gov/).
- [G4] NOAA, [Estimation of Vertical Uncertainties](https://vdatum.noaa.gov/docs/est_uncertainties.html).
- [G5] PROJ, [cs2cs documentation](https://proj.org/en/stable/apps/cs2cs.html).
- [G6] NOAA NCEI, [Portland, Maine coastal DEM metadata](https://data.noaa.gov/metaview/page?header=none&view=getDataView&xml=NOAA/NESDIS/NGDC/MGG/DEM/iso/xml/606.xml).
- [G7] Safe Software, [Geospatial Data Integration](https://fme.safe.com/guides/spatial-computing/geospatial-data-integration/) and [Data Validation and QA with FME](https://support.safe.com/hc/en-us/articles/25407541088269-Tutorial-Data-Validation-and-QA-with-FME), primary search excerpts inspected.
- [G8] Esri, [Get started with Data Reviewer](https://pro.arcgis.com/en/pro-app/3.3/help/data/validating-data/get-started-with-data-reviewer.htm), primary search excerpt inspected.
- [P1] CERN, [PLCverif user documentation](https://plcverif-oss.gitlab.io/plcverif-docs/userdocs/).
- [P2] Lopez-Miguel et al., [Formal Verification of PLCs as a Service: A CERN–GSI Safety-Critical Case Study](https://arxiv.org/abs/2502.19150), 2025, including the public extended appendix.
- [P3] CERN, [Supported SCL features](https://plcverif-oss.gitlab.io/plcverif-docs/s7frontend/SclFeatures.html).
- [P4] CERN, [Example verification walkthrough](https://plcverif-oss.gitlab.io/plcverif-docs/userdocs/Demo.html).

All sources were accessed 27 October 2026. These references support the specifically attributed observations; proposed capabilities, experiments, commercial arrangements and recommendations are researcher reasoning. No source supplies observed demand for either proposed service.
