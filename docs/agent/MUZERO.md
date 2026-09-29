[Project notice](../DISCLAIMER_SNIPPET.md)

# MuZero Planning Lab — operating guide

This optional CPU research demo trains a small neural model from environment transitions and
compares learned-model search against random, untrained and policy-only baselines. Its local
Gradio dashboard shows training returns, losses, root search statistics and bounded environment snapshots.
It is separate from the lightweight operator installation and does not need credentials or model downloads.

Download the matching release source archive or clone the repository. From its root:

```bash
python -m venv .venv-muzero
source .venv-muzero/bin/activate
python -m pip install --require-hashes -r alpha_factory_v1/demos/muzero_planning/requirements.lock
python -m alpha_factory_v1.demos.muzero_planning
```

Open http://127.0.0.1:7861 and choose **Train & compare**. Start with MiniChoice and the default
seed/budgets; then inspect the harder CartPole, MountainCar and Acrobot experiments. Short training
can fail or regress. MiniChoice is deterministic and its repeated evaluations do not establish
unseen-task generalization. **Stop** cancels between episodes; Ctrl+C stops the server.

The dedicated Linux x86-64 dependency lock is exercised on Python 3.11–3.13. Installation needs
network access or a prebuilt wheelhouse. Other platforms need compatible native PyTorch wheels.
Do not mix this optional research environment into an existing operator environment.

For finite execution and evidence export:

```bash
python -m alpha_factory_v1.demos.muzero_planning --headless --max-steps 8 \
  --output experiment.json --checkpoint weights.json
```

Reports contain configuration, software versions, actual rewards/losses, comparisons and checkpoint
weights. New output paths are required. Checkpoints are bounded JSON, never pickle; shape, environment,
duplicate-key and finite-value checks happen before replacing the current model. The checksum identifies
bytes; it is not a signature or an independent evaluation.

Docker users can run `./alpha_factory_v1/demos/muzero_planning/run_muzero_demo.sh`. The launcher
builds dependencies into the image, waits for `/__live`, and prints the complete stop command.
The non-root container uses a read-only filesystem, temporary scratch space and explicit resource limits.
Native and Docker host bindings default to loopback. Public multi-user hosting needs a separate
authentication and deployment design.

The [complete demo guide](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/main/alpha_factory_v1/demos/muzero_planning)
contains the preserved flowchart, full research archive, Colab notebook, programmatic checkpoint
example, algorithm simplifications and troubleshooting. The static gallery chart remains a labeled
sample replay; Python performs the actual neural learning.
