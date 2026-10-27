# Round 2 science opportunity: executable scientific evaluation contracts

**Decision date:** 27 October 2026. **Status:** selection dossier, not an implementation or result. **Recommendation:** **NARROW / GO for a bounded service-construction experiment**, with the stopping gates below. This is my highest-ranked science direction from this bounded search. It has public scientific records and inspectable implementations, two independent needs, and a consequential expert service to reproduce. It does not yet establish demand, superior audit quality, labor savings, or a new scientific discovery.

**The useful output:** a re-executable assessment of whether a particular scientific model comparison answers its stated question, including concrete counterexamples when it does not. The proposed retained instrument would connect the scientific object being distinguished, the observations available at each stage, the provenance of reused components, and the calculation of the final metric. Its value would have to come from reducing the construction and correction burden on unfamiliar work while preserving the question.

The opportunity is narrower than “automate peer review.” It also does not require a new molecular model, new crystal generator, novel deduplication algorithm, or proof that no prior tool does related work.

## 1. Two independently documented needs

### Need M: trustworthy evaluation of molecular identification pipelines

The June 2026 MassSpecGym audit reports evaluation issues in 17 of 26 papers, spanning leakage, shortcuts, and implementation/metric divergence. Its v1.5 response includes corrected components, pinned evaluation and an LLM-assisted submission review. Appendix A.8 explicitly retains maintainer judgment about implicit formula use, pretraining exclusions and reproducibility. This is evidence of a substantive expert task **and** strong prior art, not an unserved market. [M]

**Proposed original-purpose job:** given an actual repository, declared component provenance, candidate structures and measured tandem mass spectra, assess a stated retrieval/generalization claim. A mission must specify whether molecular formula is available, which structures are out of training scope, and what molecular distinctions the output promises. The deliverable is executable evidence about that claim, not a more flattering leaderboard score.

**Prospective beneficiary:** a benchmark maintainer, scientific model developer, research sponsor, or analytical research group comparing reusable components. These are potential counterparties inferred from the task; none has been interviewed or agreed to pay.

### Need C: meaningful comparison of crystal structure generators

The independent NeurIPS 2025 crystal audit documents duplicate representations, problematic polymorph splits and inadequate match-rate interpretation. It supplies corrected datasets, chirality-sensitive variants and METRe/cRMSE evaluation; the paper links CC-BY 4.0 data and MIT-licensed OMatG/pymatgen code. Those remedies belong in the expert baseline. [C]

**Proposed original-purpose job:** assess a generator's ability to recover structures or phases for a specified composition-generalization mission using actual public crystal records. The mission must say whether chirality, different polymorphs and alternative unit-cell representations are distinct outcomes. These are computed/reference structures, not evidence that a new material was synthesized or has useful physical properties.

**Prospective beneficiary:** a computational materials group, model developer, benchmark maintainer or research sponsor deciding which model to use or develop. Again, willingness to pay is a hypothesis.

These needs originate in separate scientific communities and concern different useful outcomes. Their common structure is a research hypothesis found during this search: an evaluation's validity depends on a purpose-specific identity relation and allowed information flow, not merely on clean file formats or a final metric implementation.

## 2. Ranked opportunities

| Rank | Bounded offering to investigate | What must actually be constructed | Why it is demanding | Decision |
|---|---|---|---|---|
| 1 | Re-executable qualification of a composed scientific evaluation pipeline, starting with Need M and transferring to Need C | A mission contract, source-traced dependency representation, executable domain adapters, counterexperiment generator, and independent acceptance checks | Meaning must survive reused models, derived observations, alternative representations, changing task boundaries and incomplete provenance | NARROW / GO for a bounded test |
| 2 | Crystal identity and metric qualification as a standalone service | An adapter that turns a specific materials question into permitted transformations and independently checked metric comparisons | A universal canonicalization policy can erase distinctions the new mission needs | GO as a fresh transfer/negative-control workload; weaker standalone flagship |
| Screened out | New de novo molecular generation from spectra | A substantially better identification system | Strong current methods and their training requirements exceed what this search establishes; benchmark improvement alone would not confirm physical discovery | Do not select for this edition |

