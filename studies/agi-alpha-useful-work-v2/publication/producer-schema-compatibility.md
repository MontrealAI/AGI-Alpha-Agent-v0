# Producer compatibility and the existing product importer

**The shared `alpha-component-decision/v1` label does not identify one identical field layout.** The corrected first-delivery record and the three primary producers use different documented shapes. A product importer written for the first delivery must not assume that every new record carrying this label is compatible. This note inventories actual JSON bytes; it introduces no adapter, replacement schema, acceptance rule or frozen-source change.

The existing product-owner handoff concerns the corrected first-delivery shape. The completed study verifies local SUCCESSOR Workbench execution for retained B and conventional C. It does **not** establish that `contrib/upgrade_decision` imports and renders all three fresh producer formats. That integration and any product adoption remain with the existing owner.

## Exact field matrix

All four examples contain `schema`, `mission_id`, `phase`, `decision`, `before_versions`, `after_versions`, `remaining_customer_work`, `limits` and `cost`. Their field-level differences are material:

| Information | Corrected first delivery | Manual A | Retained B | Conventional C |
|---|---|---|---|---|
| Record schema | `alpha-component-decision/v1` | Same label | Same label | Same label |
| Explicit producer discriminator | No `producer` or `arm` field | `producer: researcher-finalized-incumbent-template` | `arm: retained`; no `producer` field | `producer: independent-conventional-unittest-package` |
| Recorded phase | `exposed-development` | `confirmation` | `confirmation` | `confirmation` |
| Recommended action | `useful_action` | `useful_action` | `action` | `useful_action` |
| Required-case count | `coverage.requirements` | `coverage.requirements` | `cases` | `coverage.requirements` |
| Before passing count | `coverage.before_pass` | `coverage.before.PASS` | `verification.before.counts.PASS` | `coverage.before.PASS` |
| After passing count | `coverage.after_pass` | `coverage.after.PASS` | `verification.after.counts.PASS` | `coverage.after.PASS` |
| Mismatch/incomplete counts | No top-level count fields; inspect the referenced verifier evidence | `coverage.before` and `coverage.after`, keys `BEHAVIOR_MISMATCH` and `INCOMPLETE` | `verification.before.counts` and `verification.after.counts`, same keys | Same as A |
| Before/after verifier status | Referenced evidence, not a top-level `verification_status` object | `verification_status.before` / `.after` | `verification.before.status` / `.after.status` | Same as A |
| Registered job hash | No top-level `job_sha256` | `job_sha256` | `job_sha256` | `job_sha256` |
| Contract hash | Referenced evidence | Referenced evidence | `contract_sha256` | Referenced evidence |
| Consumer source identity | `coverage.consumer_source_revision`, `coverage.current_equal_source_revision`, source links and evidence | Registered job and copied/bound source evidence | `source_identity` with directory and exact `api_sha256` / `models_sha256` | Registered job and copied/bound source evidence |
| Explicit local useful-outcome flag | No boolean; scoped decision plus acceptance prose | No boolean; scoped decision plus acceptance prose | `useful_outcome_accepted` | No boolean; scoped decision plus acceptance prose |
| Explicit external customer-acceptance flag | No boolean; acceptance prose limits the claim | No boolean; acceptance prose limits the claim | `customer_acceptance_observed: false` | No boolean; acceptance prose limits the claim |
| Custody issue field | First-delivery evidence/assembly records | `custody_errors` | `custody_failures` | `custody_errors` |
| Researcher decision provenance | First-delivery assembly record | `manual_disposition` plus separate recorded finalization | Automated retained producer records | Automated conventional producer records |
| Embedded evidence binding list | `evidence` | `evidence` | Common packet evidence/manifest and job/source hashes; no top-level `evidence` list | `evidence` |

All sampled records preserve `cost.marginal_money_usd`, `cost.recurring_money_usd`, `cost.fully_loaded_money_usd`, `cost.customer_price_usd`, `cost.customer_minutes` and `cost.operator_minutes` as `null`, with `cost.actual_customer_receipts_usd` equal to zero. Other process-quantity fields differ by producer. Missing fields must remain missing or explicitly unknown; they must not be silently rendered as zero money, zero customer effort or successful acceptance.

The adjacent `requirement-results.json` also differs. A and C emit a mapping with complete `before` and `after` verifier-case lists. B emits a per-requirement list with `id`, before/after status, source reference and after-error details. This is relevant to any importer that displays individual requirements. Patch headers differ as well: A uses `baseline-component.lock` → `proposed-component.lock`; B uses `before-component.lock` → `proposed-component.lock`; C uses `before/component.lock` → `proposed/component.lock`. The actual patch content was independently checked against each registered before/after lock.

## Exact examples inspected

| Producer | Actual record | SHA256 |
|---|---|---|
| Corrected first delivery | [first-delivery-corrected/decision.json](../results/development/first-delivery-corrected/decision.json) | `42aac09cb79ff440d7686b9a917f94936dd7b0b66cb71a708205a59891330cf8` |
| Manual A | [starlette-1/manual/package/decision.json](../results/confirmation/starlette-1/manual/package/decision.json) | `983e89f9ced816ec582efb3c40774f7b524343aaf7d7d8a13b9128196040a8cf` |
| Retained B | [starlette-1/retained/delivery/package/decision.json](../results/confirmation/starlette-1/retained/delivery/package/decision.json) | `2ac88132f4b206f1c2d6caa87e4230f35f15880f4f8d5c5d2ee6a80ff87b02e7` |
| Conventional C | [starlette-1/conventional/delivery/package/decision.json](../results/confirmation/starlette-1/conventional/delivery/package/decision.json) | `bbfa5adebb192f22bacc6d8ea2be19962a50f205f0e634e1a34d6b77521e3c4e` |

These examples establish the field matrix. The separate [post-campaign custody review](../discovery/postcampaign-custody-review.md) checked all 18 primary records, not only these examples. Its record is `results/review-controls/postcampaign-custody-v3/review.json`, SHA256 `d3ab95a56f9629cef05c82fb5261df3e8b5f98c87b26c6b0a978789e28244eff`.

## Advice for the existing owner

Validate a recognized producer shape and its exact source/job/evidence bindings before rendering. The shared schema label alone is insufficient dispatch. An explicit owner-maintained compatibility adapter or a future versioned envelope can normalize the display fields, while retaining the original packet, original hash and any missing/unknown values. Unknown or inconsistent shapes should remain unsupported rather than receive guessed action, count or success values.

Integration should demonstrate the four concrete examples above, plus incomplete and regression records, through the actual importer and renderer before claiming compatibility. Such validation is future product work unless separately recorded by that owner. Do not alter these frozen study records to make an importer pass; preserve the original edition and record any new adapter or schema revision separately.

The local Workbench results remain `PUBLIC_LOCAL_EXECUTION` with admission `HOLD`, authority `[]` and settlement `NOT_CONNECTED`. Their inspections remain `UNAUTHENTICATED_HISTORICAL_IMPORT`, with no active proof or authority. Successful local B/C execution therefore supplies neither product-importer qualification nor a release, operator or financial authorization.
