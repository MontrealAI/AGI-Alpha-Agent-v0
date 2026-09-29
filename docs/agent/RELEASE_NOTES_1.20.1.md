[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# 1.20.1 — Planning lab recovery and portable evidence

The MuZero × MCTS × LLM lab now clears stale results and reports failure visibly,
supports retry after invalid input, and downloads the complete JSON report directly
from the browser. Downloads contain the same record shown on screen and require no
server-side report files. Reports identify the demo version and hash the planning
source actually used, alongside the existing evidence, measurements and weights.

Question and rationale limits now count whitespace, and the dashboard rejects
non-finite numeric inputs. The launcher validates both the selected interpreter and
its reused environment even when Python optimization is enabled. The macOS setup
path uses Apple's available PyTorch wheel instead of the Linux `+cpu` package.
Native macOS/Windows acceptance remains outside the verified Linux profile.

Behavioral tests and the browser release gate exercise report downloads, failure
recovery, stale-output clearing and input boundaries. Strict type checking now
includes the integration's CLI, lab and dashboard. Existing flowcharts, original
presentations, archives and simulator behavior are preserved.

This is a local educational planning experiment. It does not establish achieved
AGI, autonomous-enterprise readiness, model quality or financial production safety.

[Setup and use the lab](../demos/muzeromctsllmagent_v0.md).
Use [Start here](START_HERE.md) for the main agent installation and operator workflow.
