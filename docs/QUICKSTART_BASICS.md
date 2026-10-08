[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Quickstart Basics

`AGI-Alpha-Agent-v0` showcases a meta-agentic framework where agents can spawn and refine other agents. The included **α‑AGI Insight** demo runs locally or with cloud APIs when keys are provided.

This page covers the preserved **source-checkout research stack**. For the smaller maintained native
agent, use [Start here](agent/START_HERE.md). To try the browser mission without installing anything,
open [SUCCESSOR Ω](successor/index.html). The [repository guide](agent/REPOSITORY_GUIDE.md) compares the paths.

For this stack, start in the repository root with Python 3.11–3.13, Git, Docker/Compose and the Node
version pinned in `.nvmrc`. Activate your development environment first. The wizard reports missing
tools; it installs dependencies or starts services only after you select an action.

## Steps

1. Create an environment file only if you do not already have one:
   ```bash
   if [ ! -e .env ]; then cp alpha_factory_v1/.env.sample .env; fi
   ```
   Set a private `API_TOKEN` and replace `NEO4J_PASSWORD=REPLACE_ME` before launch. Keep `.env`
   private and out of Git. Provider keys are optional for paths that support local execution.
2. Run the interactive setup wizard:
   ```bash
   python -m scripts.setup_wizard --help
   python -m scripts.setup_wizard
   ```
   Select the setup action you need and inspect its output. Options 1 and 2 may download dependencies;
   options 3 and 4 launch services. A failed action reports an error and returns to the menu. Choose
   option 5 to exit. Do not launch a second copy if you already started the demo from the wizard.
3. If you have not launched from the wizard, check prerequisites and launch the demo:
   ```bash
   ./quickstart.sh --preflight
   ./quickstart.sh
   ```

Stop a foreground demo with **Ctrl+C**. If a launch fails, keep the environment and error output,
correct the reported prerequisite and retry; the setup wizard is not a reset or migration tool.
On Windows, use the documented Python launcher in [Windows setup](WINDOWS_SETUP.md) for Bash-only steps.

For advanced instructions see [README.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/README.md).
If you run into Windows-specific issues, see
[WINDOWS_SETUP.md](WINDOWS_SETUP.md).
