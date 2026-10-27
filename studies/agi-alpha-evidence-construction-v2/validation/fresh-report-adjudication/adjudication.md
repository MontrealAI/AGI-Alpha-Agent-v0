# Independent adjudication of fresh public-report reconstruction

**Result: U, E, and E+ each score 20/20 under the unchanged binary primary rubric.** Optional partial-credit sensitivity is also 20/20 for every condition. All three reproduce the requested quantities and handle the key dependence issues correctly. This supports scoped research-reconstruction acceptance; it shows no graded accuracy increment from the recovered artifact on these two tasks.

## Frozen key and adjudicator scope

The key was frozen at 2026-10-27T17:29:49.663963+00:00, before all recipient starts, with SHA-256 `0bbb2a669f7ef8622c484e0e98587b38ec0dfbe388b48f993e267edd593d59bb`. It was copied here only after completion of all three recipient runs. Neither the key nor recipient answers were edited during adjudication. The evaluator was independent of constructor and recipient execution, but had created the key and could see condition labels and the study hypothesis. This is not a fully blind assessment or a human panel.

## Scores and recorded resources

| Condition | Report A | Report B | Binary primary | Partial sensitivity | Tool calls | Elapsed seconds |
|---|---:|---:|---:|---:|---:|---:|
| U | 10/10 | 10/10 | 20/20 | 20/20 | 10 | 175.698 |
| E | 10/10 | 10/10 | 20/20 | 20/20 | 10 | 236.061 |
| E+ | 10/10 | 10/10 | 20/20 | 20/20 | 9 | 235.150 |

All conditions stayed within the common limit of ten underlying tool operations and twelve minutes. Counts include clock/skill operations and failed reads according to the recipients' stated convention. Operation-list lengths and timestamp arithmetic agree with the logs. These are recorded worklog values, not independently metered original execution telemetry. Token usage and billed cost are unknown. E+ used one fewer recorded tool operation than each comparator; its elapsed time was about 0.911 seconds below E and 59.452 seconds above U. These single noisy runs do not establish a speed or cost advantage.

## Main scientific checks

For Report A, all three correctly identify a randomized between-participant factorial design with independent focal groups. The restudy errors were constructed and counterbalanced; describing them to participants as another person's recall does not create actual participant pairing. None imports Experiment 2 yoking or treats repeated sentence responses as independent persons. All distinguish participant SD from SE and compute the same approximate Welch reconstruction: +0.22 proportion correct, SE 0.0424657, df about 41.51, and 95% CI [0.13427, 0.30573]. All explain independence, sampling-distribution approximation, rounded summaries and fixed-material scope.

For Report B, all three preserve the matched randomized crossover, within-student standardization/contrast estimator, and different outcome-analysis populations. Each computes +0.007 standardized units and holds the confidence interval/test for that difference because joint estimator covariance is unavailable. No response treats the two marginal effects as independent or uses their separate significance tests to establish a between-time difference.

## Execution verification

Each submitted calculation was copied unchanged into a temporary directory and replayed. Every replay exited successfully and its parsed JSON exactly matched the saved result. Original recipient outputs were preserved. The E+ recovered engine matched the frozen archive (SHA-256 `32a9c193200f43c94b922c9b7f5460a60a57f44031f1b2c88c8a50b15766a930`). Profiling the replay observed two `read_jats` calls, four `cell_value` calls and two `mean_difference` calls. U and E did not invoke that engine. See `execution_verification.json` and `replay_*.json`.

E+ therefore used the recovered capability concretely. It also supplied its own plus/minus cell parsing and conventional SciPy Welch calculation. Verified functional use is distinct from incremental research value: all three outputs reached the same frozen scoring ceiling.

## Criterion-by-criterion adjudication

Each row below uses the frozen criterion unchanged. All entries score 1 in the binary rubric and 1 in the optional sensitivity score. Exact per-condition excerpts and original-source locators are retained in `adjudication.json`.

### Report A

| Criterion | U | E | E+ | Reason and response locators |
|---|---:|---:|---:|---|
| A01 Report and experiment | 1 | 1 | 1 | Identifies the correct Maraver report and Experiment 1; no substitution of Experiment 2. Locations: U answer lines 7,3; E answer lines 11,5; E+ answer lines 5,3. |
| A02 Contrast and direction | 1 | 1 | 1 | Uses retrieval with feedback minus restudy with feedback, with the requested direction and no marginal/no-feedback substitution. Locations: U answer lines 5,15; E answer lines 5,21; E+ answer lines 5,13. |
| A03 Outcome and timepoint | 1 | 1 | 1 | Identifies participant-level final cued-recall correct-response proportion, same-session test after a one-minute distractor, and distinguishes it from conditional error correction. Locations: U answer lines 7,37; E answer lines 15,11; E+ answer lines 9,38. |
| A04 Population and sample-size roles | 1 | 1 | 1 | Reports Lisbon university students, total N=120 and n=30 in each selected cell; keeps sentence/item counts separate from participant counts. Locations: U answer lines 9,9; E answer lines 13,13; E+ answer lines 7,7. |
| A05 Values and uncertainty label | 1 | 1 | 1 | Extracts 0.83 with SD 0.10 and 0.61 with SD 0.21; explicitly qualifies the plus/minus quantities as participant SDs. Locations: U answer lines 15,16,18; E answer lines 21,22,24; E+ answer lines 13,14,16. |
| A06 Design and analysis unit | 1 | 1 | 1 | Correctly describes a randomized 2-by-2 between-participant design and independent focal groups. Explicitly distinguishes constructed restudy errors from actual participant yoking and rejects item-level sample inflation. Locations: U answer lines 9,11,9; E answer lines 13,15,13; E+ answer lines 7,9,9. |
| A07 Derived mean difference | 1 | 1 | 1 | Derives +0.22 proportion correct, equivalently +22 percentage points, with correct sign and scale. Locations: U answer lines 5,23; E answer lines 41,29; E+ answer lines 38,21. |
| A08 Derived uncertainty | 1 | 1 | 1 | Uses the participant-level Welch formula, SE 0.0424657, df about 41.51 and CI about [0.13427,0.30573]. States independent-participant and approximate sampling-distribution assumptions, unequal-variance allowance, rounded inputs, and fixed-material scope. Locations: U answer lines 24,33,5; E answer lines 35,41,43; E+ answer lines 22,38,40. |
| A09 Auditable provenance | 1 | 1 | 1 | Supplies exact Table 3 block/row/columns and caption/footnote plus identifiable XML method locations for participants, design and timing; separates reported inputs from derived results. Locations: U answer lines 41,37; E answer lines 50,49; E+ answer lines 46,47. |
| A10 Supported scope | 1 | 1 | 1 | Limits the positive contrast to immediate laboratory performance with this sentence set/comparator and avoids conditional-error-correction, universal education, customer, or clinical claims. Locations: U answer lines 37,37; E answer lines 45,45; E+ answer lines 42,42. |

