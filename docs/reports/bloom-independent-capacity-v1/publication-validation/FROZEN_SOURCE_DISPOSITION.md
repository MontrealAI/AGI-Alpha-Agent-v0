# Frozen-source lint disposition: explicit owner decision remains necessary

The current publication policy supports an immutable experimental companion and complete source archive. It does **not** automatically waive required Ruff findings for a source PR, or turn archived executable code into qualified runtime code.

## Smallest defensible action

Keep the original 23-source freeze, all scientific evidence, original source commit `1620454d5f29bdbc4c2a71c5ebb895e8ee6a666b`, and complete ZIP `3f272f0ac00bc2ce7f417aa99c1daf127a1c739853b1d7719d13c65db3c76c50` unchanged. Supply the existing receiving owner the exact companion and source identity, the actual six Ruff findings, and a concrete request to determine whether the edition is accepted as an explicitly experimental research companion under the existing archive convention. That decision must distinguish archival publication from repository runtime qualification. The existing full source/HTML/release checks remain required for their own changed surfaces. Do not rename Python, suppress findings, change exclusions, or recast a failing check as passed.

Until that owner disposition and normal qualification, the source PR remains blocked. The verified paper, public commit, complete source/evidence archive and runnable local demonstration can still be delivered with that status explicit. No policy requires inventing a new release to settle a packaging decision.

## Exact sources

- [PAPER_UPLOADS.md at current main197147](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/docs/agent/PAPER_UPLOADS.md): “Optional research resources after full source qualification” permits a distinct research release companion, requires actual external-download verification, preserves immutable resource identities, states that hash checking does not qualify executable code, and preserves the software owner's qualification/version/Pages sequencing. New or changed HTML still requires full qualification.
- [research_papers.py at197147](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/scripts/research_papers.py): `resource_records`, lines108–161, implements native `companion` and `source_archive` fields `{url, sha256, bytes}` with canonical repository release-download URLs and matching `source_evidence` release tag. `experimental_source` permits an immutable commit-pinned study README. These are metadata roles, not executable-code acceptance.
- [paper_changes.py at197147](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/scripts/paper_changes.py): `prove_transition` rejects software/mixed/unknown paths from its passive paper allowlist. The current PR remains full scope; an archive role does not rewrite its introduced history.
- [ruff_targets.py at197147](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/197147ffd22c5ae13113162afffaf3ce9c10aa2e/scripts/ruff_targets.py): tracked Python targets run in batches of200 and stop at the first failure. The six observed docs-copy findings are not an exhaustive report on all later study paths.
- [Receiving boundary6377105309](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6377105309): the existing coordinator owns shared-index/merge/Pages intake for exact final PDF/TeX/archive plus source PR/commit and must acknowledge intended current main before shared edits. There is no separate archival receiving approval recorded for Writer7 yet.

## If a maintained conformance release is later requested

Create a separately identified **post-study** version and manifest, retaining the canonical measured version unchanged in its existing archive/commit. A semicolon-to-line-break rewrite can preserve the parsed AST. An assigned-lambda-to-`def` rewrite changes the raw AST and cannot be called an identical-AST transformation: record the exact limited transformation and test its relevant behavior. Recheck deterministic cases and qualification/boundary outcomes; report those as engineering reproduction of a revised implementation, not fresh confirmation or retroactive evidence for the original source bytes. Timing measurements from the old code do not become measurements of the revised version.

The actual runner checks every frozen source hash in `run_study.check_freeze()` and will reject changed code against the original freeze. Do not edit the old timestamp/hashes to make a post-study version appear preregistered. A new post-study inventory can be explicit, while the original reproduction entry point remains available in the unchanged archive. Such a release is larger work than a receiving decision and is not needed to make the existing failed hypotheses and useful demonstration inspectable.

No edits, exceptions, reruns, remote writes or held operations were performed for this assessment. The subsequently reported pinned PDF validator pass is independent of the lint failure.
