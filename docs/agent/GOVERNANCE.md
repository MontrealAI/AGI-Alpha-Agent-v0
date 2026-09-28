[Project notice](../DISCLAIMER_SNIPPET.md)

# Governance Workbench — review before release

Open the [browser workbench](../solving_agi_governance/index.html) or run the standard-library
CLI on Python 3.11–3.13. No credentials, wallet, provider, database or GPU are required.
The complete [demo guide](../demos/solving_agi_governance.md)
contains formulas, schema limits, recovery instructions, original research and the preserved simulator.

```bash
python -m alpha_factory_v1.demos check solving_agi_governance
python -m alpha_factory_v1.demos run solving_agi_governance --output-dir governance-runs
```

The default constructed case passes nine modeled gates and returns `REVIEW_REQUIRED`.
Other cases deliberately block captured ballots, profitable deviation, excessive aggregate
risk or incomplete upgrade controls. A blocked decision is a useful result, not a process error.

## The complete operating path

1. Choose a case or import a scenario. Review source notes, validator identities, payoffs,
   probability bounds, voting policy and the explicit clock.
2. Evaluate nine gates. Inspect participation and quadratic credit costs, the conditional
   incentive margin, total risk bound, timelock, policy commitment and pause state.
3. Resolve blocked conditions. Even passing gates require independent verification of their
   underlying sources; editable names and hashes are not authenticated attestations.
4. Download the five-file ZIP: `scenario.json`, `dossier.json`, `jobs.json`, `review-brief.md`
   and `SHA256SUMS`. Browser and Python exports have identical bytes.
5. Replay the dossier. Imported results are recomputed in full, including the input-bound jobs.
   Altering a result and recomputing its checksum does not bypass verification.
6. Compile the nine unsubmitted jobs into an Ascension FusionPlan. Independent review,
   authenticated roles and execution authority remain separate steps.

```bash
governance-workbench --list
governance-workbench --case scale-risk --output governance-runs
governance-workbench --verify governance-runs/<sha256>/dossier.json
alpha-agent ascension-compile governance-runs/<sha256>/jobs.json --output fusion-plan.json
```

Replace `<sha256>` with the directory printed by the run. Verification is read-only.
Compilation does not post jobs, escrow rewards or authorize a policy change. The
[Ascension protocol guide](ASCENSION_PROTOCOL.md) describes the separate local-EVM path.

## Assumptions and safe interpretation

The repeated-game condition assumes stationary payoffs and public detection probability,
infinite play, risk-neutral agents and no false positives. A detected unilateral deviation
incurs an enforceable one-time slash and credible grim-trigger punishment; an undetected
deviation returns to cooperation. With zero detection, patience or stake cannot deter a
profitable deviation. This does not prove a unique equilibrium. In the original simulator, `--delta` is a
numerical update rate; its valid seeded results remain unchanged.

Aggregate risk uses `min(1, Np)` without assuming independence. Per-action bounds are supplied,
not calibrated by this software. At 10¹² actions, a 0.001 total budget requires a per-action
bound at most 10⁻¹⁵. The paper's normalized Table 4 score is a different quantity.

Every result is either `BLOCKED` or `REVIEW_REQUIRED`. Checksums bind content and support
replay; they do not authenticate an identity, vote, chain timestamp or scientific claim.
No real AGI, mainnet governance approval or universal safety theorem is established.

## Recover without losing work

Browser drafts are saved only when requested and can be restored or cleared independently
of unrelated browser data. Export a ZIP for portable retention. Scenario edits disable stale
exports. Apply edited advanced JSON before evaluating or saving it.

Native runs use content-addressed directories. An exact rerun is idempotent; an altered,
partial or symlinked prior run is refused. Preserve it and choose another output directory.
Imports are limited to 256 KB, 64 validators and bounded integer units; ambiguous keys,
invalid Unicode and non-finite or out-of-range values fail closed.

The public site is checked at 320, 390 and 1440 pixels, with keyboard controls, axe WCAG
A/AA checks and offline reload. This is Chromium acceptance, not comprehensive accessibility
certification or qualification for every browser and operational environment.

## Preserved research

The original manuscripts, TeX, PDF and PowerPoint diagrams remain unchanged. The original
README and notebook are retained as explicit archives; the current notebook executes every
case, exports a review and exercises the legacy simulator. The browser retains the sample
replay and its existing Proof Debt → AGI Jobs workspace link.
