# Independent publication-readiness review

## Disposition

**The registered study is suitable for an additive, source-only draft PR with explicit qualification limits. It is not presently claimed merge-ready, released, deployed, or accepted by native CI.** The draft stays entirely under `studies/beyond-beta-network-v1/`. The complete delivered companion carries the PDF, binary figures, preserved historical archives, and full ledgers. Git carries reviewable source, plain-text result summaries, exact artifact identities, and reproduction instructions.

This review changed no frozen source and ran no additional scientific seeds or old software tests. A read-only hash check verified all **57 frozen files**, with zero mismatches, against protocol SHA-256 `850e6978a3946f8f9d01dd0c6920b49916e955d12b420a65c1241d3c5cd675f6`. Review metadata and policy-source Git objects are recorded in `publication_review.json`.

## Current repository base

The current `main` reference was fetched and rechecked during this review:

| Field | Verified value |
|---|---|
| Repository | `MontrealAI/AGI-Alpha-Agent-v0` |
| Commit | `d28818dc89a92c40d525d7f0c805e95d8be5978a` |
| Tree | `5c20e22a1cb708263e86ad3796f0744caf150668` |
| Parent | `098117379f2920ebe37ab23dad77b7314a32518c` |
| Commit time | `2026-10-26T22:38:28Z` |
| Commit subject | `[ci] Align inherited gallery handoff coverage (#4949)` |