Rank 1 is preferable because its output is a useful expert assessment that can be executed without new laboratory measurements or speculative biological ground truth. Rank 2 is especially useful as a transfer test: the recipient must re-earn the meaning of “same object,” rather than inherit the molecular adapter's answer. Neither rank promises positive Alpha.

## 3. Strong current prior-art challenge

MassSpecGym already provides data loading, transforms, tasks, metrics and reference implementation scaffolding. The repository is MIT licensed. The available default branch resolves to commit `f259fe3780d5bd227fc6ece36ce6f397c2eef716`, labelled v1.5 part 1/2; it includes a canonicalization repair, validation notebook and loader for `MassSpecGym1.5.tsv`. Its fetched tree has only `basic_ci.yml` under workflows and no audit/review paths. Thus the paper's agentic review is **documented prior art**, while availability of that complete workflow at this pinned default-branch snapshot is **not verified**. Do not pretend that a missing fetched file makes the published method novel. [R]

The ordinary expert configuration must receive the published audit, correction scripts, ordinary notebook tools and the documented agentic-review procedure. If the complete upstream agentic implementation is available when selected, use it directly. Otherwise disclose and freeze a faithful implementation of the published procedure for E; do not quietly use a weak checklist.

For crystals, corrected data and published metrics are already available. Running those exact files on their intended task is a negative control. If that is the recipient's whole need, the efficient existing path may erase the proposed advantage.

Additional search-screened prior art includes LeakageDetector, a code-analysis plugin, and a June 2026 preprint describing limits of blind leakage identification from model outputs. These were screened at abstract level only; they support caution, not a claim of comprehensive prior-art coverage. [S1–S2]

**Residual hypothesis:** unfamiliar pipelines and changed scientific purposes still require people to connect source-level evidence, object identity, component provenance and executable counterexperiments. A retained, mission-conditioned instrument may lower that burden. This is an inference to test, not a finding that incumbents cannot do it.

## 4. The substantive reusable instrument

The proposed artifact is an executable package, not a prose summary or leaderboard dashboard. Its construction target is:

1. **A mission-specific evaluation contract.** Record the useful scientific question, permissible inputs, outcome identity, generalization boundary, metric settings, and the claims that cannot be established from the supplied evidence.
2. **A source-traced dependency representation.** Bind each data preparation step, learned component and derived field to files and versions. Distinguish observed labels from inferred or imputed fields. Represent unknown provenance explicitly.
3. **Executable identity and admissibility adapters.** Reuse existing scientific libraries. A contract chooses the relevant equivalences and exclusions; generic code must not silently impose one domain's choices on another.
4. **A counterexperiment generator.** Produce purpose-preserving transformations and targeted interventions on information available to a pipeline. Every generated test must explain why the mission permits it and what failure would mean.
5. **Independent replay and acceptance receipts.** Include raw outputs, canonical metric calculations, counterexample records, uncertainty, residual unresolved claims and exact dependency identities. A different process should be able to reproduce each claimed discrepancy.
6. **A qualified transfer package.** Retain stable code, schemas, provenance, cost and limitations. Re-evaluate the recipient's semantics and authority separately.

The ambitious part is constructing the bridge between a useful scientific question and executable evidence across multiple components and representations. Standard chemistry and crystallography algorithms remain building blocks. No claim of a new equivalence algorithm, universal formal verifier or general leakage detector is needed.

### What discovery is and is not supplied

This dossier supplies two source-grounded need families and a candidate construction hypothesis. It does not supply observed buyers, compatible commitments or successful economics.

A selected experiment should give each enterprise the source records, independent need statements, available tools, budget and acceptance requirements. Ask it to identify repeated work, propose a reusable construction and choose whether coordination is worthwhile. Do not hand it the finished dependency schema and later claim autonomous discovery.

