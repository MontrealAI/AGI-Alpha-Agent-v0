[See docs/DISCLAIMER_SNIPPET.md](../../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

### 🔬 Browser-only Insight demo
A zero-backend Pareto explorer lives in
`demos/alpha_agi_insight_v1/insight_browser_v1/`. See the **Quick-Start** section below for a short walkthrough.

## Quick-Start
Open [../../../../insight_browser_quickstart.pdf](../../../../insight_browser_quickstart.pdf)
for a concise overview of the build and launch steps.

## Prerequisites
- **Node.js 22** is required for offline PWA support and by `manual_build.py`
  to generate the service worker.
- Run `nvm use` to activate the version from `.nvmrc` before installing
  dependencies.
- **Python ≥3.11** is required when using `manual_build.py`.
- `package-lock.json` must remain checked in so `npm ci` installs the exact
  versions specified.
- Run `npm ci` before executing any lint or build script.

Verify your Node.js version before running the build script:

```bash
node build/version_check.js
```
The output should be empty for a valid setup. Only run `manual_build.py` when
this requirement is met. The `package.json` also enforces Node.js 22 or newer
via the `engines` field.

## Windows Setup

Download and install [Node.js 22](https://nodejs.org/en/download) and
[Python 3.11](https://www.python.org/downloads/) before running the build
scripts. Open PowerShell in this directory and verify the versions:

```powershell
node --version
python --version
```

Use `./setup.ps1` to install the Node modules when `node_modules` is missing.
Build and launch the demo with:

```powershell
npm run fetch-assets
./setup.ps1
npm run build    # or ./manual_build.ps1 for offline builds
npm start
```

## Environment Setup
Copy `.env.sample` to `.env` then review the variables. When `.env`
is missing the build scripts continue with default empty values:

- `PINNER_TOKEN` – Web3.Storage token used to pin results.
- `OPENAI_API_KEY` – optional OpenAI key for chat prompts. **For security, do not
  embed the key in the built HTML.** Store it in `localStorage` or enter it at
  runtime instead.
- `IPFS_GATEWAY` – base URL of the IPFS gateway used to fetch pinned runs. Set
  `IPFS_GATEWAY=<url>` to override the primary gateway.
- `OTEL_ENDPOINT` – OTLP/HTTP endpoint for anonymous telemetry (leave blank to disable).
- `WEB3_STORAGE_TOKEN` – build script token consumed by `npm run build`.
- Browsers with WebGPU can accelerate the local model using the ONNX runtime.
  Use the GPU toggle in the power panel to switch between WebGPU and WASM.
- The power panel also includes an **Offline/API** selector. Choose
  **Run Offline** to execute the bundled DistilGPT2 model via Pyodide or
  **Run with OpenAI API** when an `OPENAI_API_KEY` is available. The key is
  stored in `localStorage` and the app falls back to offline mode when absent.
- Set `window.DEBUG = true` before loading the page to expose debugging helpers
  like `window.pop` and `window.coldZone`.

Run `npm run fetch-assets` to download the Pyodide runtime and local model
before installing dependencies. Execute this command in a fresh checkout—or
remove the existing `wasm*/` directories—so placeholder files are replaced.
After the download completes, verify each file with
`python ../../../../scripts/fetch_assets.py --verify-only`. The script
retrieves the official Pyodide runtime from the jsDelivr CDN and the smaller
DistilGPT2 checkpoint from Hugging Face by default (~337&nbsp;MiB vs ~523&nbsp;MiB for
GPT‑2 124M). If a custom `PYODIDE_BASE_URL` is unreachable the helper
automatically retries using the official CDN. The deprecated `wasm-gpt2.tar`
archive is no longer used.
Set `FETCH_ASSETS_ATTEMPTS` to control the retry count when downloading assets.
Override `PYODIDE_BASE_URL` or `HF_GPT2_BASE_URL` to change the mirrors. To fetch the
full GPT‑2 124M checkpoint instead of DistilGPT2, set:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
```

If `npm run fetch-assets` fails with a 401 or 404 error, download the checkpoint directly:
```bash
python ../../../../scripts/download_hf_gpt2.py models/gpt2
```

Alternatively, execute `python ../../../../scripts/download_hf_gpt2.py`,
`python ../../../../scripts/download_gpt2_small.py`, or
`python ../../../../scripts/download_openai_gpt2.py` to fetch the full GPT‑2
124M model directly.

If the Pyodide runtime fails to download, run the helper manually:

```bash
python ../../../../scripts/fetch_assets.py
```

The script fetches the official files from `PYODIDE_BASE_URL` and falls back to the
jsDelivr and GitHub mirrors when needed. You can also retrieve the runtime with
`curl` when automation fails:

```bash
curl -L https://cdn.jsdelivr.net/pyodide/v0.28.0/full/pyodide.js -o wasm/pyodide.js
curl -L https://cdn.jsdelivr.net/pyodide/v0.28.0/full/pyodide.asm.wasm -o wasm/pyodide.asm.wasm
```
Verify the downloads with:

```bash
python ../../../../scripts/fetch_assets.py --verify-only
```

See `.env.sample` for the full list of supported variables. Download the file from [GitHub](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/.env.sample).
The compiled `dist/` directory is not version controlled. Run the build script
to create it before launching the demo.

## Build & Run
Run `npm run fetch-assets` **before installing dependencies** to download the
Pyodide runtime and DistilGPT2 weights, then install the Node modules.
`python ../../../../scripts/download_hf_gpt2.py` or
`python ../../../../scripts/download_gpt2_small.py` can also fetch the full
GPT‑2 124M model directly if you prefer,
compile the bundle:
```bash
npm run fetch-assets
./setup.sh        # installs dependencies when node_modules is missing (use `./setup.ps1` on Windows)
npm run build     # or `python manual_build.py` or `./manual_build.ps1` for offline builds
```
Run the tests with:
```bash
./setup.sh && npm test    # on Windows use `./setup.ps1`
```
The build script reads `.env` automatically and injects the values into
`dist/index.html` as `window.PINNER_TOKEN`, `window.IPFS_GATEWAY` and
`window.OTEL_ENDPOINT`. `OPENAI_API_KEY` is **not** embedded by default.
Set it in `localStorage` or provide it at runtime when prompted.
It also copies `dist/sw.js` to `dist/service-worker.js` which `index.html`
registers for offline support.
`npm run build` (or `python manual_build.py`) also replaces the
`__SW_HASH__` placeholder in `index.html` with the SHA-384 digest of
`service-worker.js` so the browser can verify the script before
registration.
After rebuilding the demo, the service worker automatically skips the waiting
phase and reloads the page so users always run the latest version.
The unbuilt `index.html` falls back to `'self'` for the IPFS and telemetry
origins, but running `npm run build` (or `python manual_build.py`) replaces
these defaults with the real values from `.env`.
Place the Pyodide 0.28.0 files in `wasm/` before building. The script copies them
to `dist/wasm` so the demo can run offline. When preparing the environment
offline run:

```bash
npm run fetch-assets
```

This downloads the Pyodide runtime and DistilGPT2 model from the configured
mirrors. Assets land in `wasm/` and `wasm_llm/`.
It also retrieves `lib/bundle.esm.min.js` from the mirror. You may instead run
`python ../../../../scripts/download_hf_gpt2.py` or
`python ../../../../scripts/download_gpt2_small.py` to pull the full GPT‑2 124M
model directly. The build and
`manual_build.py` scripts scan every downloaded asset for the word
`"placeholder"` and abort when any file still contains that marker.
`npm run fetch-assets` also downloads `lib/workbox-sw.js` from
Workbox 6.5.4 so the service worker can operate offline.
Each file is retried up to three times. If a download fails the script exits
with an error suggesting you check connectivity or the `IPFS_GATEWAY`
setting.
Run `npm run fetch-assets` if you encounter this error.
```bash
W3UP_EMAIL=<email> npm start
```
`npm start` serves the `dist/` folder on `http://localhost:3000` by default.
Set `W3UP_EMAIL` to the address registered with
[@web3-storage/w3up-client](https://github.com/storacha/w3up) so exported JSON
results can be pinned.

If `OPENAI_API_KEY` is stored in `localStorage`, the demo uses the OpenAI API for
chat prompts. When no key is present a lightweight DistilGPT2 model under
`wasm_llm/` runs locally.
Use the Offline/API selector in the power panel to switch modes at any time.

Open `index.html` directly or pin the built `dist/` directory to IPFS
(`ipfs add -r dist`) and share the CID.
The URL fragment encodes parameters such as `#/s=42&p=120&g=80`.

See [../../../../insight_browser_quickstart.pdf](../../../../insight_browser_quickstart.pdf) for a short walkthrough.
Running `npm run build` or `python manual_build.py` copies this file to
`dist/insight_browser_quickstart.pdf` so the guide is available alongside
`dist/index.html` when offline.

## Manual Build
Use `manual_build.py` for air‑gapped environments:

1. `cp .env.sample .env` and edit the values if you haven't already, then `chmod 600 .env`.
2. `npm run fetch-assets` to fetch Pyodide and the DistilGPT2 model.
   Alternatively run `python ../../../../scripts/download_gpt2_small.py`,
   `python ../../../../scripts/download_openai_gpt2.py` or
   `python ../../../../scripts/download_hf_gpt2.py` to grab
   the full GPT‑2 124M model directly from the official mirror.
   The build scripts verify these files no longer contain the word `"placeholder"`.
   Failing to replace placeholders will break offline mode.
3. Run `node build/version_check.js` to ensure Node.js **v22** or newer is
   installed. `manual_build.py` exits if this check fails.
4. `python manual_build.py` – or run `./manual_build.ps1` – bundles the app,
   generates `dist/sw.js` and embeds your `.env` settings.
5. `npm start` or open `dist/index.html` directly to run the demo.

The script requires Python ≥3.11. It loads `.env` automatically and injects
`PINNER_TOKEN`, `OPENAI_API_KEY`, `IPFS_GATEWAY` and `OTEL_ENDPOINT` into
`dist/index.html`, mirroring `npm run build`.
If `.env` is absent the script continues with empty defaults rather than aborting.

### Offline Build

Follow these steps when building without internet access:

1. Run `npm run fetch-assets` (or `python ../../../../scripts/download_gpt2_small.py` for the full GPT‑2 124M model, `python ../../../../scripts/download_openai_gpt2.py`).
2. Verify checksums match `build_assets.json` with
   `python ../../../../scripts/fetch_assets.py --verify-only` and ensure no
   files under `wasm/` or `lib/` contain the word "placeholder".
3. `npm ci` to install the locked dependencies.
4. Execute `python manual_build.py` (or `./manual_build.ps1`) to generate the PWA in `dist/`.
5. Launch with `npm start` or pin the directory with `ipfs add -r dist`.

Failing to replace placeholders will break offline mode.

### Offline build checklist

1. Run `npm run fetch-assets`.
   (`python ../../../../scripts/download_gpt2_small.py` for the full GPT‑2 124M model or
   `python ../../../../scripts/download_openai_gpt2.py` also works.)
2. `npm ci` to install dependencies from `package-lock.json`.
3. Confirm no placeholder text remains in `lib/` or `wasm*/`.
4. Execute `python manual_build.py` (or `./manual_build.ps1`) to generate the PWA in `dist/`. Use
   `npm run build` when internet access is available.

5. Run the tests offline:

   ```bash
   PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm test --offline
   ```

   Set `PLAYWRIGHT_BROWSERS_PATH=/path/to/browsers` when using a custom
   directory of Playwright binaries.

Failing to run the fetch script leaves offline mode disabled.

### Offline npm install

Create a cache on a connected machine:

```bash
npm ci --cache /path/to/npm-cache
```

Copy the cache to the target machine then run:

```bash
npm ci --offline --cache /path/to/npm-cache
```

This installs dependencies without network access.


### Fetching Assets Offline

Set `WEB3_STORAGE_TOKEN` before running the helper script:

```bash
WEB3_STORAGE_TOKEN=<token> npm run fetch-assets
```


The script retrieves the WebAssembly runtime and supporting files from the
IPFS mirror first and falls back to the OpenAI URL or configured
gateway, verifying checksums to ensure each asset is intact.

### Offline Build Steps

Requires **Node.js 22** and **Python ≥3.11**.

1. Copy `.env.sample` to `.env` and set the variables.
2. Run `WEB3_STORAGE_TOKEN=<token> npm run fetch-assets` to download the WASM runtime and model files.
3. Execute `python manual_build.py` (or `./manual_build.ps1`) to produce the `dist/` directory.
4. Open `dist/index.html` to verify offline functionality.

Run `node tests/run.mjs --offline` to confirm the build works without network access.

## Distribution
Run `npm run build:dist` to generate `insight_browser.zip` in this directory.
The archive bundles the production build along with the service worker and
assets. it stays under **500&nbsp;MiB** (the hard cap is 750&nbsp;MiB) so the entire demo can be shared easily.
Extract the zip and open `index.html` directly—no additional dependencies are
required. New users can review
[dist/insight_browser_quickstart.pdf](dist/insight_browser_quickstart.pdf) after
extraction for a brief walkthrough.

A dedicated GitHub Actions workflow
[`size-check.yml`](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/.github/workflows/size-check.yml) rebuilds the
archive when triggered manually and fails if `insight_browser.zip` grows beyond
**500&nbsp;MiB**.

## Locale Support
The interface automatically loads French, Spanish or Chinese translations based
on your browser preferences. Set `localStorage.lang` to override the detected
language. When the chosen locale file is missing, a warning appears in the
browser console and the demo falls back to the built‑in English strings.

## Toolbar & Controls
- **CSV** – export the current population as `population.csv`.
- **PNG** – download a `frontier.png` screenshot of the chart.
- **Share** – copy a permalink to the clipboard. When `PINNER_TOKEN` is set,
  exported JSON is pinned to Web3.Storage and the CID appears in a toast.
- **Theme** – toggle between light and dark mode.
- **GPU** – enable or disable WebGPU acceleration. The app sends a
  `{type:'gpu', available:<flag>}` message to the evolver worker which
  forwards the flag to mutation functions.
- **Offline/API** – toggle between the local Pyodide model and the
  OpenAI API. When the key is missing the demo automatically reverts to
  offline mode.

  Set `localStorage.setItem('USE_GPU','1')` to force the GPU backend when
  WebGPU is available.

Drag a previously exported JSON state onto the drop zone to restore a
simulation.

## Darwin-Archive
Every completed run is stored locally using IndexedDB. When storage access is
unavailable, the archive falls back to an in-memory store and data is lost on
refresh. The **Evolution** panel
lists archived runs with their score and novelty. Click **Re-spawn** next to a
row to restart the simulation using that seed.
The method `selectParents(count, beta?, gamma?, rand?)` returns weighted
samples from the archive. Pass a seeded `rand` function to ensure deterministic
results in tests or simulations.

## Arena & Meme Cloud
The **Arena panel** allows quick debates between roles on any candidate in the
frontier. Results appear ranked within the panel. The **Meme Cloud** below the
archive table visualizes common strategy transitions across runs.

## Running a Simulation
Use the **Simulator** panel to launch a full run. Adjust the seed list, population
size and number of generations, then press **Start**. When `PINNER_TOKEN` is set,
the resulting `replay.json` is pinned to Web3.Storage and the CID appears once
the run finishes. Keep this CID handy to share or reload the simulation later.

## Load via CID
Append `#/cid=&lt;CID&gt;` to the URL (or use the **Share** permalink) to replay a
previous run. The simulator fetches the JSON from IPFS and populates the chart.

## Privacy
Anonymous telemetry is optional. On first use a random ID is generated and
hashed with SHA-256 using the static salt `"insight"`. Only this salted hash and
basic usage metrics are sent to the OTLP endpoint. Clearing browser storage
resets the identifier.

Use the **Analytics** panel to enable or disable telemetry at any time.

See **Environment Setup** above for the list of supported variables.

## Safari/iOS Support
Pyodide is disabled on Safari and iOS devices because the runtime fails to load
reliably. The demo automatically falls back to the JavaScript engine instead of
executing Python code in the browser. Expect noticeably slower performance for
LLM tasks and the absence of features that rely on the Python bridge, such as
the local DistilGPT2 critic.

## Running Browser Tests

The demo includes a small Playwright and Pytest suite. **Node.js 22** is
required. After fetching the WebAssembly assets run the tests with Playwright in
offline mode:

```bash
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm test --offline
```

This command builds the bundle automatically before running the tests. It
launches Playwright to exercise `dist/index.html` and then runs the Python
checks. `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` prevents Playwright from fetching
browsers. Optionally set `PLAYWRIGHT_BROWSERS_PATH=/path/to/browsers` when using
pre‑downloaded binaries.

The Jest test `locale_parity.test.js` verifies that all translation files share
the same set of keys.

## Development

- Run `pre-commit run --all-files` to format and lint the code.
- `npm test` builds the bundle then launches Playwright and Python tests.
- See [AGENTS.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/AGENTS.md) for full contributor guidelines.

## License

The Insight browser demo and its translation files are provided under the
[Apache 2.0](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/LICENSE) license.
