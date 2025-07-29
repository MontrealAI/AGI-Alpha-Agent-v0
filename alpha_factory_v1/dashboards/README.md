[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Alpha Factory Dashboards

This directory contains Grafana dashboards used for monitoring the Alpha Factory stack. The JSON files can be imported manually or loaded automatically via Docker Compose.

## Usage

1. Ensure [Grafana](https://grafana.com/) is running (see `docker-compose.yml`).
2. To import manually, open Grafana in your browser and navigate to **Dashboards → Import**.
3. Upload `alpha_factory_overview.json` or run the helper script:

   ```bash
   python ../scripts/import_dashboard.py alpha_factory_overview.json
   ```

   The script expects a `GRAFANA_TOKEN` environment variable and optionally `GRAFANA_HOST` (defaults to `http://localhost:3000`).

## Automatic Provisioning

The Docker Compose setup mounts `docs/grafana/` for Grafana provisioning. The same dashboard JSON is placed in that directory so that running `docker compose up -d` will load it automatically.

The default Prometheus data source must be named **Prometheus**.
