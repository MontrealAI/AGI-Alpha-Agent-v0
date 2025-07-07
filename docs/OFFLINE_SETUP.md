[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Offline Setup Reference


This document summarises how to install the project without internet access.

## Build a wheelhouse
Run the helper script on a machine with connectivity:

```bash
./scripts/build_offline_wheels.sh
```

To build the wheelhouse **and** regenerate all lock files in one step:

```bash
./scripts/offline_prepare.sh
```

This collects wheels for all lock files inside a `wheels/` directory. Copy this
directory to the offline host.

Set `WHEELHOUSE=$(pwd)/wheels` before running `check_env.py` or the tests:

```bash
export WHEELHOUSE=$(pwd)/wheels
```

## Environment variables
Set these before running the helper scripts:

```bash
export WHEELHOUSE=/media/wheels
export AUTO_INSTALL_MISSING=1
```

`check_env.py` reads them to install packages from the wheelhouse when the network is unavailable.

### Prebuilt wheels for heavy dependencies
`numpy`, `PyYAML` and `pandas` ship as binary wheels on PyPI. These small wheels
can be bundled with the repository so the smoke tests run offline. Grab them
when constructing the wheelhouse so the installer does not attempt to compile
them from source:

```bash
pip wheel numpy pyyaml pandas -w /media/wheels
```

Include any other large dependencies, such as `torch` or `scipy`, by passing
their names to `pip wheel` or `pip download` with the versions pinned in
`requirements.lock`.

If the repository already contains a `wheels/` directory you can use it as the
wheelhouse directly:

```bash
export WHEELHOUSE="$(pwd)/wheels"
```

Run `check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` to install from
this local cache.

## Verify packages
Use the scripts below to confirm all requirements are satisfied:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
```

Run `pytest -q` once the check succeeds.

See [tests/README.md](../tests/README.md#offline-install) and [AGENTS.md](../AGENTS.md#offline-setup) for the full instructions.

## Tested platforms

The offline workflow was verified on **Ubuntu 22.04**, **macOS** with Docker
Desktop and **WSL2** on Windows 11. Native Windows without WSL2 often fails due
to path translation and file sharing issues, so using WSL2 is strongly
recommended.

### WSL2 setup

1. Install WSL and update it from an elevated PowerShell prompt:

   ```powershell
   wsl --install
   wsl --set-default-version 2
   wsl --update
   ```

2. Install Docker Desktop and enable **Use the WSL 2 based engine** under
   **Settings → General**. Turn on integration for your distribution under
   **Resources → WSL Integration**.

3. Inside the WSL shell install build tools and Python headers:

   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-dev build-essential libssl-dev
   ```

4. Clone the repository inside your Linux home directory, create a virtual
   environment and verify the setup:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
   ```


```bash
pytest -k 'not pwa_offline and not browser_ui'
```

### Windows Setup Tips
Docker Desktop sometimes fails to mount Windows paths when running offline.
Use the `\\wsl$\` prefix or an absolute path with the drive letter when
passing `--volume` to `docker` or `docker compose`. If you see
"drive is not shared" errors, enable file sharing for the target drive under
**Settings → Resources → File sharing** in Docker Desktop.

Activate the virtual environment from PowerShell with:

```powershell
\.\.venv\Scripts\Activate.ps1
```

If execution of the activation script is blocked, run PowerShell as
Administrator and set the policy:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Reopen the shell and retry the command. Once the environment is active, run the
setup scripts normally.

### Example: Business demo
The business demo works offline when a wheelhouse is provided. Assuming
the wheels live under `/media/wheels`:

```bash
export WHEELHOUSE=/media/wheels
export AUTO_INSTALL_MISSING=1
python alpha_factory_v1/demos/alpha_agi_business_v1/start_alpha_business.py \
  --wheelhouse "$WHEELHOUSE"
```
