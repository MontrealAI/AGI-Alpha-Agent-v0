[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Offline Wheelhouse

This directory normally stores prebuilt wheels so the MuZero Planning demo and
unit tests can run without network access. **The wheelhouse is not committed**
because some packages exceed GitHub's 100 MB size limit. Build the wheelhouse on
a machine with connectivity and copy it here (or mount the directory) as
needed. The helper script
`scripts/build_offline_wheels.sh` collects all required wheels from
`requirements.lock`, `requirements-dev.txt`, `requirements-demo.lock`
and each demo's `requirements.lock` file:

```bash
./scripts/build_offline_wheels.sh
```
Run this command before executing `python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"` and `pytest`.

Set `WHEELHOUSE=$(pwd)/wheels` before running the setup script or tests:

```bash
WHEELHOUSE=$(pwd)/wheels AUTO_INSTALL_MISSING=1 ./codex/setup.sh
WHEELHOUSE=$(pwd)/wheels AUTO_INSTALL_MISSING=1 \
  python check_env.py --auto-install --wheelhouse "$WHEELHOUSE"
```

`run_muzero_demo.sh` and `pytest` pick up the `WHEELHOUSE` environment
variable automatically when this directory exists.
