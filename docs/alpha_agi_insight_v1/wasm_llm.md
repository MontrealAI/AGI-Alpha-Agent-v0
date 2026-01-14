[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# Insight WASM LLM Assets

The α-AGI Insight browser demo ships an offline GPT‑2 124M checkpoint so the
interface can run without network access. The assets live under
`docs/alpha_agi_insight_v1/assets/wasm_llm/` and are synced into the demo build
output during the asset fetch step.

To refresh the weights from the official Hugging Face mirror, run either of the
following commands from the repository root:

```bash
npm --prefix alpha_factory_v1/demos/alpha_agi_insight_v1/insight_browser_v1 run fetch-assets
```

```bash
python scripts/fetch_assets.py
```

Set `HF_GPT2_BASE_URL` to point at a different mirror, or set
`FETCH_ASSETS_SKIP_LLM=1` when you need to skip the large model download in CI.
