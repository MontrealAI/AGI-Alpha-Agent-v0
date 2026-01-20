[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# GPT-2 Small Weights

The Insight browser demo can run locally using the GPT-2 124M checkpoint stored in
`alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1/wasm_llm/`. Use
`npm run fetch-assets` or `python scripts/fetch_assets.py` from the repository root to
retrieve the files from the official Hugging Face repository. To override the
default mirror, set `HF_GPT2_BASE_URL`:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
python scripts/fetch_assets.py
```

After downloading, the Insight build pipeline copies the directory to
`dist/wasm_llm/` so the browser demo can operate offline. Set
`FETCH_ASSETS_SKIP_LLM=1` for CI or preview builds to avoid downloading the
>500 MB checkpoint while keeping the remaining assets up to date.