If the researchers prescribe the schema or countertest grammar to bound the edition, record those as supplied structures. The observed contribution would then be construction, expert operation, correction and transfer. Selecting a known correction from these papers is calibration; it is not a new scientific discovery.

## 5. Transformation witness to register before execution

| Witness element | Proposed claim |
|---|---|
| Original useful purpose | Obtain an executable assessment of whether a particular scientific comparison supports its stated generalization claim |
| Binding restriction | Treating benchmark validity as a property of the final score or isolated dataset leaves cross-component information and purpose-dependent identity judgments to repeated manual reconstruction |
| Why removable | Source code, record identities and permitted transformations can sometimes be represented and replayed explicitly; missing provenance can remain an unresolved obligation |
| Replacement | A mission-bound contract compiles permitted identity relations, provenance checks and executable counterexperiments, reusing established scientific functions |
| Realization | Reproduce an assessment from actual public records and code; emit concrete record-level witnesses and re-run the original pipeline/metric wherever scope permits |
| Falsifier | The artifact changes the scientific question, merges distinctions the mission requires, makes unsupported safety claims about hidden provenance, fails independent replay, or costs as much as the available expert path on fresh jobs |

A counterexample to an evaluation does not prove that its underlying model has no scientific value. Conversely, no discovered counterexample does not prove the absence of all leakage or bias.

## 6. Decisive executable experiment possible without a new laboratory

### Stage 0: short acquisition and baseline gate

Pin upstream code and actual public data before construction. The large corpus, candidate lists and crystal records must be accessible, licensed for the intended use and large enough to exercise the instrument. Verify the expert path first.

Source acquisition in this dossier reached actual MassSpecGym source files and its five-spectrum debug example. The latter is **only an access/format check**, never the study's ceiling or confirmation dataset. Full benchmark files, crystal data and model checkpoints have not been downloaded or run here. The public loader and dataset URLs provide a concrete acquisition path, but runtime and dependency compatibility remain unmeasured.

Stop or narrow if only a toy fixture can be executed, if crucial provenance is inaccessible, or if the agreed job reduces to running an already complete efficient script. Do not promote a proposed acquisition path into an executed result.

### Stage 1: useful jobs and original-purpose acceptance

Use actual records and code in two workload families:

- **Molecular jobs:** a declared retrieval track and a particular composed processing pipeline. The output must identify permitted information, trace available component provenance, run a meaningful spectrum-dependence/candidate-representation check, and reproduce the declared metric. Whether a formula is permitted is fixed by the original job.
- **Crystal jobs:** a specified structure/composition generalization question and actual record/model-output files. The output must distinguish allowed representation changes from changed physical structures, preserve the mission's chirality policy, and reproduce the declared evaluation using established metrics.

The main service is a bounded assessment whose accepted output may be a pass, a reproducible counterexample, or a specifically evidenced unresolved obligation. That deliverable definition is chosen **before results**. It is not a plan-delivery contract relaxed after an inconvenient failure.

The complete acceptance rubric should require traceable inputs, unchanged scientific scope, accurate bounded conclusions, runnable artifacts, and correct handling of positive and negative controls. A persuasive report alone fails.

### Stage 2: calibration, freeze and protected confirmation

Use published failure modes as disclosed calibration examples. All configurations may read the same papers and existing fixes. Freeze the retained method, artifact and evaluation policy before confirmation.

Have a separate evaluator prepare protected jobs from new record subsets, pipeline compositions and changed mission requirements. Include valid jobs, invalid jobs and incomplete-provenance jobs. Distinguish:

- published historical reproductions;
- new combinations or transformations constructed by researchers from real data;
- any naturally occurring repository problem actually found.

The second category supports prospective software/operating-method evaluation, not a claim that new real-world scientific faults were autonomously discovered. Protected answers and future task assignments must remain outside discovery/training context.

A practical proposal is at most six development jobs and twelve confirmation jobs, with one cross-domain transfer recipient, subject to a fixed execution budget. Those counts are proposed workload limits, not power guarantees. Correlated failures across shared components must be reported by family, not counted as independent scientific replications.