### Report B

| Criterion | U | E | E+ | Reason and response locators |
|---|---:|---:|---:|---|
| B01 Report and population | 1 | 1 | 1 | Identifies the Sun report and Stanford introductory-statistics study across the autumn/winter cohorts; treats the analyzed outcomes as belonging to that study. Locations: U answer lines 50,50,50; E answer lines 55,55,59; E+ answer lines 52,52,56. |
| B02 Crossover and matching | 1 | 1 | 1 | Describes matching and complementary randomized crossover sequences, with two treatment and two control units per participant; does not invent permanent independent arms. Locations: U answer lines 52,52; E answer lines 57,57; E+ answer lines 54,54. |
| B03 Treatment and control | 1 | 1 | 1 | Describes giving and receiving peer feedback versus instructor feedback, with aligned feedback timing and solution resources; control is not absence of feedback. Locations: U answer lines 52,52; E answer lines 55,55; E+ answer lines 54,54. |
| B04 Timing and effect definition | 1 | 1 | 1 | Identifies unit quizzes versus the comprehensive Week-11 final and explains control-score standardization followed by averaging within-student treatment-minus-control contrasts; preserves standardized units. Locations: U answer lines 50,56,56; E answer lines 55,61,57; E+ answer lines 58,58,58. |
| B05 Published values and uncertainty | 1 | 1 | 1 | Extracts short 0.115, long 0.122 and both SEs 0.04 from Table 1; does not mislabel SE as SD. Locations: U answer lines 48,48,63; E answer lines 61,61,61; E+ answer lines 62,63. |
| B06 Sample-size roles | 1 | 1 | 1 | Separates 387 participants from outcome-specific 299 quiz and 320 final-exam analyses, discusses compliance/completion exclusions, and avoids treating these as independent arm counts. Locations: U answer lines 54,54,54; E answer lines 59,59,59; E+ answer lines 56,56,56. |
| B07 Descriptive reconstruction | 1 | 1 | 1 | Computes long minus short as +0.007 standardized effect units, labels it descriptive, and acknowledges rounding and distinct assessment standardizations. Locations: U answer lines 48,52; E answer lines 66,57; E+ answer lines 65,65. |
| B08 Dependence and scoped uncertainty hold | 1 | 1 | 1 | Retains the point difference while holding its unconditional CI/test because estimator covariance is unidentified; gives the covariance-dependent variance formula and explains overlapping/crossover data. Locations: U answer lines 48,54,48; E answer lines 55,57,71; E+ answer lines 54,56,67. |
| B09 Auditable provenance | 1 | 1 | 1 | Cites Table 1 named rows and SE caption, the method sample-size paragraph, and the supplement estimator pages/sections; reported and derived quantities remain distinct. Locations: U answer lines 78,68; E answer lines 83,61; E+ answer lines 80,71. |
| B10 Interpretation and scope | 1 | 1 | 1 | Does not infer increased/equal effects from the small difference or separate significance tests; limits interpretation to course and analyzed compliant/completing samples without clinical/customer validation. Locations: U answer lines 73,73,54; E answer lines 77,79,59; E+ answer lines 76,76,56. |

## Publication provenance and limits

The publication-safe sources are in `../../assay/source_packet`. They contain exact CC BY publisher article/supplement files and their mechanical text derivatives. Their receipt explicitly supersedes the historical receipt for redistribution, removes transient signed query strings, and identifies omitted OSF datasets, codebooks and metadata with stable URLs and hashes. All recipients originally had equal access to those public OSF files; no independent redistribution license was verified, so the files themselves are excluded. The original full packet and frozen inputs remain unchanged outside the repository. Do not publish the original full packet archive.

The formerly private answer key, original verifier, original verification result and freeze are released here after completion for audit. They are not included in the recovered capability capsule. The frozen verifier is retained byte-for-byte, so its optional raw-data count cross-check still expects the original local source layout; the core numerical reconstruction is reproducible from the published summaries and supplied recipient scripts without redistributing raw data.

This is one run per condition on two reports, with strong common instructions and an observed ceiling. It cannot establish population-level equivalence, expected treatment effects, clinical efficacy, customer value, commercial readiness, or cost-effectiveness. No broader repository test suite or architecture review was undertaken.
