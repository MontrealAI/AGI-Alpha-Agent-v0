[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Getting Started

This short guide describes the quickest way to run the α‑AGI Insight demo.

1. **Check the environment**
   ```bash
   python check_env.py --auto-install
   ```
   This installs missing Python packages and validates Docker.
2. **Copy the sample environment**
   ```bash
   cp alpha_factory_v1/.env.sample .env
   ```
   API keys are optional. Without them the demo runs in offline mode.
3. **Launch the stack**
   ```bash
   ./quickstart.sh
   ```
4. **Run the demo**
   ```bash
   alpha-agi-insight-v1 --episodes 5
   ```
   Set `AGI_INSIGHT_OFFLINE=1` to guarantee zero network access.

See [quickstart.md](quickstart.md) for more details and Docker instructions.
