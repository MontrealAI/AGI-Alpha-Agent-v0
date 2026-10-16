[Project notice](../../docs/DISCLAIMER_SNIPPET.md)

# A continuing local public-data mission

The additive `docs/successor/mission/` workspace uses the existing public-data
engine without modifying it. Its five views keep the mission, result, checks,
permissions and history together. This initial slice is a supplied-input CSV
reconciliation task, not a model-driven or commissioned remote executor.

## What persists

Each record binds a mission ID, revision, exact source hash, strict specification,
run ID, resulting artifact package and optional self-reported local review.
IndexedDB commits the revision comparison and replacement in one read/write
transaction. Competing tabs cannot both replace the same revision. A conflict or
failed storage operation closes editing until explicit recovery. This is local
browser persistence, not cross-device synchronization or protection against
same-origin malicious code or a compromised browser.

Reloading does not rerun work. A retained running record requires an explicit
interruption transition before another run. External imports are historical,
read-only observations; creating a new draft requires an explicit action and a
new mission identity. Imported acceptance, execution authority and payment
permissions are never restored. A changed source hash makes stored records
historical and read-only. Hashes establish consistency, not authenticity.

The generated source manifest hashes every imported module, the wrapper
presentation and its generator. Review and release receipts must also name the
exact repository commit tested; the content hash is not a claim of deployment.
Result validation recomputes the bounded deterministic report and checks exact
artifact content, rather than accepting a forged result merely because its
hashes were recomputed.

## Limits and recovery

- 12 local missions; 2,000,000 UTF-8 bytes per record; 16 prior observations.
- Public, synthetic or licensed nonpersonal two-column `group,amount` CSV.
- Exact integer amounts; no inferred currency, deduplication or decimal mapping.
- Three bounded artifacts, with explicit byte and aggregate output limits.
- A saved file is a backup. Browser storage may be cleared or unavailable.
- Provider and settlement spend are zero for this local task; device compute
  cost and actual human effort are unknown.
- Local review does not grant marketplace admission, external execution or
  settlement. Fleet commissioning and Jobs/Manager protocols remain separate.

No automatic adapter exists between this integer schema and Manager's
`id,category,value` decimal schema. That requires an independently reviewed,
lossless semantic mapping and its own compatibility evidence.

## Qualification

Run `node --test examples/successor-workbench/mission-record.test.mjs` and the
unchanged `node examples/successor-workbench/test.mjs`. Generate with
`python scripts/generate_successor_mission.py`, then run the two
`tests/browser/test_successor_mission_{store,browser}.py` scripts with the pinned
Playwright Chromium installation. Set `AXE_SCRIPT` to the installed, locked
`tests/browser/node_modules/axe-core/axe.min.js` for accessibility qualification.
The browser test explicitly reports when that audit is absent.

The recovery test imports an accepted historical record into a fresh browser
context with empty storage, creates a new draft,
changes the dataset and observes a different computed result (295 to 50), with
no inherited current review. This proves a different supplied-data task within
one family, not compatibility with all other work families or repositories.

Injected application tests cover persistence failure at run start, completion and
STOP, plus initial and post-commit index corruption. A failed write leaves the
retained database unchanged and exposes a read-only, explicitly unpersisted copy
for export. An acknowledged write followed by index failure remains marked as
committed, while further execution closes.
