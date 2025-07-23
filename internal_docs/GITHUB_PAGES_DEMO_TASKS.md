[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# GitHub Pages Demo Tasks Sprint

This short sprint guides Codex through publishing the entire **Alpha‑Factory v1** demo gallery to GitHub Pages. The goal is a polished subdirectory that showcases every demo in real time and remains effortless for non‑technical users to deploy.

## 1. Environment Checks
1. Install **Python 3.11+** and **Node.js 22+**.
2. Run the preflight script:
   ```bash
   python alpha_factory_v1/scripts/preflight.py
   ```
3. Confirm the Node version:
   ```bash
   node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
   ```
4. Install optional packages so the verification tools work:
   ```bash
   python scripts/check_python_deps.py
   python check_env.py --auto-install
   ```

## 2. Build the Demo Gallery
Execute the helper from the repository root:
```bash
./scripts/deploy_gallery_pages.sh
```
This command fetches browser assets, compiles the α‑AGI Insight interface, runs
integrity checks and builds the MkDocs site under `site/`. It also runs
`scripts/generate_gallery_html.py` to refresh `docs/index.html` and
update the `docs/gallery.html` redirect, and
`scripts/build_service_worker.py` to update the precache list.



## 3. Preview Locally
Start a quick HTTP server to examine the result:
```bash
python -m http.server --directory site 8000
```
Open <http://localhost:8000/> in a browser. Ensure the landing page shows quick links, including **Launch Demo** for `alpha_agi_insight_v1/` and **Visual Demo Gallery** with preview images or GIFs.

## 4. Deploy to GitHub Pages
When satisfied, publish the site:
```bash
mkdocs gh-deploy --force
```
Alternatively rerun `./scripts/deploy_gallery_pages.sh` which performs the same step automatically. The final URL typically resembles:
```
https://<org>.github.io/AGI-Alpha-Agent-v0/
```
Verify the service worker caches assets for offline use and that the page includes the project disclaimer.

## 5. Maintenance Tips
- Re‑run the helper whenever demo docs or assets change.
- If adding new demos manually, run `python scripts/build_service_worker.py` to
  refresh `docs/assets/service-worker.js`.
- Run `python scripts/generate_build_manifest.py` whenever the asset checksums in
  `scripts/fetch_assets.py` change so `build_assets.json` stays in sync. You can
  also pass `--update-manifest` to `scripts/fetch_assets.py` to run this step
  automatically after verifying downloads.
- Test with `mkdocs build --strict` before deploying.
- Keep `pre-commit` hooks green so the gallery builds reproducibly.

## 6. Edge-of-Human-Knowledge Sprint
Run the wrapper to rebuild and publish the entire site in one step:

```bash
./scripts/edge_human_knowledge_pages_sprint.sh
python scripts/edge_human_knowledge_pages_sprint.py
```

Prerequisites: **Python 3.11+**, **Node.js 22+** and `mkdocs`. This script mirrors the [Docs workflow](../.github/workflows/docs.yml) which the repository owner triggers manually to deploy the site.

When running inside CI, set `CI_SKIP_ENV_CHECK=1` to avoid repeating the environment installation step:

```bash
CI_SKIP_ENV_CHECK=1 ./scripts/edge_human_knowledge_pages_sprint.sh
```