The [Git commit resource](https://api.github.com/repos/MontrealAI/AGI-Alpha-Agent-v0/git/commits/d28818dc89a92c40d525d7f0c805e95d8be5978a) binds the tree and parent. At that source, the study namespace does not yet exist under `studies/`; an exact open-PR search found no matching study PR. These observations are time-bound and should be rechecked immediately before branch creation or integration. The current main SHA is a base identity, not proof of a fully qualified release.

## Rules actually read

The current [AGENTS.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/AGENTS.md), [CONTRIBUTING.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/CONTRIBUTING.md), [PR template](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/.github/pull_request_template.md), [fast-release policy](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/docs/agent/FAST_RELEASE_POLICY.md), [paper-upload guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/docs/agent/PAPER_UPLOADS.md), and relevant current [release-readiness](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/docs/agent/RELEASE_READINESS.md) sections were inspected. There is no `studies/AGENTS.md` at the reviewed base. The underlying PR workflow, release workflow, hook configuration, Ruff target resolver, and binary-integrity checker were also read for the findings below.

The contributor policy explicitly permits opening a draft or PR without completing local hooks, provided every unrun or failed check and its reason is disclosed. This does not waive required hosted checks or authorize bypassing installed hooks. Use a focused title beginning `[alpha_factory]`, below 72 characters, and complete the existing template with actual outcomes. Existing license notices remain intact; new source files use Apache-2.0 headers.

The study is **mixed software and research**, because it adds executable JavaScript, HTML, analysis/reproduction code, and a new study path. The trusted paper classifier routes any code, unknown path, mixed history, or new HTML experience through full software qualification. There is no low-risk study exception in the current policy. A paper-only check would therefore be the wrong acceptance claim, even though the scientific experiment is isolated.

## Binary transport is a concrete gate

The current [binary-integrity checker](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/scripts/check_no_binary_diff.py) rejects new binary extensions including `.pdf`, `.png`, `.zip`, and `.gz` unless the bytes match a finite existing admission or a validated paper-catalog entry. No admission exists for this study directory. The initially contemplated PDF/PNG/ZIP/GZ contribution would therefore fail this blocking integrity check.

The selected delivery plan preserves that gate:

| Destination | Contents |
|---|---|
| Additive Git draft | Model, graph, tests, exact reused upstream sources/licenses, source/evidence register, frozen protocol, TeX/BibTeX, HTML demo, plain JSON/CSV/SVG summaries and figures, audit receipts, artifact identities, reproduction instructions |
| Complete delivered companion | Everything needed to restore the study, including exact PDF/PNG outputs, full JSONL/GZ ledgers, original failed-attempt and checkpoint archives, QA images, source, and exact manifest |
| Later coordinated publication | An optional normal catalog import or versioned research release under the existing publication owner; no such action is part of this draft |

In particular, frozen `protocol/history/pre_paid_learning_unrun_source.zip` has SHA-256 `795218fecdcff29e0d72751c23d49017d6fd26576b6711ef8d37440f867c4aa5`. A source-only checkout lacks that required frozen binary until the user restores the exact companion file. The reproduction instructions must say so. Freeze verification must continue to fail when the archive is absent or different; it must not silently skip the file, regenerate a different archive, change its hash, or treat the source-only checkout as the full experiment packet.

Do not edit the binary gate, create a new exception, rename or encode binaries as text to evade detection, or change the frozen protocol to simplify transport. Plain summary files may be selectively published for bounded review; complete result histories remain in the companion with hashes and replay instructions. Final artifact hashes/bytes must be calculated from the delivered files, not filled with hypothetical placeholders.

## Hosted checks and actual native scope

The exact [PR CI workflow](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/.github/workflows/pr-ci.yml) runs trusted scope classification and separate full lint/smoke jobs for mixed changes. Its stable result contexts are `Lint (ruff)` and `Smoke tests`. Ruff resolves tracked Python files throughout the repository; a new Python helper under this study is not exempt because it is research. The PR smoke job also checks the existing demo catalog. Neither success would establish that every scientific or graph assertion was independently validated.

The [Agent release acceptance workflow](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/.github/workflows/agent-release.yml) and current policy retain source-specific review, applicable exact-main checks, one full offline Python 3.12 regression with an 80% coverage floor, installed runtime checks on Python 3.11–3.13, five representative OS/Python smoke cells, blocking security/integrity hooks, dependency audits, browser/gallery tests, packaging, and actual public-byte/installation acceptance. Formatting-only feedback is advisory in the named policy scope. This is not permission to ignore behavioral, integrity, type, security, or coverage failures.

The existing finite held-source disposition covers five exact native test/helper files and retains four unqualified native outcomes. This study does not modify, adopt, clear, or requalify them. Their owners and action restrictions remain intact. No full native CI, installed four-product tuple, release, Pages publication, or public download/install result is established by the local study tests.

The existing local receipt records seven pre-freeze test programs passing, including the graph's 41 targeted controls. They are correctly scoped as local software observations. This publication review did not rerun them. Full local setup/hooks/type/lint/docs/native checks and hosted checks should be marked **NOT RUN for this draft** unless the publication owner subsequently records actual successful execution on the composed source. Current repository instructions recommend strict docs build and applicable environment checks; their absence must be disclosed rather than silently converted into a pass.

## Frozen summary-field qualification

A targeted integration read found one reporting risk after the prospective freeze. The frozen simulator calculates `summary.retainedCapabilities` by calling `network.available()` at `C.weeks - 1` after completing the full `C.weeks + runoffWeeks` loop. If the graph clock advanced during runoff, the monotone-time guard rejects that historical request and the adapter returns false. The resulting field can therefore undercount the active capability stock as zero. The adjacent `activeAlphaRecords` calculation also combines a historical week argument with final mutable revoked/suspended state; it is not an immutable cutoff snapshot.

This observation is conditional source analysis, not a rerun or a new numerical result. It does not retroactively change recorded cash, jobs, admissions, or uses. Preserve the original frozen summaries and do not label these two fields as validated stock at the operating cutoff. If needed for the paper, a separate explicitly identified analysis may reconstruct the cutoff state from chronological graph/assessment records, or define and report current terminal eligibility. Any correction must retain the original field and disclose its separate analysis scope. No frozen driver was edited here.

The branch-protection read returned HTTP403, `Resource not accessible by integration`. Consequently this review verifies configured workflow names and written policy, not current administrator-enforced branch settings. No protection or permission setting was changed, and no alternative credentials were sought.

## Coordination and ownership

The review retrieved issue4850 and all 543 comments available at inspection, then inspected the current registration, ownership, source-handoff, and release updates. This lane is registered in [6429408648](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429408648), and its 57-file prospective freeze is recorded in [6429820934](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429820934). Related lanes remain distinct:

| Namespace | Coordination record |
|---|---|
| `studies/network-invented-economy-v1/` | [6429585982](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429585982) |
| `studies/beyond-beta-network-foundry-v1/` | [6429320283](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429320283) |
| `studies/agi-alpha-beyond-beta-v1/` | [6429369368](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429369368) |
| `studies/agi-alpha-autonomy-advantage-v1/beyond_beta/` | [6429393290](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429393290) |
| `studies/transformational-numerical-lab-v1/` | [6429774171](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429774171) |
| `studies/agi-alpha-paid-job-alpha-economics-v1/` | [6429681688](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429681688) |
| `studies/paid-work-retained-alpha-v1/` | [6429682900](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429682900) |

These are work lanes reported through the shared coordination account, not evidence of independent institutions or separate external validators. The economics owner in6429681688 requests an exact graph API/source handoff. This study can provide its future immutable draft-commit paths and `createModeledNetwork` API without taking ownership of a production registry or changing another lane's source. The last inspected release-owner update, [6429434705](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6429434705), still distinguishes completed browser checks from remaining release/package/publication work. Its checks do not qualify this draft.

Keep runtime/catalog/README homepage/generated workers, dependency locks, version files, release tags, protection settings, existing manuscripts, and all other study namespaces out of this PR. The module reuses pinned generic authority/commitment/ledger primitives and offers an inert research API; it is not installed into the production runtime. No external comment, PR, branch, dispatch, merge, catalog import, release, or deployment was created by this review.

## Suggested PR qualification statement

> Additive frozen research study under `studies/beyond-beta-network-v1/`. All commercial jobs, calls, purchases, collections, and economic skill effects are modeled. Local lifecycle/crypto/accounting controls are observed software tests with synthetic identity fixtures. This draft includes source and readable summaries; the exact complete companion supplies binary papers, figures, historical checkpoints, and full ledgers. Source-only reproduction requires restoring the manifest-bound historical archive. Local full-repository hooks/setup/docs/native CI, hosted composed-source qualification, release acceptance, and deployment are not claimed. The change is a mixed software contribution, not a paper-only upload. Existing release owners, club contracts/settlement, other studies, and source restrictions remain unchanged.
