[Project notice](../DISCLAIMER_SNIPPET.md)

# Current-source Ascension audit

This is an additive audit of the unchanged 80 requirements. The original
[acceptance snapshot](ascension-cycle-acceptance.json), engineering snapshot and signed examples remain historical records.
A command passing on one source tree does not pass a changed integration or the whole original requirement.

The generated `docs/agent/ascension-cycle-current-audit.json` report derives each requirement's current evidence, unexecuted suites,
source references, remaining acceptance, product decisions and external prerequisites from the
[scope catalog](ascension-cycle-audit-scope.json). It preserves every original ID and exact requirement text.
The original twelve graph nodes and eighteen directed edges remain separately indexed.
No whole-product completion, Mainnet activation, human benefit or pilot participation is inferred.
Issue #4787 is protocol preparation with zero observed participants, not a completed benefit trial.

## Reproduce and validate

Use Python 3.11–3.13, Node 22.17.1 and the repository's locked dependencies. Build the archived read-only profile first:

```sh
python -m scripts.build_mark_wallet
python -m scripts.ascension_current_audit list
python -m scripts.ascension_current_audit run --node "$(command -v node)" \
  --suite audit_validation --suite interruption --suite native_interruptions
python -m scripts.ascension_current_audit generate
python -m scripts.ascension_current_audit validate
```

Select additional suite IDs explicitly. `native_budget` requires the integrated reservation coordinator and its tests.
`two_cycle_browser` requires the installed contract/browser dependencies, Playwright Chromium and genuine fixed native
executor. Its only chain is the existing unforked disposable Hardhat harness. No command in this catalog commissions a
production profile, requests live funds, accepts a real provider credential or supplies an independent human approval.

Each execution creates a new evidence directory with the original combined output, source inventory, exact command,
runtime versions, return code, parsed counts where available and hashes of retained harness artifacts. Previous runs are
never overwritten. A source change or changed suite scope makes the prior run stale for the current report. The most
recent current-source run controls its suite, so a newer failure cannot be hidden behind an older pass. A malformed,
modified or internally inconsistent retained record fails validation instead of being ignored.

The content inventory covers tracked files and unignored files outside generated runtime `evidence/` and `site/` outputs,
plus the generated archive profile. Audit outputs are excluded to avoid self-reference. The observed checkout commit is
retained in each run's source manifest; the current report binds file bytes rather than claiming that a report can contain
its own future commit hash. Dependency lockfiles and runtime versions are bound, but installed dependency bytes and
independent executor integrity are not attested. Local hashes establish integrity, not review, permission or trust.

Generating an audit without running tests produces explicit `not_run` states. `validate` checks current content and retained
evidence; it is not an 80-case product pass. A passing `automated_scope_status` covers only that row's named commands.
`requirement_status` remains partial until the broader original acceptance has appropriate reviewed evidence.

The MARK acceptance workflow discovers the Node tests through its existing glob and now explicitly executes pytest audit,
native interruption and reservation tests. It retains a bounded current audit as a separate artifact. The release workflow
already discovers `tests/runtime`, including the new native tests. Other workflow results are not silently imported into
this audit: execute their catalogued commands against the final integrated tree to retain matching outcomes here.

## Interruption qualification

| Point | Deterministic current test | Scope still requiring separate evidence |
|---|---|---|
| Upload | Exact capsule CID survives failed evidence upload and explicit resume; fresh-process project restore | Actual service-account lost response and independently verified availability |
| Mint | Pending exact seal journal restores in a new process; no signing or auto-resubmission | Production-browser/EVM mint-response interruption and canonical readback |
| Approval | Imported terminal approval is downgraded to unresolved, blocking dependent sends | Actual wallet approval/purchase interruption and allowance reconciliation |
| Purchase | Pending buy intent survives fresh-process restore and blocks duplicate work | Real browser/EVM quote/rejection/reorg and canonical purchase reconciliation |
| Route | Exact plan/proof route journal survives fresh restore without rerouting | Production-browser/EVM route interruption and exact event/readback |
| Runtime start | Fresh saved request cannot authorize work; actual fixed-work interruption keeps reserved resources | Integrated browser/native-host crash and independently restored trust |
| Delivery | Retained result recovered in another Python process without execution or renewed authority | Interrupted on-chain submission with canonical receipt and exact delivered bytes |
| Review | Pending vote stays unresolved; committed native acceptance response loss is idempotent | Actual committee review interruption, quorum and deadline recovery |
| Settlement import | Original text retained as unverified; committed native import response loss is idempotent | Integrated signed settlement/current canonical receipt recovery after reorg |
| Claim | Pending reclaim intent blocks duplicate sends after fresh restore | Independent real-device recovery and full accounting completeness (the integrated local harness now checks claim-response recovery and recipient-specific CapitalReturned) |
| Successor | Separate cycles, frozen comparison and original records survive; no authority transfers | Full fresh-device/browser restore into a newly authorized distinct second mission |

All eleven named portable checkpoints execute through the production `WalletSession` and `NovaWorkflow` in fresh Node
processes. Their wallet journals and observations are synthetic. Native drills run actual bounded numerical work with
synthetic RPC and test principals; fresh Python processes reopen retained journals read-only. These are meaningful
component results, not a physical-device test or a complete integrated crash matrix.

## Remaining decisions and resources

The user selected an atomic native reservation coordinator. Its current API, multi-process, lost-response and browser
integration evidence must be retained before claiming the corresponding allocation guarantees. This audit does not change
or waive requirements 43 or 71. Closed-browser obligation monitoring still needs an accountable operating model and a
retained deadline/handoff drill. A static site has no implicit background keeper.

Real storage accounts, wallet/device combinations, human accessibility, independent reviewers, live provider execution,
qualified deployment/canary and live continuation remain separately authorized trials. Required exact-head release checks,
review, immutable tag and published-route verification remain separate from local automated results. Financial returns,
commercial value and human benefit require their own observations; missing data never becomes a positive outcome.

## Additional Jobs v0 and Fleet integration scope

This newly requested scope is additive; it does not change any of the original 80 requirement IDs or texts.

| Integration | Current boundary | Evidence required |
|---|---|---|
| Existing MARK → AscensionJobMarket | Deployed MARK has an immutable fixed market route, using $AGIALPHA | Exact current contract/browser lifecycle; no substitution with another market |
| AGIJobsv0 → Alpha | Separate $AGIALPHA adapter remains an open engineering and qualification gate | Exact version/address/ABI, role/assignment/output/settlement mappings, negative and recovery tests, actual bounded integration trial |
| Alpha → Fleet execution | Separate execution adapter remains an open engineering and qualification gate | Versioned interface, bounded current authority, genuine execution and output binding, cancellation/lost-response/idempotency |
| AGIJobManager | Separate USDC protocol | No equivalence with Jobs v0 or the immutable MARK route is inferred |

Existing fixed-workbench or Ascension two-cycle results do not clear these adapter gates. Update the separate integration
matrix only when the final integrated adapters and appropriately scoped execution evidence are available.

The additional `two_cycle_interruption_browser` suite executes the actual eleven-stage
portable recovery matrix against disposable EVM contracts and the fixed native executor.
See [its precise qualification limits](ASCENSION_INTERRUPTION_QUALIFICATION.md).
The report and raw current-acceptance runs are generated CI artifacts; they are not
committed product completion attestations.
