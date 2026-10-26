[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# GPT‑2 Small Weights

This directory stores the GPT‑2 124M checkpoint used for offline inference. Run
`npm run fetch-assets` or `python ../../../../scripts/fetch_assets.py` to
download the files from the official Hugging Face repository. Set
`HF_GPT2_BASE_URL` to override the default mirror:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
npm run fetch-assets
```

After downloading, the build script copies this directory to `dist/wasm_llm/` so
the browser demo can operate without an internet connection. Set
`FETCH_ASSETS_SKIP_LLM=1` when running CI or preview builds to avoid downloading
the >500 MB checkpoint while keeping other assets up to date.
CI sets the `CI=1` environment variable, so `scripts/fetch_assets.py` will skip
the GPT‑2 checkpoint by default unless you set `FETCH_ASSETS_INCLUDE_LLM=1`.
