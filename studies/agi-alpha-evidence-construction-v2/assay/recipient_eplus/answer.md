# Evidence reconstruction: two public reports

## Report A — Maraver et al. (2022), Experiment 1

**Target fixed before extraction.** For the University of Lisbon student sample, estimate retrieval with corrective feedback minus restudy with corrective feedback in the participant-level proportion of correct responses on the final cued-recall test. The permissible estimate is a raw difference of the two Table 3 cell means, with participant-level sampling uncertainty. The report is *Can we learn from errors? Retrieval facilitates the correction of false memories for pragmatic inferences*, [doi:10.1371/journal.pone.0272427](https://doi.org/10.1371/journal.pone.0272427).

**Design and population.** Experiment 1 enrolled 120 university students. Both factors—retrieval/restudy and feedback/no feedback—were randomized between participants in a 2×2 design, with 30 participants in each cell. The published participant paragraph's parenthetical counts are awkwardly attached to factor labels; the four-cell interpretation is corroborated by the N=120 ANOVA with residual df=116 and by the supplied Experiment 1 CSV: four cells of 30, with no blank final-correct-proportion entries. No participant exclusion rule is reported for this experiment. [A2–A3]

All participants encoded 30 Portuguese sentences selected for pragmatic-inference potential. Retrieval required completing missing sentence fragments; restudy presented 50% correct sentences and 50% sentences containing pragmatic-inference errors, counterbalanced across participants. Both target groups then saw the original correct sentence as feedback. The final cued-recall test covered all 30 sentences after a one-minute distractor, in the same laboratory session, without feedback. Correct responses included original meanings and acceptable synonyms. Although restudy was described to participants as another person's output, its errors were experimentally constructed: this is not participant-paired yoking. The analysis unit is the participant's proportion, not 30 independent item observations per participant. [A2]

| Table 3 target cell | Participants | Mean proportion | SD of participant proportions |
|---|---:|---:|---:|
| Experiment 1, Correct responses, Feedback, Retrieval | 30 | 0.83 | 0.10 |
| Experiment 1, Correct responses, Feedback, Restudy | 30 | 0.61 | 0.21 |

The table footnote explicitly defines the displayed “±” values as **standard deviations**, not SEs. XML and rendered publisher PDF agree. [A1]

**Derived reconstruction.**

\[
\widehat\Delta=0.83-0.61=0.22,
\qquad SE(\widehat\Delta)=\sqrt{0.10^2/30+0.21^2/30}=0.042466.
\]

A Welch interval permits unequal participant variances:

\[
\nu=\frac{(s_R^2/n_R+s_S^2/n_S)^2}
{(s_R^2/n_R)^2/(n_R-1)+(s_S^2/n_S)^2/(n_S-1)}=41.51,
\]

\[
\widehat\Delta\pm t_{.975,41.51}SE
=0.22\pm2.01879(0.042466)
=[0.13427,0.30573].
\]

Thus retrieval with feedback averaged **22 percentage points more correct responses**, with an approximate **95% CI of 13.4–30.6 percentage points**. This uses independent randomized participants and an approximate t-based sampling distribution for bounded participant proportions; it does not treat individual items as independent trials. It is a direct two-cell reconstruction, not the paper's factorial main effect or conditional error-correction index.

Both means and SDs are printed to two decimals, so the interval is approximate. Under ordinary nearest-hundredth rounding, mean rounding alone permits an underlying contrast approximately 0.210–0.230; those bounds are not a confidence interval. The unused no-feedback marginal is printed as 0.28 although the two printed cell means average to 0.27. That discrepancy is preserved, not repaired or used to change the target cells. [A1]

**Scope.** This supports an immediate laboratory comparison for this fixed sentence set and comparator. Restudy included externally presented misinformation, whereas retrieval generated participants' own responses; their error rates and sources differed. The authors acknowledge these limitations in Experiment 1's discussion. It does not establish lasting classroom benefits, clinical benefit, or product value. [A2]

**Precise primary-source locations.**

- **A1:** `pone.0272427.pdf`, p. 8, Table 3, “Correct responses” block → “Experiment 1” → “Feedback” row → “Retrieval” and “Restudy” columns; table footnote. XML `//table-wrap[@id='pone.0272427.t003']`, including `table-wrap-foot/fn/p`. Engine-expanded coordinates are row 3, columns 1 and 2, zero-based.
- **A2:** `pone.0272427.xml`: Experiment 1, Participants `sec004/p[1]`; Materials `sec005/p`; Design `sec006/p`; Procedure `sec007/p[1–2]`; Statistical analyses `sec008/p[1–2]`; final-test results `sec011/p[2]`; Discussion `sec013/p[2]`.
- **A3:** Author-linked `Error_correction_PI_Experiment_1.csv`, counts cross-tabulated by `CondiçãoRS` and `FeedbackComSem`; `Codebook_Experiment_1.txt`, definitions of those columns and `P_RF.RC`. Used only to check counts/measurement, not to replace printed outcome summaries.

## Report B — Sun et al. (2015)

**Target fixed before extraction.** Estimate the published long-term standardized peer-assessment effect minus the short-term effect, using Table 1, for the analyzed Stanford introductory-statistics students. The report is *Peer Assessment Enhances Student Learning: The Results of a Matched Randomized Crossover Experiment in a College Statistics Class*, [doi:10.1371/journal.pone.0143177](https://doi.org/10.1371/journal.pone.0143177).

**Design, intervention, and missingness.** The ten-week course had an introductory unit and four experimental units. Every student received peer assessment in two units and control in two, following TCTC, CTCT, TCCT, or CTTC. Matching used baseline covariates; complementary sequences were randomized within matched pairs, after covariate blocking and optimal matching. Treatment combined grading/commenting on three peers' responses with receiving three peer reviews. Controls received instructor grading; feedback timing and solution resources were aligned. Instructors blind to assignment graded the outcome assessments. [B2–B3]

The supplement reports 150 autumn and 240 winter consent-form respondents, with two and one opting out: 148+239=387 participants. Its compliance rule was at least 10 of 12 assigned peer-assessment questions, yielding 322 compliant students. The main report gives **299 students for unit quizzes and 320 for final-exam outcomes**, after compliance and assessment-completion exclusions. These are outcome-specific student totals, not independent treatment/control arm sizes. The supplement belongs to the same study, not a separate replication to pool. [B2–B3]

**What the effects estimate.** Scores were standardized with the relevant control scores' mean and SD; each student's mean standardized performance under treatment was differenced against that student's mean under control, and these within-student differences were averaged across terms. Short-term performance came from quizzes following units; longer-term performance came from corresponding content on the comprehensive final exam in Week 11. The published effects concern the retained compliant/completing samples, rather than an unrestricted intention-to-treat population. [B2–B3]

| Table 1 estimate | Standardized effect | SE | Analyzed students |
|---|---:|---:|---:|
| Short Term (unit quizzes) | 0.115 | 0.04 | 299 |
| Long Term (final exam) | 0.122 | 0.04 | 320 |

**Derived descriptive result:** \(0.122-0.115=\mathbf{0.007}\) standardized units. The table caption identifies parentheses as **SEs**. The supplement's Table 6 displays coarser 0.11/0.12 estimates; those are not substituted for the requested main-table values. Under ordinary rounding to three decimals, mean rounding alone gives approximately 0.006–0.008, not a sampling interval. [B1, B3]

**Scoped uncertainty hold.** The sources do not supply the joint covariance needed for

\[
\operatorname{Var}(\hat d_L-\hat d_S)
=SE_L^2+SE_S^2-2\operatorname{Cov}(\hat d_L,\hat d_S).
\]

Using the rounded SEs, this is \(0.0032(1-\rho)\), with unknown estimator correlation \(\rho\). The common cohort, repeated observations, matching, and overlapping endpoint samples preclude assuming independence. Neither the exact overlap/joint participant differences nor a joint covariance matrix or joint resampling distribution is supplied. Supplement §2.3 describes inference for each effect separately; it does not identify the cross-endpoint covariance. Therefore no identified CI or test of their difference is reported. Separate significance tests cannot establish a difference between timepoints.

**Scope.** The estimates are descriptively very similar, but 0.007 does not demonstrate improvement or decay over time: instruments, standardizations, and retained samples differ. Compliance selection and possible carryover/spillover further limit broader causal interpretation. This is one course across two terms, not evidence of clinical benefit or commercial readiness. [B2–B3]

**Precise primary-source locations.**

- **B1:** `pone.0143177.pdf`, p. 4, Table 1, both named effect rows and “Effect Size” column; caption. XML `//table-wrap[@id='pone.0143177.t001']`; expanded rows 1/2, column 1.
- **B2:** `pone.0143177.xml`, `/article/body/sec[2]/p[1–5]` (Materials and Methods), especially p[5] for outcome Ns; `/article/body/sec[3]/p[1]` for corresponding final-exam questions.
- **B3:** `pone.0143177.s001.pdf`: §1.1–1.2, pp. 1–3, course timing/recruitment; §1.4, p. 4, intervention; §2.1, pp. 5–6, matching/sequences; §2.2–2.4, pp. 7–9, estimator/inference/combining terms; Table 6 and §3.2, pp. 9–11, rounding/compliance; §3.3/3.5, pp. 11–15, assumptions.

## Reproduction and retained instrument

Run `python calculate.py` in this folder. It imports and invokes the recovered engine's `read_jats`, `cell_value`, and `mean_difference`; conventional Python/SciPy supplies the Welch calculation. The archive SHA256 was verified as `32a9c193200f43c94b922c9b7f5460a60a57f44031f1b2c88c8a50b15766a930`. A custom ± parser was necessary because the engine's cell parser supports parenthesized dispersion. Source identities, numerical outputs, and requalification decisions are in `calculation_results.json`. Engine flags establish neither semantic acceptance nor deployment authority. No pooled effect, commercial admission, or actual profit is inferred.
