# Archive-claims research publication handoff

**Decision:** prepare an isolated draft PR adding only
`studies/agi-alpha-archive-claims-v1/`, based on verified main
`47c17f6aca6b1bb8779dd3e47d5ba5f8af3329f4` (tree
`4e3ab01cc5140adc0ab396f6061e16c8fb4855ee`). This path is absent from that tree.
The requested reviewable research package fits the authorized task. It does not
authorize a competing canonical publisher, release allocation or changes to other
owners' branches. This audit performed no publication or external messaging.

## 1. Scope and policy

Read at the exact baseline: `AGENTS.md`, `docs/agent/PAPER_UPLOADS.md`,
`docs/agent/FAST_RELEASE_POLICY.md`, current release-readiness guidance and the
existing PR/release workflow definitions. Main was independently rechecked through
GitHub on 27 October 2026 and still matched the baseline above.

This addition contains code, data, configuration, reproducible evidence and
manuscripts. It is a **mixed source change requiring the full qualification lane**.
The paper-only classifier examines every introduced commit, not just the final
diff. New or changed HTML also requires full source qualification, even if later
reverted. Retained byte-identical dependencies remain research source; their
inclusion is not a new installed-runtime qualification.

Do not change `docs/research-papers.json`, generated homepage/README blocks,
workers, canonical HTML routes, workflows, release versions, historical evidence
or protected production scope in this PR. Preserve original licenses. Use the
repository PR template and a title beginning `[alpha_factory]`. Describe actual
scoped checks and every failed/unrun broader check. Local hooks are recommended;
their absence does not prevent opening a draft. Hosted merge and release checks
are not waived.

## 2. Immediate review edition

1. Freeze the complete deliverables and byte manifest. Confirm every changed path
   is inside the isolated study directory and all prior tree entries are unchanged.
2. Create a uniquely named research branch from the exact baseline and open a
   **draft** PR against main. Read back the resulting commit, parent, tree, file
   modes, sizes and Git blob identities. Refresh main before any later integration.
3. Use the final commit SHA in GitHub `blob/<SHA>/...` links for the complete
   Markdown manuscript and PDF preview. Use the same SHA's raw/download route for
   downloadable bytes. Choose paths from the actual final manifest; never announce
   a guessed future URL.
4. Verify the public manuscript, PDF and companion downloads return the expected
   bytes, recording HTTP outcome, byte count and SHA256. Confirm Markdown is a
   complete readable edition, not merely a table of contents. The PDF should
   already have passed page-by-page visual review.
5. Label these links **immutable research review edition**. GitHub Markdown and
   PDF preview/download satisfy reviewable browser access. Standalone HTML may be
   downloaded for local use; a GitHub HTML source page is not a hosted interactive
   application. Do not describe this state as merged, canonical Pages publication,
   a software release or external peer review.

## 3. Checks before integration and canonical publication

| Stage | Existing requirements |
|---|---|
| Draft submission | Source/readback verification and honest scoped test outcomes; no new permission gate or full-suite pass is implied. |
| Merge readiness | Configured review on the actual final source; applicable hosted checks, including the exact PR verdict names **`Lint (ruff)`** and **`Smoke tests`** from `.github/workflows/pr-ci.yml`. Check other required statuses on that source. A main-only skipped marker on a branch is not a pass. |
| Resulting-main qualification | Successful exact-main push runs of **`ci.yml`**, **`pr-ci.yml`** and **`smoke.yml`**, with their selected full-software qualification markers. The existing `scripts.wait_for_release_ci` verifies these three identities; earlier branch or main checks do not transfer. |
| Full release acceptance | Existing **Agent release acceptance** workflow: one full offline Python3.12 regression/coverage campaign with the 80% floor; strict types, blocking security/integrity hooks, dependency audits, required source/contract/browser/demo gates, installed Python3.11/3.12/3.13 acceptance, and five-cell compatibility smoke (Ubuntu3.11/3.12/3.13 plus macOS/Windows3.12). Required failures, cancellations and unexpected skips block qualification. Named cosmetic formatters remain advisory under the existing policy. |
| Public delivery | Qualified package/site source identity, matching immutable artifacts and manifests, actual clean installation where required, public browser acceptance, and re-downloaded release/PDF/served-HTML byte checks through the existing publisher. No unperformed check is reported as passed. |

Full integration/release checks are requirements for later acceptance, not reasons
to withhold the current research draft. Existing held-source exclusions and their
unqualified outcomes remain exactly as documented; this study does not alter pins
or qualify omitted behavior.

For a later passive PDF/TeX catalog addition, the publication owner can use the
existing `python -m scripts.research_papers add` and `check` importer with a new
immutable paper ID, exact original bytes and EN/FR metadata. Commit the originals,
catalog and deterministic generated outputs together. Such a verified paper-only
addition does not qualify the study's software. A new HTML reader/experience must
first pass full source qualification and be byte-identical in the public software
commit, restored site pack and checkout before a paper overlay may link it.

## 4. Preserve active owners

The current publication correction is **#4973**, head
`d7bd55799f68fc88b76e32b28a27a3e9062bedf6`, for the existing v1.46.1 sequence. It
remains open/draft at this audit. No publisher dispatch or version allocation is
part of this handoff.

Keep runtime owners #4960/#4961/#4963/#4972/#4975 and their #4984/#4985/#4987
children separate. **#4988**, head
`5d89b4ccfd0622433a46f8952285c7b291baf928`, already owns the production engineering
connection from frozen Insight to research artifacts. Our bridge invokes unchanged
main functions inside the study; it does not replace that integration. Related
research #4974/#4977/#4979/#4980/#4981/#4982/#4983/#4986 retains its original
studies and conclusions. In particular, microscopy is #4983; #4988 is engineering.

## 5. Claim boundaries verified in this package

`integration/actual-run/native-controls.json` verifies 44 exact upstream files and
an actual five-job native FusionPlan. Altered plans and Insight scores are refused.
The richer research sidecar preserves **UNPROVEN novelty** and
`flagship_awarded: false`. Neutral supplied scores are provenance fixtures, not
discovery accuracy. Draft bounty base units are inert compiler inputs, not USD,
customer revenue, funds or a transaction instruction.

The unchanged capsule validator refuses the scientific scope. The native local
Journal/TrustRegistry/CostLedger fixture keeps complete profit, obligations and
available funds unknown and refuses completeness. Displayed zero known subtotals
are not zero total cost. Its temporary signing identities are not live ENS or
external verification. No private keys are distributed, and no MARK chain context
is fabricated.

The scientific construction concerns authored finite uncertainty sets. A correct
answer conditional on those sets does not validate actual historical handwriting,
calibration, source completeness or climate claims. The study's commercial model
must stay linked to the same offering, with simulated receipts and actual zero
collections clearly distinguished. No publication step upgrades novelty,
Operational Alpha, retained Alpha or commercial evidence.
