# Evidence reconstruction

## Report A — Final correct recall in Maraver et al. (2022), Experiment 1

**Result:** Retrieval with corrective feedback minus restudy with corrective feedback is **+0.22 in proportion correct**, or **+22 percentage points**. A participant-level Welch reconstruction gives an approximate **95% CI of +0.134 to +0.306**, equivalent to **+13.4 to +30.6 percentage points**. These are derived quantities from the rounded published summaries.

**Report and target.** Maraver MJ, Lapa A, Garcia-Marques L, Carneiro P, Raposo A, *Can we learn from errors? Retrieval facilitates the correction of false memories for pragmatic inferences*, [DOI: 10.1371/journal.pone.0272427](https://doi.org/10.1371/journal.pone.0272427). The target is Experiment 1, the **Correct responses** block of Table 3, **Feedback** row, **Retrieval** and **Restudy** columns under **Experiment 1**. The outcome is each participant’s proportion of correct answers on the final 30-sentence cued-recall test. Correct includes the original wording or synonyms preserving its meaning. The final test followed a one-minute distractor after the intermediate phase, within the same laboratory session; it supplied no feedback. [A1–A3]

**Design and populations.** The report describes 120 University of Lisbon students, randomized to a 2 × 2 between-participant design: retrieval/restudy crossed with feedback/no feedback, with 30 participants per cell. Thus, 60 participants contribute to this target contrast. No participant exclusions are reported for Experiment 1; the reported overall ANOVA residual df of 116 is consistent with all 120 participants in four cells. The 30 sentences are repeated observations within a participant, not 30 independent participants; the participant’s aggregated proportion is the analysis unit. The study selected these sentences for high rates of pragmatic-inference errors. [A2–A4]

During retrieval, students attempted to complete missing sentence fragments. During restudy, they read a fixed mixture of 50% correct and 50% incorrect sentences, described to participants as another person’s recall output; sentence correctness was counterbalanced. This is not a reported pairing of participants for statistical analysis. Both target groups then saw the original correct sentence as feedback. The design therefore supports an independent-groups contrast of final participant proportions, despite repeated item responses and an earlier retrieval assessment. [A2–A3]

| Table 3 input | Mean proportion correct | SD across participants | Participants |
|---|---:|---:|---:|
| Retrieval, feedback | 0.83 | 0.10 | 30 |
| Restudy, feedback | 0.61 | 0.21 | 30 |

Table 3’s footnote explicitly defines its entries as **mean ± standard deviations**, not standard errors. [A1]

**Calculation and uncertainty.** Let R and S denote the two groups. Using their separate variances:

\[
\widehat\Delta=\bar p_R-\bar p_S=0.83-0.61=0.22,
\qquad SE(\widehat\Delta)=\sqrt{0.10^2/30+0.21^2/30}=0.042466.
\]

With \(v_R=s_R^2/n_R\) and \(v_S=s_S^2/n_S\), Welch degrees of freedom are

\[
\nu=\frac{(v_R+v_S)^2}{v_R^2/(n_R-1)+v_S^2/(n_S-1)}=41.509.
\]

Hence \(0.22\pm t_{.975,41.509}(0.042466)=0.22\pm0.085729\). This assumes independent participants and a reasonable approximate t sampling distribution for the difference of mean proportions; equal variances are not required. It does not treat 900 item responses per group as independent binomial observations. The interval concerns participant variation for these study materials, without estimating uncertainty from sampling new sentences.

Both means and SDs are rounded to two decimals. Under conventional nearest rounding, the mean difference alone can differ from 0.22 by almost 0.01; rounding the SDs also changes the CI. The displayed interval is an approximate reconstruction, not an exact recovery of an unpublished interval.

**Interpretation and scope.** Retrieval followed by feedback improved immediate final correct recall relative to this particular restudy procedure with feedback. This is a simple effect within feedback, not the marginal retrieval effect or a conditional error-correction index. A selected Portuguese sentence task in university students does not establish durable classroom learning, product/customer value, or clinical benefit.

**Precise provenance:** All XML locations below refer to `source_packet/pone.0272427.xml`.

- **A1:** `//table-wrap[@id='pone.0272427.t003']`, caption “Memory performance at the final cued-recall test”; Correct responses → Experiment 1 → Feedback → Retrieval/Restudy; its `table-wrap-foot` defines SDs.
- **A2:** `//sec[@id='sec004']/p[1]`, Participants; `//sec[@id='sec006']/p[1]`, Design; `//sec[@id='sec005']/p[1]`, Materials.
- **A3:** `//sec[@id='sec007']/p[2]`, intermediate manipulation and final test; `//sec[@id='sec008']/p[1]`, scoring and participant proportions. The supplied supplementary sentence list also supplies response-coding examples.
- **A4:** `//sec[@id='sec011']/p[2]`, correct-response ANOVA and df; Table 3 supplies the numerical inputs used here.

## Report B — Long-term minus short-term standardized peer-assessment effect

**Result:** The published difference is **0.122 − 0.115 = +0.007 standardized effect units**. **Hold the confidence interval and test for this difference:** the necessary joint covariance is not identified by the supplied summaries and supplement.

**Report and target.** Sun DL, Harris N, Walther G, Baiocchi M (2015), *Peer Assessment Enhances Student Learning: The Results of a Matched Randomized Crossover Experiment in a College Statistics Class*, [DOI: 10.1371/journal.pone.0143177](https://doi.org/10.1371/journal.pone.0143177). The setting is Stanford’s introductory statistics course in autumn and winter terms. The short-term effect concerns unit quizzes following completion of each unit and homework feedback. The longer-term effect concerns corresponding unit material on the comprehensive final examination in Week 11. [B1–B3]

**Design, intervention, and sizes.** Each student received treatment in two of four main units and control in the other two, assigned among TCTC, CTCT, TCCT, and CTTC. Matching first blocked students on gender, race, and previous statistics background, then paired students on other baseline covariates; paired students received complementary randomized sequences. Treatment involved scoring and commenting on three peers’ homework responses and receiving peer feedback. Control involved instructor grading without assessing peers; both groups received solution keys, rubrics, and feedback on the same schedule. Assessors of quizzes/exams were blinded. [B1, B3]

The supplement distinguishes 150 autumn and 240 winter consent-form respondents from the 148 and 239 participants after three opt-outs: **387 participants total**. It reports **322** meeting its compliance criterion of at least 10 of 12 assigned peer-assessment questions. The main paper’s actual outcome-specific analyses use **299 students for quizzes** and **320 for the final exam**, after noncompliance and assessment-completion exclusions. These are repeated-measure student samples, not separate treatment/control arm sizes. Each unit quiz contained six questions; those items and the four units are not independent sample-size multipliers. [B1, B3]

**Estimands and inputs.** The supplement standardizes each assessment using its control-group mean and **SD**, computes each student’s mean standardized score in treated units minus that in control units, and averages these within-student differences, pooling terms. The same approach is applied to final-exam material. These estimate standardized peer-assessment effects among the analyzed complying students, rather than an ordinary two-independent-arm Cohen’s d. [B3]

| Main Table 1 row | Effect estimate | SE of estimate | Outcome-specific n |
|---|---:|---:|---:|
| Short Term (as measured by unit quizzes) | 0.115 | 0.04 | 299 |
| Long Term (as measured by final exam) | 0.122 | 0.04 | 320 |

The caption explicitly labels parentheses as **standard errors**. [B2] The derived difference, +0.007, is in standardized units; it is not a 0.7-percentage-point change in exam scores. With effects rounded to three decimals, their unrounded difference could be approximately 0.006–0.008. The supplement’s coarser Table 6 rounding is not substituted for Table 1.

**Dependence and scoped hold.** For \(\Delta_B=\hat d_L-\hat d_S\),

\[
\operatorname{Var}(\Delta_B)=SE_L^2+SE_S^2-2\operatorname{Cov}(\hat d_L,\hat d_S).
\]

Using the rounded SEs, this is \(0.0032-2\operatorname{Cov}(\hat d_L,\hat d_S)\), or \(0.0032(1-\rho)\). Neither the covariance nor the correlation of the **effect estimators** is reported. The overlapping course cohorts, repeated units, shared assignment sequences, matching, and differing analysis sets preclude assuming independence. Sample counts and the two marginal SEs do not recover that covariance. A linked joint analysis of the student effect contributions, retaining membership, matching, and standardization information, or a reported joint covariance, is needed. Separate tests against zero cannot establish a long-versus-short difference. [B1–B3]

**Interpretation and scope.** The printed longer-term estimate is descriptively 0.007 greater. These sources do not establish improvement, decline, or equality of effects across time. The measures use different assessments and somewhat different analyzed populations. Causal generalization remains conditional on compliance/exclusion, carryover, and standardization assumptions; crossover assignment alone does not prove that post-assignment exclusions are harmless. This course does not establish effects for all learners, educational products, or clinical populations. The two reports are not pooled.

**Precise provenance:**

- **B1:** `source_packet/pone.0143177.xml`, `//sec[@id='sec002']/p[1–5]`: sequences, matching, intervention, assessments, and analysis sizes, respectively.
- **B2:** Same XML, `//table-wrap[@id='pone.0143177.t001']`: the two named rows and caption identifying SEs; `//sec[@id='sec003']/p[1]` confirms outcomes and df 298/319.
- **B3:** `source_packet/pone.0143177.s001.pdf`: §1.1 pp. 1–2 (timing), §1.2 pp. 2–3 and Table 3 (participants), §1.3 p. 3 (questions), §1.4 p. 4 (conditions), §2.1 pp. 5–6 and Table 4 (randomization), §2.2 pp. 7–8 (standardization and estimator), §2.3 p. 8 (marginal inference), §2.4 and §3.1 p. 9 (pooling/outcomes), and §3.2 p. 10 (322 compliance-qualified students). These do not supply the cross-outcome estimator covariance.

Reproducibility: `calculate.py` contains the executable calculation; `calculations.json` records its output. No raw-data effect reanalysis was substituted for the requested printed-summary reconstruction.
