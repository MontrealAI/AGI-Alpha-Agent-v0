[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Insight WASM LLM Assets

The Insight Browser demo can run fully offline when the GPT-2 124M checkpoint is
available locally. The assets live under
`alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/wasm_llm` and are
copied into the published demo during the build.

## Fetch the assets

Use the helper script to download the files from the official Hugging Face
mirror (or set `HF_GPT2_BASE_URL` to override the mirror URL):

```bash
python scripts/fetch_assets.py
```

Set `FETCH_ASSETS_SKIP_LLM=1` in CI or preview builds to avoid downloading the
large checkpoint while still updating the other demo assets.
