[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Deployment Quickstart

This guide summarizes how to publish the **α‑AGI Insight** demo using GitHub Pages.

- **Token Address:** `0xa61a3b3a130a9c20768eebf97e21515a6046a1fa`
- **Token Decimals:** `18` (ERC‑20 standard; 1 token = 1e18 base units)

## ERC‑20 Approvals for Staking and Escrow

The `StakeManager` contract pulls `$AGIALPHA` via `transferFrom`. Before staking
or locking job funds, approve the contract to move tokens on your behalf. The
token uses 18 decimals, so `1e18` equals one token.

```bash
# Approve 100 AGIALPHA for staking
cast send 0xa61a3b3a130a9c20768eebf97e21515a6046a1fa \
  "approve(address,uint256)" $STAKEMANAGER 100e18

# Approve 50 AGIALPHA for job escrow
cast send 0xa61a3b3a130a9c20768eebf97e21515a6046a1fa \
  "approve(address,uint256)" $STAKEMANAGER 50e18
```

Replace `$STAKEMANAGER` with the deployed contract address.

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
