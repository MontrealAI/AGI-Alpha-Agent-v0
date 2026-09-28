[Project notice](../DISCLAIMER_SNIPPET.md)

# Release 1.14.0 — governance that can be inspected

The governance demo now provides a complete, bounded review workflow. Users can edit a
proposal, inspect nine admission gates, compare five adversarial cases, export a reproducible
dossier and prepare input-bound Ascension verification jobs without credentials or providers.

## What changes

- A responsive Governance Workbench replaces the generic sample replay as the primary browser experience. The original replay and decision-workspace bridge remain in the research collection.
- Python and browser engines compute the same integer-based incentive, quadratic-ballot, identity, quorum, mandate, aggregate-risk, timelock, policy and pause checks.
- Incentives account separately for detected and undetected deviations. Public detection governs both the one-time slash and future punishment; zero detection cannot deter a profitable deviation through stake or patience.
- Five-file exports contain inputs, complete results, review brief, nine goal/metric/bounty job specifications and checksums. Imports recompute all outputs; stale, ambiguous, oversized and forged evidence is rejected.
- The catalog, standard-library CLI, notebook and operating guide follow the same finite workflow. A modeled pass means `REVIEW_REQUIRED`; no automatic approval or execution occurs.
- The original simulator correctly describes `delta` as its numerical update rate. Valid seeded results are preserved; invalid and excessive work requests fail clearly. The optional bridge imports without its SDK and accepts deterministic seeds.
- Original README and notebook content is archived, while the PDF, TeX, PowerPoint and all existing diagrams remain intact.

## Release evidence

Publication requires exact Python/browser parity for 125 cases, byte-identical exports for
all five shipped cases, compilable input-bound Ascension jobs, native and wheel tests,
replay of downloaded browser evidence, hostile-import rejection, keyboard and mobile
checks, axe WCAG A/AA checks, and offline recalculation on canonical and mirrored routes.
The public acceptance receipt binds these checks to the packaged commit, version, asset
hashes and native decisions. Existing historical suites and release gates remain in force.

## Upgrade and scope

Follow [the installation guide](START_HERE.md) for matching release assets.
No native journal, identity or existing protocol migration is required. Keep prior runs and
backups. New governance dossiers use an explicit versioned schema and content-addressed
output directories. See the [governance guide](GOVERNANCE.md) for reproduction and recovery.

The model evaluates supplied assumptions. It does not authenticate votes or chain state,
calibrate safety probabilities, prove unique equilibria or commission mainnet governance.
Independent validators and deployment review remain necessary outside this bounded demo.
