# Publication handoff — shared-observation study v1

## Requested disposition

Submit this additive research package as a **draft pull request scoped to
`studies/agi-alpha-shared-observation-v1/`**, and record the exact draft source and
evidence in coordination issue [#4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850).
Keep the PR draft until the normal configured review and applicable checks have
completed. The existing publication owner decides integration and publication
sequencing. This handoff allocates no release version, moves no owner branch or
release tag, dispatches no publisher, and claims no deployed canonical reader.

The recorded local static gate is not fully qualified: Ruff passes, while strict
mypy reports three typing errors on the exact frozen research compiler (an Any
return and optional-value subtraction). Black cannot import the installed
pathspec dependency. These findings are preserved in
`evidence/scoped-static-checks.json`; no hosted check or source requirement is
waived. Scientific confirmation remains bound to its original frozen source.

**Title:** AGI ALPHA FLYWHEEL — When Capability Creates Opportunity  
**Subtitle:** Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work  
**Attribution:** Vincent Boucher — President of MONTREAL.AI

The study begins from main source
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`. Its prior research reference is
`231834269599d85e49cfe1ca9917a1a874522d44`. These are study provenance, not a
claim that either source qualifies this new publication. The final draft commit,
tree, file sizes and document/package SHA-256 values belong in the final delivery
manifest and PR receipt after rendering and packaging are complete.

## Deliverables offered for review

Paths in this table are relative to this study directory. They are local or
repository artifacts, not evidence of a live public website.

| Artifact | Review source |
| --- | --- |
| Research manuscript | `paper/manuscript.md` |
| Compiled paper | `paper/AGI_Alpha_Flywheel.pdf` |
| LaTeX and its build inputs | `paper/AGI_Alpha_Flywheel.tex`, `paper/references.bib`, `paper/figures/`, and the complete `paper/` source directory |
| Browser-readable edition | `paper/AGI_Alpha_Flywheel.html` |
| English/French demonstration | `docs/English_French_Demonstration.html` |
| Executive brief | `paper/executive_brief.md` |
| Reproducible instrument and independent evaluation | `capability/`, `data/`, `evaluation/`, `economics/`, `integration/`, `scripts/`, and `reproduction/` |
| Protocol, source freezes, receipts and retained failures | `evidence/`, `development/`, `results/`, and `evaluation/confirmation-v1/` |
| Publication instructions | This file and the final delivery manifest |

All earlier study editions, approved original PDFs, catalog entries, worker
identities and owner histories remain preserved. No existing paper record is to
be silently reused for these different bytes.

## Why there is no immediate paper-overlay deployment

The checked repository already supplies a publication mechanism. This study
does not need a second catalog, website publisher or release mechanism.

- `docs/agent/PAPER_UPLOADS.md`, “What runs,” restricts the passive paper lane to
  the catalog, immutable/new manuscripts and exact deterministic presentation
  output. Code, unknown paths, mixed changes and unproved history require full
  source qualification. A study-directory-only research PR is therefore **not**
  automatically a paper-only publication change.
- The same guide, “Optional research resources after full source qualification,”
  explicitly requires full source qualification for every new or changed HTML
  experience. The classifier and overlay allowlist do not acquire an HTML
  exception because a page is called a reader or a research artifact.
- `scripts/research_papers.py:experience_hashes` includes both `reading` and
  `experience` resources. `scripts/publish_paper_site.py:require_qualified_experiences`
  requires each linked HTML file to have identical bytes in the qualified
  software source, its restored public site pack and the current checkout. It
  does not copy a new HTML file into the passive overlay.
- `scripts/publish_paper_site.py:prepare` requires an exact clean current-main
  checkout, a fully public matching software release, a strict paper-only
  descendant proof and intact released site assets. A study branch or an
  unqualified HTML addition does not meet those conditions.
- `docs/agent/FAST_RELEASE_POLICY.md` reduces specified repeated checks; it does
  not change deployment permissions, waive exact-source or artifact integrity,
  reuse unqualified historical results, or turn unperformed checks into passes.

A later **separate passive PDF/TeX/catalog change** may use the existing narrow
lane without a software-version bump if its complete history independently
qualifies and the matching software baseline is public. That possibility does
not publish this new browser edition and is not a bypass for its HTML or code.

## Existing owner and sequencing evidence

The stored `evidence/coordination_snapshot.json` was observed at
**2026-10-27 16:52:36 UTC**. It is a dated coordination observation; refresh the
owner's current disposition before any merge, publication or dispatch.

| Evidence | Consequence for this handoff |
| --- | --- |
| [Comment 6444554230](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6444554230) | The minimal v1.46.1 patch was reserved for the two already approved paper readers, after the existing v1.46 lease. It did not allocate a general next release or import unrelated runtime work. |
| [Comment 6445666386](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6445666386) | The same #4969 publication owner continued exact-source review and qualification; public readers still depended on eligible integration and served-byte verification. |
| [Comment 6447589625](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6447589625) | Main had advanced to `47c17f6a` through #4969. The handoff explicitly preserves its v1.46.1 publication/install closure and the #4960/#4961/#4963 owner histories; it allocates no successor release and dispatches no publisher. |
| `docs/agent/RELEASE_NOTES_1.46.1.md` | The existing publisher alone owns release and Pages deployment; a new reader requires its own configured exact-source review, applicable PR checks, resulting-main acceptance and independent public verification. |

This study preserves #4960, #4961, #4963, #4969, #4970 and #4972 ownership and
the other declared research lanes. It requests a reviewable research disposition,
not priority over another owner's integration or release.

## Minimal actionable owner handoff

1. **Review the isolated draft.** Bind the PR to its exact final commit/tree and
   delivery manifest. Review the manuscript, actual recipient receipt,
   independent evaluation, economic corrections, provenance, rights and original
   failures together. Record the checks actually performed and all remaining
   applicable checks. Local study checks are not full repository or production
   qualification.
2. **Choose the existing integration lane.** After checking current #4850
   sequencing, the existing owner can include the browser assets in an eligible
   qualified source integration. This study proposes no version number and does
   not reopen or supersede the reserved #4969 publication.
3. **Use the existing catalog if publication is accepted.** A suitable new,
   immutable ID is `agi-alpha-shared-observation-v1`, subject to a fresh collision
   check by the owner. Intended destinations are
   `docs/papers/agi-alpha-shared-observation-v1.pdf`,
   `docs/papers/agi-alpha-shared-observation-v1.tex`,
   `docs/reports/agi-alpha-shared-observation-v1/index.html`, and
   `docs/reports/agi-alpha-shared-observation-v1/demonstration.html`.
   These are proposed integration paths, not files already installed in the
   canonical site. Preserve exact reviewed PDF/TeX bytes, the requested byline,
   bilingual descriptions, research limits and accessible fallback content.
   Copy the complete build sources with the research companion; do not imply
   that an isolated TeX file reproduces external figures or other dependencies.
4. **Import and validate through the maintained tooling.** Once approved HTML
   files and exact metadata exist in the owner's integration, use
   `python -m scripts.research_papers add --pdf <approved-pdf> --tex <approved-tex> --metadata <temporary-metadata-json>`
   and `python -m scripts.research_papers check`. The importer uses the existing
   `docs/research-papers.json` schema and regenerates bounded presentation.
   Do not hand-edit generated blocks or workers. `reading` and `experience`
   resources carry exact local paths and SHA-256 values. Add a commit-pinned
   `experimental_source` link only after the corresponding remote source exists.
   Add release-download companion links only after the owner has verified their
   actual public bytes; a planned URL or declared digest is insufficient.
5. **Complete the applicable source and publication gates.** New HTML requires
   full source qualification, configured exact-source review and applicable PR
   checks. The resulting main must satisfy the existing acceptance, security,
   coverage, integrity, browser, artifact and installation gates. Under the
   current fast-release policy, the full offline Python 3.12 campaign retains
   its 80% coverage floor; installed runtime acceptance remains on Python
   3.11/3.12/3.13. Named advisory formatting checks must not be misreported as
   blocking gates, and blocking Ruff, type, security and integrity checks must
   not be omitted. Any exceptional finite coverage disposition remains exactly
   scoped by its existing policy and owner.
6. **Let the existing publisher deploy and verify.** For a qualifying later
   passive overlay, the existing `Paper site publication` workflow prepares and
   validates outside the Pages lock, rechecks current main/public baseline and
   monotonic provenance under the shared `github-pages` lock, and verifies
   served bytes after deployment. A full source integration instead follows its
   existing software publication process. Preserve software identity in
   `release.json` and separate any paper-overlay provenance. Record the stable
   reader URL only after the authorized workflow and independent served-byte
   verification succeed.

The proposed canonical reader route is
`https://montrealai.github.io/AGI-Alpha-Agent-v0/reports/agi-alpha-shared-observation-v1/`.
**This is a proposed future route, not a verified live link.** No alternative
Pages, raw-content renderer or separate hosting deployment is authorized by
this handoff.

## Required scientific scope on the public reader

The public edition must retain the distinction between executed local software
and modeled observations, customers, acceptance, collections and costs. The
finite Bayesian model uses supplied synthetic probabilities and model-time
deadlines; it does not implement orbital propagation, calibrate a real sensor,
authorize a maneuver, authenticate live ENS identities, or establish operational
spaceflight safety.

The retained compiler matched the independent conventional reference on all
48 protected fresh missions, including valid plans and correct refusals. This is
conformity evidence, not measured superiority over the competent exact method.
Actual recipient transfer and identical-content ordinary-library parity are
preserved. The conditional source offering can produce a modeled contribution,
while the complete modeled campaign loses money, all 48 primary fresh acquisition
orders are declined, and additional commercial retention is rejected. No live
customer revenue, profitable network compounding, measured frontier-model
Operational Alpha or graph-specific advantage is established. AI-assistance and
researcher-construction disclosures remain visible.

## Suggested coordination message after the draft exists

> Additive shared-observation research handoff for **AGI ALPHA FLYWHEEL — When
> Capability Creates Opportunity**, Vincent Boucher — President of MONTREAL.AI.
> The draft PR is restricted to `studies/agi-alpha-shared-observation-v1/` from
> base `47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4`; its final source/tree and
> document/package identities are in the attached delivery manifest. Executed
> independent finite-model conformity and actual artifact transfer are separated
> from conditional commercial modeling, correct refusals and the campaign loss.
> The package includes PDF/LaTeX, reproducible code/data, evidence, executive
> brief and EN/FR browser assets. Please retain the existing #4969/v1.46.1
> publication/install owner and all runtime/research owner histories. The PR
> remains draft pending normal review/checks. No release is allocated and no
> publisher or Pages workflow is dispatched. New browser HTML requires the
> existing full source qualification; the passive paper overlay is not a bypass.
> `publication/HANDOFF.md` gives the exact integration and verification gates.

Replace the draft reference and manifest reference with their actual verified
identities before sending. This template does not itself create a remote PR,
issue comment, release asset, publication approval or public-site receipt.
