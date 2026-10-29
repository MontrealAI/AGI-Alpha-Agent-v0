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

## Recovering a byte-mismatched checkout

Catalog hashes always describe the exact original bytes. A digest mismatch can
mean a local edit or corruption; an older checkout with `core.autocrlf=true` is
another possible cause. The new manuscript attributes protect fresh checkouts,
but updating an existing checkout may retain its previously converted CRLF bytes.
Even the first forced checkout of the new commit may leave those bytes unchanged.
Do not normalize a manuscript, change its catalog hash, or force-reset/clean the
existing worktree to make validation pass. Preserve staged, unstaged and untracked
work there, including any intentionally revised originals that need a new ID.

Use an independent local clone for inspection instead. Linked worktrees share
the original repository's `.git/info/attributes`, whose rules can override the
committed manuscript attributes and convert even a fresh sibling's bytes. Do not
edit those local rules as part of recovery; the independent clone leaves them
untouched and does not copy them. First choose a
specific, verified source commit containing the byte-preserving attributes, or a
previously qualified tag that contains them. Obtain its full commit SHA from a
trusted source and independently check its provenance. Do not assume the latest
main commit is a qualified release. The block below resolves and checks that
explicit SHA locally only after clearing inherited Git routing; it stops if the
commit cannot be resolved.

From the existing repository, substitute that full SHA and choose a unique sibling
destination that does not exist. These commands work without changing the
original worktree's files, index or local configuration. `--no-local` uses
Git transport over the explicit local path, without a network fetch, rather than
copying local object-store links or alternates. Do not use `--shared` or `--reference`:

Use Bash or Git Bash, not a generic POSIX shell. Run the entire parenthesized block:
its subshell clears inherited Git-prefixed variables regardless of letter case
before any Git command, including source-SHA resolution. Native Windows Git
also recognizes names such as `git_object_directory` or `Git_Dir`; an uppercase-only
Bash prefix match would leave them behind. Otherwise routing variables can
redirect writes outside the clone or leave it dependent on external objects.
It then disables global and system Git configuration for every Git command in
the subshell using `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`.
This excludes external execution settings such as `core.fsmonitor`, which are
not disabled by `core.hooksPath`. The original repository's local configuration
is neither rewritten nor copied to the independent clone.
The caller's environment is unchanged. If a variable cannot be unset, or any
Git command or SHA comparison fails, the block stops with a nonzero exit status.
Do not continue to validation after a failed block. The empty `core.attributesFile`
setting disables global attributes, `GIT_ATTR_NOSYSTEM=1` disables system
attributes, and `--template=` prevents configured templates from installing
`info/attributes` in the clone. Apply the attribute settings to both clone and
checkout: `-text` alone does not disable a global smudge filter. These settings
apply only to the commands below and do not change the original configuration.
The command-local `core.hooksPath=/dev/null` also prevents configured hooks from
rewriting files during clone or checkout, without editing or deleting those hooks.

```sh
(
  recovery_env_vars=$(compgen -A variable) || exit 1
  while IFS= read -r recovery_var; do
    case "$recovery_var" in
      [gG][iI][tT]_*) unset "$recovery_var" || exit 1 ;;
    esac
  done <<< "$recovery_env_vars"
  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 || exit 1
  source_sha=FULL_VERIFIED_COMMIT_SHA
  resolved_sha=$(git rev-parse --verify "$source_sha^{commit}") || exit 1
  [ "$resolved_sha" = "$source_sha" ] || exit 1
  GIT_ATTR_NOSYSTEM=1 git -c core.attributesFile= -c core.hooksPath=/dev/null \
    clone --template= --no-local --no-checkout . ../AGI-Alpha-Agent-byte-clean || exit 1
  GIT_ATTR_NOSYSTEM=1 git -c core.attributesFile= -c core.hooksPath=/dev/null \
    -C ../AGI-Alpha-Agent-byte-clean checkout --detach "$source_sha" || exit 1
  recovered_sha=$(git -C ../AGI-Alpha-Agent-byte-clean rev-parse --verify HEAD) || exit 1
  [ "$recovered_sha" = "$source_sha" ] || exit 1
  printf '%s\n' "$recovered_sha"
)
```

