[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational
goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes
financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# GPT-2 Small Weights

The Insight demo can run fully offline by loading GPT-2 124M weights from
`docs/alpha_agi_insight_v1/assets/wasm_llm/`. Fetch them with either of the
following commands (from the repository root):

```bash
npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets
```

```bash
python scripts/fetch_assets.py
```

Override the default mirror by setting `HF_GPT2_BASE_URL`:

```bash
export HF_GPT2_BASE_URL="https://huggingface.co/openai-community/gpt2/resolve/main"
```

Set `FETCH_ASSETS_SKIP_LLM=1` in CI or previews to avoid downloading the
>500 MB checkpoint while keeping the remaining assets up to date.
