# Version 1.10.1 — Operator reliability and recovery

This patch addresses failure paths found while auditing the published 1.10.0 release. The supported
profile remains a private, single-operator service and a public browser decision workspace.

## Corrections

- Remove a legacy plugin signature bypass: registry membership can no longer accept a wheel whose
  Ed25519 verification fails. The loader and verifier CLI now share strict base64/raw-key/full-wheel
  verification. Real signing, tampering and CLI tests replace formerly skipped OpenSSL recipes.

- Inference enforces a total request deadline, including slow or trickling response bodies. Timed-out
  connections close; missions retain the failure and require explicit recovery.
- A retired worker can record a failure only against its own last mission revision. It cannot mark a
  replacement worker failed after lease expiry and recovery.
- Non-ASCII authorization values receive the normal 401 denial instead of causing a server error.
- Backup creation enforces the same 256 MiB uncompressed limit as restore, removes only its own failed
  partial archive, and flushes the completed archive before reporting its checksum.
- Contributor setup uses compatible pinned hook dependencies, installs the current package after
  legacy environment checks, and is exercised in a fresh environment by release acceptance.
- Source-checkout version reporting matches the package and catalog, with a release consistency test.
- Current installation, monitoring, recovery, compatibility and validation documentation accompanies
  the patch. Version labels and offline caches identify the matching release.

## Compatibility

No mission journal, identity, configuration or receipt migration is required. Backups preserve the
recorded pause state; pause before creating an upgrade checkpoint and resume deliberately after restore.
Use a new environment and restored home as described in the [operator guide](OPERATIONS.md).

The eleven Decision Studio cases retain calculation version **1.10.0**. Existing v2 dossiers replay
unchanged, and the archived 1.9.0 v1 policy remains available. The original manuscript and all original
source paths remain preserved.

## Verification

New runtime regressions exercise two concurrent workers around lease expiry, late results and late
failures, a real HTTP provider that stalls or sends continuing fragments, malformed authorization,
oversized backup refusal and interrupted archive writes. Successful provider responses and existing
recovery checkpoints are also checked. The ordinary release gates remain required: Python 3.11–3.13,
full regression and coverage, strict types, real model and Docker execution, all browser experiences,
strict documentation builds, public-site acceptance and release-asset checksum verification.

## Breaking changes

There are no schema changes. Correct existing raw Ed25519 signatures remain valid; invalid allowlisted
signatures and modified wheels now fail. The contributor signing instructions describe the exact format. The configured inference timeout now limits total request time rather
than only network inactivity. Backup rejects state that the supported restore command could not accept.
These failures are explicit; neither automatically retries or changes existing operator files.

[Project notice](../DISCLAIMER_SNIPPET.md)
