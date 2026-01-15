[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Insight WASM LLM Assets

The Insight browser demo ships an offline GPT-2 124M checkpoint so text generation can run without
network access. The source assets live under
`alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/wasm_llm/`.

To refresh them, run the demo asset fetcher and (optionally) override the download mirror:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
npm run fetch-assets
```

The build pipeline copies the downloaded files into `dist/wasm_llm/`. Set
`FETCH_ASSETS_SKIP_LLM=1` in CI or preview builds to avoid downloading the large checkpoint while
keeping other assets up to date.
