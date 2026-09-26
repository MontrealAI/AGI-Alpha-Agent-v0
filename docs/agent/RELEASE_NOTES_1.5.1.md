# $AGIALPHA Agent 1.5.1 — release hardening

This patch addresses concrete gaps found while reviewing the Ascension release for dependable
operation. All original demos, flywheels, the white paper and earlier releases remain preserved.

- Upgrade supported operator and CPU demo locks to `cryptography==50.0.1`, addressing the upstream
  certificate-verification and PKCS#7 advisories affecting the previous pin. The runtime uses Ed25519,
  not these certificate/PKCS#7 interfaces; its signatures, exports and recovery are revalidated.
- Require a dated Python advisory scan covering every exact operator package. Advisories, missing
  or skipped packages and scanner failures block release packaging. Existing browser audits remain.
- Verify current main immediately before Pages deployment, before release mutation, and again after
  uploading and re-downloading assets. Superseded runs cannot intentionally publish an older candidate.
- Bind CI Health to the intended commit; reject stale API results and prevent pending workflows or
  unsuccessful reruns from being reported as passing when their waiting period expires.
- Correct branch-protection context names to the actual GitHub check runs and document the remaining
  administrator setup. Release gating does not imply main is protected from direct pushes.
- Refresh current installation/container/browser instructions and add a release-readiness guide
  stating supported operation, evidence, upgrade/recovery and remaining qualification boundaries.

The release requires the existing full runtime, inference, sandbox, EVM, regression, native demo,
browser, mobile, offline and public Pages acceptance gates, plus new publication/watchdog/advisory
regression cases. Inspect the manifest and validation archive for exact results and commit.

For upgrades, pause, verify and back up first; install into a new environment and restore into a new
private home. No journal migration is required. Keep the old environment and pre-upgrade backup until
your representative missions pass. Never overwrite the old identity or published release assets.

Browser economics/governance remain labeled simulations. This patch does not claim independently
audited security, mainnet operation, broad browser certification, or proof of the paper’s AGI claims.

Upstream advisories: [PKCS#7](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5),
[DNS constraints](https://github.com/pyca/cryptography/security/advisories/GHSA-m2h6-j472-rp4c),
[chain construction](https://github.com/pyca/cryptography/security/advisories/GHSA-jwv3-5hgf-82ww).
