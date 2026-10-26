# Opt-in bounded retries for pinned browser model downloads

The existing downloader already verifies SHA256, reuses valid cached files and
atomically replaces a destination only after verification. The checksum, temporary-file cleanup and atomic-replacement sequence is retained.
`download()` gains an explicit keyword-only opener resolved at call time; no
module-global transport is temporarily replaced.

This addition provides `download_with_retry(output, attempts=1, backoff=0.25)` and
an explicit CLI option:

```
python scripts/download_browser_model.py --output PATH --attempts 3
```

**Default behavior remains one attempt.** Opt-in retries apply to the **whole
manifest**, potentially including model weights, not merely metadata. At most
three queue attempts are allowed. Previously verified files are reused. The attempt cap alone is not a byte cap, total-duration deadline, concurrency
lock or quota reservation. Optional paired resource budgets are described below. A socket timeout does not bound the total operation. Operators must
consider payload sizes and their permitted network/resource budget before opting
in. No large downloads were run for this publication.

## Optional cumulative application-read budgets

Supply both `--max-body-bytes N` and `--max-requests M` with positive integers to
opt into a per-invocation budget, sized from approved artifact requirements and
retry allowance. The same budget object is retained across all retry attempts.
Neither value is inferred from credentials, billing limits or available funds.
Omitting both preserves the prior unbudgeted path; supplying only one is rejected
before work. Defaults still do not enable retries.

`max_body_bytes` counts bytes actually returned by application reads, including
bytes returned before a later read failure. Reads request at most the remaining
allowance plus **one overflow-detection byte**; a breaching chunk is rejected
before being handed to the downloader for writing. The guarantee requires the
underlying response to honor `read(n)`. Unexpected overlarge reads are rejected
and their observed bytes recorded, not retrospectively made bounded.

`max_requests` counts opener invocations, including failed opens. Internal HTTP
redirects or retries inside the underlying transport are not separately counted.
These counters are **not wire traffic, OS buffering, egress bills or a total
runtime deadline**. An already blocked read cannot be interrupted by this guard.
Bytes swallowed internally by a failed read are unobservable. Budget objects
require sequential use, not concurrent mutation or adversarial custom transports.

Exhaustion raises a nonretryable `ResourceLimitExceeded` (`ValueError` subclass).
The original temporary-file cleanup and checksum/atomic commit logic still runs;
previously verified files remain available. Valid cache entries consume no
transport budget. An undersized budget can correctly reject legitimate useful
work; rejection is a resource tradeoff, not a free reliability gain. No production
weight-sized workload or live-server qualification is claimed.

A disclosed local nonterminating-response probe required an external watchdog at
4,096 returned bytes without the guard; a 1,000-byte guard stopped at 1,001 bytes
including detection, with no invalid commit. A four-file metadata/partial-timeout
probe completed with identical artifacts at a sufficient 1,348-byte budget;
1,347 bytes safely rejected useful completion. These are controlled application
stream probes, not real endpoint incidents, wire measurements or economic savings.

## Policy

Retry only HTTP 429/500/502/503/504, direct TimeoutError/ConnectionError, and
URLError wrapping those two exception types. Unknown URL errors, TLS validation,
authorization, checksum and filesystem permission errors propagate immediately.
Stop after the requested 1–3 attempts and preserve the final exception. Sleep only
between failed attempts, with exponential delays from the declared backoff.
Backoff is finite and restricted to 0–2 seconds: maximum total sleep is six seconds
(default backoff totals 0.75 seconds when three attempts are explicitly selected).
Retry-After interpretation, jitter and a whole-operation deadline are not added.

## Recurring work and evidence

The workload is the repository's existing pinned artifact inventory. Admission
should be triggered by an approved manifest change or genuinely missing/corrupt
local files; same-pin valid cache checks are not new jobs. No scheduler, live
operator profile, model installation or financial action is activated here.

A prior local study, based on main
`3b040e68adae8196f7bda4c65f92af92ee6f7335`, exercised ten controlled fault traces
against baseline, a retained retry wrapper and a conventional retry wrapper. Four
unique metadata files totaled 1,341 bytes. Completed queues increased from 2/10 to
5/10 with retry; the conventional wrapper tied exactly. Requests rose from 18 to
31. These were 30 case-arm executions, not customer jobs or real endpoint outages.
The research wrapper defaulted to three attempts; **this production proposal
separately preserves one attempt by default** and requires explicit opt-in.

This is a reliability/capability improvement with additional work, not measured
cost savings, autonomous invention, commercial payback or a full economic
Flywheel win. Model weights, browser inference, production outage behavior and
resource economics remain unqualified. No research payloads or unverified
third-party license material are included in this change.

## Regression checks and release boundary

`tests/test_browser_model_retry.py` covers budgets, delays, error classification,
exception identity, early success, default behavior, CLI opt-in, multi-file cache
reuse and zero new requests for a warm queue. It uses synthetic bytes in temporary
manifests, never mutates the checked-in manifest and makes no network requests.
`tests/test_browser_download_budget.py` adds cumulative partial-read/retry,
open-attempt, overflow cleanup, cache no-op, context-lifetime and CLI budget tests.
The original `tests/test_browser_model_download.py` remains unchanged and checks
corruption rejection, cache reuse and atomic destination preservation.

Run all three tests in the repository's supported environment. Local tests and source
publication are not a merge, release, approved installation or live deployment.
Existing integration-owner, Security, operator and release gates remain in force.
