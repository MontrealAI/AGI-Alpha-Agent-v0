[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Sandbox Resource Limits

Generated code snippets run in a restricted subprocess. The following environment variables control the CPU time and memory available to the sandbox:

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_CPU_SEC` | `2` | CPU time limit in seconds. |
| `SANDBOX_MEM_MB` | `256` | Maximum memory in megabytes. |

When unset, the defaults above are applied.
