[Project notice](../../DISCLAIMER_SNIPPET.md)

# Alpha 1.41.1 public installation and measured correction

The eligible #4886 delivery is merged, published and installed from public artifacts. A later load sample exposed a cold-start concurrency defect; it remains recorded as a failure. Its correction has been adopted into the existing 1.42/#4890 source and still needs qualified integration/publication and fresh installed verification. The original enterprise Harness and Fleet actions remain held. **Full SUCCESSOR Harness completion is not claimed.**

## Exact delivered source and checks

- [PR #4886](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4886) merged as [787bc547f8c44854931b316d7286b8bc9f9c8bba](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/787bc547f8c44854931b316d7286b8bc9f9c8bba), tree `fddf8462e4508462e2bb0a591a1e940aa9da97ee`, exactly the reviewed tree of `1ea9ea0b75bf8154a869d4d63a3b16d23ddab48a`.
- [Public v1.41.1](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.41.1), release 422882471, published 2026-10-24T17:42:33Z. Annotated tag `97b61a4c45cecadd968aab40ac854104763a2ada` resolves to that merged source.
- [Agent acceptance 40106911750](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40106911750), attempt 2: SUCCESS, 38 successful required job records. Source regression: 4,735 passed, 81 skipped, four original held nodes deselected, four xfailed, 192 warnings, 82.19% coverage. Source typing, blocking hooks, preservation, package installation and public browser gates passed. The four deselected native outcomes remain unqualified.
- [Anonymous artifact receipt](anonymous-artifacts.json): every one of the 106 new public asset bodies, 2,851,918,924 bytes, checked against API sizes/digests and SHA256SUMS using four streams in 186.112s. Four published browser reports were authenticated against the pack inventory and matching manifest.
- [Fresh public installer receipt](installation-result.json) and [installed acceptance](installed-acceptance.json): supported Python 3.12.14, Node 24.22.1, Linux x64, new virtual environment outside checkout. Exact installed workbench module SHA256 is `6efb59f24b67dbaf0932166ba8161eb9797b9866cbc36c123015b4465bfd737c`. Installer check-only, installation and pip check passed; 16 CLI commands, both real-worker mutation cases, explicit interrupted recovery, export/restore and existing two-generation rehearsal passed.

The native rehearsal's actual verdict is **RETAIN_INCUMBENT**, qualification **HOLD**, production authority false. Explicit restoration is `restored-stopped`, with no active proofs, grants or serving release. Local source keys were retained before the tested exports/runs; local signatures are not organizational independence.

The maintained [workbench](https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/work/) and [Alpha journey](https://montrealai.github.io/AGI-Alpha-Agent-v0/successor/alpha/) have source-bound public browser reports here. English/French, 320/390/1440 layouts, keyboard, accessibility and saved offline work are recorded in [the public workbench receipt](public-workbench-browser.json). [Eight-route anonymous readback](public-site-readback.json) retains the actual served bytes and original preferred PDF. The original [research companion release](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/study-successor-omega-harness-detector-v1-2026-10-24) remains a separately scoped simulated study, with original losses/counterexamples and bytes preserved.

## First local run

Use Python 3.11–3.13 and Node 22 or later; release CI pins Node 22.17.1. Download these four matching v1.41.1 public assets into one folder: `install_agent.py`, `requirements-agent.lock`, `SHA256SUMS`, `alpha_factory_v1-1.41.1-py3-none-any.whl`. The matching public-file installer and commands below were exercised outside checkout:

```sh
python3 install_agent.py --release-dir . --venv .venv-agent
.venv-agent/bin/alpha-agent --version
.venv-agent/bin/alpha-agent --home agent-state init
.venv-agent/bin/alpha-agent --home agent-state doctor
.venv-agent/bin/alpha-agent successor-work example documentation --output mission.json
.venv-agent/bin/alpha-agent successor-work plan mission.json
.venv-agent/bin/alpha-agent --home agent-state successor-work run mission.json --output result
.venv-agent/bin/alpha-agent --home successor-state successor-demo --output successor-evidence
```

Choose new home/output paths; existing files are retained. On Windows use the environment's `Scripts/alpha-agent.exe`. Follow the [versioned operating guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/787bc547f8c44854931b316d7286b8bc9f9c8bba/docs/agent/START_HERE.md) for review, backup, explicit restore and profile boundaries. Cold concurrent first-use remains the known 1.41.1 limit below. Sequential initialization/work is the tested first-run route; this is not live Fleet or settlement.

The frozen `verify_public_1_41_1.py`, `accept_installed_1_41_1.py` and `measure_installed_1_41_1.py` retain the executed procedures. Reproduce installed acceptance using that new environment's Python, `--commit 787bc547f8c44854931b316d7286b8bc9f9c8bba`, `--module-sha256 6efb59f24b67dbaf0932166ba8161eb9797b9866cbc36c123015b4465bfd737c` and a new `--output` directory. The load procedure needs `--commit` and a new `--output`. Operator homes contain secrets and are deliberately excluded from this evidence directory.

## Load failure, safe recovery and actual correction

[Original installed load receipt](installed-load-failed-samples.json): one finite sample per level, numerical fixed worker, one fresh home per level, no provider, wallet, contract or Fleet. At most the listed number of submissions was in flight. Successful outcomes awaited local review.

| Missions | In flight | Errors | Successful missions/s | Median seconds | P95 seconds | Storage growth bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 5.38 | 0.184 | 0.184 | 53641 |
| 4 | 2 | 1 | 7.59 | 0.194 | 0.199 | 160137 |
| 16 | 4 | 0 | 12.73 | 0.275 | 0.432 | 868745 |

Overall 20/21 completed; this is **not a clean concurrency or general scale qualification**. RSS sampling recorded 21,970,944 bytes without observed growth, but combined child peaks were not established; that is not a memory bound. CPU/storage/raw timings and review backlog remain in the receipt. Allocated machine price and actual human review time are unknown; no resource measure is realized profit.

The original failed request recorded `ValueError` without its message. A [separate deterministic public-package reproduction](cold-start-public-reproduction.json) pauses the first role-key write after directory creation, making a second request reliably report `local principal state is incomplete; do not silently replace role keys`. The first request succeeds and the journal verifies. This proves a real cold-start race consistent with the observed failure; it does not invent the original request's missing message.

[Explicit old-package recovery](failed-load-explicit-recovery.json) inspected that failed UUID, confirmed it had no work registration, resubmitted the exact numerical inputs after setup completed, and obtained `review` on its first registered execution attempt. All three earlier successes and the original signed checkpoint prefix remained intact. One explicit recovery intervention was required. The original load sample remains failed.

[Runtime correction 5ab92e5f4d2199ccfbfe2dd7e68e5a10205d07ee](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/commit/5ab92e5f4d2199ccfbfe2dd7e68e5a10205d07ee) changes two files: use the existing journal transaction during local-role setup, plus actual concurrent-first-use and damaged-state regressions. The new test fails on released source in 0.58s. Corrected workbench/state/private-backup tests pass 57 cases in 9.49s; the exact composition with owned 1.42 source passes 57 in 9.87s, with 54-source runtime typing and Ruff/Black. Genuine missing keys/manifests remain refused, with existing history unchanged.

The existing #4890 owner acknowledged the handoff at [6387898937](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4890#issuecomment-6387898937) and adopted both exact files into `d671adc03ed8029d72031ba5944638b56704b81e` / tree `22d11bd0bf799d000c8f82dc9cc108cd5c01ec42`, with current release notes. The combined-head configured review reported no major findings. [#4892](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4892), the short-lived stacked contribution, was closed as redundant after verified adoption. It was not merged as another route. **#4890 retains integration/publication ownership; the runtime lane retains fresh public installed verification after release.** Adoption in an open PR is not main integration, publication or installed qualification. No 53-source/cache-edition or held-pin change was needed.

## Preserved CI recovery and original holds

[Pages recovery receipt](pages-recovery.json) keeps the first automatic 20-minute timeout, its successfully uploaded 465-file artifact and later cancellation. The same-job retry endpoint returned 403/already-running; fresh metadata confirmed actual attempt 2. No extra retry endpoint, source/gate change or manual publisher was used. The second Pages job and ordinary dependent publisher passed. Earlier successful stages retain their original execution timestamps; they were not relabelled as newly executed work.

[Compatibility matrix](compatibility.json) separates the retained Alpha 1.39 / Jobs rc.20 / Manager 1.20.1 API route from the unqualified new installed tuple. USDC6 and AGIALPHA18 remain distinct. The local qualifying route uses no contract or live transaction; five-contract deployment references remain point-in-time records.

- Original Harness #4863 at `c455ad4ce109c86df2fef09d19674810290b5185` still needs the original configured task's terminal review and separate source-specific merge disposition (records 6345107482 and 6347342683). Bridge #4865 at `6bb361d522d80dc900cc2a480014531c6a44b66e` remains dependent.
- Unreferenced original-lineage preparation `f2869e602e65b3fd61593b57d3d2484481a499b1` / tree `51889848ab485f373b93b3ac0d7191fa5c4727a2` preserves all eight original paths and all other main787 leaves. Its 41 development cases passed; [receipt/raw log/JUnit](prepared-harness-receipt.json) retain that scope. It is not canonical adoption, review/merge clearance or installed release acceptance.
- Fleet combined `d0d4459b48a6cb45b0b6393be5099484ad8c6313` remains unadopted/unpublished/unqualified. The original runtime/restriction operator must expose the original decision/payload/permitted scope for target `0b13d3ffb25381dc2ebf9c39abda24824660fd3b`, then establish eligible exact-candidate review. New actors, branches, reviews or SHAs do not clear that restriction.

The current resumable action is the existing #4890 combined-source qualification and normal release, followed by a new public-package installation/concurrency sample. Original Harness/Fleet operations remain isolated until their legitimate decisions exist. This checkpoint establishes no unattended development session.
