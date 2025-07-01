[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Edge Demo Pages Sprint for Codex

This short guide details how Codex can expose every Alpha‑Factory demo via GitHub Pages. The goal is a beautiful subdirectory that plays each showcase in real time and remains trivial for non‑technical users to publish.

## 1. Prepare the Environment

1. Install **Python 3.11+** and **Node.js 20+**.
2. Run the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Verify Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional packages:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build and Verify

Execute the new helper from the repository root:

```bash
./scripts/deploy_gallery_pages.sh
```

The script fetches browser assets, compiles the Insight demo, regenerates documentation and runs integrity checks. If Playwright is available, it opens a local server and verifies the PWA works offline.
`scripts/generate_gallery_html.py` runs as part of the helper so `docs/index.html`
always lists the current demos and updates the `docs/gallery.html` redirect.

## 3. Deploy

Upon successful validation the helper publishes the MkDocs site to the `gh-pages` branch using `mkdocs gh-deploy`. The final URL typically resembles:

```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```

The root `index.html` now presents a few quick links. Choose **Visual Demo Gallery** to explore every README or **Launch Demo** for the insight preview.

## 4. Ongoing Maintenance

- Re‑run `./scripts/deploy_gallery_pages.sh` whenever demo assets or docs change.
- Test the site locally with `mkdocs build --strict` before deploying.
- Ensure `pre-commit` passes so the page builds reproducibly.

