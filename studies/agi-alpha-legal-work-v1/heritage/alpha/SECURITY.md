[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)

# Security Policy

## Reporting a Vulnerability

If you discover a security issue in this project, please contact us at <security@montreal.ai>.
We aim to acknowledge your report within **3 business days** and provide a more detailed
response within **7 days**. We request that you do not publicly disclose the issue
until we have addressed it.

Thank you for helping keep this project safe.

## Third-party Services

This project avoids Chainlink VRF and other subscription-based dependencies. Keep new contributions free of external service requirements.

## Supported release security checks

The current operator release requires a complete hash-locked Python dependency advisory scan and
browser dependency audits, with dated reports retained in its validation archive. See
[release readiness](docs/agent/RELEASE_READINESS.md) and [validation scope](docs/agent/VALIDATION.md).
A successful automated scan is not an independent security audit. The local operator API is intended
for loopback use on a private host; the static Pages workspace has no account or hosted agent backend.

## Historical container security workflow

The preserved [`security.yml`](.github/workflows/security.yml) is a separate manual container
build/scan/signing workflow requiring registry credentials. It is not an operator-release acceptance
gate and does not establish that current release containers are signed, independently audited, or
accompanied by verified SLSA attestations. Its release-attachment step is conditional on a release
event, whereas this workflow currently exposes manual dispatch. Consult the actual published assets
and run evidence; do not infer successful scanning or signing from the presence of a workflow file.
