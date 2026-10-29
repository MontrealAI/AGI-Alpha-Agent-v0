Development UI readiness evidence
================================

Exact main `12770c22b4a9f90f2013bbfb64242f912ba5071e` failed its Python 3.12
runtime acceptance in Agent run `40640285041`, job `122656903827`. Compose marked
the development UI unhealthy after approximately 188 seconds. The job ran
18 minutes 57 seconds, below its unchanged 25-minute limit. Earlier shared
consumer/configuration checks and the two default-container tests passed. The
two subsequent telemetry HTTP checks were never reached.

The validator removed its container and volume without retaining startup logs
or health-probe output. The original npm, Vite, network, resource or timing
cause is unknown. No such cause is inferred from the unhealthy label.

`ORIGINAL_FAILURE.json` binds the completed decoded log and actual downloaded
runtime artifact to the failing source. `runtime312-completed-log.raw.json`
losslessly preserves the exact connector-decoded UTF-8 log through gzip/base64;
this is not an assertion about original HTTP transport bytes. Raw text passed
the existing privacy check before archival. The bounded excerpt remains
separate. The artifact contained the passing legacy-container JUnit result but
no development-UI startup/health diagnostics or successful Compose report.

The narrowly scoped correction retains bounded UI logs, focused state/health
and disk availability before cleanup. `FREEZE.json` preserves all original
readiness conditions, HTTP module assertions, cleanup obligations and existing
time limits. It grants no access, provider budget or on-chain authority.

The first diagnostic candidate passed 16 local tests but independent probes
found two flaws: credential fragments could survive clipping or JSON escaping,
and cancellation could leave an owned diagnostic descendant running after its
leader exited. The probes used fictional credentials. That candidate is
rejected and preserved in `PRE_REVIEW_VALIDATOR.py.txt`,
`PRE_REVIEW_TESTS.py.txt`, `PRE_REVIEW_QUALIFICATION.json` and
`INDEPENDENT_FINDINGS.json`. Later corrections must retain this negative
evidence and earn their own qualification.

A later local counterexample found that a fictional credential in a decoded
JSON object key survived value-only masking. Its failing run and exact source
are preserved in `JSON_KEY_ORIGINAL_RUN.json`, `json-key-original.txt`,
`json-key-original.xml` and `PRE_JSON_KEY_VALIDATOR.py.txt`. The correction
masks both keys and values while retaining typed numeric and boolean state.
`CORRECTION_HISTORY.json` records the intermediate assertion failure and a
metadata field correction without rewriting the original receipts.

The corrected candidate passes 32 focused pure Python cases and scoped Ruff
lint (`LOCAL_QUALIFICATION.json`). This is local failure-path qualification,
not Docker startup or release acceptance.

The final independent check found two missing collection type annotations and
missing third-party YAML stubs in the test environment. The pre-annotation
source and failed type output are retained. `FINAL_READY.json` binds the
annotation-only correction to fresh focused tests, Ruff and strict source
typing with separately installed YAML stubs. `CUSTODY_OUTPUT_MAP.json` closes
the original prepublish receipt's output filenames without rewriting that
receipt or its failed whitespace evidence.

Local tests and review cannot establish a healthy Docker startup. Fresh
exact-main runtime acceptance, the complete release campaign, publication,
actual public-byte installation and the frozen operating canaries remain
separate requirements. A later successful startup would not establish the
original failure's root cause. Actual complete monetary costs remain unknown;
customer collections are zero and no Alpha is inferred.

Vincent Boucher — President of MONTREAL.AI
