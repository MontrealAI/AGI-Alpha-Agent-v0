[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# α-AGI Insight v1

This directory hosts the static α‑AGI Insight demo used in the documentation. Build the docs with `mkdocs build` and open `alpha_agi_insight_v1/index.html` from the generated `site/` folder. To preview the files directly from the repository, run:

```bash
python -m http.server --directory docs/alpha_agi_insight_v1 8000
```

and navigate to <http://localhost:8000/>. Direct `file://` access is unsupported due to browser security restrictions.

**Live demo:** <https://montrealai.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/>

The project’s GitHub Pages site displays a landing page with links. Non‑technical users can open <https://montrealai.github.io/AGI-Alpha-Agent-v0/> and choose **Launch Demo** to reach this directory.

For details on publishing the site automatically, see [Quick Deployment](../HOSTING_INSTRUCTIONS.md#quick-deployment).

The charts rely on synthetic data for illustration. Refer to the project disclaimer for important usage information.

Below the interactive charts, the demo includes a dedicated **Meta‑Agentic Tree Search** panel. It visualizes how the search algorithm explores and refines strategies as new nodes appear. See the **Meta-Agentic Tree Search Progress** section for a live view of this exploration.

### Prerequisites

* **Python ≥3.11**
* **Node.js ≥20** (checked via `node build/version_check.js`)
* **MkDocs**

## One-Command Build

Run the helper script to build the Insight progressive web app (PWA) and generate the `site/` directory:

```bash
./scripts/edge_human_knowledge_pages_sprint.sh
```

The script installs Node dependencies, builds the browser bundle and runs `mkdocs build`. When executed in CI, it also publishes the resulting `site/` directory to GitHub Pages.
The bundled site registers a service worker so the demo remains available offline once loaded. The PWA now ships with a fully functional service worker. Ensure both `lib/workbox-sw.js` and `manifest.json` are present in the docs directory—these files enable caching. The service worker fetches `lib/workbox-sw.js` relative to `index.html`, so keep the file under `lib/`. Serve the files with a simple HTTP server (e.g. `python -m http.server`) so the service worker can register; opening `index.html` directly with `file://` will not work.

Preview the generated site locally with:

```bash
python -m http.server --directory site 8000
```

For convenience, run `./scripts/preview_insight_docs.sh` to build the demo and immediately serve it on `http://localhost:8000/`.

The [`📚 Docs` workflow](../../.github/workflows/docs.yml) runs the same script but is triggered manually from the GitHub UI by the repository owner to publish the contents of `site/` to GitHub Pages.

### Testing offline mode

To verify that the PWA works without an internet connection:

1. Run `./scripts/preview_insight_docs.sh`. The script builds the docs, starts a
   local server and automatically launches a headless browser.
   It waits for the service worker to register, disables network access and
   reloads the page. The command exits with an error if the page fails to load
   offline.
2. Alternatively, build the documentation with `./scripts/edge_human_knowledge_pages_sprint.sh`
   and serve the `site/` directory locally:
   `python -m http.server --directory site 8000`.
3. Open <http://localhost:8000/> in a browser.
4. After the page loads, disable your network connection and reload.
   The demo should still display correctly.
5. If the page does not load offline, open your browser's developer console
   and inspect any service worker errors. Confirm `lib/workbox-sw.js` and
   `manifest.json` are served next to `index.html`.
Contributors are encouraged to run this check before publishing changes.
After deployment, verify `lib/workbox-sw.js` matches the hash stored in
`service-worker.js`:

```bash
python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
```

This prevents caching issues caused by missing or corrupted assets.

if WebKit fails to install so the suite can still pass.
