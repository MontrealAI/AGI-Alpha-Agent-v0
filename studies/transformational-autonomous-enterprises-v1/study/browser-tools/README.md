# Optional local browser QA

These dependencies are **only for automated browser checks** of the new Writer #4 graph-revalidation interface. They are not required for the local demonstration, the recorded evidence view, or the scientific evaluation. Use a normal browser to inspect the demonstration manually.

The optional toolchain pins `playwright` **1.62.1** and `@sparticuz/chromium` **153.0.0** in `package.json` and `package-lock.json`. The QA script resolves both from this directory; it does not require `NODE_PATH`, a global Playwright installation, or a browser downloaded by Playwright. Package installation disables lifecycle scripts. Chromium is supplied by its pinned npm package and extracts its executable when QA starts. The demonstrated host is Linux; other platforms have not been qualified.

## Install and start

Use Git, npm, and Node 24.19.0. From the **full companion root**, install the optional packages:

```sh
npm ci --prefix study/browser-tools --ignore-scripts --no-audit --no-fund
```

Start the ordinary local demonstration in the first terminal:

```sh
node study/quickstart.mjs
```

Keep that server running at `http://127.0.0.1:8765/study/interface/`. Initial setup requires public network downloads. If the full local runtime is already installed and its readiness was checked, `node study/server.mjs` starts the same server directly.

In a second terminal at the companion root, choose a **new, not-yet-existing output directory**:

```sh
TAE_QA_OUTPUT=study/qa-runs/my-new-check node study/interface/qa.cjs
```

Use a different output path for each run. The QA script writes reports, screenshots, and an export file into the supplied directory; reusing a path can overwrite that run's files. Do not target the supplied `evidence/interface/` or `evidence/interface/final/` directories, which retain the original observations.

The checks exercise the fixed local journey, including one interruption and one fresh two-mission execution with mock-token settlement. They require the setup-created repositories and local EVM dependencies, not only these optional browser packages. Fresh computation is saved separately under `study/runs/`. No wallet, gas purchase, paid model endpoint, or mainnet action is involved.

This script targets only the new loopback HTTP interface. It does not run the earlier restricted browser objectives or native/site probes. The supplied 11-check browser result remains historical evidence; installing these packages does not constitute a new QA pass.
