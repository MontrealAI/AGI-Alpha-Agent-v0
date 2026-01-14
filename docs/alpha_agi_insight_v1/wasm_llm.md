[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# GPT-2 Small Weights

The offline Insight browser demo bundles the GPT-2 124M checkpoint in
`docs/alpha_agi_insight_v1/assets/wasm_llm/`. Fetch the model assets from the
official Hugging Face mirror using the same tooling as the Insight Browser
build pipeline:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
python scripts/fetch_assets.py
```

The build scripts copy this directory into the distribution bundle so the demo
can operate without network access. Set `FETCH_ASSETS_SKIP_LLM=1` when running
CI or preview builds to avoid downloading the >500 MB checkpoint while keeping
other assets current.
