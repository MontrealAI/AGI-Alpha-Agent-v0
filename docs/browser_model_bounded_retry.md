# Opt-in bounded retries for pinned browser model downloads

The existing downloader already verifies SHA256, reuses valid cached files and
atomically replaces a destination only after verification. Those guarantees and
the complete `download()` function remain unchanged.

This addition provides `download_with_retry(output, attempts=1, backoff=0.25)` and
an explicit CLI option:

```
python scripts/download_browser_model.py --output PATH --attempts 3
```

**Default behavior remains one attempt.** Opt-in retries apply to the **whole
manifest**, potentially including model weights, not merely metadata. At most
three queue attempts are allowed. Previously verified files are reused. The
attempt cap is not a byte cap, total-duration deadline, concurrency lock or quota
reservation. A socket timeout does not bound the total operation. Operators must
consider payload sizes and their permitted network/resource budget before opting
in. No large downloads were run for this publication.

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
The original `tests/test_browser_model_download.py` remains unchanged and checks
corruption rejection, cache reuse and atomic destination preservation.

Run both tests in the repository's supported environment. Local tests and source
publication are not a merge, release, approved installation or live deployment.
Existing integration-owner, Security, operator and release gates remain in force.
