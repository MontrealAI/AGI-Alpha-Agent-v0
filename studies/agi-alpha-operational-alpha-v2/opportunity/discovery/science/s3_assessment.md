# S3 — Qualification of a scientific model for a new requested prediction

**Decision:** worth a bounded technical pilot; not yet a selected flagship, proven commercial service, new identifiability algorithm or biological discovery.

This candidate was identified after the initial H4 mechanism-design proposal was questioned. The revised opportunity follows a documented software/scientific-instrument need: a calibrated, reusable model can fit its original data while failing to justify the particular quantity a successor now wants to predict. The instrument would qualify that request using the actual measurement regime and provenance of fixed parameters, and return a checkable qualification, counterexample or missing-evidence obligation.

## Evidence that makes the need specific

The 2026 PEtab Select paper explicitly identifies identifiability as relevant to popular selection criteria and describes comprehensive identifiability analysis across large model spaces as computationally impractical. It proposes selective automated analysis as a useful future direction. This supports a scoped integration need, not a claim that identifiability methods have not been invented. [1]

The source-pinned H4 case provides a concrete reuse boundary. Its observations are equilibrium abundances and its common reverse rate is fixed. A successor may reasonably ask for an equilibrium quantity or for a timed response. Those are different scientific requests despite using the same model files. The latter needs physical-rate evidence that the original data cannot supply. A correct model-selection result need not answer it.

**Do not describe this as an error in the original study.** The original purpose was to explain stationary combinatorial patterns. A model's declared fixed parameter is legitimate within that purpose. The new risk arises when a recipient silently interprets its normalized clock as a calibrated physical clock for another mission.

## Beneficiary and useful accepted outcome

The initial beneficiary is a research software team, core facility, modeling consultancy or scientific customer reusing a published dynamical model for a new prediction. A useful delivered packet answers:

1. What exactly is the requested quantity, in what units and operating conditions?
2. Which source measurements and assumptions constrain that quantity?
3. Which properties are actually supported, conditional or unqualified?
4. Can the unsupported part be exhibited by two admissible realizations with equivalent original evidence but materially different requested outcomes?
5. What additional measurement or calibration would remove the particular obstruction?

The outcome is a qualified reuse decision. It is neither blanket certification of the model nor an assertion that the biological system is correct.

## Binding restriction and proposed transformation

The obstructive assumption is that a fitted parameter vector and a successful executable replay transfer the scientific meaning of the original model into any new request. The removable part is the conflation of software identity, calibration evidence and mission-specific validity.

The alternative is a **request-specific evidence contract**: bind a model version, actual observations, parameter-provenance statements and a requested functional; construct the right observational equivalence relation; then qualify only the functional that the evidence supports. Existing algebraic and statistical methods do the analysis. A versioned adapter and workflow make their correct application reproducible across agents.

| Transformation-witness element | Proposed retained evidence |
|---|---|
| Original useful purpose | Answer the stated scientific prediction within its tolerance, units, operating envelope and deadline. |
| Restriction | Original calibration is being reused as though it identifies every new requested quantity. |
| Removable assumption | Fit adequacy and software replay are sufficient mission qualification. |
| New representation | Explicit separation of observed data regime, fixed-parameter provenance, requested quantity and admissible alternative realizations. |
| Executable realization | PEtab/SBML ingestion, observation-regime construction, existing symbolic/statistical analysis, proof/counterexample serialization, mission decision. |
| Falsifier | Incorrect acceptance/rejection, unsupported physical assumptions, or no accepted-output improvement over competent tools and ordinary expert review. |

This connects the three foundations without claiming a new solver: change the question's representation, offer an evidence-based service with explicit responsibility, and let successors inherit the generic qualification procedure while rechecking new meaning and authority.

## What is new, what is supplied, and what is not claimed

**Supplied ingredients:** PEtab and SBML, the public H4 model/data, fitted parameter values, structural-identifiability and observability algorithms, profile likelihood, symbolic algebra, conservation laws, and the existing successor Harness. They are available to every comparison arm.

**Proposed construction:** a repeatable adapter from a scientific reuse request plus actual data files to the appropriate analysis, with a durable witness and a clear boundary between generic checked structure and new mission qualification. Root's team, not an autonomous scientist, proposes this construction.

**Not established:** superiority of the workflow; an unmet commercial backlog; a novel mathematical method; the truth of a new biological mechanism; or improved autonomous invention. A favorable outcome could be legitimate Operational Alpha or useful transfer of existing expertise. If the baseline already performs the same task well, that result must stand.

## Actual assets now retrieved

After the first follow-up's blocked web and shell retrievals, the parent authorized continued retrieval through the existing GitHub connector. The complete case and root license were recovered at:

`PEtab-dev/petab_select@7b1a1528cee614e72f17eb82338472e7ba91d8de`

The **13 files** are in `source_checkout/petab_select/`; each byte sequence was verified against the Git blob SHA. The manifest also records SHA-256 and immutable source URLs. A direct CSV inventory confirms **252 rows**, all with `time=inf`, over **15 observable identifiers**. The SBML declares the normalized initial state and does not declare a physical time unit. The parameter table fixes `da_b=1`; it does not contain an independent physical-rate calibration. These are observed file properties, not deductions from a search snippet.

The root BSD-3-Clause license is retained. Do not imply author endorsement. The original paper's supplementary material and Zenodo archive were not downloaded; their rights and exact version are not inferred from the repository license. The current case is a transparently identified supplied artifact, not our discovery.

## Strong conventional baseline

The comparison must give the baseline the **same model, measurements, mission and parameter-provenance information**, along with existing PEtab tooling and a competent route to structural/practical identifiability. SIAN or StructuralIdentifiability.jl can be used where applicable; a direct symbolic steady-state formulation and exact conservation/scaling checks are also genuine available alternatives.

