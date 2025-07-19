[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# React Web Client

This directory contains a small React interface built with [Vite](https://vitejs.dev/) and TypeScript. It fetches disruption forecast results from the API and renders a Plotly chart.

## Setup

This project requires **Node.js ≥20**. The Vite build depends on
`@vitejs/plugin-vue` 6 to support Vite 7.

```bash
cd src/interface/web_client
nvm use                # optional, selects the version from `.nvmrc`
npm ci
npm run dev        # start the development server
npm run build      # build production assets in `dist/`
```

The build step uses Workbox to generate `service-worker.js` and precache the
site's assets so the demo can load offline.

`VITE_API_BASE_URL` defaults to `/api`. Override it and `VITE_API_TOKEN` to embed
the API bearer token at build time:

```bash
# prepend '/api' to all requests and embed a token
VITE_API_BASE_URL=/api VITE_API_TOKEN=test-token npm run build
```

The app expects the FastAPI server on `http://localhost:8000` by default. After
running `npm run build`, open `dist/index.html`, run `npm run preview` or copy the
`dist/` folder into your container image.

When building the Docker image from the project root, ensure `npm --prefix alpha_factory_v1/core/interface/web_client run build` completes so that `alpha_factory_v1/core/interface/web_client/dist/` exists. The `infrastructure/Dockerfile` copies this directory automatically.

A basic smoke test simply runs `npm test`, which exits successfully if the project dependencies are installed.

## Usage with Docker Compose

Set the variable when launching containers:

```yaml
services:
  web:
    environment:
      VITE_API_BASE_URL: /api
```

## Offline Setup

Follow these steps to use the web client without internet access:

- On a machine with network access, build the npm cache and export it:

```bash
cd src/interface/web_client
npm ci
tar -cf npm-cache.tar ~/.npm
```

- Copy `npm-cache.tar` to the offline host and import the cache:

```bash
tar -xf npm-cache.tar -C ~/
```

- Run installation in offline mode:

```bash
npm ci --offline
```

This installs packages from the local cache without contacting the registry.
