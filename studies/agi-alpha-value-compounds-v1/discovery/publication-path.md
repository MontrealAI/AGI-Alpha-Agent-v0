# Additive publication and integration path

Observed 26 October 2026, 13:30 UTC. This is a read-only integration audit, not publication, release qualification, production activation, or an owner handoff. All existing research, historical URLs, held-action source pins and Security/operator restrictions remain intact.

## Current identities and ownership

The study's Alpha source remains `eb07086ac42799ff45f7b1c946a2f7c514bd3bbc`. Main has since advanced to `804e1afeb78ea48fb4807d76b336803aa0906a20` through #4929 (a reviewed E721 compatibility successor). A new integration branch should use a freshly read base; changing that base must not silently change the study's experimental source. The latest public software release observed was v1.43.0, published 25 October and peeled to `5499495911bf8822ac0aa8c9007f00789c1132b5`. The earlier resulting-main Agent release acceptance run [40323676127](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40323676127) was still in progress when checked. Merged, source-reviewed, released and public-site-qualified are distinct states.

The [09:37 ownership transition](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6412831163) applies only to the four specified qualified contributions, #4917/#4922/#4920/#4921. It preserves Security, binary-admission, held-action, approved-operator, runtime-adoption and release/site gates. It does not grant this new lane a general right to merge unrelated work. The [13:05 lane declaration](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6416712158) preserves current integration/publication ownership and excludes the parallel recurring repair-admission/validation-cost study. Existing #4899/#4915/#4918 held work must not be adopted or amended by this lane.

## Recommended additive layout

Use `studies/agi-alpha-value-compounds-v1/` for the inspectable source, ledgers, protocol, demonstration and reproducibility package, and `agi-alpha-value-compounds-v1` as the immutable paper ID. A read-only directory listing at main `804e1afe` found no existing studies directory name containing value, compound, compat or review; check again before integration. Do not overwrite prior studies or paper IDs.

The implementation and HTML demonstration are executable software. Keep their actual review/classification requirements. A separate passive PDF/TeX import can use the existing narrow paper path after the source is available under a stable commit and its links can be verified. Do not classify a mixed implementation/demo change as paper-only merely because it accompanies a paper.

## Existing paper importer

At the study pin, [`scripts/research_papers.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/scripts/research_papers.py) (Git blob `d517cffc88da41e086ac612dc24673b114c20e73`) is the canonical importer. Run:

```sh
python scripts/research_papers.py --root . add --pdf /absolute/paper.pdf --tex /absolute/paper.tex --metadata /absolute/metadata.json
python scripts/research_papers.py --root . check
```

It copies exact provided PDF/TeX bytes into `docs/papers/<id>.pdf` and `.tex`, appends the immutable entry to `docs/research-papers.json`, and regenerates maintained catalog surfaces. It refuses existing destination IDs and verifies PDF title/passivity. It does not compile TeX. Required metadata are id, title, author, date, topic and summary; bilingual topic/summary must follow the current schema. The usual passive change includes PDF, TeX, catalog, README, homepage and three generated workers. Preserve earlier IDs, records and bytes.

Relevant catalog resources already supported:

| Resource | Required destination and qualification |
| --- | --- |
| `experimental_source` | Exact 40-character source commit URL in this repository at `studies/<slug>/README.md` |
| `current_companion` | Corresponding `main/studies/<slug>/README.md` URL |
| `companion` / `source_archive` | Canonical published-release ZIP download URL with measured SHA256 and byte count; no guessed release URLs |
| `reading` / `experience` | Exact local `docs/reports/<slug>/<name>.html` with hash; executable HTML requires applicable software qualification |
| `tex_source` | Only when the submitted TeX really is standalone |

Parser limits are 512,000 bytes for the catalog, 25,000,000 for a paper or experience and a signed-31-bit numeric bound for companion size. These schema limits do not authorize otherwise held binary uploads or deployment.

[`scripts/paper_changes.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/scripts/paper_changes.py) (blob `44734a69a3ed675913b5944f04093cb93aded12d`) proves exact ancestry and permitted passive deltas. It verifies preservation of earlier catalog entries and generated outputs. Extra source, scripts or executable HTML take the applicable software path.

## Public site and release separation

The [Paper site publication workflow](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/.github/workflows/paper-publication.yml), blob `8d8a257cae21c5d7796954070d18af32886fc0da`, executes trusted main source. Its publisher [`scripts/publish_paper_site.py`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/scripts/publish_paper_site.py), blob `f152887cdd156795e8da533b890a68bf08cc1614`, restores and verifies an already public software release, proves a strict paper-only descendant, overlays permitted passive files, validates the composed homepage, guards against main/source changes and live rollback, and then verifies publicly served paper bytes. It does not create a software release, wheel, source archive or tag. Mixed changes defer to full software acceptance. A prior green paper workflow is not evidence that this new paper or demo is live.

For this study, a reviewable source commit/draft PR is a concrete deliverable even while publication gates remain pending. Public publication should only be claimed after actual accessible URLs and expected bytes have been checked. Catalog resource records should refer only to destinations that exist and meet their required identity conditions.

## Available credential-free connector operations

The existing GitHub connector exposes the following mutation capabilities. They were inspected but never invoked during this audit; no credentials were created or requested.

```text
create_blob(repository_full_name, content, encoding='utf-8'|'base64')
create_tree(repository_full_name, base_tree_sha?, tree_elements[])
create_commit(repository_full_name, parent_sha, tree_sha, message, additional_parent_shas?)
create_branch(repository_full_name, branch_name, exactly one of sha/base_ref)
update_ref(repository_full_name, branch_name, sha, expected_sha?, force?)
create_pull_request(repository_full_name, base, head, title, body, draft, maintainer_can_modify?)
```

No per-payload cap is documented in these tool schemas. Read `github_fetch` permits approved GitHub GET resources but rejects oversized/non-UTF8 responses and binary downloads. Binary blob encoding support does not override binary admission or authorize execution.

For an already authorized reviewable contribution, the conservative additive sequence is: freshly read base commit/tree; create immutable content blobs; make a tree based on that exact tree; make a commit with that exact parent; create a new isolated branch; open a draft PR with exact qualification status and unresolved restrictions. Never update main or another owner's branch. A later branch update should use the expected-head lease, inspecting a rejected lease before any retry. Do not force-update publication history or manufacture a passing review state.

The [repository instructions](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/AGENTS.md) use an `[alpha_factory]` PR title under 72 characters and require honest test/lint reporting. Local full-environment setup is not a prerequisite to opening a draft, but required hosted reviews/checks remain blocking. The [fast-release policy](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/eb07086ac42799ff45f7b1c946a2f7c514bd3bbc/docs/agent/FAST_RELEASE_POLICY.md) preserves the existing Security, binary-integrity and exact held-source restrictions; no new study warrants modifying them.

## Confirmation preparation status

`curation/build_confirmation_registry.py` is ready and syntax-checked. It consumes only a completed exact source custody inventory, metadata v3 (SHA256 `eeddceae75c6b10c97369da9baff2fc69928e9e9fe3c0025499c2529e846160e`) and the captured 56-file Alpha consumer scope. It verifies raw bytes and inventories and emits a separate mission registry. Neither this registry construction nor primary confirmation retrieval has run. Requests, FastAPI and urllib3 confirmation bodies remain unopened pending the lead's explicit final-freeze signal. No primary outcomes informed these publication recommendations.
