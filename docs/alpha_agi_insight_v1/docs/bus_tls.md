[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational
goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes
financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Bus TLS Setup

The Insight demo uses a gRPC message bus for communication between agents. When `AGI_INSIGHT_BUS_CERT` and
`AGI_INSIGHT_BUS_KEY` are provided the bus requires TLS and authenticates requests with `AGI_INSIGHT_BUS_TOKEN`.

## Generating a Self-Signed Certificate

Use `openssl` to create a private key and certificate valid for one year. Run `infrastructure/gen_bus_certs.sh` to
execute these commands automatically and print the environment variables, or run them manually:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/bus.key \
  -out certs/bus.crt \
  -days 365 \
  -subj "/CN=localhost"
```

## Environment Variables

Set the following environment variables when launching the orchestrator:

```bash
export AGI_INSIGHT_BUS_CERT="$(pwd)/certs/bus.crt"
export AGI_INSIGHT_BUS_KEY="$(pwd)/certs/bus.key"
export AGI_INSIGHT_BUS_TOKEN="replace-me"
```

## Verifying the Connection

Once the orchestrator is running, ensure the agents can connect. The agents log a successful TLS handshake on startup.
