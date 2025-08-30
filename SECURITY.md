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

## CI security workflow

The GitHub Actions workflow [`security.yml`](.github/workflows/security.yml) builds and signs the container image. It generates CycloneDX SBOM files for the Python and Node packages, scans the final image with Trivy and fails if any high or critical vulnerabilities are found. After a successful scan the image is signed with `cosign` and an SLSA provenance file is attached to the GitHub Release along with the SBOMs.
