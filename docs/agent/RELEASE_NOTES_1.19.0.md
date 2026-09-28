[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# 1.19.0 — MuZero Planning Lab

The MuZero demo now trains its representation, dynamics, reward, value and policy heads from
bounded replay. Previously the dashboard searched a randomly initialized model and provided
no training path. Action selection now includes immediate reward plus discounted child value,
with min/max normalization and explicit simulation and depth limits.

The local dashboard provides measured learning curves, losses, held-out baselines, search statistics
and an inspectable experiment record. A finite CLI exports reports and portable JSON checkpoints.
MiniChoice introduces delayed rewards in two steps; CartPole, MountainCar and Acrobot remain
available as harder research tasks. No general solving or improvement guarantee is made.

The dedicated Linux CPU environment pins current PyTorch and Gradio with dependency hashes.
The repaired Compose launcher builds dependencies into a non-root, read-only image, waits for
health, binds to loopback, and prints a complete stop command. Native launch is also local by default.
No credentials, downloaded model or automatic LLM/agent gateway is needed.

The original README, notebook, SDK experiment, Compose experiment and flowchart are preserved,
with a source-commit and SHA-256 preservation manifest. The static gallery retains its sample
replay and introduces the maintained local training path. The Colab notebook runs the same finite
experiment without creating a public tunnel.

Validation adds behavioral checks for reward-aware PUCT, visits, depth bounds, gradients,
termination and time-limit targets, RNG isolation, checkpoint corruption, cancellation cleanup
and measured learning. A mandatory release job runs the actual dashboard and Docker image.

[Start the MuZero demo](MUZERO.md).
This is an educational MuZero-style implementation with scalar heads and local replay. It is not
DeepMind's full Atari recipe, achieved AGI, or a deployed autonomous enterprise/financial system.

Use [Start here](START_HERE.md) for the main agent installation and the
[MuZero guide](MUZERO.md) for this optional research environment.
