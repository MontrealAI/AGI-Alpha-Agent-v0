[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Quick Start Guide

This tutorial shows how to install the prerequisites, run the Colab notebook and launch the demo either offline or with
API credentials.

## Installing prerequisites

1. Install **Python 3.11–3.13** and create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip pre-commit==4.2.0
   ```
2. Install **Docker** and **Docker Compose** (Compose ≥2.5).
3. Install **Node.js 22** for the web client. Run `nvm use` to activate the version from `.nvmrc`.
4. Ensure `git` is available. Verify the tools:
   ```bash
   python --version
   docker --version
   docker compose version
git --version
```

### Offline setup

Build the wheelhouse before disconnecting from the network:

```bash
./scripts/build_offline_wheels.sh
export WHEELHOUSE="$(pwd)/wheels"
```
Run this script before executing `python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` and `pytest`.
When no network connection is available, install dependencies from the
wheel cache with:

```bash
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
WHEELHOUSE="$WHEELHOUSE" ./quickstart.sh
```

See [docs/OFFLINE_INSTALL.md](OFFLINE_INSTALL.md) for detailed steps.

## Running the Colab notebook

Open
Google Colab and execute the following steps:

1. Run the first cell to clone the repository and install dependencies.
2. Optionally set `OPENAI_API_KEY` in the second cell.
3. Execute the demo cell to launch the Insight search loop.

The notebook works entirely offline when no API key is provided.

## Launching the demo

From the repository root, verify the environment and start the demo:

```bash
python check_env.py --auto-install  # may take several minutes
# Press Ctrl+C to abort and rerun with '--timeout 300' to limit waiting
./quickstart.sh
```

Alternatively build and run the Docker image in one step:
```bash
./run_quickstart.sh
```

### Using the prebuilt Docker image

```bash
docker pull montrealai/alpha-factory:latest
docker run --rm -p 8000:8000 \
  -v $(pwd)/.env:/app/.env montrealai/alpha-factory:latest
```

Only the Python **3.13** build updates the `latest` tag.

Copy `.env.sample` to `.env` and add your API keys to enable cloud features. Without keys, the program falls back to the
local Meta‑Agentic Tree Search:

`AF_MEMORY_DIR` controls where the demos store their JSONL history. The sample
file uses `/tmp/alphafactory`, which is wiped on reboot. Set it to a persistent
folder if you want to keep results across sessions.

```bash
alpha-agi-insight-v1 --episodes 5  # with or without OPENAI_API_KEY
```

Run `pre-commit run --all-files` once the setup completes to ensure formatting.

### Windows Subsystem for Linux (WSL)

When working on Windows, install **WSL 2** and enable Docker Desktop's
"Use the WSL 2 based engine" option under **Settings → General**. Also enable
WSL integration for your Linux distribution to share the Docker daemon.

Clone this repository inside your WSL home directory to avoid path translation
issues. Paths on the Windows drive such as `/mnt/c/...` sometimes break volume
mounts or slow down file operations.

Start a WSL shell from PowerShell and run the setup as usual:

```powershell
wsl
cd ~/AGI-Alpha-Agent-v0
python check_env.py --auto-install
./quickstart.sh
```

When building Docker images from PowerShell, reference the WSL path using the
`\\wsl$` prefix:

```powershell
docker build -f Dockerfile \\wsl$\Ubuntu\home\<user>\AGI-Alpha-Agent-v0
```

These steps prevent common path and permission errors on Windows.

### WSL 2 Setup Tips

Run the following commands from an elevated PowerShell window to ensure WSL 2 is ready:

```powershell
wsl --install
wsl --set-default-version 2
wsl --update
```

Open your Linux shell and install the build tools required by packages like `psutil` and `cryptography`:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libssl-dev
```

When package installation fails inside WSL, missing headers are often the culprit. Reinstall the wheel after installing the tools above.

#### Common WSL errors

| Symptom | Resolution |
|---------|------------|
| `docker: command not found` | Start Docker Desktop and enable WSL integration. |
| `Cannot connect to the Docker daemon` | Run `wsl --shutdown` then reopen the shell. |
| Permission errors when accessing `/mnt/c` | Clone the repo under your WSL home directory. |
| Compilation failures for `psutil` or `cryptography` | Ensure `build-essential` and `python3-dev` are installed. |

## OpenAI Agents SDK and Google ADK integration

Expose the search loop via the **OpenAI Agents SDK**:

```bash
python alpha_factory_v1/demos/meta_agentic_agi/openai_agents_bridge.py
# → http://localhost:5001/v1/agents
```

Enable the optional **Google ADK** gateway for federation:

```bash
pip install google-adk
ALPHA_FACTORY_ENABLE_ADK=true \
  python alpha_factory_v1/demos/meta_agentic_agi/openai_agents_bridge.py
```

The bridge automatically falls back to local execution when the packages or API keys are missing.
