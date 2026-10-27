# Additional challenge of evidence revalidation

Date: 2026-10-27. Additional substantive source budget: four documents. Read exactly four: EPPI Reviewer product page; crop-yield source notes; crop-yield analysis notebook; MetaLab about/changelog. Repository directory trees and license metadata were inspected as metadata. Initial exploration used nine substantive sources, giving thirteen total for this stream.

## The most concrete environmental source packet obtained

Repository: https://github.com/maxanochirim/network-meta-analysis-using-crop.yield.data

Frozen commit: `623148fa24df4eef59c65bd6eef5fb53b6a433bb`.

GitHub repository license metadata: **AGPL-3.0**. Preserve original license and attribution if distributing derived code/data; the repository license declaration does not independently verify the authors' rights in every underlying paper. Primary paper: *The implementation of network meta-analysis in Ecology; a case study using crop yield data*, Anochirim, Grainger, Stewart and Takola, DOI `10.32942/X2JH0R` (identified through search; not read within this budget).

Files obtained or identified:

| Repository path | Size | Git blob SHA | Purpose |
|---|---:|---|---|
| `raw_data/readme` | 1,858 B | `9c9bb1db84d8244ec24460e0874cd1f13e94ae3c` | Original useful purpose and inclusion rules |
| `raw_data/yield_dataset.xlsx` | 321,691 B | `dc88fe405433e738976d2c8ee0658bebc1664833` | Actual source workbook; downloaded locally |
| `data/yield_data.RDS` | 79,421 B | `f72c1121760776bf9530c2a7818a7c1b38279ddd` | Author-prepared analysis data; identified, not downloaded |
| `network_meta_analysis.qmd` | 10,612 B | `b505915ecf79200debc5416af32f054f2f3aa32f` | Published analysis narrative and executable R |
| `R/yield_data.R` | 1,580 B | `7293dd5a0eb478ea0f15230dc65b2ad01e1819f8` | Author preprocessing; identified, not read within budget |

Local source packet: `discovery_systems/frozen/yield_dataset.xlsx`, `crop_source_notes.txt`, and `crop_analysis.qmd`.

The notes define the outcome as crop yield in kg/ha and eligibility as randomized, paired intervention/control comparisons with complete SD, n and outcome information, excluding second-line treatments. The analysis uses `pairwise()` with `sm="SMD"`, then `netmeta`. This supplies real semantic decisions and data coordinates without an invented dependency graph.

However, this is not yet a small clean experiment. The notebook has inconsistent record counts (3733 versus 3939), description of mean differences despite a standardized-mean-difference setting, and other narrative/code issues. These are unresolved discrepancies, not invitations to choose a favorable interpretation. An independent reproduction must decide which source is authoritative or report ambiguity. Its code already supplies most data transformation structure. A new artifact cannot call that supplied structure autonomous discovery.

Potential bounded task: construct a traceable intake and inclusion instrument that preserves the original eligible comparison and documented outcome meaning, then use clearly injected workbook corrections/deletions to compare a complete expert rerun with a retained incremental reanalysis. Match correctness before measuring work. If the existing R pipeline already handles those changes for negligible additional effort, reject the recurring-work advantage. The actual notebook is a strong baseline and should not be withheld from it.

## Prior art that materially narrows the opportunity

EPPI Reviewer: https://eppi.ioe.ac.uk/cms/er/ (web reference `turn25view0`). Its current official page describes meta-analysis, outcome entry, auto-comparisons, OpenAlex integration and LLM automated coding. A review-maintenance instrument should not claim that extraction, analysis or living updating are generally unavailable.

MetaLab: https://github.com/langcog/metalab/blob/c74e7ee00f0b89983c500367d60d7238ad8a041c/about.qmd. This source explicitly documents standardized effect sizes, field validation, versioned data releases, provenance and browser-executed analyses. Its 2026 changelog describes actual legacy issues: hidden errors in a funnel test, duplicated power-simulation observations, inconsistent model hierarchy, an age filter difference and broken downloads. The same source states CC BY 4.0 for MetaLab and its datasets unless noted otherwise. The repository has many accessible CSV files. Example: `resources/csv/NaturalSpeechSegmentation_Neuro.csv` (8,524 bytes), but importing that prepared file is not evidence reconstruction.

MetaLab already repaired its legacy issues. These documented issues could be strong historical controls or transfer challenges, but rebuilding their supplied solution does not establish a newly discovered opportunity. The source is saved as `frozen/metalab_prior_art_about.qmd`.

## Result of the challenge

The broad revalidation idea survives only as a hypothesis about **rescuing heterogeneous legacy evidence into a reliable, purpose-scoped instrument**, where the required provenance and semantic decisions are absent or broken. It does not survive as a claim that new software is needed merely to rerun a maintained meta-analysis after a row changes. A small FAIR-corpus case with open source evidence and a genuine reconstruction burden may be a better flagship packet than this crop notebook.

No source within the bounded search establishes willingness to pay for this narrow rescue service, recurring demand, or superior model performance. A positive cash simulation cannot supply those missing facts.