### Stage 3: fair configurations and decisive endpoints

| Configuration | Contents |
|---|---|
| H | A scoped human scientific software/evaluation service, priced from estimated hours unless a matched quote becomes available |
| U | Representative competent ordinary use of the same frontier model, with normal tools and access to relevant documentation |
| E | Published expert corrections, standard libraries, notebook/replay practice, and the strongest actually available/documented agentic audit workflow |
| E+ | The same E resources plus the frozen retained instrument |
| Recipient control | What the fresh recipient can already do with existing corrected data and tools |
| Sharing control | An ordinary file/library package with identical artifact contents, permissions and retrieval information |

Measure accepted assessments at matched resource budgets, then full costs at matched acceptance. Count construction, failed attempts, retries, runtime, tokens, tool use, residual expert judgment and customer effort. Score false reassurance and incorrect rejection separately. “Number of warnings” is not a useful success metric.

If no published per-example predictions/checkpoints can be obtained within budget, do not invent them or train a giant replacement. Narrow to an explicit dataset/evaluation qualification service with actual record-level witnesses. A claim about changed model ranking requires actual reproduced predictions.

**Prospective feasibility crossing:** choose a delivery budget and turnaround requirement before confirmation. A new offering is feasible only if the full E+ assessment meets acceptance and that fixed bound while E does not. If both qualify, report better or equal economics. The commercial model must also count the retained artifact's construction and upkeep over the observed workload.

## 7. Commercial construction that does not assume demand

A possible paid offering is “re-executable qualification of this specified scientific evaluation pipeline,” with a fixed scope, delivered artifacts and a documented unresolved-evidence policy. It does not sell scientific truth, regulatory certification, guaranteed discovery or a favorable conclusion.

Prospective buyers choose independently among internal expert work, free benchmark tools, a narrower report, deferral and decline. Their need definitions may be incompatible; a molecule-specific contract need not subsidize a crystal-specific adapter.

The common engine could be financed by a development milestone with optional later adapters. Any shared arrangement should be conditional on independently expressed participation, compatible rights and actual common work. Possible terms are:

- a small scoped assessment first, which may conclude that the existing free tool is sufficient;
- a priced construction milestone only after the source/access/acceptance gate;
- customer-specific delivery milestones with clear cancellation, partial-delivery and refund terms;
- licenses to generic components, while customer data, unpublished model weights and protected evaluation jobs remain private;
- no automatic right to execute a recipient's infrastructure.

A coordination mechanism could pool the cost of a generic provenance/contract engine while each participant retains a separate mission adapter and acceptance test. That mechanism is useful only if its additional coordination, serving and rights costs are lower than independent construction. Test technical artifact alone, ordinary coordinated purchasing alone, and their combination. A conventional expert service must be allowed to offer the same arrangement.

**Illustrative H parameterization, explicitly assumed:** 10–30 expert hours at USD 150–300/hour gives USD 1,500–9,000 for a well-scoped assessment. This is a sensitivity range, not a sourced market price, quote, willingness-to-pay estimate or promised saving. No sales or collections exist.

Keep paid delivery and necessary learning in A; incremental qualification, retention, rights, sharing and maintenance in B; optional further R&D/Gym work in C. Developer time, rejected audits and customer support count. Deposits may finance work but are obligations until earned; expected profit does not establish sufficient liquidity.

## 8. Transfer, retention and what could become possible next

A useful lineage would be:

**Molecular pipeline need → source-traced executable evaluation contract → qualified assessment → retained generic engine → fresh materials recipient → new purpose-specific adapter → accepted assessment or honest refusal.**

The scientific definitions must be freshly qualified. An identity policy acceptable for one measurement may be wrong for a chirality-sensitive recipient. The successor inherits source, algorithms and evidence of generic behavior; it does not inherit acceptance, permission, or the right to re-use protected records.

