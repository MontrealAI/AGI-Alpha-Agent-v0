[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# α‑AGI Insight v1 GitHub Pages Access Sprint

This short guide distills the essential steps required to build and publish the **α‑AGI Insight v1 — Beyond Human Foresight** demo so that anyone can experience the full browser‑based simulation directly from GitHub Pages. It assumes a fresh clone of the repository and minimal familiarity with command‑line tools.

## 1. Environment Preparation

1. Install **Python 3.11+** and **Node.js 20+**.
2. Install `mkdocs`, `mkdocs-material` and `playwright`:
   ```bash
   pip install mkdocs mkdocs-material playwright
   ```
3. Verify Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Ensure optional Python dependencies are present:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Static Demo

Run the helper script from the repository root:

```bash
./scripts/edge_human_knowledge_pages_sprint.sh
```

This command:
- Downloads the PWA assets (`npm run fetch-assets`).
- Installs exact Node dependencies (`npm ci`).
- Builds the browser bundle and exports `tree.json` if `lineage/run.jsonl` exists.
- Verifies the service worker hash and generates the MkDocs site under `site/`.

Test the result locally:

```bash
python -m http.server --directory site 8000
```

Open <http://localhost:8000/alpha_agi_insight_v1/> and confirm:
- Charts render correctly.
- The **Meta‑Agentic Tree Search** panel animates nodes one by one, highlighting the best path.
- The logs toggle works as expected.

## 3. Deploy to GitHub Pages

To publish the site, run the helper below. It performs preflight checks,
builds the PWA, verifies offline access and deploys everything in one step:

```bash
./scripts/deploy_insight_full.sh
```

The script builds the docs and pushes them to the `gh-pages` branch via `mkdocs gh-deploy`. When it finishes, it prints the final URL, typically:

```
https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/
```

Anyone can then browse to this address to view the fully interactive demo.

## 4. Updating the Tree Search Visualization

After running a new simulation, refresh the tree search data:

```bash
python alpha_factory_v1/demos/alpha_agi_insight_v1/tools/export_tree.py \
  lineage/run.jsonl -o docs/alpha_agi_insight_v1/tree.json
```

Rebuild and redeploy using the commands above so the GitHub Pages site reflects the latest search.

## 5. Final Checklist

- ✅ Service worker registered (`lib/workbox-sw.js` present and hash verified).
- ✅ `forecast.json`, `population.json`, and `tree.json` included in `docs/alpha_agi_insight_v1/`.
- ✅ Demo loads in an incognito browser and works offline after the first visit.
- ✅ No secrets (e.g., `OPENAI_API_KEY`) appear in the deployed HTML or JS.
- ✅ Meta‑Agentic Tree Search animation plays smoothly.

Following these steps ensures a polished, production‑ready deployment that a non‑technical user can replicate with a single command.
