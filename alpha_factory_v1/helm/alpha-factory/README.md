[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# alpha-factory Helm Chart

This chart deploys the core **Alpha Factory** service including the API, UI and optional monitoring stack. It mirrors the provided Docker Compose setup while remaining easy to customise.

## Installation
```bash
helm upgrade --install alphafactory ./helm/alpha-factory \
  --set env.OPENAI_API_KEY=<key>
```

The service exposes:
- REST + gRPC on port `8000`
- Web UI on port `3000`
- Prometheus metrics on port defined by `env.METRICS_PORT` (default `9090`)

Liveness and readiness probes hit `/healthz` to ensure Kubernetes can reliably
restart unhealthy pods.

The chart ships with a `values.schema.json` file enabling Helm's built‑in value
validation. Custom values are checked at install time for structural mistakes so
misconfigurations are caught early.

## Values
- `image.repository` – container image (default `ghcr.io/montrealai/alpha-factory`)
- `image.tag` – image tag (default `v2`)
- `env` – key/value environment variables passed to the container
- `replicaCount` – number of pods
- `service.type` – Service type (`ClusterIP`, `LoadBalancer`…)
- `existingSecret` – use a pre-created Secret instead of the generated one
- `spiffe.enabled` – enable SPIFFE sidecar
- `grafanaService` – NodePort configuration for Grafana when Prometheus stack is enabled

## Monitoring
When `prometheus.enabled` is true, a `ServiceMonitor` matching label `app.kubernetes.io/name=alpha-factory` is created by the dependency. Grafana is provisioned with a finance dashboard.
