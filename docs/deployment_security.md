[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# Secure Deployment

This guide explains how to protect Alpha-Factory in production.

- **Token Address:** `0xa61a3b3a130a9c20768eebf97e21515a6046a1fa`
- **Token Decimals:** `18` (ERC‑20 standard; 1 token = 1e18 base units)

## TLS configuration

Use TLS to encrypt both the REST API and the gRPC bus. Run `infrastructure/gen_bus_certs.sh` to generate a self-signed certificate or supply your own:

```bash
./infrastructure/gen_bus_certs.sh
# prints AGI_INSIGHT_BUS_CERT, AGI_INSIGHT_BUS_KEY
```

Set these environment variables when starting the orchestrator. For the REST API you may terminate HTTPS with a reverse proxy like Nginx or pass `--ssl-keyfile` and `--ssl-certfile` to `uvicorn`.

## API tokens

Set `API_TOKEN` to a strong secret so clients must send
`Authorization: Bearer <token>` when calling the REST endpoints.
Combine this with `API_RATE_LIMIT` to limit requests per minute.

## Loading secrets from Vault

Alpha‑Factory can pull credentials from HashiCorp Vault by setting
`AGI_INSIGHT_SECRET_BACKEND=vault` and providing `VAULT_ADDR` and
`VAULT_TOKEN`. Secrets like `OPENAI_API_KEY` are read from
`secret/data/alpha-factory` by default.

## Mounting secrets into containers

Do not commit private keys or tokens. Instead, mount them at runtime:

### Docker Compose

```yaml
services:
  orchestrator:
    volumes:
      - ./certs:/certs:ro
    environment:
      - AGI_INSIGHT_BUS_CERT=/certs/bus.crt
      - AGI_INSIGHT_BUS_KEY=/certs/bus.key
      - API_TOKEN_FILE=/run/secrets/api_token
    secrets:
      - api_token
secrets:
  api_token:
    file: ./secrets/api_token
```

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alpha-factory
type: Opaque
stringData:
  api_token: "strongtoken"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alpha-factory
spec:
  template:
    spec:
      containers:
        - name: orchestrator
          image: alpha-demo
          volumeMounts:
            - name: certs
              mountPath: /certs
              readOnly: true
          env:
            - name: AGI_INSIGHT_BUS_CERT
              value: /certs/bus.crt
            - name: AGI_INSIGHT_BUS_KEY
              value: /certs/bus.key
            - name: API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: alpha-factory
                  key: api_token
      volumes:
        - name: certs
          secret:
            secretName: alpha-factory
            items:
              - key: bus.crt
                path: bus.crt
              - key: bus.key
                path: bus.key
```

Store keys in a secure secret manager and never check them into git.
