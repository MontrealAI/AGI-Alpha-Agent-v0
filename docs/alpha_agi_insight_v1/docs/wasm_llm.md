# WASM LLM assets

The Insight Browser demo can optionally load a lightweight LLM bundle from the `wasm_llm/`
asset directory to enable fully offline inference. These files are intentionally large, so
CI and documentation builds skip downloading them by default.

## How to enable

1. Download the GPT-2 weights and tokenizer files with the asset helper:
   ```bash
   FETCH_ASSETS_SKIP_LLM=0 python scripts/fetch_assets.py
   ```
2. Rebuild the Insight browser bundle:
   ```bash
   cd alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1
   npm run build
   ```

## Skipping downloads

Set `FETCH_ASSETS_SKIP_LLM=1` to avoid downloading or validating the LLM weights when
building the demo or docs. This keeps disk usage low while preserving the rest of the
offline Insight experience.
