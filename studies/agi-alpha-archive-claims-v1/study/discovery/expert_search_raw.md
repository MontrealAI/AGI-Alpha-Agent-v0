# AGI ALPHA — independent E search arm

Date: 2026-10-27. Scope: independent expert discovery; no other arms' material was inspected. Exactly six web search queries were issued. Primary research and its linked open-data reference were used. No spending, publication, outreach, or external mutation occurred.

## Result and confidence

**One conditional productive-instrument candidate merits a small falsification experiment. No novel scientific method or commercially validated unmet need was established.** Three other lines were rejected as headlines because the strongest retrieved approaches already cover the proposed transformation. The surviving candidate also has substantial prior art; its contribution would have to be demonstrated in the cost and faithfulness of constructing scientific uncertainty models from real archives, not in inventing certain-answer semantics.

The conditional candidate is an **archival measurement instrument that answers a scientific question while leaving ambiguous records unresolved**. It reports a conclusion only when it holds for every admitted transcription, semantic interpretation, and calibration history. Otherwise it produces conflicting admissible histories. This could unlock useful measurements from irreplaceable archives before complete transcription is affordable or possible.

An exact finite construction was executed locally. It establishes the conditional mathematical mechanism and an important negative control. It establishes neither real-world extraction quality nor originality nor willingness to pay.

## Starting from restrictions

The initial search did not start with a supplied application. It considered restrictions that block valuable outcomes:

1. A historical observation cannot be repeated, and an ambiguous digit cannot honestly be replaced by a confident guess.
2. Confidential or incomplete data cannot support an arbitrarily precise causal answer.
3. Internal physical states may be inaccessible to measurement, and a learned simulator cannot be assumed correct in a new regime.
4. Identical or similar analytical signatures cannot be made into unique chemical identities by increasing a classifier's confidence.

The common resource is structured redundancy: relations among measurements, known symmetries, scientific equations, and orthogonal chemical reactions. Available capabilities include literature retrieval, multimodal interpretation, executable program generation, and deterministic finite verification. The proposed role of the frontier model is to construct and critique a representation of these relations. It does not replace the verifier or establish that its interpretation set contains reality.

## Candidate 1 — scientific claims from unresolved archival measurements

**Disposition: conditional candidate; proceed only to the bounded experiment below. Originality confidence: low to moderate. Commercial confidence: low. Mechanism confidence within an explicitly finite model: high.**

### Beneficiary and productive value

Climate and environmental historians, observational-science groups, and institutions preserving old laboratory records may need a specific defensible measurement from a large archive, while complete transcription is unaffordable. The valuable output is a reusable, source-grounded scientific statement with an auditable uncertainty envelope. Examples include a bound on a month's rainfall, the number of recorded days exceeding a threshold, or whether two period means differ by more than a prespecified amount. The instrument must distinguish statements about the recorded observations from statements about the physical climate, which additionally require sampling, station, and instrument assumptions.

The unmet-need hypothesis is: some scientifically useful questions are stable across unresolved source ambiguity, but current acquisition workflows often spend effort reconstructing the whole table before assessing this stability. This is a hypothesis to test with users, not an established market fact.

### Specific prior art and its limitation

Vercruysse et al. evaluate human-assisted extraction of handwritten climate tables and supply a labeled Cobecore validation set. Their workflow addresses recognition and table reconstruction, with experts supplying context and corrections. They also discuss source arithmetic errors, so a written total must not automatically become unquestioned ground truth. [S1]

The strongest mathematical baseline is **certain answers over incomplete databases**. Feng et al.'s AU-DBs preserve bounds through relational operations and aggregation. Their paper explains C-tables with shared variables and global constraints, and approximate translations that lose tightness. Exact C-table reasoning can reproduce this run's example. [S2]

The specific unresolved practical issue is deriving a sufficiently inclusive, source-linked model of glyph, layout, unit, date, calibration, and source-error uncertainty at less expert cost than full reconstruction. Merely combining OCR with a solver is insufficient evidence of a new contribution.

**Named strong baselines:** S2 describes **Mimir** and **Vizier**'s uncertainty-exposing cleaning lenses, with virtual C-tables and symbolic attributes. These are historically documented capabilities, not a claim about current products. The proper baseline already retains alternative repairs. Ordinary constrained optimization of q over those worlds computes the proposed scalar bounds. Therefore an LLM front end, provenance wrapper, or review flow does not itself earn a new scientific headline. The toy tests established dependence-aware reasoning, not failure of these baselines.

