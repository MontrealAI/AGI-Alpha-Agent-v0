[See docs/DISCLAIMER_SNIPPET.md](../../../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

This chart deploys the α-AGI Insight demo.

Example usage:
```bash
helm upgrade --install insight ./alpha_factory_v1/demos/alpha_agi_insight_v1/infrastructure/helm-chart \
  --set env.OPENAI_API_KEY=<key> \
  --set env.RUN_MODE=api
```
Values such as `service.port` or `image` can be customised via `--set` or a custom values file.
`values.example.yaml` demonstrates typical overrides such as API tokens, service ports and replica counts.
