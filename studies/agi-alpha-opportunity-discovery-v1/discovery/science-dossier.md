# Discovery dossier: physical-world science opportunities

Research date: 2026-10-27. Investigator: independent discovery subagent. Budget: at most 12 attempted primary-source page reads and approximately 15 minutes. Actual: 12 attempted reads, 9 successful, 3 fetch failures; five search rounds. No external contact, model experiment, physical experiment, sales or authentication was performed. This is opportunity-selection evidence, not confirmation of feasibility.

## Candidate S1: Preserve a scientific purpose when transferring an experiment to a different laboratory

**Beneficiary and outcome.** Small research laboratories, core facilities and their customers want an experiment to answer the same scientific question on their available equipment. A syntactically executable translation is insufficient if a new volume, mixing process, liquid property, calibration or timing changes the measured phenomenon.

**Existing accomplishment.** Shi et al. (NeurIPS 2024) already construct protocol dependence graphs through syntax, semantics and execution stages and report expert-level translation. SiLA provides laboratory interoperability. LAP v0.1 proposes instrument cards, reservations, task-bound authorization and measurement schemas; the paper explicitly states that it is a design specification without implemented or empirically validated status. Search also identified PRISM, which connects protocol generation, simulation and robotic execution, and AEGIS, an assay-aware validation system. These are required prior art and possible building blocks; their names must not be recast as this project's invention.

**Specific remaining hypothesis.** A small laboratory may lack an economical way to prove or reject *scientific equivalence* after equipment or workflow substitution. The useful instrument would return a witness: original purpose and acceptance criterion, altered physical assumption, preserved invariants, residual uncertainty and the smallest measurement that can distinguish an acceptable substitution from a misleading one. Whether existing expert practice already supplies this at adequate cost remains unresolved.

**Why now.** Tool-using models can combine protocol text, schemas, instrument capabilities, code and experiment logs. Existing simulators lower the cost of checking digital executability. Neither fact establishes biochemical or physical equivalence.

**Construction.** Extend the existing SUCCESSOR mission verifier with a protocol-transfer witness adapter. Use SiLA/Autoprotocol/Opentrons-compatible artifacts where appropriate. Keep physical uncertainty explicit. Never infer laboratory authority from an agent's generic identity or a prior successful run. The retained asset is a family-specific verifier and experiment-design workflow, not a competing instrument registry.

**Smallest decisive experiment.** Obtain a fixed set of publicly documented benign colorimetric or dilution workflows plus real source/target equipment information. Freeze original-purpose acceptance before transfer. H is an equivalent laboratory method-transfer service; U is ordinary, well-specified frontier-model use with available tools; E is established protocol translation plus simulation; E+ adds the witness method. A local first stage can execute volume/timing/units/deck constraints and planted semantic counterexamples. A decisive physical stage requires independently measured output or existing cross-laboratory measurements. Transfer the frozen method to a separate recipient and unfamiliar assay family. A local simulator alone cannot establish scientific success.

**Falsifiers.** The method fails to detect scientifically consequential substitutions; false alarms erase its savings; the conventional expert workflow already delivers the same result at equal or lower complete cost; independent measured outcomes violate the invariant despite a passing witness; the method cannot transfer without expensive assay-specific reconstruction.

**Commercial arrangement.** A bounded method-transfer assessment with staged payment: evidence audit, executable translation, and optional partner-laboratory validation. Several compatible laboratories could cofund a generic verifier while owning their assay data. Contributions are conditional on completion and rights; refunds, failed calibration, withheld customer data and incompatible equipment can dissolve the bundle. No price, demand or coalition is observed. Instrument validation, liability allocation and customer willingness to pay remain major unknowns.

**Decision.** Reserve candidate. It is consequential, but the explored space has strong recent prior art and local digital fixtures do not satisfy the physical acceptance condition. Do not select merely because protocol parsing is easy to code.

## Candidate S2: Turn a methane alert into a financeable and verifiably completed intervention

