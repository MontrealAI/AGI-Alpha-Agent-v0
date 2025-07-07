[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# alpha-factory-remote Helm Chart

This chart deploys a remote worker pod for the **Alpha‑Factory** swarm. It packages a single worker container alongside optional Prometheus/Grafana monitoring via the `kube-prometheus-stack` dependency.

## Installation
```bash
helm upgrade --install af-remote ./helm/alpha-factory-remote \
  --set env.OPENAI_API_KEY=<key>
```
The worker exposes gRPC on port `8000` and publishes Prometheus metrics on the
port defined by `env.METRICS_PORT` (default `9090`). Liveness and readiness
probes query `/healthz` for reliable orchestration.

Like the main chart, `alpha-factory-remote` includes a `values.schema.json` file
for validating custom values during installation. Incorrect types or unexpected
fields trigger an immediate error, simplifying debugging.

## Values
- `image.repository` – container image (default `ghcr.io/montrealai/alpha-factory`)
- `image.tag` – image tag (default `v2`)
- `env` – key/value environment variables passed to the container
- `replicaCount` – number of worker pods
- `workerService` – type and port of the Service exposing the worker
- `spiffe.enabled` – enable SPIFFE sidecar
- `grafanaService` – NodePort configuration for Grafana when Prometheus stack is enabled

## Metrics & Dashboards
When `prometheus.enabled` is true, a `ServiceMonitor` matching label `app.kubernetes.io/name=alpha-factory` is created by the dependency. Grafana is provisioned with a finance dashboard.
