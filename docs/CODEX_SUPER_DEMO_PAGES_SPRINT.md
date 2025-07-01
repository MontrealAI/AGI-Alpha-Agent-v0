[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Alpha‑Factory – Complete Demo Pages Sprint for Codex

This sprint outlines a robust, production‑ready path for Codex to publish **every**
advanced demo under `alpha_factory_v1/demos/` as a single, visually rich GitHub
Pages site. The goal is an intuitive experience where non‑technical users can
launch each showcase directly from a browser and watch it unfold in real time.

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
4. Install optional packages:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Insight Demo

The Insight browser bundle powers the animated tree search. Refresh it with:
```bash
./scripts/build_insight_docs.sh
```
This step exports `tree.json` when lineage logs exist, regenerates
`docs/index.html` via `scripts/generate_gallery_html.py` and verifies the
service worker hash for offline support.

## 3. Generate the Demo Gallery

From the repository root run:
```bash
./scripts/deploy_gallery_pages.sh
```
The script fetches assets, copies preview media for each demo and builds the
MkDocs site under `site/`.

## 4. Preview Locally

Serve the site to confirm every page loads and animations play smoothly:
```bash
python -m http.server --directory site 8000
```
Visit <http://localhost:8000/> and explore the **Demo Gallery**. Ensure the
**Meta‑Agentic Tree Search** animation highlights the evolving branches in real
time and that screenshots or GIFs accompany each README.

## 5. Deploy to GitHub Pages

Publish the site using `mkdocs`:
```bash
mkdocs gh-deploy --force
```
GitHub Pages serves the final result at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The root `index.html` now presents quick links. Select **Launch Demo** for the Insight preview or **Visual Demo Gallery** for all other showcases.

## 6. Verify the Live Site

1. Load the URL in an incognito window to avoid cached assets.
2. Disable the network and reload `alpha_agi_insight_v1/` to confirm offline
   functionality.
3. Check that each demo page includes preview media and clear instructions.
4. Search the page source to ensure no secrets leaked during the build.

Following this sequence yields a polished, comprehensive GitHub Pages deployment
where every demo unfolds visually and organically for end users.