It would be unfair to feed an ODE identifiability package a continuous-time observation model when only equilibrium measurements were collected, then call its answer a tool failure. A competent baseline is allowed to formulate the equilibrium observation problem correctly. It is also allowed to recognize the common-rate scaling ambiguity by inspection.

Practical uncertainty may require profile likelihood or another suitable uncertainty calculation; a floating-point rank threshold alone must not be treated as proof. Exact symbolic witnesses should be used only for properties actually covered by them. For example, a common-rate scaling witness disqualifies an absolute time scale under an unknown common rate; it does not prove every parameter or equilibrium prediction is unidentifiable.

A useful preflight bound for the **full candidate superset** follows from the observation dimension: one normalized equilibrium over sixteen states has at most fifteen independent mean-abundance coordinates. A smooth map from thirty-three freely varying kinetic parameters to those means cannot have a full-column-rank local sensitivity matrix. This is a necessary dimension check, not a complete identifiability theorem. It does not disqualify the published eight-parameter selected model, identify which individual quantities remain learnable, or treat repeated measurements as new independent mean coordinates. Their statistical precision still matters.

The fixed `da_b=1` is not a free parameter inside the published fit. Any physical-clock witness must explicitly introduce an unknown conversion from normalized model time to physical time, justified by absence of independent calibration evidence for that new mission. If a credible physical calibration is supplied, the analysis and acceptance must change accordingly.

## Smallest decisive pilot

### Freeze the useful outputs before trials

Use the real H4 source/data to define several meaningfully distinct requests, with requirements frozen independently of solving arms:

- A **steady-state observable** under the original assumptions. The method must preserve valid uses rather than rejecting everything.
- A **physical-time prediction** without additional clock calibration. The method must expose the unsupported time interpretation and return a reproducible witness or explicit qualification requirement.
- The same timed request with a **separately supplied, explicit calibration interval**. The method must propagate that information and avoid retaining an obsolete blanket rejection.
- A **changed observation or mission** that breaks the previously applicable reasoning, so that inherited generic checks cannot silently validate a different purpose.

The calibration interval in the third request would be an openly assumed test condition unless drawn from a real independent source. Its introduction tests conditional reasoning and capability adaptation, not empirical knowledge of H4 kinetics.

H4 alone is an instrument demonstration. Fresh transfer should use at least one separate public model/data family with a different observation regime and independently reviewed requested quantity. Freshness comes from the new semantic request and artifact, not from changing a random seed in the same known counterexample. The result must remain bounded to these missions.

### U, E and E+ distinctions

U has reasonable frontier-model prompting, file/tools access, the same conventional packages and time budget. E has a frozen established scientific-model review workflow. E+ adds only the new retained adapter/witness capability developed on separate work. Record whether E already knows each check and whether the recipient can access the public examples. No hidden expected answer, favorable initialization or task-specific completed witness is placed only in E+.

Evaluate accepted packets and unjustified approvals/refusals at matched budget. At matched accepted quality, count actual tool/model use, corrections, source preparation, automated checks and residual attention. Where billing is unavailable, leave actual monetary cost unknown and perform separately labeled pricing scenarios. A cheap useful capability should face a proportionate test, not an artificial research tax.

### Decisive acceptance and negative controls

An independent reviewer checks that the packet preserves mission semantics, uses the actual data regime, distinguishes declared assumptions from measurements, and produces valid witnesses or explicit bounds. Include a valid reuse that must pass, an unsupported physical prediction that must fail or be qualified, a genuinely informative calibration, and an inherited witness whose applicability has expired after a mission change.

Give any discovered representation back to the original solver. Compare direct file/library distribution with graph distribution using identical content and permissions. These isolate expertise, transfer and organization.

## Commercial and participation mechanism

The first offering would be a bounded **scientific-model reuse qualification service**, referenced to the equivalent human research-software/modeling service. Price and effort would initially be explicit hypotheses because this exploration observed neither quotes nor transactions. The deliverable's value is a trustworthy decision about proceeding, buying a measurement or stopping, not a favorable biological result.

A shared instrument could become economical for several unrelated reuse requests that independently need the same generic PEtab/SBML adapter. A commissioning contract can separate the public/common adapter from confidential mission data and evidence, fund construction in milestones and price each mission's qualification separately. Membership grants eligible capability access; it does not grant experimental or financial authority.

The complementary hypothesis is testable: independently commissioned mission work may repeatedly pay adapter construction costs; coordinated commissioning may spread those costs only when participants actually share the requirement and accept the rights/maintenance terms. Give the uncoordinated baseline access to the same off-the-shelf tools. Permit nonparticipation, withdrawal, common adapter failure, refunds and delayed payment. A positive expected margin still requires enough opening cash to fund work before collection.

No synthetic coalition should be described as observed demand. Research selection may proceed with transparent hypotheses; commercial launch requires evidence sufficient for actual contracts and obligations.

## Assessment

**Consequential gap:** credible and specifically documented as an integration/qualification need. **Independent computational acceptance:** achievable for bounded witnesses and mission contracts. **Conventional competition:** strong and must be included. **Frontier-model contribution:** plausible source interpretation and workflow execution, unproven. **Reusable instrument:** clear, provided it generalizes beyond the hand-identified H4 witness. **Commercial evidence:** presently hypothetical. **Research decision:** proceed to a small pilot if this opportunity outranks the other dossiers; do not invest in a large simulator first.

### Source

[1] Pathirana et al., *PEtab Select*, 2026, especially Availability and future directions: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1014774 . The parent independently opened this page. Public case provenance and immutable links are recorded in `h4_source_manifest.json`.
