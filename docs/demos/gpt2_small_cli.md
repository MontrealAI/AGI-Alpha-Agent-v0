[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# GPT‑2 Small CLI Demo

![preview](../gpt2_small_cli/assets/preview.svg){.demo-preview}
# GPT‑2 Small CLI Demo

This minimal example downloads the official GPT‑2 124M checkpoint using
`scripts/download_gpt2_small.py`, which first tries the Hugging Face mirror and
falls back to the OpenAI archive if necessary. Files land under `models/gpt2`.
`scripts/download_openai_gpt2.py` remains available as a direct fallback. The weights are
converted to the Hugging Face format via `scripts/convert_openai_gpt2.py` on
first run. If PyTorch is unavailable, the demo falls back to the hosted `gpt2`
model from the `transformers` hub.

```bash
python -m alpha_factory_v1.demos.gpt2_small_cli --prompt "The future of AI" --max-length 50
```

[View README on GitHub](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/gpt2_small_cli/README.md)