Confirm the reported SHA is exactly the chosen commit. Do not add `--force`, reuse
an occupied directory, or delete existing work to clear a destination error;
choose another nonexistent sibling path. Git refuses a nonempty destination.
If the chosen commit is unavailable in the clone, stop rather than checking out a
different source. The clone contains committed source, not the old checkout's
staged, unstaged or untracked edits.
Activate a Python environment containing the hash-locked validator dependencies
from `requirements-papers.lock` (see the installation command above); a fresh
clone does not install dependencies. Then enter the new sibling and invoke the
validator as a module from that repository root:

```sh
cd ../AGI-Alpha-Agent-byte-clean
python -m scripts.research_papers check
```

Passing there establishes that checkout's manuscript validation, not software
release qualification. If the fresh sibling still fails, stop and investigate
the exact file, source commit and catalog instead of rewriting originals or
accepting a different hash. Keep the old worktree and review its local changes
separately; this procedure neither migrates nor discards them. Fresh hosted
Windows checks and all required source-specific release checks remain mandatory.

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

Workflow concurrency retains exact source SHA grouping before classification,
except PR CI supersedes earlier heads of the same pull request. Its replacement
head classifies the complete base-to-head history, not only the latest commit:
a paper commit following unmerged software changes still reruns full software
checks. Other workflows and non-PR events retain their existing grouping; main,
merge-group and manual PR CI runs continue to use exact-SHA groups. Cancelled
superseded runs remain in history and are never treated as passes or inherited
qualification. Cancellation-aware guards retain always-run evidence cleanup;
no current-head checks are removed and stale software still cannot publish.

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

## Optional research resources after full source qualification

The same catalogue can describe a paper's interactive experience and reproducible
companion without creating a second publication index. Schema
`agialpha.research-papers.v1` retains its original closed fields and rendering.
Schema `agialpha.research-papers.v2` permits one optional `resources` object per
paper; all other record fields remain unchanged. The allowed resource roles are:

| Role | Exact fields | Navigation label |
| --- | --- | --- |
| `experience` | `path`, `sha256` | Explore the interactive foundry |
| `companion` | `url`, `sha256`, `bytes` | Download the research companion |
| `source_evidence` | `url` | View source and evidence |

The existing original-PDF link remains the paper's primary action. All labels have
fixed French translations, descriptive accessible names, and static HTML links
that remain available without JavaScript. The extra metadata cannot inject
markup, arbitrary labels, scripts or remote image resources.

An experience is a UTF-8 ordinary file at
`docs/reports/<versioned-study-name>/<simple-name>.html`, with its exact lowercase
SHA256. It is bounded to 25,000,000 bytes. Companion links use this repository's
canonical `https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/download/`
route, a simple release tag and a `.zip` asset name, with exact SHA256 and a
positive integer byte count below 2 GiB. Source-and-evidence links use this
repository's release `tag/` route; when both external roles are present, they must
name the same research release. Queries, fragments, encoded path components and
other hosts are rejected. A declared hash or URL alone is not evidence that an
external asset exists: the publication owner must verify the actual research
release downloads and include their source/evidence receipts before linking them.

Published resource identities are immutable, like paper originals. A changed
experience or companion requires a new versioned paper record. The local importer
can refer to an existing exact experience, but does not install it or execute it.
It rejects missing, changed, executable, symlinked or invalid-UTF-8 local targets
before copying the new paper. Hash checking does not qualify executable code.

**Adding this schema support, its renderer/validator changes, or any new or changed
HTML experience requires full source qualification.** The strict classifier and
the paper overlay's PDF/TEX allowlist are unchanged. Even an HTML change later
reverted within the introduced history requires the full lane. The overlay does
not copy HTML: any linked experience must already be byte-identical in the public
software commit, restored site pack and current checkout. Otherwise preparation
defers without altering the site. A later passive paper update can then link those
already-qualified bytes while preserving all existing software and site files.

Homepage acceptance checks the generated resource links in its existing bilingual,
responsive and no-JavaScript journeys, and binds local/built/served experience
bytes to the catalogue. Study-specific scientific and interaction evidence remains
separately scoped; passing homepage checks does not establish physical correctness,
real demand, contract execution or general autonomous capability. A distinct
research release can distribute a companion without replacing the latest software
release. Neither a research release nor this metadata is permission to bypass the
current software owner's qualification, version and Pages sequencing rules.
