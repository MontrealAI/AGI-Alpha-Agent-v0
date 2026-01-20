[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# Insight WASM LLM Assets

The Insight demo ships optional GPT-2 weights for offline inference in the
browser. These assets are downloaded by `scripts/fetch_assets.py` and stored
under the `wasm_llm/` directory in the Insight browser build output.

## Assets

- `pytorch_model.bin`
- `vocab.json`
- `merges.txt`
- `config.json`

## Download controls

- Set `FETCH_ASSETS_SKIP_LLM=1` to skip the GPT-2 downloads.
- Override the base URL with `HF_GPT2_BASE_URL` if you use an internal mirror.
