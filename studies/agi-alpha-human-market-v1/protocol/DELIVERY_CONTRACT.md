# CSV cleanup and reconciliation: frozen service contract draft

The buyer is an operations analyst preparing a recurring nonpersonal export for import or reporting.
The supported result is one normalized CSV, duplicate and exception registers, every input record's
disposition, exact output checksums, a data quality report, and instructions for an automated revision.
No missing value is guessed and no conflicting record is silently discarded.

## Input

A UTF-8 CSV (optional UTF-8 BOM), at most 10 MiB and 1-50,000 data records, has exactly these headings,
in this order: `record_id,category,date,amount,updated_at`. Comma or semicolon delimiter is explicit.
Each cell is at most 256 Unicode characters. Quoted delimiters, quotes, newlines and CRLF are supported.
Only public nonpersonal or labeled synthetic inputs are allowed. No spreadsheet formulas execute.

The JSON job has schema `csv-clean-job/v1`, `id`, `data_class`, `source` (`file`, `sha256`), and `rules`.
Rules contain `delimiter` (comma or semicolon), `amount_locale` (`dot` or `comma`), `date_format`
(`iso` or `dmy`), `key_policy` (`hold` or `latest`), `missing_markers` and `category_map`.
The data_class values are exactly `public` or `synthetic`; public declares public nonpersonal inputs.
The normalized missing_markers set must include the empty string or the rule set is refused.
Source filename is a local basename. The supplied SHA-256 must match the exact original bytes.
Job IDs contain 1-80 ASCII letters, digits, underscores or hyphens. Source filenames contain 1-120
ASCII letters, digits, underscores, hyphens or dots, excluding dot and double-dot. Missing markers
have at most 20 entries; category_map has at most 200 pairs. Every marker/map string has at most
256 characters. Conflicting normalized category-map keys are rejected. No extra job/rule fields.

## Normalization

Trim surrounding whitespace and normalize strings to Unicode NFC. Record identifiers retain case
and leading zeros. Category replacement uses only exact customer-provided category_map entries after
the same normalization. Required category missingness is checked after that replacement.
Unmapped categories remain unchanged. Missing markers are matched exactly
after normalization; record_id, category, date and amount are required. Blank updated_at is valid for
hold policy. Every missing updated_at marker becomes the empty string in canonical output.
Every other nonmissing updated_at must be a valid ISO date in years 1900-2100.

All date and amount digits are ASCII. Dot amounts allow optional minus, 1-10 digits and an optional decimal point followed by 1-2 digits.
Comma amounts allow optional minus, 1-10 ungrouped digits or properly grouped thousands using dots,
and an optional comma followed by 1-2 digits. Grouped forms contain 1-3 thousands groups and at most
10 integer digits after removing separators. No plus, exponent, currency symbol or guessed locale.
Absolute amount in cents must not exceed 999999999999. Output uses signed decimal with exactly two
digits; negative zero becomes 0.00. ISO dates are YYYY-MM-DD; dmy dates are DD/MM/YYYY, validated
against the calendar, and emitted as ISO. Valid years are 1900-2100. No formula interpretation occurs.

Invalid rows are quarantined with sorted distinct reason codes: MISSING_RECORD_ID, MISSING_CATEGORY,
MISSING_DATE, MISSING_AMOUNT, INVALID_DATE, INVALID_AMOUNT, INVALID_UPDATED_AT. Under latest policy,
missing updated_at is MISSING_UPDATED_AT. A row can have more than one reason. Do not additionally
mark a missing value as invalid. Source record numbers start at 1 after the header and count parsed
records, so embedded newlines do not change record numbering.

## Duplicate and version policy

Among valid normalized rows, exact duplicates across all five fields keep the lowest source record
number; later copies receive DUPLICATE_EXACT and a kept_source_row link. Remaining rows group by
record_id. Under hold policy, a key with different surviving rows quarantines all surviving members
with CONFLICTING_KEY. Under latest policy, select the greatest updated_at ISO date. A unique latest
row is retained; older surviving records receive SUPERSEDED and link to that selected source row.
If two different surviving rows tie at the greatest date, quarantine ALL surviving members of that
key with CONFLICTING_LATEST. Duplicate links retain their original first occurrence even when that
first occurrence is later quarantined or superseded; the disposition map makes that explicit.

Clean rows sort by record_id using Unicode code-point order. Quarantines, duplicates and superseded
rows sort by source record number. The canonical semantic result has `clean` (objects with the five
normalized fields plus source_row), `quarantine` (source_row, reasons), `duplicates` (source_row,
kept_source_row), `superseded` (source_row, kept_source_row), and `disposition` (source_row, status).
Status is CLEAN, QUARANTINE, DUPLICATE_EXACT, or SUPERSEDED. Every input record occurs exactly once
in the disposition list and the four categories partition the original record count.

## Versions and acceptance

G0 is a newly constructed ordinary Python csv/decimal/calendar workflow, not the historical native
two-column integer adapter. It supports dot/ISO/hold and the complete common output contract.
G1 adds declared comma amounts and dmy dates. G2 adds explicit latest-version reconciliation.
An unsupported job is safely refused and is NOT a billable completed cleanup. No baseline is
claimed unable to reconstruct either capability with ordinary tools.

Confirmation: 24 fresh jobs, eight each simple (dot/ISO/hold), locale (comma/dmy/hold), and versioned
(mixed locale rules/latest). All versions run on all jobs, with balanced order and one attempt each.
Six separately reported stresses cover 50,000 rows, quoted cells, ties/missing/invalids, bad hash,
duplicate headings and invalid UTF-8. No confirmation replacement or outcome-dependent repair.
Exact clean/quarantine/duplicate/superseded/disposition equality against a separately authored latent
oracle plus source/packaging integrity is required. Expected safe refusals in malformed stresses are
safety results, not accepted customer deliveries. Same-session independent checking is not external
customer acceptance. Human effort and commercial demand are not inferred from record count.

Discovery budget: six portfolio families, one new adapter, two capability generations, at most six
development datasets, one frozen confirmation campaign, and one separately frozen economic campaign.
One automated revision is supported by changing explicit rules and retaining both source identities.
Professional judgment, fuzzy entity resolution, Excel workbook edits and confidential inputs are out
of scope. Human retail comparisons must include their additional scope or remain qualified estimates.
