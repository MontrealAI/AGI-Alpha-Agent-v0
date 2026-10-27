# Opportunity dossier: fatigue evidence and thermal decision metrology

**Research date:** 27 October 2026. **Researcher:** AI-assisted foundations/prior-art workstream. **Status:** comparative opportunity research; no flagship implementation, customer discovery interview, physical measurement, or sale has been performed. These are researcher-proposed opportunities. They are not autonomously discovered instruments or verified market gaps.

## Recommendation to the selection team

| Candidate | Consequential need | What could be constructed | Most serious objection | Present decision |
|---|---|---|---|---|
| A. Transferable fatigue evidence after an additive-manufacturing process change | Decide which process/material changes deserve further development and which fatigue evidence must be reacquired | A tail-aware evidence-transfer and test-allocation instrument, with explicit rejection of unsupported transfer | Existing commercial ML qualification and transfer-learning products are close competitors; dependable tail validation requires expensive, independently measured fatigue outcomes | **Do not select as this edition's primary executable flagship without a suitable physical dataset and an industry/lab evidence owner.** Keep as a serious longer-horizon candidate. |
| B. Mission-relative thermal metrology under globally ambiguous surface evidence | Make a defensible thermal-design decision when several material models fit the same available measurements | Compatible-countermodel generation, bounded decision certificates, and a physically feasible next-measurement procurement plan | Goal-oriented and decision-focused experimental design already exist; the small algebraic ambiguity example alone would be another supplied-solver fixture | **Conditional go for a bounded construction study, not yet a flagship selection.** First establish two consequential independently specified missions, an adequate evidence source, and a strong conventional control. Otherwise no-go. |

Candidate B has the sharper falsifiable restriction. Its potential contribution is an instrument connecting **actual evidence, global ambiguity, a customer's original thermal decision, feasible measurements, and joint procurement**. It does not invent goal-oriented experimental design, thermoreflectance, the Schur ambiguity, or the three-face remedy. The fact that an ambiguity has a compact mathematical description is compatible with a consequential need, but does not establish one. Selection must turn on useful decisions and evidence unavailable at acceptable cost, not on how quickly a matrix example can be coded.

### Search and evidence boundaries

The initial allowance was at most eight focused queries and four deep primary sources per candidate. Candidate A used seven focused queries and four deep sources. Candidate B used eight initial queries and four primary sources. At the parent's request, a documented extension of three queries and three deep sources examined goal-oriented design and concrete tooling. The three extension sources are GO-OED, GoBOED, and the official PyApprox tutorial. The parent also supplied the older budget-feasible experimental-design mechanism paper; only its abstract was screened here. Search returns and abstracts were screened more broadly, but no claim of exhaustive novelty or product-feature absence follows.

The exact Wang–Ban paper was retrieved directly after the web reader repeatedly failed; its unversioned URL served **v2**, not v1. All 47 pages, including the supplement and references, were read. The local PDF is `wang_ban_2609.13536v2.pdf`, SHA-256 `b7261d68de12bdb9c1533b7c08588df4b5ce47bdfdce0d21e001905b83fce89a`. Other sources received a focused read of their relevant methods, results, limitations, or product documentation. Do not describe those as full-paper audits. `source_manifest_foundations.json` records the successful source downloads and any failures.

## A. Transferable fatigue evidence after an AM process change

### Independently motivated need and beneficiaries

The need is to make defensible decisions about fatigue-critical metal parts when a process, machine, feedstock, heat treatment, geometry, or service load changes. Plausible beneficiaries are component developers, qualified AM service bureaus, material suppliers, and laboratories supplying design evidence. These are beneficiary classes, not identified buyers. Their useful outcome is a scoped decision and evidence package: which change is promising, which inherited observations remain relevant, what uncertainty remains, and which additional tests are necessary. Screening, design allowables, and final qualification must remain distinct services.

The 2026 NASA/FAA CM4QC strategy identifies obstacles including multiscale fatigue mechanisms, extreme events, inadequate uncertainty treatment, and restricted access to validation data. It also describes active programs developing fatigue-aware digital twins and model-assisted qualification. This is evidence of a substantial technical problem and substantial existing effort. It is neither an authorization to qualify a part nor an observed willingness to pay. The report explicitly disclaims Federal policy status. [A1]

### Prior art and strong outside options

