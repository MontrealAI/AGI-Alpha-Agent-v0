[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.


# 🏭 Production Deployment Guide — Alpha‑AGI Business v1

This guide summarises the minimal steps required to run the **Alpha‑AGI Business v1** demo in a production‑like
  environment. The service works fully offline but upgrades automatically when `OPENAI_API_KEY` is present.

1. **Prepare the configuration**
   - Run `python scripts/setup_config.py` to create `config.env` if missing and edit as needed.
   - Set `OPENAI_API_KEY` to enable cloud models or leave empty to use the bundled local fallbacks.
   - Optionally enable the Google ADK gateway by setting `ALPHA_FACTORY_ENABLE_ADK=true`.
   - Set `MCP_ENDPOINT` to push logs to a Model Context Protocol server (optional).
   - Set `MCP_TIMEOUT_SEC` to adjust the timeout for MCP requests (default: 30 seconds).
   - `API_TOKEN` defaults to `"demo-token"` *(for demonstrations only)*; always set a strong secret before deploying.
   - For API protection set either `AUTH_BEARER_TOKEN` or `JWT_PUBLIC_KEY`/`JWT_ISSUER`.
   - Validate that all Python packages are available. From the project root run:
     ```bash
     AUTO_INSTALL_MISSING=1 python check_env.py --auto-install
     ```
     Provide `WHEELHOUSE=/path/to/wheels` for air‑gapped setups. **Running this
      command is mandatory before executing the demos or running the test suite.**
      The `openai-agents` and `google-adk` packages are optional and are only
      required when using the OpenAI Agents runtime or the Google ADK gateway.
   - Build wheels for these optional packages when preparing an offline
      deployment:
      ```bash
      pip wheel openai-agents google-adk -w /path/to/wheels
      ```
      Provide this directory via `WHEELHOUSE` during installation on the
      production host.
Run `pre-commit run --all-files` after the dependencies finish installing.

2. **Launch the service**
   - **Docker** (recommended for consistent environments):
     ```bash
     ./run_business_v1_demo.sh [--pull] [--gpu]
     ```
   - **Native Python**:
     ```bash
     pip install -r ../../requirements.txt
     python run_business_v1_local.py --bridge
     ```

3. **Run in Colab**
   - Open [`colab_alpha_agi_business_v1_demo.ipynb`](colab_alpha_agi_business_v1_demo.ipynb).
   - Run the setup cell; dependencies are installed automatically.
   - The notebook exposes a Gradio dashboard and OpenAI Agents SDK bridge.

4. **Access the interface**
   - REST/Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Gradio dashboard: [http://localhost:7860](http://localhost:7860)
   - Prometheus metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)

### Verifying the ADK Gateway
When `ALPHA_FACTORY_ENABLE_ADK=true` and the optional `google-adk` package are
installed, the service spawns an ADK gateway.  Look for a log message like:

```
ADK gateway listening on http://0.0.0.0:${ALPHA_FACTORY_ADK_PORT}  (A2A protocol)
```

Confirm connectivity with:

```bash
curl http://localhost:${ALPHA_FACTORY_ADK_PORT}/docs
# or
curl http://localhost:${ALPHA_FACTORY_ADK_PORT}/healthz
```

5. **Shutting down**
   - Docker: `./run_business_v1_demo.sh --stop`
   - Native Python: press `Ctrl+C`; the orchestrator shuts down gracefully.

For advanced options see [`README.md`](README.md) in the same directory.

---

## Further Resources

- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)
- [Google ADK reference](https://google.github.io/adk-docs/)
- [Agent-to-Agent protocol](https://github.com/google/A2A)
