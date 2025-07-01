[See docs/DISCLAIMER_SNIPPET.md](../docs/DISCLAIMER_SNIPPET.md)

# Hosting Instructions

This project uses [MkDocs](https://www.mkdocs.org/) to build the static documentation.
The generated site is hosted at <https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/>.

## Quick Deployment

`deploy_insight_demo.sh` downloads the Insight browser assets, installs the
Node dependencies and then invokes `publish_insight_pages.sh`. The latter runs
`build_insight_docs.sh` to refresh the MkDocs site and pushes the result to the
`gh-pages` branch. When the script completes it prints the GitHub Pages URL.

For an end‑to‑end build **with verification** use `deploy_insight_full.sh`. This
wrapper script runs the environment preflight checks, builds the PWA, verifies
offline functionality and then publishes the docs in one step.

1. Fetch the assets:
   `npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets`
2. Run the build script with `./scripts/publish_insight_pages.sh` (or execute
   `deploy_insight_demo.sh` to perform both steps automatically).
3. Verify the page at `https://<org>.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/`.

## Prerequisites

- **Python 3.11 or 3.12**
- `mkdocs` and `mkdocs-material`
- **Node.js 20+** *(optional, only for building the React dashboard)*
- Run `node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js` to verify Node ≥20 before building
- `unzip` to extract `insight_browser.zip`

Install MkDocs:

```bash
pip install mkdocs mkdocs-material
```

Before building the demo, ensure optional Python packages are available:

```bash
python scripts/check_python_deps.py
python check_env.py --auto-install
```

## Build the Insight Demo

The static browser bundle lives under
`alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1`. Install the
Node dependencies then create the distribution archive:

```bash
cd alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1
npm install
npm run build:dist
```

`npm run build:dist` produces `insight_browser.zip`. Extract the archive and copy
its contents into `docs/alpha_agi_insight_v1` so MkDocs can include the files:

```bash
unzip -o insight_browser.zip -d ../../../docs/alpha_agi_insight_v1
```

Generate `tree.json` from the latest run so the visualization reflects the
current meta-agent state. `scripts/build_insight_docs.sh` automatically
refreshes this file when `lineage/run.jsonl` is present, so the command below is
only needed when running it manually:

```bash
python alpha_factory_v1/demos/alpha_agi_insight_v1/tools/export_tree.py \
  lineage/run.jsonl -o docs/alpha_agi_insight_v1/tree.json
```

The helper script `scripts/build_insight_docs.sh` automates the steps above.
Run it from the repository root to build the bundle, refresh
`docs/alpha_agi_insight_v1` and generate the site.

Whenever demo assets change, rerun `python scripts/build_service_worker.py` to
update `docs/assets/service-worker.js`. Otherwise visitors may see outdated
files due to the service worker cache on GitHub Pages.


## Building the Site

Run the following from the repository root:

```bash
mkdocs build
```

This generates the HTML under `site/`. Verify that the Insight demo was copied
correctly:

```bash
ls site/alpha_agi_insight_v1
```
Ensure `lib/workbox-sw.js` resides under `site/alpha_agi_insight_v1/lib/` because the service worker expects the file relative to `index.html`.

Serve the site locally to test it:

```bash
python -m http.server --directory site 8000
```

Then browse to <http://localhost:8000/alpha_agi_insight_v1/>. Direct `file://`
access is unsupported due to the service worker; use a minimal HTTP server or
GitHub Pages.

The "📚 Docs" workflow
[`docs.yml`](../.github/workflows/docs.yml) automatically runs
`scripts/build_insight_docs.sh`, builds the site and pushes the result to the
`gh-pages` branch.

### Manual Publish

To trigger a one-off deployment outside of CI run:

```bash
./scripts/publish_insight_pages.sh
```

This wrapper script rebuilds the browser bundle, regenerates the MkDocs site and
runs [`scripts/generate_gallery_html.py`](../scripts/generate_gallery_html.py)
so `docs/index.html` includes the latest demos and updates the `docs/gallery.html`
redirect.
It then uses `mkdocs gh-deploy` to push the contents of `site/` to the `gh-pages` branch.
Use it when testing changes locally or publishing from a personal fork.

## Publishing to GitHub Pages

When changes land on `main` or a release is published, `docs.yml` pushes the
`site/` directory to the `gh-pages` branch. GitHub Pages serves the result at
`https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/`.
Opening `https://montrealai.github.io/AGI-Alpha-Agent-v0/` shows a landing page
with quick links. Choose **Visual Demo Gallery** to open the full showcase, or
select **Launch Demo** to jump directly to the insight demo.
The standard [project disclaimer](DISCLAIMER_SNIPPET.md) applies.

## Verifying Deployment

Confirm the workflow is enabled under **Actions** and that
[`docs.yml`](../.github/workflows/docs.yml) specifies
`permissions: contents: write`. Run the "📚 Docs" workflow from the GitHub UI or
push to `main` to trigger it. The initial run creates the `gh-pages` branch.
After it finishes, browse to
<https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/> and
check that the insight demo loads.

Run the integrity check to make sure `lib/workbox-sw.js` matches the hash
embedded in `service-worker.js`:

```bash
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
```

This step catches missing or corrupted assets after deployment.

## Capturing Demo Previews

Use `scripts/capture_demo_preview.py` to generate short recordings for the
documentation. The helper launches a demo inside a virtual display and captures
the screen with `ffmpeg`.

```bash
python scripts/capture_demo_preview.py path/to/demo.sh -o demo.mp4
```

Supply a `.gif` output name to automatically convert the clip after recording.
`--duration` and `--size` adjust the recording length and virtual display size.
