[See docs/DISCLAIMER_SNIPPET.md](../../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
# α‑AGI Insight Docs

Documentation for the α‑AGI Insight demo.


Whenever `alpha_factory_v1/core/utils/a2a.proto` changes, regenerate the protocol stubs:

```bash
./tools/gen_proto_stubs.sh
```

This updates `alpha_factory_v1/core/utils/a2a_pb2.py` and `tools/go_a2a_client/a2a.pb.go`.

## Quickstart

From the `alpha_factory_v1/demos/alpha_agi_insight_v1` directory run the
environment check before launching the demo:

```bash
python ../../../check_env.py --auto-install
```

Start the Insight demo with the repository root
[quickstart.sh](../../../quickstart.sh):

```bash
../../../quickstart.sh
```

An interactive walkthrough is available in the Colab notebook
[colab_alpha_agi_insight_v1.ipynb](../colab_alpha_agi_insight_v1.ipynb).


## Configuration

Before deploying the Helm charts, edit `alpha_factory_v1/helm/alpha-factory/values.yaml` and `alpha_factory_v1/helm/alpha-factory-remote/values.yaml`.
Set `NEO4J_PASSWORD` to the real database password and configure a strong Grafana `adminPassword`.