### Actual connection discovered in this search

The link is between archival metrology and program verification's possible-world semantics. Instead of resolving every ambiguous observation, one can ask whether the requested scientific statistic is invariant over the remaining possibilities. Shared nuisance variables matter: a calibration offset can cancel in a difference even when individual absolute readings remain uncertain. Generic independent intervals can lose that cancellation.

A further hypothesis is to treat internally redundant archive entries as fallible measurement checks, analogous to error-detecting codes, while allowing errors in the checks themselves. This is **not** claimed as a new coding-theory result. A source total or formula must remain an observation with its own error model, rather than being elevated to an infallible constraint because it is convenient for decoding.

### Transformation witness and preserved obligations

Let E be the source evidence and W(E,A) the explicit set of admissible histories under documented assumptions A. A history includes transcription alternatives, row/column assignments, units and dates, shared calibration variables, and permitted source errors. For a requested quantity q, compute an enclosure [L,U] containing q(w) for every w in W. A threshold claim q > t can be certified only if L > t. If the truth value differs across histories, return two actual witnesses.

The crucial inclusion obligation is that the true history belongs to W. A solver verifies implications from A; it cannot verify that the model's reading of an old page is exhaustive. A low-probability or missing OCR alternative must not be silently removed. Inaccessible entries need broad declared domains or an explicit inconclusive result. Physical plausibility constraints cannot simply delete rare extreme events. Unit, date, and calibration changes must be modeled whenever evidence leaves them open.

Each result should retain source crops, coordinate links, variable domains, every assumption, proof/checker inputs, bounds, and counterexamples. Contradictory source entries must produce an unsatisfied-assumption report or an expanded error model; an empty possibility set must never yield a vacuous scientific certificate.

### Why now

The verified resources are a public annotated climate-table benchmark [S1], established uncertainty-query semantics [S2], and the presently available ability to generate and execute exact small programs. The timing hypothesis is that multimodal agents can reduce the expensive semantic-model construction step across heterogeneous pages. This run did not measure that ability on the benchmark, and the mathematical ingredients substantially predate current agents.

### Executed exact finite construction

Files:

- `expert_discovery_verify.py` — deterministic Python verifier using exact rational arithmetic.
- `expert_discovery_exact_result.json` — bounds and extremal witness histories.

The synthetic source has eight readings. Every reading has two unresolved digit interpretations, separated by 0.6 measurement units. The instrument's calibration is one of -0.4, 0, or +0.4 units. At most one source entry may also contain a ±0.1-unit error. The requested claim is that the late-period mean exceeds the early-period mean by more than 0.35 units.

| Model | Histories exhaustively checked | Exact change interval | Result |
|---|---:|---:|---|
| Calibration shared across periods | 13,056 | [3/8, 13/8] | Claim certified; all eight glyph ambiguities remain unresolved |
| Calibration independently uncertain by period | 39,168 | [-17/40, 97/40] | Claim not certified; actual conflicting histories returned |

All assertions passed. The negative control shows that the desired conclusion disappears when the shared-calibration assumption is withdrawn. This prevents the demonstration from silently treating cancellation as a fact about real instruments. It also shows why the assumed correlation structure is substantive scientific evidence.

This is a synthetic exact construction, not an OCR benchmark, climate finding, measured labor saving, or new theorem. The effect is reproducible with established exact possible-world reasoning.

### Minimal decisive experiment on real evidence

1. Obtain the open Cobecore images and labels at DOI `10.5281/zenodo.12784802`, linked by S1. The citation was verified; the dataset payload was not downloaded during this run because the web fetch failed. Use the provided ten-page validation collection as a bounded first test, then a distinct archive for transfer if it passes.
2. Have an archive scientist specify 30 useful within-page aggregate or threshold questions before seeing system outputs. Do not select thresholds after seeing which answers are easy to certify. Avoid a long-term climate-trend claim unsupported by the sampled pages.
3. Hide gold transcriptions while the agent constructs the admissible histories. A human verifies binding semantic assumptions and can broaden domains. Log all minutes and interventions, including calibration and layout interpretation.
4. Compare against the strongest available complete-transcription workflow with expert review, a generic exact C-table/solver supplied the same representation, and simple independent bounds. The exact C-table baseline is expected to agree mathematically; the proposed advantage must be total construction effort or previously unusable scientific output, not a solver win against a deliberately weak baseline.
5. Require zero false certificates on this bounded gold set, explicit disclosure of any gold reading excluded by W, at least one expert-valued nontrivial answer while substantial ambiguity remains, and a prespecified material reduction in total expert time. A suggested go/no-go target is a twofold time reduction at matched evidentiary obligations; this target is a design choice, not an observed effect.
6. Inject column shifts, unit changes, nonshared calibration, and mistaken source totals. The instrument must expand uncertainty or become inconclusive. Detecting only single-cell OCR errors is not enough.

