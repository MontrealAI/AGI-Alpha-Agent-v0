[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)
# Insight Demo GitHub Pages Sprint

This document outlines the minimal tasks required to publish the **α‑AGI Insight v1** demo to GitHub Pages so that users can experience the full browser-based simulation, including the animated meta‑agentic tree search.

- Install **Python 3.11+**, **Node.js 22+**, `mkdocs`, `mkdocs-material` and `playwright`.
- Run `node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js` to confirm the Node version.
- Execute `python scripts/check_python_deps.py` and `python check_env.py --auto-install` to install optional dependencies.

## 2. Build the Static Demo
- From the repository root, run `./scripts/edge_human_knowledge_pages_sprint.sh`.
  - This fetches assets, builds the browser bundle, and refreshes `docs/alpha_agi_insight_v1/`.
- Verify that `docs/alpha_agi_insight_v1/index.html` loads locally using:
  ```bash
  python -m http.server --directory site 8000
  ```
- Browse to <http://localhost:8000/alpha_agi_insight_v1/> and confirm the charts and the animated tree search function correctly.

## 3. Deploy to GitHub Pages
- Execute `./scripts/publish_insight_pages.sh` to build and deploy the `gh-pages` branch.
- Once the workflow completes, verify the live site at:
  <https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/>
- Opening <https://montrealai.github.io/AGI-Alpha-Agent-v0/> shows a landing page with quick links. Use **Launch Demo** to reach this path or open the **Visual Demo Gallery** for other pages.

## 4. Maintain the Demo
- Update `forecast.json` or `population.json` to change the scenario, then re-run `edge_human_knowledge_pages_sprint.sh`.
- Run `scripts/verify_insight_offline.py` to ensure offline caching works before publishing.

These steps keep the demo production-ready and easily reproducible for non‑technical users.

## 5. Update the Meta-Agentic Visualization
- Generate a fresh `tree.json` after each simulation run so the animated tree search reflects current strategies:
  ```bash
  python alpha_factory_v1/demos/alpha_agi_insight_v1/tools/export_tree.py lineage/run.jsonl -o docs/alpha_agi_insight_v1/tree.json
  ```
- Rebuild the site with `./scripts/edge_human_knowledge_pages_sprint.sh` and confirm the nodes animate progressively on page load.

## 6. Final Verification Checklist
- Check that `docs/index.html` links to `alpha_agi_insight_v1/index.html`.
- Load the GitHub Pages URL in a private browsing window to verify caching and service worker installation.
- Search the page source for strings like `OPENAI_API_KEY` to ensure no secrets leaked.
- Run `python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1` after each build.

## 7. Confirm Meta-Agentic Animation
- After deployment, open the live site and watch the **Meta-Agentic Tree Search Progress** panel.
- Nodes should appear sequentially and the best path should highlight in red.
- If no nodes appear within a few seconds, rebuild the site and ensure `tree.json` is valid.
