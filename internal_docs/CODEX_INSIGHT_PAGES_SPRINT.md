[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# α‑AGI Insight v1 – GitHub Pages Sprint for Codex

This short guide provides a step-by-step sprint for Codex to ensure the **α‑AGI Insight v1 – Beyond Human Foresight** demo is fully accessible from a GitHub Pages subdirectory. The resulting static site must showcase the animated **Meta‑Agentic Tree Search** in real time and remain easy for non‑technical users to deploy.

## 1. Environment Setup

1. Install **Python 3.11+** and **Node.js 20+**.
2. Install `mkdocs`, `mkdocs-material` and `playwright` via `pip`:
   ```bash
   pip install mkdocs mkdocs-material playwright
   ```
3. Verify Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional Python packages:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Demo

Run the bundled helper from the repository root:

```bash
./scripts/edge_human_knowledge_pages_sprint.sh
```

This script fetches the browser assets, compiles the PWA, exports `tree.json` when lineage logs are present, verifies the service worker and generates the MkDocs site under `site/`. After the build completes run the integrity check to ensure the cached Workbox file matches the service worker hash:

```bash
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
```

Preview the result locally:

```bash
python -m http.server --directory site 8000
```

Navigate to <http://localhost:8000/alpha_agi_insight_v1/> and confirm:

- Charts load correctly and scale with the window.
- The **Meta‑Agentic Tree Search** panel animates each node and highlights the best path in red.
- Logs toggle properly with the *Show/Hide Logs* button.
- Disable your network connection and reload the page to verify the service worker caches assets for offline use.

## 3. Deploy to GitHub Pages

Use the deployment helper to publish the docs. The new `deploy_insight_full.sh`
script performs additional environment checks and runs a quick offline test
before pushing to GitHub Pages:

```bash
./scripts/deploy_insight_full.sh
```

The script rebuilds the site and pushes `site/` to the `gh-pages` branch via `mkdocs gh-deploy`. It prints the final URL upon completion, typically:

```
https://<org>.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/
```

Verify the live demo in an incognito window to ensure no cached assets interfere. The service worker should register and allow offline access after the first load.

## 4. Update the Tree Search Visualization

After generating new lineage logs, refresh the tree visualization before rebuilding:

```bash
python alpha_factory_v1/demos/alpha_agi_insight_v1/tools/export_tree.py \
  lineage/run.jsonl -o docs/alpha_agi_insight_v1/tree.json
```

Rerun the build and deployment commands so GitHub Pages reflects the latest search progression.

## 5. Final Verification Checklist

- ✅ `forecast.json`, `population.json` and `tree.json` present in `docs/alpha_agi_insight_v1/`.
- ✅ `lib/workbox-sw.js` and `manifest.json` accompany `index.html` for PWA offline support.
- ✅ `scripts/verify_workbox_hash.py` reports a valid hash for the deployed service worker.
- ✅ No API keys or secrets embedded in the HTML or JavaScript.
- ✅ Meta‑Agentic Tree Search animation renders smoothly on the live site.
- ✅ Branch connections animate as they appear, clearly tracing the search path.
- ✅ Demo functions offline after first visit.
- ✅ Opening `https://<org>.github.io/AGI-Alpha-Agent-v0/` displays the
  landing page with a link to `alpha_agi_insight_v1/` via `docs/index.html`.

Following these steps yields a robust, production-ready deployment of α‑AGI Insight v1 on GitHub Pages, accessible to any user via a simple link.
