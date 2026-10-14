[Project notice](../DISCLAIMER_SNIPPET.md)

# Nova-Seed Studio acceptance and evidence

This matrix tracks the 35 acceptance cases in the implementation handoff and the tests actually executed.
**PASS** applies to the named evidence and environment; **partial** identifies an unperformed part of a broader
case. Local exact-source EVM, historical bytecode, browser-provider fixtures, real-dependency fork and
live-mainnet observations are different evidence classes. No mainnet transaction or physical-wallet trial is
claimed here.

## Baseline and implementation map

The starting default-branch reference was `7436a02cc4619d4f636bd02390888b9bb47a7eb3`. The implementation checkout
incorporated MARK PR #4778 at `5ad36fdc5870b9667e681eb81f41e3c923b8375b`; that work subsequently merged into main
at `c38f430d5a07064ad7c19ae761e91eaad3e48efe`. The implementation browser reports record their base commit and
the exact asset digests they exercised. Release acceptance must rerun against the actual release commit and
matching assets. These are repository references, not evidence of mainnet activity.

| Surface | Responsibility |
| --- | --- |
| `docs/ascension/mainnet/` | Additive guided browser route |
| `docs/assets/nova-studio/` | Plan/package/publication and lifecycle orchestration |
| `docs/assets/ascension/crypto.mjs` | Existing compatible Web Crypto capsule format |
| `docs/assets/ascension-wallet/` | Shared wallet selection, ABI/policy, intent and recovery journal |
| `tests/contracts/test/ascension/` | Current-source and archived-bytecode contract acceptance |
| `tests/mark-wallet/` | Shared codec, provider, recovery and build regressions |
| `docs/agent/NOVA_SEED_STUDIO*.md` | Guide, formats, threat model and commissioning/support boundaries |

## Acceptance matrix

| Case | Executed result and scope |
| --- | --- |
| 01 Preservation | Protected-source diff unchanged; strict MkDocs PASS. Full release regression pending |
| 02 Shared foundation | PASS E4/E6 shared client, journal and same-origin locks |
| 03 No-wallet start | PASS E1/E5 actual create, compile, seal, export and reopen |
| 04 Wallet/network changes | PASS E3/E4/E6 fixture/EVM selection, rejection and stale-context barriers |
| 05 Profile policy | PASS E4/E5/E7 archive, unknown profile, ABI/code/binding and build isolation |
| 06 Identity | PASS E3/E9 namespaces, bad labels, wrapped expiry and admission; real fork external |
| 07 Operator boundaries | PASS E3 distinct authorized fixture actors; real authority qualification external |
| 08 Compiler parity | PASS E1/E2 counts 1/2/3/7/127/128, 268 leaves/proofs; 0/129 reject |
| 09 Numeric/text bounds | PASS E1 exact integer/UTF-8/aggregate bounds and E2 Solidity parity |
| 10 Encryption parity | PASS E1/E5 exact inner plan, legacy conversion, wrong passphrase, tamper and size |
| 11 Commitment distinction | PASS E1 separate hash meanings and decrypt-bound package identity |
| 12 Publication | PASS E1/E8 real adapter with fixture transport; real service upload unperformed |
| 13 Mint intent | PASS E3/E8 exact zero-value seal with zero token allowance |
| 14 Mint receipt | PASS E3/E8 exact event/readback; subsequent mint, foreign emitter and missing logs |
| 15 Existing seed | PASS E1/E3 kit/receipt resume, current ownership and mismatched artifacts |
| 16 Risk lifecycle | PASS E3/E8/E9 stake, quorum, exclusions, expiry/revocation; real independence external |
| 17 Funding math | PASS E1 reachability/overflow/partial target; E3/E8 purchase accounting |
| 18 Approval interruption | PASS E3 rejected purchase and correct allowance/balance resume |
| 19 Bloom | PASS E3/E8 explicit phase transition; E1 rejects false activation of closed campaign |
| 20 Routing | PASS E2/E3/E8 exact proof/index; odd-tree duplicate-specification boundary |
| 21 Routing rejection | PASS E1/E2/E3/E9 proof/spec/budget/replay/capacity/authority and foreign-job scope |
| 22 Runtime truth | PASS E1/E3/E8 exact native result/job binding; export never claims connection |
| 23 Settlement | PASS E3 all four current-source outcomes; E8 accepted payout/burn accounting |
| 24 Exits | PASS E3 expiry, collection/closure/reclaim; live competing transactions unperformed |
| 25 Unknown broadcast | PASS E3/E4/E6 actual lost response/reload; physical mobile trial unperformed |
| 26 Concurrency | PASS E4/E6 same-browser locks; other devices remain outside the lock boundary |
| 27 Replacement/finality | PASS E3/E4 real cancellation/reorg and E1 settlement finality lag |
| 28 Ownership/successor | PASS E1 discovery and E9 successor/transfer protection; combined UI trial separate |
| 29 Recovery portability | PASS E1/E5 fresh kit import and E3 fresh-client chain reconciliation |
| 30 Hostile inputs | PASS E1/E4/E5/E6 parser, URL, metadata, publication and exact-asset checks |
| 31 Actual browsers | E5/E8 Chromium/keyboard/EN-FR/layout PASS; manual screen-reader trial unperformed |
| 32 Wallet trials | Real extension, physical mobile and hardware trials unperformed |
| 33 Complete vertical slice | PASS E3 current-source/native lifecycle and E8 actual browser through settlement |
| 34 Authorized canary | Unperformed; requires commissioned deployment, consenting actors and authorization |
| 35 Launch/rollback | PASS E4/E7 registry/expiry/recovery policy; live rollout rehearsal external |