**Commercial overlap is substantial.** Senvol's official ML description already offers targeted data-generation plans, machine/material transfer learning, process-to-property prediction, and support for qualification and requalification. The supplier's claims are not independent performance evidence. Nevertheless, they make a generic proposal to “use AI to reduce coupons” an inadequate novelty claim. A prospective recipient could license such software, engage its services, retain a specialist lab, conduct conventional test programs, use conservative established material/process envelopes, or abandon the proposed change. The public page does not establish its current price or whether a particular proposed feature is absent. [A3]

Two primary research directions further narrow the gap. Guo and colleagues combine EBSD/microCT-derived structure with elastic, fracture, and crystal-plasticity calculations to derive a fatigue-initiation distribution. Their demonstration uses selected correlation coefficients; calibrating them against experimental fatigue failures remains future work. Agreement with per-subcube evaluations of the same life formula is not independent validation of observed fatigue outcomes. The paper provides simulation inputs in a public repository. [A2]

Bean and colleagues use graded AM specimens, high-resolution digital image correlation, and computer vision to predict fatigue strength across compositions. Their demonstration's conventional comparison covers the two endpoint compositions; the authors identify limited sampled area, a single surface/specimen, possible missed rare events, and potential strength overestimation. They frame it as accelerated material screening. Its reported acceleration must not be promoted into a general qualification-cost reduction. Public SEM automation is a building block, and rights must be checked before reuse. [A4]

### Concrete gap hypothesis

The unresolved hypothesis is narrower than prediction: **Can an instrument determine when economical microstructural/surface measurements support transfer of a fatigue-screening decision, allocate additional measurements to the relevant tail, and refuse transfer when a changed process or geometry invalidates that evidence?**

This is not established as a missing commercial feature. Before selection, give the exact prospective deliverable to a domain expert and compare it with the strongest available commercial workflow. If an incumbent already supplies it at acceptable total cost, the opportunity could still be expert deployment or service delivery, but its technical novelty and incremental retained-capability claims should be reduced accordingly.

The instrument would need to construct an executable relation among process identity, spatial sampling, defect morphology, local loading, model validity, and the decision's required error rate. A mean-property regressor or narrative literature review would not satisfy this need. A useful retained capability could be a calibrated detector of unsupported evidence transfer, a test-plan generator, or a specialist service that knows when its own evidence is insufficient.

### Transformation witness and demanding test

| Witness element | Proposed content |
|---|---|
| Original purpose | Select or reject a candidate process/material change while preserving the agreed fatigue-screening or design-evidence standard. |
| Binding restriction | Every changed case must either start an expensive broad test program or rely on inherited evidence whose applicability is unverified. |
| Why possibly removable | Some mechanisms and measurements may transfer across genuinely compatible changes, while targeted testing exposes the differences that matter. This is a hypothesis to test. |
| Replacement | A scoped, uncertainty-aware evidence-transfer and test-allocation instrument, coupled to a shared measurement campaign when overlap is real. |
| Realization | Versioned executable analysis of actual microscopy/CT/test records, a concrete new test plan, and a blind decision on held-out changes. |
| Falsifier | Unsafe over-transfer, poor tail coverage, no cost advantage after calibration, a conventional workflow matching the result, or incompatibility among the proposed buyers' evidence needs. |

The construction study should begin with separately specified change requests, not a menu of compatible specimens and ready-made buyers. Preserve the original reasons for each request and each decision threshold. The system must discover any shared measurement structure. Cases found incompatible remain negative evidence.

Use historical measured fatigue outcomes only when their provenance, censoring, specimen preparation, loading conditions, and rights are inspectable. Hold out an entire machine/process or geometry family, not random rows from the same build. The proposed artifact should choose which evidence to acquire under a fixed measurement budget and return either a supported decision or a bounded abstention. Independent evaluators should reveal the hidden fatigue outcomes only after the decision policy is frozen. A retrospective simulator can debug the instrument; it cannot establish safety of actual transferred allowables.

The strong conventional arm includes established fatigue testing, mechanistic modeling, design of experiments, commercial/available ML tools, and a competent fatigue specialist. A separate control receives the discovered sampling formulation, so better formulation can be distinguished from better numerical execution. Calibrate decision thresholds before confirmation; do not declare an unsupported rare-event guarantee from a small convenient sample.

### Commercial construction and inheritance

A possible offering is a common evidence campaign plus confidential customer-specific interpretation. The common component might be a compatible process family, a calibration coupon series, or validated image-processing machinery. Each customer retains its own geometry, loading, acceptance authority, and confidential data. A lab performs authorized measurements; the enterprise supplies the protocol and interpretation; an independent reviewer supplies whatever review the promised outcome actually requires.

