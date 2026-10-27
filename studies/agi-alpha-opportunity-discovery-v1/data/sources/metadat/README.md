# Frozen metadat source packets

Upstream: Wolfgang Viechtbauer and collaborators, **metadat 1.7-2**,
https://github.com/wviechtb/metadat, commit
`0cb96ce4ff16586a9dbc8a9b0f9bc617538d2738`.

The upstream package declares **GPL (>=2)** in `DESCRIPTION`. The preserved
files retain that license. A copy of GPL v2 is provided in `GPL-2.0.txt`.
Original paper references and dataset author attribution are retained in the
`.r` and `.Rd` files. These source assets are not relicensed Apache-2.0.

`SOURCE_RECEIPTS.json` records exact upstream URLs, Git blob hashes, local
SHA-256 hashes, byte lengths, retrieval time and the CSV formatting operation.
All seven original files matched the Git blob SHA supplied by the connector.
Original CRLF/LF bytes are preserved. The two CSV files change only table
serialization; values and `NA` tokens are unchanged. They contain no new
effect-size calculations.

## What these packets can establish

They are **supplied secondary extraction data**, not papers automatically
read and extracted by the new instrument. The dataset documentation and
transformation programs supply meaning that a purpose-preserving instrument
must respect. They support an executable test of revalidation, transfer and
semantic refusal. Familiar published meta-analysis is the conventional
calculation baseline, not a claimed new discovery.

No primary statistical analysis was run while obtaining these packets.
Source records, not prepared hypothetical claim graphs, define the input.
Any amendment, withdrawal or changed mission used in this edition must be
identified as an injected fixture unless separately sourced.

## Origin: writing-to-learn interventions

Files: `data-raw/dat.bangertdrowns2004.txt`, `.r`,
`man/dat.bangertdrowns2004.Rd`, `dat.bangertdrowns2004.csv`.

The 48 rows describe comparisons of increased writing emphasis with
conventional instruction on content-related academic achievement. Positive
effects mean greater achievement in the intervention group. The source paper
is Bangert-Drowns, Hurley and Wilkinson (2004), *Review of Educational
Research* 74(1), 29-58, DOI `10.3102/00346543074001029`.

The raw table has `di` (the supplied uncorrected effect) and `ni` (total sample
size), not ready-to-use `yi` and `vi`. The preserved upstream script applies:

```
yi = round((1 - 3/(4*ni - 9)) * di, 2)
vi = round((8 + yi^2)/(2*ni), 3)
```

The documentation explicitly says that its standardized mean differences are
bias-corrected and differ slightly from the article, and that sampling
variances assume equal-sized treatment and control groups because only total
n is supplied. A representation of these data as observed original arm sizes
or exact unbiased original-paper estimates is incorrect. Preserve upstream
rounding if reproducing the supplied package analysis.

`grade` codes elementary/middle/high-school/college as 1/2/3/4. `length`
means intervention duration in weeks. `minutes` means minutes per writing
assignment. `meta` flags metacognitive reflection prompts. Missing moderator
values must not silently become zero. Repeated author/year combinations do
not independently establish duplicate observations or sampling independence.

## Fresh purpose: teacher expectancy and pupil IQ

Files: `data-raw/dat.raudenbush1985.txt`, `.r`,
`man/dat.raudenbush1985.Rd`, `dat.raudenbush1985.csv`.

The 19 rows examine teacher expectancy effects on pupil IQ. Positive `yi`
means higher IQ scores in the group designated as likely to improve. The
effect metric is a standardized mean difference; the useful question differs
from writing-to-learn and academic achievement.

This table already supplies `yi`, `vi`, treatment `n1i` and control `n2i`.
The groups are often unequal. The upstream preprocessing deletes `sei` and
retains the supplied `vi`, attaching total n as metadata. Applying the
origin packet's equal-group variance reconstruction here changes the
evidence without source authorization. Squaring its rounded `sei` also need
not reproduce the supplied rounded `vi` exactly.

`weeks` means teacher-student contact **before** the expectancy induction.
It is not intervention duration. `setting` distinguishes group and
individual testing; `tester` distinguishes aware and blind test
administrators. A shared unit such as weeks or a shared effect metric does
not make the mission semantics interchangeable.

The packet draws effects from Raudenbush and Bryk (1985), DOI
`10.3102/10769986010002075`, and setting/tester metadata from Raudenbush
(1984), DOI `10.1037/0022-0663.76.1.85`. The latter title says 18 experiments
while the package describes 19 studies/rows. Two rows have the same
Pellegrini & Hicks author/year and distinct tester conditions. Preserve this
unit-of-analysis uncertainty. An independent-effects REML reproduction of
the conventional packet does not prove that all observations are
statistically independent or settle the original scientific conclusion.

The Rd example caps the `weeks` moderator at 3 for its mixed-effects
example. This is supplied modeling structure, not a newly discovered
nonlinearity. The new study's REML-only engine should not silently claim to
reproduce that moderator model.

## Scope boundaries

- No inference about current educational efficacy follows solely from
  reproducing these historical packets.
- A renewed mission must specify population, intervention, outcome, effect
  direction, admissible variance construction and requested analysis.
- Stable numerical code may transfer; dataset meaning and authority must
  be checked again.
- Exact agreement with a complete expert rerun is required before measuring
  any recurring-work saving.
- No proprietary source-paper full text has been redistributed here.
