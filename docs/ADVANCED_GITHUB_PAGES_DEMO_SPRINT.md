[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Advanced GitHub Pages Demo Sprint for Codex

This sprint details how Codex can publish every demo under `alpha_factory_v1/demos/` to GitHub Pages so that each showcase plays in real time, with highly visual elegance. The workflow reuses the existing automation scripts and emphasises environment checks and offline verification.

Run `./scripts/edge_of_knowledge_sprint.sh` from the repository root for a complete one-command deployment.

## 1. Verify the Environment
1. Install **Python 3.11+** and **Node.js 20+**.
2. Execute the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Confirm Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional packages and verify baseline requirements:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```
5. Ensure every README embeds the disclaimer:
   ```bash
   python scripts/verify_disclaimer_snippet.py
   ```
6. Validate the demo packages:
   ```bash
   python -m alpha_factory_v1.demos.validate_demos
   ```

## 2. Build the Insight Demo
Regenerate the progressive web app and check the service worker hash:
```bash
./scripts/build_insight_docs.sh
```
This step exports `tree.json` when lineage logs are present,
regenerates `docs/index.html` via `scripts/generate_gallery_html.py` and ensures
the meta‑agent tree search animates organically.

## 3. Generate the Demo Gallery
Compile all documentation and build the MkDocs site:
```bash
./scripts/deploy_gallery_pages.sh
```
The helper fetches browser assets, refreshes docs and outputs the static site under `site/`.

## 4. Preview Locally
Serve the site to ensure animations and images load smoothly:
```bash
python -m http.server --directory site 8000
```
Open <http://localhost:8000/> and navigate through `index.html`.

## 5. Deploy to GitHub Pages
Publish the gallery when satisfied:
```bash
mkdocs gh-deploy --force
```
GitHub Pages hosts the result at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The landing page now presents a short menu. Use **Visual Demo Gallery** to browse every demo or **Launch Demo** for the insight preview.

## 6. Maintenance Tips
- Re-run `./scripts/deploy_gallery_pages.sh` whenever docs or assets change.
- Capture GIFs or screenshots under `docs/<demo>/assets/` for a highly visual experience.
- Run `mkdocs build --strict` and ensure `pre-commit` passes before deploying.
