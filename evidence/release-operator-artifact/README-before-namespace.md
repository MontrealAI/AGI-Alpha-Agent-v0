[Project notice](../../docs/DISCLAIMER_SNIPPET.md)

# A bounded operator artifact from the existing package job

The complete package artifact `12780221756` is 2,345,831,234 bytes, exceeding the
connected downloader's 536,870,912-byte limit. That rejected retrieval is not
repeated. The existing package job now uploads a separate, attempt-scoped operator
artifact after its unchanged build, installer checks, checksum verification and
full artifact upload. It uses the same pinned upload action and only six explicit
release paths: the agent wheel, agent lock, installer, checksums and two manifests.

The full release artifact, authoritative package output, publication gates and
installation checks remain unchanged. Previous operator artifacts are excluded
from bulk evidence downloads on retry. No new job, publisher, permission, token,
runtime, source pin, worker or webpage is introduced.

Two added handoff tests check the precise allowlist against included and excluded
fixture files, unchanged bytes, distinct run/attempt identities, successful
verification ordering and the unchanged complete artifact. Existing retry tests
also exclude prior operator outputs. All **76 CI-contract tests pass** after
reconstruction, with Ruff lint and formatting passing. Full workflow YAML equality
proves that the two declared package-job changes are the only semantic changes.

The original workspace disappeared after an earlier 76-test pass. Its uncommitted
source hashes and disk receipts were lost; they are not invented or transferred
to this qualification. The retained tool readback is preserved separately in
`RECOVERY_HISTORY.json`. The exact `8b2bb77c59aaf066f2837f387c7f38d5a5fc1aff`
checkout was restored from GitHub; the editing patch was reconstructed from tool
history, formatted and freshly tested. `recovered-source.patch` reproduces the
current change. This packet's hashes and passing checks describe those newly
qualified bytes.

The fresh isolated tool environment contains repository-pinned Ruff 0.12.5,
pytest 8.4.1 and PyYAML 6.0.2 with recorded tool dependencies. The shared Python
environment is unchanged. The required action updater ran on exact temporary
copies of itself and `ci.yml`, exited zero and left real action pins unchanged.
Its regex matched no version-commented pinned lines, so no action-version or
network freshness is asserted. Local actionlint remains unavailable; no Go or
hook environment was installed, and the hosted actionlint gate remains required.

`contracts.json` records the fresh command, output and exact source identities.
`static-checks.json` records preservation and tool scope. `BEFORE.json` binds the
restored baseline. This is a reviewed packaging correction, not evidence that a
new artifact has already been published or that either canary has executed.
