[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Demo Access Sprint for Codex

This short sprint distills how Codex can publish the **Alpha‑Factory v1** demo suite to GitHub Pages so every showcase is accessible from a single, beautiful subdirectory. The process mirrors the existing demo gallery script while emphasising verification and a smooth real‑time experience.

## 1. Verify the Environment

1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight check:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Confirm the Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional dependencies:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Insight Demo

The Insight browser bundle powers many visualisations. Refresh it with:
```bash
./scripts/build_insight_docs.sh
```
This regenerates `docs/alpha_agi_insight_v1/`, refreshes `docs/index.html` via
`scripts/generate_gallery_html.py` and verifies the service worker hash. The
directory contains everything needed for offline access and the animated
Meta‑Agentic Tree Search.

## 3. Generate the Demo Gallery

Run the gallery helper:
```bash
./scripts/gallery_sprint.sh
```
It compiles the docs, copies preview assets for every demo and builds the MkDocs site under `site/`.

## 4. Preview Locally

Start a simple HTTP server:
```bash
python -m http.server --directory site 8000
```
Open <http://localhost:8000/> and navigate through the gallery. Ensure each page loads its screenshots or GIFs and that `alpha_agi_insight_v1/` animates the tree search in real time.

## 5. Deploy to GitHub Pages

Publish the site:
```bash
mkdocs gh-deploy --force
```
Upon completion, GitHub Pages serves the gallery at:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
The root `index.html` now displays a menu with quick links. Use **Visual Demo Gallery** for the full list or **Launch Demo** for the insight preview.

## 6. Verify the Live Site

1. Load the URL in an incognito window.
2. Check that `alpha_agi_insight_v1/` works offline after the first visit (disable network and reload).
3. Confirm each demo page includes preview media and instructions to run locally.
4. Search the page source for secrets to ensure none leaked.

Following this sprint yields a polished, user‑friendly GitHub Pages deployment showcasing all demos in a single subdirectory.