**Kill conditions:** true interpretations are routinely omitted; verified domains are too broad to answer useful questions; domain construction costs as much as transcription; the buyer primarily needs a general clean dataset; or a straightforward existing uncertainty-database workflow performs equally well with equal effort. Under those outcomes, this is routine engineering and should not headline AGI ALPHA.

### Customer participation and pricing mechanism

An archive owner supplies permitted scans and available metadata. A domain scientist chooses the questions and defines what scientific use would justify the effort. An independent reviewer checks a blinded sample and the binding assumptions. No participant was contacted in this run.

A sensible proposed mechanism is a fixed fee for an audited question batch, including inconclusive outcomes, rather than payment for positive conclusions. Use the customer's measured cost of full transcription and verification as the comparison; a pilot fee could be capped at an agreed fraction of that cost. This is a proposed incentive design, not verified pricing or demand. A paid continuation should require the customer to accept the scientific utility of the output and the observed labor economics.

### Successor inheritance

The reusable asset is an evidence model and verifier: source hashes and crops, semantic alternatives, shared nuisance variables, error bounds, user-approved queries, exact or conservatively enclosing calculations, assumption provenance, failed certificates, and actual counterexample histories. Add the blind benchmark, all costs, and the falsification cases. A successor can rerun a claim, weaken an assumption, transfer a validated source schema, or discover which new evidence matters without depending on a predecessor's prose or confidence.

## Candidate 2 — causal answers from aggregate or unavailable individual data

**Disposition: reject as a novelty headline.**

Beneficiaries would be evidence-synthesis groups that cannot access raw individual records. The potential value is a conservative causal bound without fabricating microdata. The proposed connection was to compile aggregate evidence and scientific assumptions into a finite/polynomial model and return effect bounds with counterexample data-generating processes.

However, Duarte et al.'s automated causal-bounding approach already accepts incomplete or mismeasured discrete evidence, derives polynomial programs, and provides valid bounds during computation plus an explicit sharpness guarantee. That directly occupies the proposed central transformation. Its computational and assumption-elicitation limitations do not make a generic agent wrapper a scientific discovery. [S3]

**Obligation-preserving witness:** keep every data-generating process consistent with the declared graph, evidence, and assumptions; optimize the estimand over that set. The guarantee is conditional on those assumptions and on valid treatment of sampling uncertainty. No raw-data invention is needed.

**Why now / discovered connection:** agents may help translate heterogeneous published summaries into the established formalism, but no distinct new instrument was identified. The newly noticed connection is useful automation, with substantial predecessor ownership.

**Minimal decisive experiment:** a binary treatment/outcome example with exact finite response types; compare results and setup effort with autobounds under the same constraints. Introduce missingness and mismeasurement. Matching the existing bounds proves implementation correctness, not novelty. A credible successor candidate would require an independently valuable inference that the established system cannot express or deliver.

**Customer and price:** an evidence group supplies estimands and assumptions and reviews outputs; a fixed audited-analysis fee avoids incentives to narrow bounds artificially. No demand or price was established.

**Inheritance:** executable estimand definitions, evidence provenance, constraint translation, exact finite countermodels, inference tests, and the explicit record that ordinary automated partial identification is prior art.

## Candidate 3 — scientific observables that eliminate inaccessible nuisance fields

**Disposition: reject as presently formulated; no adequately novel gap isolated.**

Beneficiaries would be experimentalists who can measure some fields but not internal pressure, forcing, or hidden sources. The value would be a physical-law test based only on accessible measurements. The contemplated connection was automatic symbolic elimination plus formal verification: synthesize an integral observable that cancels arbitrary nuisance terms, instead of reconstructing unmeasured states.

Reinbold et al. already combine physical constraints, weak formulations, and symbolic regression to infer dynamics with unmeasured pressure and forcing. Their treatment requires problem-specific choices of weight functions and latent-variable structure; this is a real limitation, but automatic generation of such choices has not been shown here to exceed established mathematical engineering. [S4]

