[See docs/DISCLAIMER_SNIPPET.md](../../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Bus TLS Setup

The Insight demo uses a gRPC message bus for communication between agents. When `AGI_INSIGHT_BUS_CERT` and `AGI_INSIGHT_BUS_KEY` are provided the bus requires TLS and authenticates requests with `AGI_INSIGHT_BUS_TOKEN`.

## Generating a Self-Signed Certificate

Use `openssl` to create a private key and certificate valid for one year. Run
`infrastructure/gen_bus_certs.sh` to execute these commands automatically and
print the environment variables, or run them manually:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/bus.key \
  -out certs/bus.crt \
  -days 365 \
  -subj "/CN=localhost"
```

Set the environment variables to the generated paths:

```
AGI_INSIGHT_BUS_CERT=/path/to/certs/bus.crt
AGI_INSIGHT_BUS_KEY=/path/to/certs/bus.key
AGI_INSIGHT_BUS_TOKEN=change_this_token
```

Change `AGI_INSIGHT_BUS_TOKEN` to a unique secret before starting the
orchestrator. When TLS is enabled the application exits with a
``ValueError`` if this variable is empty or still set to the default
``change_this_token``.

### Windows (PowerShell)

Install the [OpenSSL Windows binaries](https://slproweb.com/products/Win32OpenSSL.html) and run the equivalent commands:

```powershell
New-Item -ItemType Directory -Force -Path certs
openssl req -x509 -newkey rsa:4096 -nodes `
  -keyout certs/bus.key `
  -out certs/bus.crt `
  -days 365 `
  -subj "/CN=localhost"
```

## Docker and Docker Compose

Place `bus.crt` and `bus.key` under `./certs` next to `docker-compose.yml` and mount the directory:

```yaml
services:
  orchestrator:
    volumes:
      - ./certs:/certs:ro
```

Inside the container reference the mounted files:

```
AGI_INSIGHT_BUS_CERT=/certs/bus.crt
AGI_INSIGHT_BUS_KEY=/certs/bus.key
AGI_INSIGHT_BUS_TOKEN=<token>
```

For a single container run use:

```bash
docker run -v $(pwd)/certs:/certs:ro \
  -e AGI_INSIGHT_BUS_CERT=/certs/bus.crt \
  -e AGI_INSIGHT_BUS_KEY=/certs/bus.key \
  -e AGI_INSIGHT_BUS_TOKEN=<token> \
  alpha-demo
```
