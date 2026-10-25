<!-- SPDX-License-Identifier: Apache-2.0 -->
# Historical a163 core verification custody

This directory contains a data-only record of **213 passed and 1 known skip**
for commit `a163b5b3e34551e5dfdf2075c6f69c8cdb3e0c1f` and tree `f276927ce6ff188a729f40c4942b28bc9d4a2f88`. It does not qualify any later commit.
The clean checkout observed while preparing this append plan was
`4d8fb7bccba4e252faaefeefce666f2242b109fa`; that observation is not a transfer of the recorded passes.

All 35 selected original reports are byte-exact. Their individual SHA256 and
Git blob identities are recorded in the separately reviewed append plan.
The failed dependency precheck, DNS acquisition, two legacy collection errors,
one XML/public collection error and final known skip remain visible. Setup
errors were corrected in the isolated QA driver/environment, not erased.

`privacy-license-audit.json` explains retained diagnostic metadata and exclusions.
No database body, private-home content, token, package wheel, provider data,
licensed scanner rule body, source archive or executable is included.
`source-inventory.json` was checked against all 18 actual committed source bodies.

`rollback-snapshots.json` retains only hashes, sizes, schemas and row/fixture
presence counts for synthetic SQLite snapshots. The separately restored
five-column backup accepts the old writer; the upgraded copy retains both old
and new rows. New rows are not automatically usable by that old writer. PG,
actual FAISS, concurrent-writer safety and general crash-safe legacy merging
remain unqualified.

The QA interpreter explicitly used provided QA/primary dependencies.
`dependency-provenance.json` records the only exact wheel installed into that
task interpreter without including its body. This is not a clean application
installation, public runtime installation, native worker or held-test pass.

`cost-summary.json` records scoped observations and unknowns. Human effort,
inference, full lifecycle and monetary costs remain unknown. CPU/wall observations
are separate from mission work units and charged native allowances.

The existing integration lead remains the only publisher. Publication must be
append-only on the existing evidence branch: preserve every existing leaf;
refuse an existing destination with different bytes. This plan changes no ref,
authority grant, runtime, scientific artifact, compatibility scope or incumbent.