**Beneficiary and outcome.** Facility operators, commissioning agencies and repair providers need a suspected persistent release to be investigated and, if appropriate, repaired with defensible evidence and affordable execution. The original purpose is an actual resolved release, not a favorable report or disappearance of an alert.

**Established capabilities.** MARS-S2L already detects methane in public imagery and has been deployed operationally; its 2025 paper reports real notifications and verified mitigation cases. UNEP's platform already integrates datasets and offers CSV/JSON downloads. GFMR already provides grants, technical assistance, project preparation and finance, including support for responses to MARS. The World Bank describes a repair facility in Uzbekistan intended to replenish itself using gas savings. Detection, financing and a reinvestment loop are therefore established ingredients.

**Specific unresolved gap.** UNEP's response dictionary states that satellite observations alone cannot always establish cessation; its response rate records stakeholder feedback rather than a count of completed repairs. The IEA identifies split incentives, upfront capital, available services and staff as barriers. The proposed gap is a small-case *closure-and-financing compiler*: given an alert, available observations, operator rights, a field provider and a possible funder, determine what evidence and commitments are still missing, construct a conditional intervention package, or correctly decline it. We do not yet know whether this workflow is undersupplied for a reachable buyer segment.

**Transformation.** Replace the assumption that a detector's alert or later non-detection is a sufficient commercial deliverable with a conditional package tied to the original physical outcome. The package contains an observation-validity model, targeted field investigation, a repair scope if justified, a payer with authority, milestone obligations, contingency funds and a closure rule. This is an integration hypothesis, not a claim of a new remote-sensing algorithm or a newly invented funding model.

**Why now.** Public observations, open detection research and documented case histories permit automatic preparation of verifiable evidence packets. Frontier intelligence may lower the work needed to reconcile narrative case reports, data dictionaries and obligations. Physical access, local authority and actual repair remain independent requirements.

**Smallest decisive experiment.** Freeze a dated archive of public MARS cases and separate their pre-intervention evidence from withheld outcomes. Execute an instrument that checks timestamp order, whether an observation was capable of detection, whether source attribution changed and whether feedback actually describes repair. Demand explicit insufficient-evidence states. Compare H, U, E and E+ on factual reconstruction and properly qualified closure recommendations; give E the same public datasets, dictionaries and conventional tools. Any positive claim about physical reduction needs field records or independently verified outcomes. A separate synthetic financing module can test technical construction alone, coordination alone and their combination without claiming real participation.

**Falsifiers.** Existing MARS/GFMR/provider workflows already prepare equivalent packets economically; the purported small-case segment does not exist; missing observations prevent useful decisions; model-generated attribution or repair scope is unreliable; operator permission or a payer cannot be secured; bundled cases suffer correlated failure that consumes reserves; transaction costs exceed the benefit of pooling.

**Commercial mechanism.** Sell a scoped evidence-and-delivery preparation service to an authorized operator or program; a provider may be paid for investigation before committing to repair. A funder may advance only a verified milestone tranche, with unspent deposits refundable and reserves for failed/partial work. Recovered gas savings are customer benefits unless contractually collected; seed grants are financing, not earned service revenue. Avoid treating a carbon price, quoted social benefit or hypothetical gas savings as enterprise cash. No observed customer or price is claimed.

**Transfer and next possibility.** A rights-cleared evidence adapter could help a fresh recipient assess a different site's observation gaps; a successfully qualified obligation template could lower later preparation effort. Test transfer across different observation patterns and owners rather than copying a case with hidden outcomes. A successor still needs a new mission's evidence, authority and acceptance. Graph-specific value requires comparison with an ordinary library containing identical content and permissions.

**Decision.** More attractive than S1 for *bounded opportunity validation* because the actionable gap and complementary technical/commercial barriers are documented. Not yet a justified flagship. The next gate is to show a buyer-specific deficit relative to existing MARS/GFMR services and to obtain enough independent observations for a meaningful retrospective test. Do not build a favorable coalition simulator before that gate.

## Selection implications