Participation is conditional: each buyer compares price, delay, expected decision value, confidentiality exposure, and residual risk against its real outside option. A quorum reservation is not revenue. Development begins only after contracts allocate nonrefundable work, refundable balances, withdrawal, failed specimens, retesting, and rights. A shared bad calibration or invalid transfer assumption creates correlated losses across buyers. Pooling does not diversify that risk away.

Compare technical improvement alone, pooled contracting alone, and their combination. Include rejected cohorts, scheduling costs, specimen fabrication, lab time, expert interpretation, model validation, refunds, support, and maintenance. Set prices from comparable scoped lab/engineering quotations or explicit buyer-value hypotheses; no public matched price was recovered in this search. Calculate worst cash deficit separately from expected contribution, with laboratory deposits and collection delays explicit.

Retain executable processing, calibration versions, applicability rules, and authorized reference evidence. A successor can reuse them for a different part only after checking the new process identity, geometry, loads, and acceptance meaning. It does not inherit a previous customer's qualification or permission. A worthwhile feasibility crossing would be a previously unaffordable evidence package becoming deliverable within the recipient's declared budget and risk limit. A cheaper already-feasible program is improved economics, not a newly feasible offering.

**Go/no-go:** serious need, but no-go as the present flagship without a suitable measured dataset and an accountable evidence partner. Its crowded prior art and physical validation burden are material, not cosmetic. Do not substitute synthetic fatigue curves and call the result expanded industrial possibility.

## B. Thermal design decisions under globally ambiguous surface evidence

### Independently motivated need and beneficiaries

The useful purpose is a thermal-design decision: select an orientation or heat-spreading arrangement, decide whether a proposed operating condition satisfies a temperature limit, or determine which additional evidence is necessary before a consequential design commitment. Potential beneficiaries include anisotropic substrate suppliers, power-device development teams, specialty crystal/device designers, and thermal-metrology laboratories. No customers or sales are evidenced here.

The most promising initial scope is an anisotropic material and geometry for which the unresolved tensor directions can actually change the specified decision. Do not assume every wide-bandgap stack has this problem. Independently known symmetries, material orientations, or adequate existing measurements may remove the ambiguity. In particular, a buried-interface problem in a nominally isotropic stack should not be relabeled as a fully anisotropic tensor problem simply to use a convenient theorem.

### What the primary sources establish

Wang and Ban's v2 paper treats linear Fourier diffusion in planar, laterally homogeneous coated stacks with complete heat flux and scalar interfaces. Same-face surface data depend on an anisotropic layer through its cross-plane conductivity and in-plane Schur complement. Changing frequency, delay, beam shape, or offset cannot recover the missing directions. A spatially uniform rear Robin boundary also preserves this ambiguity. Two orthogonal faces can have full local sensitivity rank yet retain two globally equivalent tensors; three resolved signed face-invariant sets determine the tensor. Their recovery demonstration is synthetic, with fixed auxiliary inputs. Internal/rear detection, patterned interfaces, and other departures require separate analysis. These are established results and limitations, not our inventions. [B1]

Buried-interface measurement itself is already active prior art. Zhang and colleagues' PWA-TDTR work combines broadband probing and joint fitting on three multilayer systems; its GaN/diamond example identifies sensitivity and interface-model limitations. Cheng and colleagues previously demonstrated dual-frequency thermal mapping and used steady-state signals to examine buried interfaces. These papers provide useful measurement possibilities and cautions, not proof that arbitrary device structures are identifiable. A proposed instrument must respect specimen preparation, calibration, and access requirements. [B2, B4]

The NETZSCH PicoTR product already offers thermal-property and multilayer-interface analysis with supported specimen configurations. Its documented geometries and sample dimensions are not permission to measure any encapsulated chip. Calibration/repeatability specifications are conditional examples, not universal uncertainty bounds. Buying an instrument, commissioning an established laboratory, or using an expert's existing analysis are genuine outside options. [B3]

### Prior art defeats the broad “decision-focused AI” novelty claim

GO-OED already optimizes information about nonlinear predictive quantities rather than all parameters. GoBOED explicitly optimizes downstream decision objectives and discusses parameter directions irrelevant to those decisions. Sandia's PyApprox supplies executable nonlinear goal-oriented experimental design with multiple risk/deviation objectives and cross-evaluation of designs. These must be included in the competent expert workflow. A user interface around them is not a new scientific method, though competent deployment can create Operational Alpha for a recipient who lacks it. [B5–B7]

