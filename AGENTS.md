# AGENTS.md

Guidelines for human contributors and automated agents.

## Coding style
- Target Python 3.11+ and include type hints.
- Indent with 4 spaces and wrap lines at 120 characters.
- Write concise Google style docstrings for public modules, classes and functions.

## Workflow
1. Bootstrap the environment using `.codex/setup.sh`. Set `WHEELHOUSE=/path/to/wheels` for offline installs.
2. Run `python check_env.py --auto-install` to ensure optional packages are available.
3. Execute `pytest -q`. If tests fail, explain the reasons in your pull request.
4. Keep new code well tested and adhere to the style guide.

## Pull requests
- Summarise changes clearly.
- Note any failing tests and provide context.
