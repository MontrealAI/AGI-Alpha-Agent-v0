[Project notice](../../docs/DISCLAIMER_SNIPPET.md)

# Sparse supplier delivery: one bounded improvement

This is an additive child of PR #5011 at `dc6027f35bfede9060e525772aa1e38f59b34158`.
It integrates the previously local supplier-delta adapter and repairs its packet checker.
The existing catalogue engine is unchanged. It is not a new invention runtime, ledger or release.

## Run from the repository root

Python 3.11-3.13; the bounded command uses the standard library, no provider key and no network.
Choose a new output directory on every attempt; existing evidence is not overwritten.

```sh
python -m contrib.enterprise_campaign.delta_delivery \
  --before contrib/enterprise_campaign/delta_examples/before.csv \
  --delta contrib/enterprise_campaign/delta_examples/updates.csv \
  --keys sku --write-fields price --decimal-fields price \
  --aliases '{"product_code":"sku","new_price":"price"}' \
  --output /tmp/alpha-delta-first
```

The example changes A's price from 10.00 to 12.50. B, C and local notes remain intact.
The result includes `updated.csv`, `safe-preview.csv`, `rollback.csv`, `package.json`,
`request.json`, `acceptance.json`, `usage.json`, `transfer-record.json` and `REPORT.md`.
Do not open arbitrary machine CSV cells as trusted spreadsheet formulas; review the separate escaped preview.
The preview policy is the existing engine's policy, not universal spreadsheet security certification.

Check the packet in a separate read-only process using the original inputs and the approved request:

```sh
python -m contrib.enterprise_campaign.delta_acceptance \
  --before contrib/enterprise_campaign/delta_examples/before.csv \
  --delta contrib/enterprise_campaign/delta_examples/updates.csv \
  --request /tmp/alpha-delta-first/request.json \
  --package /tmp/alpha-delta-first/package.json

python -m unittest contrib.enterprise_campaign.test_delta_delivery \
  contrib.enterprise_campaign.test_delta_packet -v
```

The request must match the operator's intended keys, writable fields and aliases. Do not treat a request
supplied by an untrusted producer as its own authorization. Hashes bind bytes, not semantic truth or identity.
The checker does not import the producer or its helpers, and it does not edit the candidate. Both share the
host, author/session and libraries: procedural separation only, not an independently secured or external verifier.

## Four mechanisms, one delivery

| Mechanism | This iteration |
| --- | --- |
| Structural transfer | Apply transactional partial-update semantics: omitted items are unchanged, not deleted. |
| Executable adaptation | Convert a sparse feed to a complete after-image and reuse the existing native patch and rollback. |
| Adversarial verification | Independently reconstruct the entire expected packet, including preview, changes and counts. |
| Retention | Keep counterexamples as regressions and write a scoped transfer record with each successful delivery. |

The structural mapping was supplied by the developer. No frontier-model analogy discovery, general strategy
synthesis or recursive invention was executed. The conventional implementation matches the intended output.
Do not call this an advantage over competent conventional software, or a transformational flagship.

## The defect that justified this investment

The original local add-on's checker accepted four altered packets after their hashes were recomputed:
an unsafe substituted preview, an empty change list, a false original-row count and a substituted producer identity.
The original 26 software tests nevertheless passed. This was a gap in the add-on's standalone acceptance scope;
the normal delivery command also calls the unchanged native apply/rollback revalidation. These probes did not
establish that the native engine or the complete original CLI accepted those forged packets.

The correction reconstructs every native field from the trusted inputs, checks exact field sets, source identity,
native and enclosing digests, the change list, escaped preview and trace. Canonical comparisons distinguish
booleans from integer counts. All four original counterexamples are rejected. Malformed containers return rejection.

`DELTA_QUALIFICATION.json` records scope, source identities, tests, known gaps and the earlier outcomes.
The earlier standalone ZIP remains historical evidence; its passing tests are not relabeled as full verification.

## Contract and boundaries

Update existing keys only. Explicit aliases and writable fields; no inserts, implicit deletes or inferred authority.
Preserve membership, original row/header order, untouched fields and exact original rollback bytes.
Inputs remain bounded to 200,000 UTF-8 bytes, 1,500 rows, 32 columns and 4,096 characters per cell.
Blank text updates are intentional; blank/nonfinite decimal values refuse. A header-only feed is a no-op.

The CLI creates a local review packet, not a remote catalogue update. Output is not an atomic directory transaction;
a failed write may leave an incomplete directory, which must not be treated as delivered or reused as fresh output.
The separate packet check verifies the JSON packet against trusted inputs, not arbitrary later changes to all sibling
files. Inspect/read the packet's source-bound output or recheck exported files before use. Work in an operator-owned
local directory; this is not a malicious-host sandbox or a production publication channel.

The usage record measures elapsed time through CSV writes, before remaining JSON/report serialization. It is not a
complete labor or monetary cost. No exact-dollar cost is inferred. Complete actual cost and profitability are unknown.
There were no paid model calls, customer acceptance, revenue, payments, outreach or remote writes.
No business simulator result is generated or inherited as proof of this adapter's economics.

## Next investment decision

Retain the bounded adapter as a candidate for reviewed integration. Do not add more product features merely because
an analogy is appealing. Next measure the complete accepted-job effort on authorized representative inputs:
preparation, operator review, correction, delivery and support, against an equally capable conventional service.
Record unknown quantities as unknown. Use the existing campaign and CostLedger rather than create another ledger.
A new feature needs a reproducible failed requirement or an observed bottleneck. No live pilot or spending is authorized.

Code availability, useful delivery, commercial success and causal successor benefit remain separate claims.
The existing equal-tool-parity and payment-incentive limitations are not repaired by this change.
Preserve #4850 coordination, #5011 ownership, #5018 invention integration and all normal main/release gates.
No dependency, workflow, security control, held source pin, payment system or publisher is changed.
