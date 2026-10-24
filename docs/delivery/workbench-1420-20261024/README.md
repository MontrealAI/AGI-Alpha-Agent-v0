# Standalone Alpha 1.42 verification checkpoint

This is a prospective verification handoff, not a release or acceptance result.
Existing source/release owner: #4890 and its generated-document correction #4894.
Runtime-owner handoff: #4890 comment6387898937; coordination #4850.

The runtime's immutable submission correction is public in1.41.1, exact
source787bc547f8c44854931b316d7286b8bc9f9c8bba. Its complete anonymous artifact,
fresh installation, mission and recovery evidence is retained at data-only
commit714e7f95c65c8e5ffc3bc8423cc0698ba0f7b317. Its original concurrent-load
sample remains failed20/21; one explicit same-ID resubmission acknowledged the
three earlier successes. That resubmission does not turn the sample green.

The first-use principal-inventory guard was adopted byte-for-byte by the existing
1.42 owner in reviewed headd671adc03ed8029d72031ba5944638b56704b81e and merged as
aedc92779c142bded5bf552ecfb3e0b6ba8f8fba. Normal main run40122949132 remains
unqualified: three runtime cells first passed1055 runtime cases then failed26
generated demo-page version assertions; a separate MARK keyboard timeout is
retained by its owner. Correction #4894/90568ad6d2aa0155804e3bbaf72d73d3b6b5c975
has configured review6388392560 with no findings. Its six applicable hosted
groups, exact resulting-main qualification and public1.42 publication are pending
at this checkpoint. No failed assertion, protected pin, historical release or
permission control was weakened. Independent focused generated-doc validation:
183 passed,1 skipped,12.71s; second generation byte-identical. The source owner
separately reports933 complete publication cases and154 legacy-fragment cases.

The supplied1.42 procedures are prepared and unexecuted against public1.42:

1. `verify_public.py`: anonymous tag/source and EVERY public asset body, size,
   API digest and checksum; audit five source-bound public browser reports,
   including the19-case/nine-download `/try/` guide.
2. Public `install_agent.py`: first `--check-only`, then a fresh isolated venv
   outside the source checkout; `pip check`, installed version/origin and module
   SHA25687ad9f365ebf1b5c1e93edc275e6fe933b6c247e51b848b52dc66c34344a8492.
3. `accept_installed.py`: existing16-command CLI journey, immutable caller inputs,
   forced two-worker first use, genuine incomplete-role refusals, interrupted
   recovery, export/explicit restore and the existing bounded successor rehearsal.
   Its retain-incumbent/HOLD outcome grants no production authority.
4. `verify_upgrade.py`: a private copy of the stopped1.41.1 load home, consistent
   SQLite snapshot and pre-existing public checkpoint; all four earlier successes
   acknowledged without worker replay, extra history, key replacement or proof.
5. `measure_installed.py`: finite1/4/16/64 workloads, max1/2/4/4 in flight, fresh
   home per level; throughput, latency, errors, CPU, storage, sampled RSS and
   individual process high-water marks. One sample per level is not general scale
   qualification. Human review time and allocated machine price remain unknown.
6. `verify_site.py`: anonymous byte readback of nine actual deployed routes and
   the retained preferred PDF. Mobile/EN/FR/keyboard/axe/offline behavior belongs
   to actual source-bound public browser reports, not an HTTP-only inference.

Memory instrumentation correction: the old `/proc` sampler used namespace
`os.getpid()` against host-PID `/proc` data here and omitted children. Its prior
zero-growth reading is not valid combined-memory evidence. The retained before
and after sanity receipts show the correction to `/proc/self/stat` sees a known
32MiB Node allocation. The corrected sampler observes72,019,968bytes combined
growth in that sanity check, with child high-water72,413,184bytes. These are
instrument validation numbers, not mission performance. Sampled sums can miss
peaks and double-count shared pages; individual high-water marks do not form a
simultaneous combined peak. No speed/memory improvement is claimed over the old
procedure. `validate_memory_sampler.py` reproduces the corrected sanity method.

No private homes, local role keys, API tokens or SQLite stores belong in this
public checkpoint. Only explicit public receipts/scripts/logs are selected.
The upgrade fixture stays private. A new version's assets must never overwrite
the preserved1.41.1 release.

## Compatibility and held operations

| Route | Exact current scope | Qualification |
|---|---|---|
| Alpha1.41.1 /787bc547 | Public106 assets, fresh local installation and fixed-worker mission/recovery; concurrency failure retained | Standalone core accepted; load failed |
| Alpha1.42.0 / corrected-main pending | Cold-start guard plus browser guide; normal correction #4894 | Not yet published or installed |
| Jobs discovery-v2.1.0-rc.20 /f7c00e668fe31ce1ea907f0006b6c14dc9db5e01 | Historical accepted local API route; AGIALPHA path remains separate | No Alpha1.42 tuple qualification |
| Manager1.20.1 /c5958eae872458c2f3cac48fea0b4bbfadc6ac6c | Historical accepted local commissioning/review route; USDC6 | No Alpha1.42 tuple qualification |
| Fleet candidate d0d4459b48a6cb45b0b6393be5099484ad8c6313 | Separate unfinished combined candidate; canonical main45759fb0 | Not native/adopted/released/installed qualified |
| Original Harness #4863 /c455ad4ce109c86df2fef09d19674810290b5185 | Original review6345107482 terminal result unknown; separate merge restriction6347342683 | Held; neither is cleared by this delivery |
| Bridge #4865 /6bb361d522d80dc900cc2a480014531c6a44b66e | Dependent original work | Not canonical; parent hold retained |

Fresh metadata inspection at this checkpoint finds Jobs rc20, Manager1.20.1 and
Fleet local-skills-preview.5 still public. Newer owner candidates are not silently
treated as releases. Current cross-product/native qualification stays false.
No four excluded native objectives, five protected source/test files, financial
transactions, contract deployments or security settings are touched.

The original configured-review/restriction operator must expose the terminal
original Harness decision and separate source-specific merge disposition. The
original Fleet runtime/restriction operator must expose its original stopped
review decision and eligible scope before exact-current review/P1 disposition.
A new actor, name, branch, SHA or passing component test supplies neither decision.
This checkpoint is resumable; it is not an unattended execution claim.