Budget-feasible experimental-design mechanisms also predate this proposal. The parent-supplied Horel–Ioannidis–Muthukrishnan abstract concerns strategic experiment costs under a specific information-value model. It is a building block; its guarantees do not automatically apply to non-submodular complementary measurements, multiple design buyers, uncertain delivery, and refundable funding. [B8]

### A possible claim worth testing

> Given a recipient's original thermal-design decision and its actual surface evidence, construct independently checkable compatible countermodels or a bounded decision certificate; if the decision remains unresolved, construct a physically feasible measurement and procurement plan that can resolve the relevant uncertainty at acceptable total cost.

This claim is deliberately conditional. The opportunity hypothesis is that assembling globally sound evidence, mission-specific consequence, real lab constraints, and procurement remains sufficiently difficult to justify a reusable instrument. The search has not established that all laboratories or existing products lack it.

The instrument should first ask whether the useful decision is invariant across admissible models. Full tensor recovery is unnecessary when every compatible model supports the same required conclusion. Conversely, if two compatible models reverse the decision, a precise pair is more useful than an unjustifiably narrow fitted error bar. The output can be a robust decision, a counterexample, an executable additional-measurement plan, or an honest no-feasible-plan result.

Let the admissible set be specified prospectively by the measurement model, reported noise/calibration bounds, material constraints, geometry, and independently justified prior information. For a proposed decision (a), evaluate the range of its acceptance quantity (g(a,\theta)) over this set. A sampled ensemble can find counterexamples; it does not certify the absence of them. Any claim of a global bound needs an exact reduction, verified numerical bounds, or another justified coverage argument. If those checks are computationally unaffordable, the instrument must label the result partial.

Do not force a positive feasibility crossing by widening temperature limits, dropping a design condition, or choosing a negligible objective. A recipient may accept a conservative existing design and gain nothing from further characterization. That is a valid no-op outcome.

### What must actually be constructed

The retained asset must go beyond an implementation of the paper's matrix formula. It needs an evidence adapter with units, signed orientation registration, model scope, calibration, and provenance; a forward-model interface spanning at least the relevant measured and application settings; a compatible-model/certificate engine; and an experiment planner constrained by real sample access, preparation, fixture compatibility, lab capacity, and collection timing. Each certificate should carry its computational tolerance, uncertainty assumptions, and exact mission identity.

A front-surface measurement and an application with finite lateral boundaries need not have the same observation symmetry. That distinction could be useful, but its consequences require a separately checked application model. An analyst must not claim that a theorem about an ideal planar measurement automatically certifies a finite device. Similarly, changing uniform convection is not a clever additional view: the source already shows why that does not supply the missing information.

Feasible alternatives might include measurements on another genuinely accessible registered face, independent crystallographic information with appropriate uncertainty, or a different sensing configuration. A wafer cannot be assumed to have three accessible, equally prepared faces. Rear or internal sensing may require destructive preparation, a new specimen, or new apparatus. Those dependencies belong in the plan and its cash requirements. If only a repeat of the same uninformative observation is affordable, the correct output is to stop or alter the offering.

### Transformation witness

| Witness element | Proposed content |
|---|---|
| Original useful purpose | A specific design/operating decision under an unchanged thermal acceptance condition. |
| Restriction | Available measurements admit distinct material explanations; repeated fitting or more same-face settings may fail to resolve the decision. |
| Potentially removable assumption | The workflow assumes it must estimate every parameter or assumes a locally well-fitted tensor is sufficient. Neither is necessary for every mission. |
| Replacement formulation | Carry the entire justified compatible class into the mission; certify invariant decisions, expose decision-reversing countermodels, and procure only relevant additional information. |
| Executable realization | Actual measurement traces and metadata feed the instrument; a separate thermal forward solver checks proposed certificates/countermodels and a laboratory checks proposed measurements. |
| Falsifier | An accepted certificate fails on an admissible countermodel; the proposal relies on an unavailable surface or unmodeled preparation; strong expert tools produce the same result more cheaply; or no consequential mission benefits. |

### Decisive bounded experiment and fair controls

Start with at least two separately motivated thermal mission briefs, including their geometry, operating conditions, decision threshold, available material evidence, permissible interventions, cost ceiling, and deadline. Identify evidence from actual published experiments or an authorized laboratory; report exactly what is measured and what is supplied by researchers. If no adequate raw traces/calibration records can be obtained, retain a clearly labeled computational study, and reduce the claim accordingly.

