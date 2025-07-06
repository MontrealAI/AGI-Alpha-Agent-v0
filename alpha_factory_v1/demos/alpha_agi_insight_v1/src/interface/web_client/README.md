[See docs/DISCLAIMER_SNIPPET.md](../../../../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Alpha AGI Insight Web Client

This directory contains a minimal React application built with [Vite](https://vitejs.dev/).
It connects to the API server at `/ws/progress` and logs messages to the console.

## Development

```bash
cd alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_client
npm ci
npm run dev       # open http://localhost:5173
```

## Build

```bash
npm run build  # outputs static files in dist/
```

The production bundle lives under `dist/` and is served automatically by the API
server when present.