Both candidates survive as consequential problem hypotheses; neither supports a claim that an economically feasible new enterprise has been discovered. The research can legitimately record rejection or deferral after prior-art investigation. A stronger proposal from another domain should outrank these if it has a clearer unmet need, accessible acceptance evidence and a decisive experiment within the available budget.

## Primary-source inventory

All sources retrieved 2026-10-27. URLs below are source locators, not promises of immutable content. The parent should freeze full source bytes/versions before an experiment or paper depends on them.

| ID | Source and scope | Retrieval ref | Status |
|---|---|---|---|
| S01 | Shi et al., Expert-level protocol translation for self-driving labs, NeurIPS 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/54dd9e0cff6d9214e20d97eb2a3bae49-Abstract-Conference.html | turn9view0 | Abstract opened; PDG workflow and authors' performance claim |
| S02 | Zhu et al., LAP v0.1. https://arxiv.org/html/2606.03755v1 | turn9view1 | Opened; explicitly unimplemented design specification; arXiv v1 dated 2026-06-02, displayed author line also has 2026-08-24 |
| S03 | SiLA standards. https://sila-standard.com/standards/ | turn6search0 | Search result read; page open timed out |
| S04 | UNEP, MARS response data dictionary. https://methanedata.unep.org/dict-mars-response-rates | turn9view3 | Opened; response metric and observation limitation |
| S05 | UNEP, Eye on Methane release notes v2.0 (2025-11-15). https://methanedata.unep.org/release-notes | turn9view4 | Opened; integrated data and CSV/JSON export |
| S06 | Allen et al., Artificial intelligence for methane detection: from continuous monitoring to verified mitigation, arXiv 2511.21777v1. https://arxiv.org/html/2511.21777v1 | turn9view5 | Opened; existing operational model and mitigation cases; paper license CC BY-NC-SA 4.0 |
| S07 | IEA, Global Methane Tracker 2025, Overcoming barriers to abatement. https://www.iea.org/reports/global-methane-tracker-2025/overcoming-barriers-to-abatement | turn12view0 | Opened; split incentives, capital, staff and service barriers |
| S08 | World Bank, About GFMR. https://www.worldbank.org/en/programs/gasflaringreduction/about | turn12view1 | Opened; existing finance/technical-assistance service and restricted eligibility |
| S09 | World Bank, Turning Waste into Value (2026-01-05). https://www.worldbank.org/en/brief/2026/01/05/flaring-and-methane-reduction-examples | turn12view2 | Opened; existing repair cases and savings-replenished facility |
| S10 | PRISM, DOI 10.1039/D6DD00004E. https://pubs.rsc.org/en/content/articlehtml/2026/dd/d6dd00004e | turn11search23 | Search result read; page 403. Do not treat as full-text audited |
| S11 | AEGIS, arXiv 2607.15620. https://arxiv.org/abs/2607.15620 | turn11academia31 | Search abstract read; page open disabled. Do not rely on unverified performance numbers |
| S12 | UNEP, August 2026 MARS snapshot metadata. https://wedocs.unep.org/items/40527a43-6a3b-45a2-a268-6bcf0fd731d9/full | turn12view5 | Metadata opened; actual PDF not read. Rights listed CC BY-NC-ND 3.0 IGO; do not assume commercial redistribution rights |

## Search history and rejected routes

1. Broad current autonomous laboratory/reproducibility and measurement-interoperability searches. Rejected a generic science-agent registry because recent work directly addresses it.
2. Protocol transfer and public satellite ground-truth searches. Rejected another methane detector as an obvious duplication of deployed MARS-S2L.
3. Exact titles for protocol translation, MARS-S2L and SiLA. Identified the mature/expert baselines and LAP's status.
4. UNEP MARS response and mitigation-data searches. Identified the distinction between feedback and cessation plus downloadable data.
5. Existing methane finance and protocol validation searches. Identified GFMR's existing repair-finance loop and PRISM/AEGIS; narrowed both opportunities rather than claiming their ingredients as new.

No candidate was selected on numerical advantage. No simulated result was generated. The next research budget should be conditional on evidence of a still-unserved scope.