The test should contain an invariant-decision case, a decision-reversing ambiguity case, and an unresolvable-within-budget case. Those are evaluation categories, not a promise of favorable outcomes. Include unfamiliar combinations of orientation constraints, layer structure, and application geometry. Do not make every test a perturbed copy of the paper's supplied tensor. Protect fresh missions and any extra measurements from the construction team.

The expert E arm receives the same evidence, suitable frontier model, conventional inverse-analysis tools, global-search expertise, goal-oriented/decision-focused design software, and the published three-face solution. E+ receives the retained instrument. The ordinary U arm receives a competent task brief and the same available model/resources; H is a matched specialist engineering/metrology service, priced from a real quotation or disclosed estimated hours. No complete-dollar advantage is established by this dossier.

Measure accepted original-purpose decisions, false certificates, correct abstentions, expensive measurements avoided or required, total analysis and correction effort, turnaround, customer preparation, and cash needed to deliver. Freeze a feasibility threshold before evaluation. Compare at matched accepted quality and matched resource budgets. A formal counterexample that prevents an unsupported design release is useful, but it is not automatically profit or an expanded offering.

Independent checks should include a distinct implementation of the forward response, convergence checks, adversarial compatible models, correlated calibration errors, uncertain face registration, and model mismatch. For a bounded certificate, verify the bounds rather than merely reproducing the candidate's own samples. All unmodeled regimes must trigger explicit scope limits. Physical deployment needs fresh experimental verification and accountable engineering acceptance.

To test discovery rather than possession, a separate fresh agent should receive a new mission and the frozen operating method without the earlier finished formulation. Compare its ability to construct a sound new adapter/measurement proposal with E. Retention can make later execution easier without improving the discovery process; these are different outcomes.

### Common evidence procurement and commercial mechanism

One possible coalition contains a material supplier, two device-design users, and a metrology lab. They qualify as a coalition only if their decisions genuinely share an evidence identity: compatible lot/state, treatment, temperature range, material orientation information, and applicable model. Sharing the name of a material is insufficient. The system must discover this overlap from independently motivated requests and reject incompatible combinations.

The common deliverable is a rights-cleared measurement/certificate package; each design user separately purchases confidential mission interpretation. A user whose decision is already invariant may decline further testing. Another may fund an extra accessible orientation because its own decision is sensitive. The supplier may pay for a reusable characterization asset only if it values the defined rights. The laboratory sells specified preparation and measurement work, not guaranteed favorable physics.

Compare four packages: conventional private delivery; improved technical instrument with private procurement; coordinated procurement using established methods; and the combination. Price and participation are optimized or elicited under explicit assumptions rather than a fixed discount. Customers can choose a lab, use conservative designs, postpone, or decline. No assumed compatible buyers, vendor quotation, token issuance, or speculative intellectual property value is revenue.

A conditional commitment specifies minimum funding, cancellation dates, preparation responsibilities, measurement acceptance, failed-sample handling, data ownership, publication rights, refunds, and a separately funded interpretation step. Refundable deposits remain obligations. Before commitment, simulate cash timing for cancellation, partial delivery, default, queue delays, retesting, and a shared calibration failure. The enterprise must finance the largest resulting cash deficit or reduce the offer. A positive expected surplus does not make restricted deposits spendable.

### Successor and next useful possibility

Retain the executable evidence adapters, verified forward-model components, certificate policy, and licensed generic data. A new recipient can receive a skill or authenticated specialist service, with its access, execution authority, and confidential inputs separately checked. Generic qualification can be reused only when the complete relevant identity and reuse policy permit it. New geometry, purpose, uncertainty, or thermal limit requires fresh mission assessment.

A useful successor test is a different thermal decision on a compatible material: does inherited structure reduce the analysis or evidence-acquisition requirement enough to meet a predeclared budget/deadline/risk threshold? If both configurations already meet it, report lower cost or better reliability. If the recipient already has equivalent expertise and tools, transferred access may add no value. Compare an ordinary library containing the same artifacts and permissions before attributing any benefit to a graph.

### Candid construction decision

**Conditional go** to construct a bounded instrument if the selection team can secure two independently motivated, consequential missions and an adequate evidence path. The hard problem is connecting globally valid ambiguity handling to distinct real decisions and feasible measurements; a demonstration of that connection can be useful even when the component algorithms are established. If the result is principally careful orchestration of existing methods, call it Operational Alpha and measure it fairly.

