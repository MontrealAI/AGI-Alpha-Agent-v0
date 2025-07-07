[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Offline Setup Guide


This guide explains how to prepare and use a wheelhouse so `check_env.py` and the
setup scripts work without internet access.

## Build the wheelhouse

Run the following commands on a machine with connectivity:

```bash
mkdir -p /media/wheels
pip wheel -r requirements.lock -w /media/wheels
pip wheel -r requirements-dev.txt -w /media/wheels
```
These wheels cover the runtime and development dependencies needed for the test
suite. Copy the directory to the offline host and set
`WHEELHOUSE=/media/wheels` so `check_env.py` and `pytest` install packages from
this local cache.

You can optionally compile a lock file from these wheels:

```bash
pip-compile --no-index --find-links /media/wheels --generate-hashes \
    --output-file requirements.lock requirements.txt
```

Copy the resulting directory to the offline host.

## Environment variables

Set `WHEELHOUSE` to the directory containing your wheels and enable automatic
installation:

```bash
export WHEELHOUSE=/media/wheels
export AUTO_INSTALL_MISSING=1
```

`check_env.py` uses these variables to install missing packages via `pip` without
contacting PyPI. When a `wheels/` directory exists in the repository root the
setup script automatically sets `WHEELHOUSE` for you.

## Running `check_env.py`

Invoke the helper with the `--wheelhouse` flag to verify dependencies:

```bash
python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
```

The command prints `Environment OK` when all required packages are available.

## Browser Demo Tests