The next productive possibility is a new, sufficiently affordable assessment or data-reuse job, not an imagined discovery pipeline. Admission can be rejected if construction costs, specialist adaptation, missing provenance or maintenance dominate. Useful paid assessments can still be a commercial success even if optional shared retention is uneconomic.

## 9. Selection decision and limits

**Go:** a bounded construction/transfer study of an executable expert assessment service, after data and E-baseline preflight.

**Narrow:** preserve separate scientific questions and use mature domain tools. Treat full agentic-audit code availability, per-example outputs and nontrivial corpus runtime as acquisition gates. Claims about repaired evaluation are distinct from claims about improved science.

**No-go:** “first AI scientific auditor,” “autonomous molecular discovery,” “new crystal prediction algorithm,” a five-record flagship, guaranteed compounding, universal leakage certification, or revenue inferred from avoided research expense.

The decisive failure could be commercially valuable information: existing v1.5/OMatG workflows may already make the job cheap, or cross-domain adaptation may consume every saved hour. This direction is still a legitimate experiment because the useful need, strong comparator and executable acceptance artifact can be specified before observing those results.

## 10. Source record and bounded search

Five search queries were used; no additional search sweep was performed. Three primary source families were examined in depth: the MassSpecGym audit, the crystal audit and the MassSpecGym repository. Reads of source sections and files stayed within those families. Abstract-only leads are identified separately.

- **[M] Hongxuan Liu et al.** *MassSpecGym in the Wild: Uncovering and Correcting Evaluation Pitfalls in AI-Driven Molecule Discovery*, arXiv:2606.19624v1, submitted 17 June 2026. Primary full text: https://arxiv.org/html/2606.19624v1 . Relevant sections: 3–7 and Appendix A.8. Web evidence: `turn97view0`, `turn98view0`. The first direct fetches failed; a subsequent linked fetch succeeded. No reliance on the Hugging Face page's AI-generated summary.
- **[C] Maya M. Martirossyan et al.** *All that structure matches does not glitter*, NeurIPS 2025; arXiv:2509.12178v2, 3 December 2025. Primary full text: https://arxiv.org/html/2509.12178v2 . Relevant sections: 3–4, Appendices A–C. Web evidence: `turn92view1`, `turn94view1`, `turn94view2`. Public data references include https://huggingface.co/datasets/colabfit/carbon-24_unique , https://huggingface.co/datasets/colabfit/carbon-24_unique_with_enantiomorphs , https://huggingface.co/datasets/colabfit/perov-5_polymorph_split . Referenced metric implementation: https://github.com/FERMat-ML/OMatG . Those linked repositories/datasets were not separately audited in depth.
- **[R] MassSpecGym authors' repository.** https://github.com/pluskal-lab/MassSpecGym/tree/f259fe3780d5bd227fc6ece36ce6f397c2eef716 . Default branch and recursive tree read through the GitHub connector on 27 October 2026. Download source declared by its loader: https://huggingface.co/datasets/roman-bushuiev/MassSpecGym . Read and preserved actual MIT license, debug spectrum file, canonicalization script and loader source. Repository acquisition record: `round2_science_sources/massspec_source_manifest.json`.
- **[S1], screened abstract only.** Eman AlOmar et al., *LeakageDetector*, arXiv:2503.14723. https://arxiv.org/abs/2503.14723 .
- **[S2], screened abstract only.** Laurence A. Jacobs, *A prior-free blind detection of information leakage from model predictions*, arXiv:2606.11267. https://arxiv.org/abs/2606.11267 .
- **Other search-screened generation competitors:** MADGEN (ICLR 2025) and *Test-Time Tuned Language Models Enable End-to-end De Novo Molecular Structure Generation from MS/MS Spectra*, arXiv:2510.23746. These screened leads are not performance comparisons conducted by this study.

**Evidence labels:** published findings are sourced; source files and repository tree are observed read-only artifacts; proposed instrument and experiments are researcher/assistant constructions; costs, buyers, participation and financing are hypotheses. No new instrument code, laboratory experiment, training campaign, customer sale or paid service has been executed for this dossier.

