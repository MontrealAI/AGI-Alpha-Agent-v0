[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.23.0 — Complete demo catalog readiness

The shared demo guides had fallen behind the runnable catalog: they reported conflicting finite-command
counts and described several maintained labs as earlier toy or deployment examples. This release aligns
the entry points across all 26 entries and adds a read-only prerequisite report for the whole installation.

Follow [Install and run](START_HERE.md) to install matching, checksum-verified release assets into a new
environment. Activate it, then inspect the catalog:

```bash
python -m alpha_factory_v1.demos check --all
python -m alpha_factory_v1.demos check --all --json
```

The report covers 23 catalog commands and three guide-only entries. It lists missing declared modules
and bundled files without importing optional training backends, launching services, downloading models
or creating run state. Exit status is 0 when every command has its declared prerequisites and 2 when
any are missing. A READY result is a presence check; model execution and service commissioning have
their own validation requirements.

The [walkthrough](DEMOS.md) includes the maintained Sovereign, Finance, Discovery, Experience and planning
experiences alongside the existing full Ascension lifecycle. The [validation matrix](DEMO_VALIDATION.md)
distinguishes all 17 finite offline launch contracts, optional native training, services and guide-only
entries. A new documentation consistency gate checks release versions, modes, counts and validation
boundaries before the catalog smoke test, preventing these shared guides from silently drifting again.

Validation adds regressions for missing modules and assets, guide-only entries, unchanged credentials,
no imports/downloads/state writes, installed-wheel aggregate checks and preservation of research diagrams
during synchronization. Existing native, browser, offline, notebook, container, protocol and publication
gates remain required. Their outcome belongs to the matching workflow and release manifest.

All original demo directories, flowcharts, research archives, source launchers and media are retained.
No journal, report or data migration is required. The supported profile remains bounded local research
and a private single-operator agent; independent validator consensus, mainnet deployment and general
AGI capabilities remain separately unestablished. See [release readiness](RELEASE_READINESS.md).
