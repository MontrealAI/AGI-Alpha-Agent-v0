[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# DistilGPT2 Weights (Default)

This directory stores the DistilGPT2 checkpoint used for offline inference.
The smaller default reduces the download from ~523&nbsp;MiB to ~337&nbsp;MiB
compared to GPT‑2 124M. Run `npm run fetch-assets` or
`python ../../../../scripts/fetch_assets.py` to download the files from the
official Hugging Face repository. Set `HF_GPT2_BASE_URL` to override the
default mirror, for example to fetch the full GPT‑2 124M checkpoint:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
npm run fetch-assets
```

After downloading, the build script copies this directory to `dist/wasm_llm/` so
the browser demo can operate without an internet connection. Set
`FETCH_ASSETS_SKIP_LLM=1` when running CI or preview builds to avoid downloading
the >500 MB checkpoint while keeping other assets up to date.
