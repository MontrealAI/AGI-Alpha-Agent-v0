# Add a research paper

The paper lane publishes research, not new software qualification. Existing
originals are immutable. Revised manuscripts need a new versioned ID and files.
It never compiles TeX, rewrites a PDF, runs manuscript code, moves a release tag,
or changes an existing software archive.

## One import, then the normal pull request

1. Install the small, hash-locked validator in your development environment:

   ```sh
   python -m pip install --require-hashes --only-binary=:all: -r requirements-papers.lock
   ```

2. Save a small metadata file outside the repository, for example `paper.json`:

   ```json
   {
     "id": "my-paper-v1",
     "title": "My Paper",
     "author": "Author name · Organization",
     "date": "2026-10-21",
     "topic": {"en": "A SHORT TOPIC", "fr": "UN SUJET COURT"},
     "summary": {
       "en": "One accurate sentence describing the study and its limits.",
       "fr": "Une phrase exacte décrivant l'étude et ses limites."
     }
   }
   ```

3. Import the original PDF, and optionally its UTF-8 TeX source:

   ```sh
   python -m scripts.research_papers add --pdf /path/to/paper.pdf --tex /path/to/paper.tex --metadata /path/to/paper.json
   python -m scripts.research_papers check
   git diff --stat
   ```

   Omit `--tex` when unavailable. The importer preserves bytes under
   `docs/papers/<id>.pdf` and `.tex`, records SHA256 hashes, and regenerates the
   README paper block, accessible bilingual homepage cards, and three existing
   lightweight service workers. The default placement is after existing cards;
   reorder catalog records to change presentation order. The first record remains
   the featured paper. Optional metadata fields include `subtitle`, `display_title`
   and `pdf_title`; the last is otherwise read from the PDF's title metadata.
   Do not edit the generated blocks or workers by hand.

4. Commit the catalog, originals and generated outputs together in one commit,
   not as a bare-PDF push followed by a separate metadata push. Review and commit
   only these generated changes and originals using the normal
   pull-request/main process. No release-version bump is needed for a verified
   paper-only upload. Do not commit the temporary import metadata file.

The catalog supports English originals with English/French descriptions. Text is
escaped as data; no HTML, JavaScript or templates are evaluated. Checks require
bounded ordinary files, exact hashes, a PDF title, and passive navigation only.
Academic destinations and clicked HTTP(S)/mailto links remain usable. Automatic
initial navigation and its action chains must stay inside the PDF. Scripts, launch
operations, forms, external file references/attachments, active media and arbitrary
embedded files are rejected. The existing bounded passive C2PA content-credentials
attachment is preserved but is not treated as verification of its claims. A PDF rejection never rewrites the
original; correct the source document explicitly and give revisions a new ID.

## GitHub web editor alternative

Do not upload a bare paper directly to main expecting the fast lane. Create a
branch/pull request first. Upload originals under `docs/papers/` and add a catalog
record (copy an existing non-featured record, supplying the new ID, title, author,
date, EN/FR topic and summary, original PDF metadata title, file paths and SHA256
hashes). Hashes must be calculated from the actual bytes, not guessed.

The trusted pre-change classifier can produce a `paper-preview-…` Actions artifact
containing the five deterministic README/homepage/worker files. Download and
extract it, review the changes, and upload those files to the same branch using
their existing paths. This read-only workflow has no permission to commit for you.
It is a convenience preview, not acceptance, and does not override any failed
check. A local reviewer can run the same importer instead.

Squash-merge the complete reviewed change so main receives one valid paper-only
commit. Intermediate bare-upload or unrendered branch commits deliberately do not
qualify as a paper-only history; their PR can run full checks, but the complete
squash commit on main takes the narrow lane if its proof passes. A normal merge
retaining those intermediate commits requires full qualification. This is the
explicit tradeoff for retaining strict history proof without a write-enabled bot.
The one-command local import avoids that extra download/upload round trip.

## What runs

The pre-change trusted policy inspects every introduced Git commit, not merely
its final diff. Only the catalog, its immutable/new manuscript files, and exact
reproductions of the bounded README/homepage blocks and workers take the paper
lane. Any code, workflow, dependency, template, other README edit, unknown path,
file mode, deletion, mixed change, unavailable history or proof failure requires
full software qualification. Dispatches also require the full lane. Histories are
bounded to 200 introduced commits; a longer chain needs a new software baseline.
Successful paper checks are explicitly not full-runtime historical evidence.

Workflow concurrency includes the exact source SHA before classification, so a
new paper does not cancel an older software run. This intentionally permits some
superseded software work to finish using runner resources; stale software still
cannot publish. Cancellation-aware execution guards do not remove always-run
evidence cleanup.

## Software identity versus paper-site identity

A pending software snapshot remains valid only if every subsequent commit is a
verified paper-only descendant. All runtime tests, tags, wheels, source archives,
release manifests and immutable site packs continue identifying that exact tested
software SHA. A paper upload does not relabel them as accepting the newer commit.

The website overlay waits until its matching software version is public. If it
arrives during software acceptance, successful release completion retries the
latest papers. It restores the exact published site packs, changes only the
verified paper surface, then validates homepage accessibility, bilingual/no-JS
presentation, links and served PDF bytes. No browser/runtime/scanner suite is
substituted for required full software checks on mixed changes.

Live `release.json` retains the software `commit` and version and adds an explicit
`paper_publication` pointer. The separate `paper-publication.json` records the
software baseline, paper commit, catalog hash, overlay hashes and paper-only
validation scope. These are site records, not edits to software release assets.
The unchanged strict site-pack schema remains the software baseline. Preparation
and propagation checks happen outside the shared Pages lock; inside it, current
main, public release identity and monotonically advancing paper provenance are
checked again. Older paper runs and already-public software reruns cannot roll
back a later paper site. If newer software is pending, publication defers instead
of layering its unqualified inputs onto an older release.

## Installing this lane

The catalog, tooling and workflow change itself requires normal full software
qualification. It cannot retroactively turn a prior paper push into accepted
runtime evidence. Keep the current candidate and publish this improvement in a
later fully checked version, or explicitly supersede the unpublished candidate
and qualify the combined source as the next release. That is a release sequencing
decision, not permission to waive checks or republish an existing version.
