[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.35.1 — Cancellable public-document reads

The native Computer Use reader now stops blocked DNS lookups and slow streamed responses within a
supervised read deadline. Previously, the HTTP inactivity timeout did not bound the total response time,
and the session's STOP/deadline checks waited for the complete read to return.

Each approved public-document request runs in a disposable child process. The parent checks the current
session between bounded waits, applies one eight-second wall-clock limit to DNS and HTTP together, and
kills and reaps the reader on cancellation or timeout. The child receives the retained approved reader source, installed dependency roots, exact URL, method and
remaining byte allowance through standard input. It inherits no provider credential, proxy or PYTHONPATH
environment, executable startup hook or cached bytecode. Each invocation starts with an empty private
bytecode-cache prefix.

Exact approved URLs, public-IP validation, pinned destination IPs, original-host TLS verification,
GET/HEAD-only access, redirect refusal and byte limits remain enforced. An interrupted read conservatively
reserves its remaining per-read allowance because the exact bytes received before termination are unknown.
The reader requests identity encoding, refuses compressed responses before consuming their bodies, and
uses raw-byte iteration so decompression cannot allocate an oversized body ahead of the byte limit.
STOP and deadline exceptions reach the native session; they cannot be converted into an ordinary denied
page and followed by more work. Existing uncertain action reservations and cleanup receipts remain intact.

Fresh permits bind the browser worker, public-reader source bytes and fixed reader bootstrap in their
worker commitment. Session approval captures the exact reader bytes once; each broker retains that
immutable snapshot and executes it from standard input. Replacing the source file after approval or at
subprocess creation cannot select new code. Scoped snapshot state resets even when a factory fails.
The same permit now binds the fixed pure-Python HTTPX dependency closure and its certificate resource.
Each child imports these captured bytes from memory instead of reopening installed packages. Package or
certificate replacement after approval cannot select later dependency bytes; changed installations require
a fresh permit. Signed native receipts retain that session's worker digest, so completed and interrupted
handoff returns keep their original source attribution even after an in-place source update.
Prepare a new permit after upgrading. The existing handoff, return and historical archive wire formats
are unchanged; earlier signed receipts and release assets retain their original source identities.
Previously exported native return/history JSON remains readable as historical evidence. Internal journals
from older runtimes that lack the signed worker digest are not upgraded by guessing from current files;
this exporter refuses them. Retain the original exported return and exact historical runtime. Recovery of
an unexported legacy journal has not been qualified by this release.

The English/French Computer Use history panel now links to the native Jobs and Manager supplier receivers
for unsigned, unfunded $AGIALPHA and USDC proposals. The legacy catalog routes remain available in their
own flow. A shared portable learning-archive inspector gives receivers the flagship's existing native
checks while preserving complete original archive and history bytes, including earlier catalog work,
strategy lessons, Computer Use attempts and owner reviews. Import creates no execution or payment authority.
The normal Alpha restore controls also merge native Computer Use history into the same project. Restore
the original complete archive first to retain catalog lessons, then import the latest native history.
Earlier attempts and reviews remain intact; conflicting evidence, unrelated projects and malformed UTF-8
or BOM-prefixed JSON are refused without replacing the retained workspace.

Strategy development, transformational reframing, the local catalog example and portable history retain
their existing behavior. Use only
public, non-personal inputs in the current assessment and trials. Public accessibility alone does not
establish that a document is non-personal or that its proposed use is permitted.

## Qualification and commissioning

New tests exercise actual disposable processes, blocked DNS, a real slow-stream loopback HTTP server,
STOP and deadline cancellation, child cleanup, byte accounting and native interrupted receipts with no
automatic replay. Source-replacement regressions execute the retained bytes after both in-place changes
and replacement inside process creation, and verify that unapproved code never touches its marker.
The loopback server uses explicit test-only DNS/transport substitutions; it does not
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
