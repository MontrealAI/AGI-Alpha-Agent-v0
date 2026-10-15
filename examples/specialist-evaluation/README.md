# Specialist evaluation: preparation and reported evidence

Additive future-stage route: `/successor/evaluate/`. This implements contract
preparation, immutable byte commitments, strict reported-result comparison and
portable historical recovery. It is **not an independent certification service**.
No protected trial, source verification, organization authentication, provider
call, native execution, spending, wallet action or production admission occurs.

## Customer flow

1. Define one bounded mission and exclusions. Replace the explicitly illustrative
   scaffold with the selected candidate, incumbent and best credible alternative.
   Record why that alternative is credible. Bind exact source, configuration,
   tools, knowledge and interface commitments for all three systems.
2. Freeze the complete contract, including shared protected task-set commitment,
   separate formation commitment, protocol, resource policy, trial count,
   metrics, uncertainty method, hard constraints, reviewer/custodian identities,
   conflicts policy and expiry. Editing any field creates a different digest.
3. Fill the generated report template from actual supplied evidence. Null means
   unknown. Complete all three comparator rows under the same conditions. The
   inspector checks bindings and conservative interval gains; it does not verify
   measurements, uncertainty methodology, source authenticity or task custody.
4. Inspect reported gains, unknown burdens, failures, interrupted/uncertain runs,
   scope and expiry. Each attempt is retained. A failed earlier attempt prevents
   a later successful retry from silently clearing the negative history. Every
   attempt retains its derived comparison, including unknown outcomes. The open
   page refreshes expiry on deadline, focus, visibility and before saving;
   historical record bytes are unchanged.
5. Save/reopen strict JSON. Malformed or changed records are rejected without
   replacing current work. Draft edits hide stale results; the previous valid
   record remains downloadable. Refresh is not persistence: explicitly save.

UI text supports English/French. Machine schemas and status identifiers remain
English. Reports contain commitments and metadata, never a hidden-test payload,
executable path, key, grant or imported trust root. Do not place protected cases,
answers, personal data or secrets inside free-text labels. Different commitments
alone cannot demonstrate disjoint datasets; distinct names cannot establish
organizational independence.

## Three deliberately separate decisions

- `reportedComparison`: local calculation over unverified supplied reports.
  Clear conservative gains over both baselines can produce only
  `reported-comparison-ready-for-review`.
- `independentVerdict`: `not-established`; `verification`: `uncommissioned`.
  An independently governed reviewer registry, conflict checks, sealed-test
  custody, freshness/contamination audit, source verification and signed receipt
  verification are **not implemented or commissioned**. No checkbox or
  self-signed JSON can satisfy these gates. This module has no designation-issuer
  API. `designation` remains `not-earned`.
- `admission`: `not-requested`; `authority`: `none`. Even a future verified
  mission-scoped verdict must not confer operational authority. Beating two
  comparators alone cannot establish general ASI or superiority outside scope.

Seven dimensions are required: quality, cost, time, safety, robustness, human
burden and proof effort. Integer-scaled units and uncertainty intervals avoid
silent floating-point/unknown-as-zero conversions. There is no scalar tradeoff
that lets quality erase a safety or cost regression. Thresholds and valid
uncertainty methods require qualified review before real evaluation.

## Existing evidence paths and integration boundary

Reuses `docs/assets/successor/engine.mjs` canonical serialization, bounded strict
parser and domain-separated digest. `proposalDigest` can reference an exact
Alpha discovery brief; this does not upgrade its hypothesis into evidence.
`bindParticipant` commits supplied exact JSON/UTF-8 material but does not check
its provenance. An evidence digest may refer to an existing native workbench
artifact/report, whose original validator and review/export remain authoritative
for that narrow native claim. This module does not parse or replace native
Jobs/Manager/Fleet artifacts or turn their signatures into independence.

The protected evaluator must retain private cases outside discovery/formation,
provide approved public commitments, and independently establish identity,
conflicts, custody and completeness. No such backend is claimed here. Replacing
candidate/dependencies/conditions requires a new contract and fresh proof.
Restoring historical reports never restores live permission or current trust.

This isolated stage does not alter the frozen discovery/release files. Main
journey linking, gallery/service-worker regeneration and full release admission
must happen in a separately reviewed integration change, not by silently changing
the earlier frozen release. The committed generated page has its own exact
source manifest and hash-only CSP with `connect-src 'none'`.

## Checks and release requirements

```sh
node --test examples/specialist-evaluation/engine.test.mjs examples/specialist-evaluation/app.test.mjs
python scripts/generate_specialist_evaluation.py
python -m pytest --noconftest -o addopts= tests/test_specialist_evaluation_delivery.py -q
AXE_SCRIPT=tests/browser/node_modules/axe-core/axe.min.js python tests/browser/test_specialist_evaluation_browser.py
```

`CHROMIUM_EXECUTABLE` optionally selects an existing installed Chromium.
The dedicated `Specialist evaluation acceptance` workflow requires exact-head
unit/source checks and browser QA, without conditional skipping, and saves
screenshots tied to the tested commit. It covers EN/FR, keyboard activation,
mobile/200% layout, Axe, literal markup, repeated actions, stale edits, interrupted
freeze/import, malformed UTF-8 and historical recovery. Independent source review
and passing exact-head browser CI are required before merge/publication. The
workflow's presence is not proof it passed, nor branch-protection configuration.

`app.test.mjs` runs the actual application source with DOM stubs and a controlled
clock for deadline/focus/visibility/export and retry regressions. These are local
application tests, not a substitute for the required real-browser CI.

The implementation follows the user's four-stage Specialist reference: freeze,
fresh protected work, fair comparison, earned scoped designation. Only the first,
reported-comparison and recovery mechanics are operational here. The fresh-proof
and independent-designation stages are explicit uncommissioned dependencies.