**No-go** if the proposal reduces to the published six-parameter example, if all useful decisions are already solved by current expert practice, if the only improvement is more compute or more measurements, or if the study supplies the instrument, compatible buyers, and financing and then relabels their selection as invention. Current evidence supports a serious opportunity hypothesis, not a verified market gap, novel theorem, field-ready instrument, or profitable enterprise.

## Primary sources

- **[A1]** Glaessgen et al., *Computational Materials for Qualification and Certification (CM4QC) Strategy Document*, NASA/TM–20260001729, DOT/FAA/TC-26/10, March 2026. Relevant sections: fatigue mechanisms, uncertainty, validation, active programs. https://ntrs.nasa.gov/api/citations/20260001729/downloads/NASATM-20260001729.pdf
- **[A2]** Guo, Sundararaghavan, Kramer, *Uncertainty quantification of fatigue initiation life for powder bed fusion metal additive manufacturing*, arXiv:2609.03163v1. Relevant §§5.3.2, 6 and data availability. https://arxiv.org/abs/2609.03163v1 . Listed simulation-input repository: https://github.com/yulin-g/UQ-fatigue-life-PBF-AM (not audited here).
- **[A3]** Senvol, official Senvol ML product page, accessed 27 October 2026. Vendor claims. https://senvol.com/ml/
- **[A4]** Bean et al., *Accelerated Fatigue Strength Prediction via Additive Manufactured Functionally Graded Materials and High-Throughput Plasticity Quantification*, arXiv:2502.13159v1. Relevant §§2.2.4, 3.3, 4.2. https://arxiv.org/html/2502.13159v1 . Listed automation repository: https://github.com/cmbean2/Automated-SEM-Procedure (not audited here).
- **[B1]** Wang and Ban, *Identifiability of the three-dimensional anisotropic thermal-conductivity tensor in thermoreflectance measurements: Single-orientation limits and full-tensor recovery*, arXiv:2609.13536v2, 15 September 2026; 47 pages including supplementary information. https://arxiv.org/abs/2609.13536v2 . Exact downloaded version and hash above.
- **[B2]** Zhang, Jiang, Yang, *Thermal Characterization of Buried Interfaces in Multilayer Heterostructures via TDTR with Periodic Waveform Analysis*, arXiv:2604.12539v1. https://arxiv.org/abs/2604.12539v1
- **[B3]** NETZSCH, official PicoTR product documentation, accessed 27 October 2026. Vendor specifications. https://analyzing-testing.netzsch.com/en-US/products/time-domain-thermoreflectance-analyzer-tdtr/picotr
- **[B4]** Cheng et al., *Thermal Visualization of Buried Interfaces by Transient and Steady-State Responses of Time-Domain Thermoreflectance*, arXiv:2103.08084v1. https://arxiv.org/abs/2103.08084v1
- **[B5]** Zhong et al., *Goal-Oriented Bayesian Optimal Experimental Design for Nonlinear Models using Markov Chain Monte Carlo*, arXiv:2403.18072v2; SIAM/ASA Journal on Uncertainty Quantification 14 (2026), 19–47. https://arxiv.org/html/2403.18072v2
- **[B6]** Go, Qian, Yoon, *Goal-driven Bayesian Optimal Experimental Design for Robust Decision-Making Under Model Uncertainty*, arXiv:2605.26093v1. https://arxiv.org/html/2605.26093v1
- **[B7]** Sandia/PyApprox official tutorial, *Goal-Oriented OED: Designing for Prediction on a Predator-Prey System*, accessed 27 October 2026. This establishes available functionality, not a thermal-domain performance benchmark. https://sandialabs.github.io/pyapprox/boed_pred_nonlinear_usage.html
- **[B8]** Horel, Ioannidis, Muthukrishnan, *Budget Feasible Mechanisms for Experimental Design*, arXiv:1302.5724v4; LATIN 2014. Parent-supplied source; abstract screened only in this workstream. https://arxiv.org/abs/1302.5724v4

## Evidence handed to the broader study

Preserve both candidates and this negative prior-art evidence in the search history. No quantities here are calibrated prices, observed demand, learning gains, earned revenue, or deployed capabilities. The dossier supplies hypotheses and falsifying tests. Its principal addition is a sharper selection standard: a real original-purpose decision, an explicit information or transfer restriction, a constructed and independently checked instrument, and a viable evidence-delivery arrangement must all survive comparison with what the recipient can already obtain.
