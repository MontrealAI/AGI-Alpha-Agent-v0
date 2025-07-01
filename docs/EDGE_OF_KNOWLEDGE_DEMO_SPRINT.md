[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Edge‑of‑Knowledge Demo Gallery Sprint for Codex

This sprint distils how Codex can publish the entire **Alpha‑Factory v1** demo suite to GitHub Pages so that every showcase unfolds in real time and remains effortless for non‑technical users to explore.

## 1. Environment Validation
1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Verify the Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional Python packages so the verification tools succeed:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build and Verify the Gallery
Execute the helper from the repository root:
```bash
./scripts/deploy_gallery_pages.sh
```
This command fetches browser assets, compiles the Insight demo, refreshes all documentation, runs integrity checks and, when Playwright is available, validates offline functionality.
The helper also invokes `scripts/generate_gallery_html.py` so `docs/index.html`
tracks new demos automatically.

## 3. Preview Locally
Serve the site to ensure each page loads smoothly:
```bash
python -m http.server --directory site 8000
```
Browse to <http://localhost:8000/> and click through `index.html`. Confirm that every demo README displays its preview media and that `alpha_agi_insight_v1/` animates the meta‑agent tree search progressively.

## 4. Deploy to GitHub Pages
Publish the gallery when satisfied:
```bash
mkdocs gh-deploy --force
```
The site becomes accessible at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The landing page now displays quick links. Select **Launch Demo** for the insight preview or open the **Visual Demo Gallery** to view every README as the demos unfold organically.

## 5. Maintenance Tips
- Re‑run `./scripts/deploy_gallery_pages.sh` whenever demo docs or assets change.
- Capture short GIFs or screenshots under `docs/<demo>/assets/` to keep the gallery highly visual.
- Test with `mkdocs build --strict` before deploying and ensure `pre-commit` hooks pass.
