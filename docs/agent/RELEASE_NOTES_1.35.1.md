[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.35.1 — Cancellable public-document reads

The native Computer Use reader now stops blocked DNS lookups and slow streamed responses within a
supervised read deadline. Previously, the HTTP inactivity timeout did not bound the total response time,
and the session's STOP/deadline checks waited for the complete read to return.

Each approved public-document request runs in a disposable child process. The parent checks the current
session between bounded waits, applies one eight-second wall-clock limit to DNS and HTTP together, and
kills and reaps the reader on cancellation or timeout. The child receives only the exact URL, method and
remaining byte allowance through standard input. It inherits no provider credential or proxy environment.

Exact approved URLs, public-IP validation, pinned destination IPs, original-host TLS verification,
GET/HEAD-only access, redirect refusal and byte limits remain enforced. An interrupted read conservatively
reserves its remaining per-read allowance because the exact bytes received before termination are unknown.
The reader requests identity encoding, refuses compressed responses before consuming their bodies, and
uses raw-byte iteration so decompression cannot allocate an oversized body ahead of the byte limit.
STOP and deadline exceptions reach the native session; they cannot be converted into an ordinary denied
page and followed by more work. Existing uncertain action reservations and cleanup receipts remain intact.

Fresh permits bind both the browser worker and public-reader source bytes in their worker commitment.
Prepare a new permit after upgrading. The existing handoff, return and historical archive wire formats
are unchanged; earlier signed receipts and release assets retain their original source identities.

The English/French Computer Use flagship, strategy development, transformational reframing, local catalog
example, portable history and separate USDC/$AGIALPHA routes retain their existing behavior. Use only
public, non-personal inputs in the current assessment and trials. Public accessibility alone does not
establish that a document is non-personal or that its proposed use is permitted.

## Qualification and commissioning

New tests exercise actual disposable processes, blocked DNS, a real slow-stream loopback HTTP server,
STOP and deadline cancellation, child cleanup, byte accounting and native interrupted receipts with no
automatic replay. The loopback server uses explicit test-only DNS/transport substitutions; it does not
weaken the production public-network policy or establish a live provider task.

Exact-head hosted regression, package, Docker, browser, documentation, release and served-site acceptance
remain required before publication. The matching published manifest and successful workflow identify
delivery. This source document does not assert those gates have completed.

No smart contract, compiler profile, historical deployment, ENS configuration, on-chain authority,
funding or activation change is included. Ubuntu Hardhat creation retains hidden local ephemeral
deployer-key entry; Ledger governance remains on Mac Studio. Live signing and deployment remain
separately authorized. Live-model qualification, independent review and economic outcomes remain
separate from this runtime repair.

[First-use guide](START_HERE.md) · [Computer Use setup](SUCCESSOR_COMPUTER_USE.md) ·
[Release readiness](RELEASE_READINESS.md) · [Jobs/Fleet boundaries](ECOSYSTEM_ADAPTERS.md)
