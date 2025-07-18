[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

## Disclaimer
This demo is a conceptual research prototype. References to "AGI" and
"superintelligence" describe aspirational goals and do not indicate the
presence of a real general intelligence. Use at your own risk.

# Safety Notes

This system monitors numeric instability, reward hacking, and policy divergence. It can pause training when anomalies are detected and enforces role-based agent scopes.

Monitoring numeric instability helps catch sudden spikes or NaN values that signal faulty gradients or diverging models. The training loop logs running statistics for rewards, activations, and losses, and halts when numbers move outside safe bounds.

Policy divergence occurs when the agent's behavior drifts from its intended strategy. By periodically comparing actions against a baseline policy, the system can stop training if the divergence grows beyond a threshold.