Rows record targeted evidence, not exhaustive mainnet qualification. Cases 06/16/21 still need the pinned
real-dependency rehearsal. Cases 02/26 exercise the shared lock implementation; an explicit Studio/MARK mixed-tab
trial is distinct from two MARK tabs. Case 28 includes contract-level successor and transfer tests, while the
combined transferred-successor browser trial remains separate. Case 31 includes 42 automated axe checks but
does not establish WCAG conformance or screen-reader
usability. Case 32 has no physical device evidence. These boundaries must remain visible at launch review.

## Executed evidence

Executed targeted evidence recorded during implementation:

**E1 — Nova modules: 36 passed (25 plan/package/storage and 11 workflow).** Covers compiler, exact funding
arithmetic, capsule/kit recovery, publication fixture transport, ownership discovery, native byte preservation
and finality states.

```sh
node --test tests/nova-studio/plan.test.mjs tests/nova-studio/package.test.mjs \
  tests/nova-studio/storage.test.mjs tests/nova-studio/workflow.test.mjs
```

**E2/E3 — Current-source EVM: 21 passed (8 parity and 13 lifecycle cases).** Node 22.17.1 and Python 3.12.14;
run from `tests/contracts`. E2 alone covers browser/JS/native whole-plan and 268 Solidity leaves/proofs.
E3 adds the actual shared workflow/client, native delivery, settlement and exits.

```sh
ALPHA_PYTHON=<absolute-checkout>/.venv/bin/python npx hardhat test --no-compile \
  test/ascension/nova-plan-parity.test.js test/ascension/nova-studio.test.js
```

**E4 — Shared wallet: 168 passed on Node 22.17.1.** Differential ABI, wallet/journal/policy, hypothetical
qualified profiles, older unresolved receipts and unsupported transaction envelopes.

```sh
node --test tests/mark-wallet/core.test.mjs tests/mark-wallet/recovery.test.mjs \
  tests/mark-wallet/abi.test.mjs tests/mark-wallet/qualification.test.mjs
```

**E5 — Actual Chromium preparation: PASS, 12 check groups and 42 axe panel/viewport checks.** No-wallet
preparation/import, exact assets, mirrored route, keyboard, EN/FR and desktop/mobile layouts.

```sh
python -m scripts.validate_nova_studio --output <report-directory>
```

**E6 — Existing MARK actual Chromium: PASS, 15 check groups.** Permission boundaries, journal/reload,
same-browser lock, replacement/finality, reorg and malicious metadata.

```sh
python -m scripts.validate_mark_wallet --output <report-directory>
```

**E7 — Profile build: 4 passed.** Deterministic archive and isolated source-bound local profile, including
mainnet/ABI/address/output-boundary rejection.

```sh
python -m unittest discover -s tests/mark-wallet -p 'test_build.py'
```

**E8 — Actual Chromium to disposable current-source EVM: PASS, 18 transactions and 13 check groups.** The
real UI reaches mint, separate-actor review, campaign opening/funding, activation, routing, worker delivery,
review and paid settlement. It checks the resulting payout/burn/refund accounting and exports a recovery kit.
Publication uses fixture transport; accounts are disposable EVM actors, not physical wallets.

```sh
python -m scripts.validate_nova_studio_evm --output <report-directory>
```

**E9 — Full contract regression: 129 passed, including E2/E3.** The recorded `nova-contracts-all.log` covers
the existing lifecycle, identity/oracle, auction, MARK, settlement, SUCCESSOR and deployment-record suites.
It verifies successor parent/independent-review rules, suspension of new treasury spending after an NFT
transfer, and protection of committed capital. Namespace/label failures, wrapped expiry, admission revocation,
quorum/self-review, reviewer capacity, altered plan/replay and exact payout accounting also passed.

```sh
npm test --prefix tests/contracts
```

