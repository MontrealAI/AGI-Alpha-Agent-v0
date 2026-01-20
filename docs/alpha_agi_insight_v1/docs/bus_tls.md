[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)

# Insight Demo Bus TLS

This page documents the TLS settings for the Insight demo message bus. The
bus configuration is shared with the backend orchestrator and is controlled by
environment variables.

## Environment variables

- `BUS_TLS_CA_CERT` — Path to the certificate authority bundle.
- `BUS_TLS_CERT` — Client certificate path used by the orchestrator.
- `BUS_TLS_KEY` — Private key path for the client certificate.
- `BUS_TLS_EXPECTED_SUBJECT` — Optional subject/issuer validation.

## Notes

- The TLS settings are consumed by the gRPC bus implementation in
  `alpha_factory_v1/backend/bus/grpc_bus.py`.
- Set the paths in your `.env` file before running the orchestrator or the
  Insight demo quickstart.
