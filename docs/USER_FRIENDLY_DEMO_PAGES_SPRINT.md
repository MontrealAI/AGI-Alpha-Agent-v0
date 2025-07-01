[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# User‑Friendly Demo Pages Sprint for Codex

This sprint ensures that every advanced demo in `alpha_factory_v1/demos/` unfolds visually and elegantly on GitHub Pages. The tasks combine the existing automation scripts with best practices so non‑technical users can deploy the gallery from a subdirectory with a single command.

## 1. Validate the Environment
1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight check:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Confirm Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional packages so verification tools succeed:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Insight Demo
Execute the bundled helper to compile the progressive web app and verify its service worker:
```bash
./scripts/build_insight_docs.sh
```
This step exports `tree.json` when lineage logs exist, rebuilds
`docs/index.html` via `scripts/generate_gallery_html.py` and ensures offline
support works as expected.

## 3. Generate the Demo Gallery
From the repository root, build the complete gallery and documentation:
```bash
./scripts/deploy_gallery_pages.sh
```
The script fetches assets, refreshes every README, runs integrity checks and outputs the static site under `site/`.

## 4. Preview Locally
Serve the result to confirm animations play smoothly:
```bash
python -m http.server --directory site 8000
```
Open <http://localhost:8000/> and explore `index.html`. Each demo README should display its preview media so users can watch the scenarios unfold in real time.

## 5. Deploy to GitHub Pages
Publish the gallery once satisfied:
```bash
mkdocs gh-deploy --force
```
GitHub Pages serves the final URL at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The landing page now displays quick links. Use **Launch Demo** for `alpha_agi_insight_v1/` or open the **Visual Demo Gallery** to explore every showcase.

## 6. Maintenance Tips
- Capture short GIFs or screenshots under `docs/<demo>/assets/` for a highly visual experience.
- Re‑run the helper whenever demo docs or assets change.
- Verify `pre-commit` hooks pass and run `mkdocs build --strict` before deploying.
