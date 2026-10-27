# Evidence reconstruction: recipient E

## Prespecified scope and method

For A, the population is Experiment 1's university participants; the outcome is each participant's proportion of correct final cued-recall responses; the permissible estimate is the retrieval-with-feedback minus restudy-with-feedback mean difference from Table 3, with design-supported uncertainty. For B, the population is the analyzed students in the two statistics-course cohorts; the outcomes are standardized unit-quiz and corresponding final-exam achievement; the permissible estimate is the published long-term effect minus short-term effect from Table 1. These are separate studies and are not pooled.

Publisher XML supplied the primary numerical and design record. PDF table rendering, the B supplement, and A's codebook/participant counts provided cross-checks. Calculation inputs remain the printed summaries, not recalculated raw-data means.

## Report A: final correct-response proportions

**Identity and target.** Maraver MJ, Lapa A, Garcia-Marques L, Carneiro P, Raposo A (2022), *Can we learn from errors? Retrieval facilitates the correction of false memories for pragmatic inferences*, [DOI](https://doi.org/10.1371/journal.pone.0272427), **Experiment 1 only**. The outcome counts answers matching the original sentence or synonyms preserving its meaning, divided by all 30 sentences. Blank responses remain a distinct response category, rather than being removed from the denominator. This is overall final accuracy, not accuracy conditional on an earlier error. [A1, A2]

**Design and denominators.** The study recruited 120 University of Lisbon students. Both learning condition and corrective feedback were randomized between participants in a 2-by-2 design: 30 participants in each cell, including 30 retrieval-with-feedback and 30 restudy-with-feedback. The participants paragraph's parenthetical n values are awkwardly attached to factor labels; the four-cell interpretation is corroborated by the reported ANOVA denominator df of 116 and the supplied data's four groups of 30. All 120 data rows have a nonempty final-correct-proportion field. No additional Experiment 1 exclusion is described in the inspected methods. The 30 sentence observations per person are not 30 independent participants. [A1, A3]

All participants first encoded the sentences. Retrieval participants then attempted cued recall; restudy participants read 15 correct and 15 incorrect sentences, counterbalanced across participants. This was a constructed restudy sequence, not actual participant-level yoking to a retrieval partner. Both target groups then saw the original correct sentence as feedback. Following a one-minute distractor, everyone completed the final 30-item cued-recall test without feedback, within the same session. [A1]

**Printed inputs and reconstruction.** In Table 3, the **Correct responses / Experiment 1 / Feedback** row gives:

| Condition | Participant n | Mean proportion | Participant-level SD |
|---|---:|---:|---:|
| Retrieval | 30 | 0.83 | 0.10 |
| Restudy | 30 | 0.61 | 0.21 |

The table footnote explicitly labels the quantities after the plus/minus sign as **standard deviations**, not standard errors. These cells and the footnote agree with the rendered primary PDF, page 8. [A2]

The **derived** difference is

\[
\widehat\Delta_A=0.83-0.61=0.22.
\]

For independent participant groups, a Welch approximation uses

\[
SE=\sqrt{0.10^2/30+0.21^2/30}=0.0424657,
\quad
\nu=\frac{(s_R^2/n_R+s_S^2/n_S)^2}
{(s_R^2/n_R)^2/(n_R-1)+(s_S^2/n_S)^2/(n_S-1)}=41.5087.
\]

Thus \(0.22\pm t_{.975,41.5087}(0.0424657)\), with critical value 2.01879, gives an **approximate 95% CI of [0.1343, 0.3057] proportion units**: **22.0 percentage points, CI 13.4 to 30.6 points**, favoring retrieval with feedback. This assumes independent participants and an adequate approximation to the sampling distribution of their mean proportions; it does not require equal variances or assume independent sentence trials. It conditions on the selected stimulus set rather than estimating variation over all possible materials.

The displayed means and SDs have two decimals, so the reconstruction is approximate. Mean rounding alone allows roughly 0.21-0.23 for the underlying difference. The feedback marginal mean 0.72 matches the two target means' average. Elsewhere, the non-feedback total is printed as 0.28 although its two displayed equal-size cell means average 0.27; this off-target inconsistency is preserved and not used to repair the target. [A2]

**Interpretation and limitation.** The specified laboratory comparison supports greater immediate final accuracy under retrieval plus feedback for these sentences and participants. Restudy included deliberately incorrect sentences, so this does not establish superiority to every ordinary restudy method. It does not establish durable educational gains, clinical benefit, or product/customer value.

**A source locations.**

- **A1:** `pone.0272427.xml`, `/article/body/sec[2]` (Experiment 1), Methods: `sec[1]/sec[1]/p[1]` (Participants), `sec[1]/sec[3]/p` (Design), `sec[1]/sec[4]/p[2]` (Procedure), and `sec[1]/sec[5]/p[1]` (Statistical analyses/coding). Final-test ANOVA: `/article/body/sec[2]/sec[2]/sec[2]/p[2]`.
- **A2:** Same XML, `//table-wrap[@id='pone.0272427.t003']`, Correct responses block, Feedback row, Experiment 1 Retrieval/Restudy columns, and table footnote; primary PDF page 8.
- **A3:** `Codebook_Experiment_1.txt`, entries `CondiçãoRS`, `FeedbackComSem`, `P_RF.RC`; `Error_correction_PI_Experiment_1.csv`, corresponding columns, checked only for participant/cell counts and nonempty target values.

## Report B: long-term minus short-term standardized effect

**Identity, intervention and outcomes.** Sun DL, Harris N, Walther G, Baiocchi M (2015), *Peer Assessment Enhances Student Learning: The Results of a Matched Randomized Crossover Experiment in a College Statistics Class*, [DOI](https://doi.org/10.1371/journal.pone.0143177). The study covered two offerings of Stanford's introductory statistics course. Treatment involved scoring/commenting on peers' homework and receiving peer feedback; control homework was graded by instructors. Feedback timing and access to the solution key were aligned. Short-term learning was measured by unit quizzes after feedback; longer-term learning by the corresponding unit questions on the comprehensive week-11 final exam. Graders were blinded. [B1, B2]

**Design and sample accounting.** Students crossed over between treatment and control for two units each, using TCTC, CTCT, TCCT, or CTTC sequences. Matching blocked on gender, race and prior statistics background, then paired similar students on other covariates; a coin flip assigned complementary sequences within pairs. The unit of the reported estimator is a student's within-person contrast, with repeated unit measurements and matched assignment, not independent permanent treatment/control arms. [B1, B2]

There were 390 consent-form respondents enrolled for credit: 150 autumn and 240 winter. Three opted out, leaving 148 + 239 = **387 participants**. Main-report analyses used **299 students for quizzes** and **320 for final exams**, after compliance and assessment-completion exclusions. Supplement section 3.2 calls **322** the final sample under completion of at least 10 of 12 assigned peer-assessment questions. That compliance count must remain distinct from the main report's outcome-specific counts; losses are not fully tabulated by criterion. Six questions per unit quiz and 12 assigned peer-assessment questions are item/workload counts, not arm sizes. [B1, B2]

**Meaning and printed inputs.** Supplement section 2.2 standardizes each assessment using its control-group mean and **SD**, computes each student's average standardized treatment score minus average standardized control score, and averages those student contrasts. The same approach is applied to final-exam questions associated with the treated/control units. Main Table 1 reports **short term 0.115 (SE 0.04)** and **long term 0.122 (SE 0.04)**; its caption explicitly identifies parentheses as **standard errors**, not SDs. Supplement Table 6 gives the coarser 0.11 and 0.12; the requested reconstruction uses the more precise main-table entries. [B1, B2]

The **derived descriptive contrast** is

\[
\widehat\Delta_B=0.122-0.115=\boxed{0.007}
\]

in standardized effect units, with the longer-term estimate slightly larger. With three-decimal means, rounding alone permits approximately 0.006-0.008. The contrast compares estimates on assessment-specific standardizations and somewhat different analyzed samples; it is not an individual's measured gain over time.

**Scoped uncertainty hold.** The appropriate variance is

\[
\operatorname{Var}(\widehat\Delta_B)=SE_L^2+SE_S^2-2\operatorname{Cov}(\hat d_L,\hat d_S).
\]

The main article and supplement provide marginal SEs and separate significance tests, but no joint covariance, exact overlap membership, paired cross-outcome contrast variability, or joint randomization distribution. The outcomes share students, assignments and course contexts. Neither independent-arm precision nor treating the two effects as independent is justified. Consequently **a numerical CI or test for their difference is not identified by the supplied summaries**. Resolving it requires the covariance of the two actual estimators, or linked outcome data plus a joint analysis preserving crossover and matched-assignment dependence and outcome-specific missingness. Separate significant treatment effects do not establish a significant between-time difference.

**Interpretation and limitation.** The supported descriptive finding is 0.007, not evidence that benefits increased or were equivalent over time. Exclusions restrict applicability to the analyzed compliant/completing students; excluding noncompliers from both crossover periods alone does not eliminate every selection concern. A single course in two terms cannot establish broad educational, clinical, or customer outcomes.

**B source locations.**

- **B1:** `pone.0143177.xml`, `/article/body/sec[2]/p[1-5]` (Materials and Methods: design, matching, intervention, outcomes, samples), `/article/body/sec[3]/p[1]` (Results), and `//table-wrap[@id='pone.0143177.t001']`, both effect rows and SE caption; primary PDF page 4.
- **B2:** `pone.0143177.s001.pdf`, sections 1.1-1.3, pp. 1-3 (schedule, recruitment, items); section 2.1, pp. 5-6 and Table 4 (matching/crossover); sections 2.2-2.4, pp. 5, 7-9 (standardization, within-student estimator and pooling); section 3.1 and Table 6, pp. 9-10 (coarser effect summaries); section 3.2, pp. 10-11 (compliance).

## Reproducibility

`calculation.py` implements the Welch reconstruction and exact-decimal check of both mean differences. `calculation_results.json` contains its outputs. The two sources' results are separate; no meta-analytic pooling, independent-arm reconstruction for B, or unsupported between-time test was performed.