Strouwen and Micluţa-Câmpeanu additionally study experimental design to discriminate plausible missing-physics models. Kötz et al. combine learned dynamics, symbolic regression, and counterexample-driven validation. Accordingly, “an agent designs a revealing experiment for a surrogate” is also an occupied headline. [S5, S6]

**Transformation witness:** for an exact finite system y = Aθ + Bz, any vector w with wᵀB = 0 yields wᵀy = wᵀAθ independent of arbitrary nuisance z. Require wᵀA to retain sensitivity to the target. In differential systems the corresponding integration-by-parts and boundary obligations must be explicitly verified. Merely finding a nullspace is not a new scientific contribution.

**Why now / discovered connection:** an agent might translate a scientist's equations and sensor restrictions into a verified annihilation problem. The key unresolved issue is whether this offers useful observables outside existing expert constructions, unknown-input methods, and weak-form discovery. This run did not research that complete neighborhood; novelty cannot be claimed.

**Minimal decisive experiment:** exact rational matrices with hidden-source channels; automatically produce a witness or an impossibility certificate, compare with a standard nullspace method, then try a held-out weak-form PDE with boundary terms. Equal output from ordinary linear algebra kills a novel-method claim. No such comparison was executed here.

**Customer and price:** a research group supplies sensor and boundary constraints and evaluates a blind observable; a fixed verified-assay-development fee could fund work if a usable new measurement results. Physical deployment requires the group's participation. No paid demand was established.

**Inheritance:** equations, derivations, observability conditions, proof artifacts, counterexamples showing failure when a boundary assumption changes, and validated measurement operators. An agent's plan alone is insufficient.

## Candidate 4 — chemistry-generated fingerprints for ambiguous metabolites

**Disposition: reject the broad headline; any narrower proposal needs a new prior-art search and experimental chemistry.**

Beneficiaries are analytical laboratories confronting molecules whose ordinary mass signatures do not uniquely identify structure. The potential value is reliable structural information without purchasing a standard for every unknown. The contemplated connection was to treat derivatization reactions as experimental queries on a molecular hypothesis set and synthesize a discriminating reaction sequence.

MCheM already combines orthogonal post-column reactions, a shared mass-spectrometry representation, and downstream annotation. It validates three reactions on 359 standards. Its reported reactivity false positives and some degraded downstream rankings matter: reaction evidence cannot be treated as an infallible logical oracle. [S7]

A separate experimental study compares predicted fragment structures with infrared ion spectroscopy and finds serious disagreement for its tested set. This warns against promoting a predicted fragmentation graph to a physical proof. It does not imply that every annotation algorithm is useless or that the result generalizes to all compounds. [S8]

**Transformation witness:** retain each candidate whose experimentally justified reaction-response set includes the observations, including false reaction and nonreaction possibilities; assert identity only if the remaining admitted set is a singleton. This is conditional on candidate completeness and the reaction model. Out-of-library molecules cannot generally be guaranteed detectable by a finite candidate decoder.

**Why now / discovered connection:** current multiplexed chemistry creates new experimentally observable information. An error-correcting-code perspective could assess whether a panel has enough independently measured response separation to tolerate a stated number of failures. But no search in this run established originality for that connection, and computing extra logical parity bits from the same three measurements would not create independent physical evidence.

**Minimal decisive experiment:** use the published standard structures and measured reaction outcomes, hide identities, and compare a robust finite-set decoder against MCheM's established filtering. Include false responses, close isomers, and withheld candidate structures. A finite codebook alone can prove conditional distinguishability or its failure; it cannot validate a reagent's real-world selectivity. A genuinely new contribution would need either additional physically demonstrated independent channels or useful robustness beyond established methods.

**Customer and price:** the lab selects an identification problem, supplies instrument access, and runs blinded standards; price by independently validated sample batch or validated assay, with inconclusive outcomes included. No chemistry was ordered or performed here.

**Inheritance:** candidate structures, measured reaction outcomes including failures, instrument conditions, response uncertainty sets, distinguishability counterexamples, and baseline comparisons. Synthetic reaction predictions must remain clearly distinguished from observed chemistry.

## Exact query log

All six were issued through the stronger web search engine; no additional search queries were issued. Subsequent operations only opened or searched within already found primary papers and their explicit data links.

