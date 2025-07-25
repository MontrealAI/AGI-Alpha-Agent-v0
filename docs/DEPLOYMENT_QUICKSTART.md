[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Deployment Quickstart

This guide summarizes how to publish the **α‑AGI Insight** demo using GitHub Pages.

## Prerequisites

- **Python ≥3.11** with `mkdocs` installed
- **Node.js ≥22**

Verify Node:

```bash
node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
```

## Build and Publish

1. Fetch the browser assets:
   ```bash
   npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets
   ```
   Set `PYODIDE_BASE_URL` or `HF_GPT2_BASE_URL` to mirror locations if the default CDN is blocked.
2. Build the PWA and deploy to GitHub Pages:
   ```bash
   ./scripts/publish_insight_pages.sh
   ```

The script compiles the PWA, runs `mkdocs gh-deploy` and pushes the `site/` directory to `gh-pages`.
Visit:

```
https://<org>.github.io/AGI-Alpha-Agent-v0/alpha_agi_insight_v1/
```

after the workflow finishes.

## Troubleshooting

- Check your Node version if the build fails:
  ```bash
  node alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/build/version_check.js
  ```
- Confirm the service worker includes the correct Workbox hash after publishing:
  ```bash
  python scripts/verify_workbox_hash.py site/alpha_agi_insight_v1
  ```
- Validate that the SRI hash in `index.html` matches `insight.bundle.js`:
  ```bash
  python scripts/check_insight_sri.py site/alpha_agi_insight_v1
  ```
