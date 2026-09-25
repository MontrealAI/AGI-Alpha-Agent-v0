[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# GPT‑2 Small CLI Demo

![preview](../gpt2_small_cli/assets/preview.svg){.demo-preview}
<!-- CURRENT-DEMO:START -->
## Current runnable path — 1.5.0

**Mode:** Local model. Generates text with the actual GPT-2 124M model.

**Prerequisites:** torch, transformers and roughly 550 MB model storage; first download requires network. Use --model-path PATH --offline with cached weights.

From the repository root after [installation](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/README.md#start-locally):

```bash
python -m alpha_factory_v1.demos run gpt2_small_cli
```

**Expected result:** Generated text after the model has loaded.

**Scope:** CPU latency varies; this is a completion model, not an instruction-following assistant.

The [catalog](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/README.md) explains installation, stopping, backups and recovery.
Browser charts for legacy demos are labeled sample replays. Original research
narratives and advanced scripts below are preserved; they do not expand the tested
scope stated here.
<!-- CURRENT-DEMO:END -->

This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.



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
