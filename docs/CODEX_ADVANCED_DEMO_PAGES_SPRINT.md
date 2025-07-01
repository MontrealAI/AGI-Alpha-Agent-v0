[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Advanced Demo Pages Sprint for Codex

This sprint outlines a robust sequence to publish the **Alpha‑Factory** demo gallery on GitHub Pages. It builds upon the existing automation scripts so each showcase unfolds organically and remains trivial to deploy by non‑technical users.

## 1. Environment Validation
1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight check:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Confirm Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional packages so verification tools work:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Insight Demo
Execute the bundled helper:
```bash
./scripts/build_insight_docs.sh
```
This compiles the Insight PWA, exports `tree.json` when logs are present,
regenerates `docs/index.html` via `scripts/generate_gallery_html.py` and
verifies the service worker hash.

## 3. Generate the Demo Gallery
From the repository root:
```bash
./scripts/deploy_gallery_pages.sh
```
The script fetches assets, refreshes documentation and builds the MkDocs site under `site/`.

## 4. Preview Locally
Serve the site to verify every page:
```bash
python -m http.server --directory site 8000
```
Navigate to <http://localhost:8000/> and ensure each demo README loads with its preview media. The **Meta‑Agentic Tree Search** animation should play smoothly.

## 5. Publish to GitHub Pages
Deploy the site when satisfied:
```bash
mkdocs gh-deploy --force
```
The gallery becomes available at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
Confirm the landing page shows a menu. Selecting **Launch Demo** opens `alpha_agi_insight_v1/`. Verify offline access works after the first visit.

## 6. Maintenance
- Rerun `./scripts/deploy_gallery_pages.sh` whenever demo docs or assets change.
- Test with `mkdocs build --strict` before deploying.
- Keep `pre-commit` hooks green so the gallery builds reproducibly.