E3 includes exact burn/refund arithmetic; rejected-result and delivery-timeout slashing; missing-review refund
without slashing; lost response after real local broadcast and recovery despite a subsequent mint; rejected
purchase after successful allowance and resumed funding; revoked/expired funding exits; and receipt
disappearance after an actual local `evm_revert`. It also executes the native Engine, signs a real delivery,
replays it through the native verifier, imports the trusted exact-byte result in the workflow and submits it
for accepted on-chain settlement. Wrong signer, rounded native timestamp, foreign events/jobs and wrong
indexed routes fail. Storage uses fixture transport of the real adapter and actors use disposable local
accounts. This is not independent real-world review, a continuously connected runtime or mainnet payment.

The retained E3 implementation log, `nova-evm-final.log`, has SHA-256
`31a81acdb6022b71d7add7f281bf1305a0c20b4687a03860044bf47f36b70f0a`. It records 21 passes in 40 seconds.
This identifies that execution, not a later source revision. The initial strict Solidity compile also succeeded
for 55 source files. Final commit acceptance must produce its own reports after code freeze.

E5 and E6 reports include the exact asset hash map, base commit, release version, test origin, check names,
`realMainnetTransactions: false` and `physicalWalletValidated: false`. Actual screenshots and private synthetic
recovery fixtures are CI/release artifacts, not binary additions to the source tree. Retrieve the Studio
artifacts from the
[acceptance workflow](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/workflows/nova-studio.yml).
The `nova-studio-browser` artifact contains `report.json`, `studio-protected.png` and EN/FR captures at
1440, 390 and 320 pixels. Those images show synthetic local preparation with no wallet; they are not mainnet
receipt evidence. The `nova-studio-evm` artifact is a separate current-source browser lifecycle report.

E1 also verifies that 128 short jobs can seal and reopen; maximum-length text can compile while exceeding
the compatible sealed-capsule size, which is rejected before encryption with repair guidance. A security review
found that caching recovery by capsule hash alone could let a changed outer plan inherit a prior decrypt check.
The implementation now binds recovery to capsule, plan, profile and evidence; E1 includes this regression.
The test outcome does not certify the actual meaning of public evidence or independent-review decisions.

## Preservation scope

During implementation review, `git diff --numstat` showed no changes in `contracts/ascension`, the complete
`deployments/ethereum-mainnet/2026-10-11` archive, the existing capsule cipher, the existing JavaScript plan
compiler or the native Ascension compiler/delivery module. Recheck that statement on the merge candidate.

| Necessary edits | Purpose and regression gate |
| --- | --- |
| Ascension/Desk links and templates | Add discovery without replacing destinations; gallery/link checks |
| Ascension mobile header CSS | Wrap the added navigation at 320px; complete original browser regression PASS |
| Shared wallet modules | One ABI, policy and journal; existing MARK plus new differential/profile tests |
| Build/cache/navigation | Ship local assets and exclude sensitive offline caches; strict gallery/asset checks |
| Release/evidence registration | Package Studio and require actual acceptance; preserve existing release gates |

No necessary change upgrades an on-chain address, migrates a balance, removes a flowchart, replaces the Lab,
or turns an old simulation control into a real-money action. Generated test/build output is not a reason to
rewrite unrelated checked-in assets.

For each executed command retain its exit status, full report, tested commit/tree and relevant profile identity.
Retain actual implementation screenshots and their browser/test context. A fixture screenshot may demonstrate
layout; it must not be presented as a real mainnet receipt. Never copy a successful result from another commit.

Required repository setup, preflight, dependency, lint, type, regression and release checks remain applicable.
If dependencies/network restrictions prevent a required check, record it as blocked with its exact reason.
Do not turn skipped work, a planned command or a partial test suite into a blanket pass.

The exact-source integration command is expected to run from `tests/contracts` after locked installation:

```sh
ALPHA_PYTHON=../../.venv/bin/python npx hardhat test test/ascension/nova-studio.test.js
```

The executable fixture uses the actual Studio workflow and shared wallet client, with local-only profile
construction isolated from production. The recorded E3 run passed; reproducing it against a different commit
requires rerunning the command and retaining that new result.

## External completion gates

| Gate | Owner and completion evidence |
| --- | --- |
| Independent security review | Qualified reviewers: named exact-commit/profile review and resolved findings |
| Real-dependency fork | Deployment/security operators: pinned real token/ENS lifecycle and accounting |
| Qualified mainnet profile | Operators/maintainers: actual source/runtime/binding records and reviewed registry |
| Canary scope/participants | Wallet owners and authorities: explicit actors, limits and authorization |
| Bounded live canary | Consenting actors: actual receipts, reconciled balances and separate launch decision |
| Physical wallet/accessibility | Product QA/device holders: versioned trials and disclosed unsupported cases |
| Public Pages deployment | Release pipeline: actual live route and exact frontend/profile version |

No mainnet spending, replacement deployment, governance changes, independent audit, hardware trial or public
activation is claimed by these local software results. Update individual rows only when their evidence exists.
