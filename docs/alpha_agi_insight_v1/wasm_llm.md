[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Insight v1 WASM LLM Assets

## What `wasm_llm` is for

The Insight v1 browser demo can run a lightweight local language model when no API key is
available. The `wasm_llm/` assets store the GPT-2 124M checkpoint used by the demo so that
the offline chat experience works without network access.

## Where the assets live

- Source assets for the demo live in
  `alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/wasm_llm/`.
- The documentation mirror for the demo ships a copy under
  `docs/alpha_agi_insight_v1/assets/wasm_llm/` for the static site bundle.
- Build scripts copy these files into `dist/wasm_llm/` so the deployed demo can load
  them locally.

## Updating or rebuilding the assets

From `alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/`, run:

```bash
npm run fetch-assets
```

This downloads the GPT-2 checkpoint from the configured mirror. You can override the mirror
URL with `HF_GPT2_BASE_URL`. After downloads complete, the build pipeline copies the assets
into `dist/wasm_llm/` so the browser demo can run offline. When CI or preview builds should
avoid pulling the >500 MB weights, set `FETCH_ASSETS_SKIP_LLM=1`.

## Licensing and disclaimer notes

The GPT-2 model weights are redistributed from upstream sources (for example the OpenAI
community mirror). Review the upstream license terms before distributing the assets. The
project-wide disclaimer above applies to this demo as well.
