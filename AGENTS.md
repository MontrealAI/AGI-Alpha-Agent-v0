# Contributor Guide

This repository contains the Alpha-Factory v1 package and demos.
The instructions below apply to all contributors and automated agents.

## Development Environment
- Create and activate a **Python&nbsp;3.11 (3.11.x only; 3.12 not yet supported)** virtual environment before running the setup script.
- Run `./codex/setup.sh` to install the project in editable mode along with minimal runtime dependencies.
- When offline, export `WHEELHOUSE=/path/to/wheels` first so both
  `check_env.py --auto-install` and `./codex/setup.sh` install from the
  local wheelhouse:
  
  ```bash
  export WHEELHOUSE=/path/to/wheels
  ./codex/setup.sh
  python check_env.py --auto-install
  ```
  This installs any missing optional packages from the wheelhouse if provided.
- Execute `pytest -q` and ensure the entire suite passes. If failures remain, document them in the PR description.
- Run `python alpha_factory_v1/scripts/preflight.py` or
  `./quickstart.sh --preflight` to verify Docker, git, and required
  packages. After verification, run `./quickstart.sh` to launch the
  project. The script creates the virtual environment and installs
  required dependencies automatically. See the
  [5‑Minute Quick‑Start](README.md#6-5-minute-quick-start) section in the
  README for more details.
- On Windows or systems without Bash, run `python alpha_factory_v1/quickstart.py`.

## Coding Style
- Use **Python&nbsp;3.11** or newer and include type hints for public APIs.
- Indent with 4 spaces and keep lines under 120 characters.
- Provide concise [Google style](https://google.github.io/styleguide/pyguide.html#381-docstrings) docstrings
for modules, classes and functions.
- Format code with `black` (line length 120) and run `ruff` or `flake8` for linting, if available.
- Ensure code is formatted before committing.
- Run `mypy --config-file mypy.ini .` (or `pyright`) with a **strict** configuration. The
  `mypy.ini` configuration file is located at the repository root.
- Install pre‑commit and set up the git hook:
  1. `pip install pre-commit`
  2. `pre-commit install`
  3. Run `pre-commit run --all-files` once to populate the cache.
  4. Run `pre-commit run --files <paths>` before committing.
    CI will reject commits that fail these checks.

## Pull Requests
- Keep commits focused and descriptive. Use meaningful commit messages.
- Ensure `git status` shows a clean working tree before committing.
- Run `python check_env.py --auto-install` and `pytest -q` before committing. \
  Document any remaining test failures in the PR description.
- Summarize your changes and test results in the PR body.
- Title PRs using `[alpha_factory] <Title>`.
- All contributions are licensed under Apache 2.0.

### PR Message Guidelines
- Keep the subject line concise and under 72 characters.
- Optionally include a short body explaining the rationale.
- Consider using a simplified Conventional Commits prefix such as
  `feat:`, `fix:` or `docs:` to ease changelog generation.