1. `site.arxiv.org automatic causal bounds aggregate data partial identification polynomial optimization autobounds`
2. `site.nature.com mass spectrometry structure elucidation ambiguity isomers identification limitations orthogonal measurements`
3. `site.arxiv.org scientific data digitization historical records uncertainty OCR constraints weather observations ambiguity`
4. `site.arxiv.org certified reduced order model missing physics falsification conservation laws experimental data symbolic regression`
5. `"certain answers" OCR scientific historical data uncertainty`
6. `"mass spectrometry" "experimental design" "isomers" identification chemical reactions`

## Primary evidence ledger

- **S1.** Vercruysse et al., *Human-in-the-loop tabular data extraction methods for historical climate data rescue*. Published online 8 May 2025, IJDAR volume 29 (2026). [Paper](https://link.springer.com/article/10.1007/s10032-025-00524-y). Relevant evidence: heterogeneous handwritten-record difficulty, expert-assisted extraction, and the labeled Cobecore dataset DOI. The source also shows why an inconsistent historical total may itself be wrong. Data reference: [10.5281/zenodo.12784802](https://doi.org/10.5281/zenodo.12784802). Payload access failed in this run.
- **S2.** Feng, Huber, Glavic, Kennedy, *Efficient Uncertainty Tracking for Complex Queries with Attribute-level Bounds*, 2021. [Primary preprint](https://arxiv.org/abs/2102.11796); [full text](https://arxiv.org/html/2102.11796v1). Relevant evidence: bounds-preserving uncertain queries including aggregation; C-tables with global conditions; approximate translation can lose tightness. This is strong prior art against claiming the candidate's core reasoning as new.
- **S3.** Duarte, Finkelstein, Knox, Mummolo, Shpitser, *An Automated Approach to Causal Inference in Discrete Settings*. [Primary preprint](https://arxiv.org/abs/2109.13471); [published full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11566246/). Relevant evidence: general discrete causal bounds, incomplete and mismeasured evidence, valid interim bounds and sharpness guarantees.
- **S4.** Reinbold et al., *Robust learning from noisy, incomplete, high-dimensional experimental data via physically constrained symbolic regression*, 2021. [Primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC8163752/). Primary search extraction supplied the abstract and relevant discussion; later full-page opening encountered an access challenge. Relevant evidence: weak-form elimination of latent pressure and forcing, with problem-specific domain knowledge required.
- **S5.** Strouwen and Micluţa-Câmpeanu, *Experimental Design for Missing Physics*. [Primary preprint](https://arxiv.org/abs/2604.01231). Repository records submission 21 March 2026 and journal reference IFAC-PapersOnLine 59(6), 481–486 (2025). Relevant evidence: sequential discrimination of symbolic candidate missing-physics models.
- **S6.** Kötz, Sjöberg, Åkesson, *Optimal Control-Based Falsification of Learnt Dynamics via Neural ODEs and Symbolic Regression*. [Primary preprint](https://arxiv.org/abs/2602.00031), submitted 18 January 2026. Relevant evidence: candidate counterexamples validated on the original system, with surrogate refinement for spurious traces.
- **S7.** Vitale et al., *Enhancing tandem mass spectrometry-based metabolite annotation with online chemical labeling*. Nature Communications 16:6911 (2025). [Primary PDF](https://www.nature.com/articles/s41467-025-61240-z.pdf). Relevant evidence: integrated orthogonal reaction/annotation instrument; 359 standards, 139 detected derivatization events and five classified false positives in that validation. These figures describe the paper's set, not universal reaction-error rates.
- **S8.** *A spectroscopic test suggests that fragment ion structure annotations in MS/MS libraries are frequently incorrect*. Communications Chemistry (2024). [Primary article](https://www.nature.com/articles/s42004-024-01112-7); [PDF](https://www.nature.com/articles/s42004-024-01112-7.pdf). Relevant evidence: experimental infrared checks of a bounded sample of predicted fragment structures. Search extraction was available; later HTML opening failed.

## Explicit limits

The six-query search is not an exhaustive novelty review. Scientific and customer-value statements marked as proposals or hypotheses are inferences, not facts established by the cited papers. The exact finite construction demonstrates what follows from specified assumptions; it does not establish those assumptions for an archive. None of the four proposals has a verified customer, a validated price, or evidence of superhuman discovery. The appropriate next action is the bounded Candidate 1 falsification experiment, with permission to reject the candidate if its value reduces to familiar engineering.

Arm frozen after the six-query search and exact construction. The report's strongest-baseline clarification uses S2 already read during the arm; no new search was made. Refinement against any earlier project or other arm is outside this independent report.
