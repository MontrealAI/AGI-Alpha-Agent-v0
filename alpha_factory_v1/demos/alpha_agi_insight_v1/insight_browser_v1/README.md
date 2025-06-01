### 🔬 Browser-only Insight demo
A zero-backend Pareto explorer lives in
`demos/alpha_agi_insight_v1/insight_browser_v1/`.

## Prerequisites
- **Node.js ≥20** must be installed.

## Build & Run
```bash
npm install
npm run build    # compile to dist/
PINNER_TOKEN=<token> npm start
```
`npm start` serves the `dist/` folder on `http://localhost:3000` by default.
Set `PINNER_TOKEN` to your [Web3.Storage](https://web3.storage/) token so the
Share button can pin snippets to IPFS.

Open `index.html` directly in your browser or pin the folder to IPFS
(`ipfs add -r insight_browser_v1`) and share the CID.

## Toolbar & Controls
- **CSV** – export the current population as `population.csv`.
- **PNG** – download a `frontier.png` screenshot of the chart.
- **Share** – copy an embeddable iframe snippet to the clipboard and, when
  `PINNER_TOKEN` is set, pin it to IPFS.
- **Theme** – toggle between light and dark mode.

Drag a previously exported JSON state onto the drop zone to restore a
simulation.
