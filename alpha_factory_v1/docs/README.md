[See docs/DISCLAIMER_SNIPPET.md](../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Documentation Overview
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk.

Start with the [1.12.0 factory guide](../../docs/agent/FACTORY_GUIDE.md),
[operator runbook](../../docs/agent/OPERATIONS.md), [Ascension protocol](../../docs/agent/ASCENSION_PROTOCOL.md)
and [release evidence](../../docs/agent/RELEASE_READINESS.md). All original reference diagrams remain.

This directory hosts reference files and configuration snippets for **Alpha‑Factory v1**.

- `alpha_agi_agent.md` – technical blueprint of the α‑AGI Agent runtime.
- `alpha_agi_business.md` – preserved research architecture of an α‑AGI Business.
- `REMOTE_SWARM.md` – quick‑start to launch remote agents via Helm.
- `download.html` – minimal installer guide for Alpha‑Factory Pro.
- `grafana/` – Grafana dashboards and datasource provisioning.
- `prometheus.yml` – sample Prometheus scraper configuration.

When running the Insight demo the `/simulate` endpoint and CLI accept `energy`
and `entropy` parameters to control the initial state of generated sectors.

Historical image-signing example: verify an image only against its actual publisher identity, provenance and immutable digest. This release does not assert that every historical image was published or signed:
```bash
cosign verify ghcr.io/montrealai/alpha-factory:latest
```
