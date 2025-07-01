[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Edge-of-Knowledge Demo Tasks Sprint for Codex

This sprint condenses the steps required for Codex to expose every advanced demo under `alpha_factory_v1/demos/` on GitHub Pages. The goal is a polished subdirectory where each showcase unfolds in real time with smooth, highly visual interactions.

Run `./scripts/edge_of_knowledge_sprint.sh` from the repository root for a one-command deployment.

## 1. Validate the Environment
1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
3. Verify the Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
4. Install optional packages so verification tools succeed:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```
5. Verify every README includes the standard disclaimer:
   ```bash
   python scripts/verify_disclaimer_snippet.py
   ```

6. Validate the demo packages:
   ```bash
   python -m alpha_factory_v1.demos.validate_demos
   ```

## 2. Build the Insight Demo
Execute the helper to compile the progressive web app and confirm the service worker hash:
```bash
./scripts/build_insight_docs.sh
```
When lineage logs are present this exports `tree.json`, refreshes
`docs/index.html` via `scripts/generate_gallery_html.py` and ensures the
**Meta‑Agentic Tree Search** plays back organically.

## 3. Generate the Demo Gallery
From the repository root:
```bash
./scripts/deploy_gallery_pages.sh
```
The script fetches assets, refreshes documentation and builds the MkDocs site under `site/`.

## 4. Preview Locally
Serve the result to ensure animations load smoothly:
```bash
python -m http.server --directory site 8000
```
Browse to <http://localhost:8000/> and step through `index.html`. Confirm that every README displays preview media so viewers can follow along in real time.

Verify offline support:
```bash
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
python scripts/verify_insight_offline.py
```

## 5. Deploy to GitHub Pages
Publish the gallery once satisfied:
```bash
mkdocs gh-deploy --force
```
The final URL typically resembles:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The landing page now displays quick links; pick **Visual Demo Gallery** for all showcases or **Launch Demo** for the insight preview.

## 6. Maintenance Tips
- Re‑run the helper whenever demo docs or assets change.
- Capture short GIFs or screenshots under `docs/<demo>/assets/` for a highly visual experience.
- Test with `mkdocs build --strict` before deploying and ensure `pre-commit` hooks pass.
