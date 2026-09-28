[Project notice](../DISCLAIMER_SNIPPET.md)

# Insight Discovery Workbench

Open the [browser workbench](../alpha_agi_insight_v0/index.html) to compare cross-sector hypotheses,
inspect their supplied evidence, allocate review time and export a reproducible dossier.
The [complete guide](../demos/alpha_agi_insight_v0.md) includes formulas, schema limits, recovery,
API boundaries, provider opt-in, the maintained notebook and original research flowcharts.

```bash
python -m alpha_factory_v1.demos check alpha_agi_insight_v0
python -m alpha_factory_v1.demos run alpha_agi_insight_v0 --output-dir discovery-runs
insight-workbench --list
insight-workbench --case public-software --output insight-runs
```

Discovery needs only Python 3.11–3.13 and the source package. It makes no provider calls. All five
starter cases use explicitly synthetic assumptions. Priority scores are not probabilities or values;
source coverage records supplied references, not authenticated evidence.

The six-file ZIP contains a normalized scenario, recomputable dossier, unsubmitted verification jobs,
plaintext unminted Nova-Seed drafts, a review brief and checksums. Importing a dossier recomputes all
results; a matching hash alone is insufficient. Changed or partial native output is rejected.

The [Ascension protocol](ASCENSION_PROTOCOL.md) documents the separately operated cryptosealing,
validator, MARK, Sovereign and marketplace lifecycle. Exported jobs bind the complete input hash and
carry goal, success metric and an 18-decimal $AGIALPHA bounty. The workbench submits no jobs and holds
no funds. Validator attestations, source quality, operational authority and deployment fitness require
independent evidence.

The original research presentation, flowchart, notebook and numeric-search launchers remain available.
The numeric search now uses correct UCB observation accounting, a local RNG and bounded explicit
provider selection. The local API defaults to loopback, forbids provider and server-path requests,
limits bodies and concurrent calculations, and never installs dependencies during startup.
