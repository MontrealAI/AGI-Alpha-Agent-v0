[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Edge-of-Human-Knowledge Pages Sprint for Codex

This sprint explains how Codex can publish the **Alpha-Factory** demo gallery to GitHub Pages so each showcase plays back organically with a single command. Use the shell wrapper `scripts/edge_human_knowledge_pages_sprint.sh` or the cross‑platform Python version `scripts/edge_human_knowledge_pages_sprint.py` which call the full deployment workflow and print the final URL.

## Quick Start
1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the wrapper:
   ```bash
   ./scripts/edge_human_knowledge_pages_sprint.sh
   # or on systems without Bash
   python scripts/edge_human_knowledge_pages_sprint.py
   ```
   This triggers `edge_of_knowledge_sprint.sh` which performs environment validation, dependency checks, README disclaimer verification, asset builds, integrity tests and finally deploys the site via `mkdocs gh-deploy`.
3. Visit the printed URL in an incognito window and ensure `index.html` links to every demo with preview media.

## Maintenance
- Re-run the wrapper whenever demo docs or assets change.
- Validate formatting and basic tests before publishing:
  ```bash
  pre-commit run --files <changed_files>
  pytest -m 'not e2e'
  ```
