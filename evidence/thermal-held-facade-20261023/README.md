# Thermal enterprise facade composition — local preparation only

The one bounded probe completed successfully on 2026-10-23 with the expected
Studio rejection. This directory is outside the product repository. No held
source was edited, published, copied into another PR, or used to clear a review
restriction. The prospective merge is left uncommitted in `checkout/`.

## Exact source

| Role | Identity |
|---|---|
| Thermal candidate, #4871 | `f1ac7df95d802b12bf194b3fa7be6f4c30a62ef4` |
| Held Ascension facade, #4865 | `6bb361d522d80dc900cc2a480014531c6a44b66e` |
| Held harness ancestor, #4863 | `c455ad4ce109c86df2fef09d19674810290b5185` |
| Actual common merge base | `0a668817284fed9010ad71ce405dbd5906ef2b28` |
| Prospective composition tree | `abc12184debbdd7f2c8ecf9928cc5482dc7b09f8` |

Git performed a conflict-free `merge --no-commit --no-ff`; no manual conflict
resolution or source dependency changes were needed. `composition.json` records
the real commit trees and parents, source hashes, and unchanged held blobs.
The forthcoming #4871 recovery fix is **not covered** by this result.

## What actually ran

The probe used the existing Python 3.12.14 isolated environment and Node 22.17.1.
It installed no dependencies. Its subprocess environment contains only the
recorded executable path, locale, temporary-directory, and Python isolation
settings. Public Git retrieval separately retained the tool environment's proxy
variables; the runtime probe did not inherit them or service credentials.

| Journey | Actual bounded result |
|---|---|
| Delivered heat through unchanged enterprise Python API | 3680 J, one attempt, `CONDITIONAL_BOUNDS_MET` |
| Heat capacity through unchanged enterprise Python API | 150 J/K, one attempt, `CONDITIONAL_BOUNDS_MET` |
| Heat recovery through unchanged enterprise Python API | 7/10, one attempt, `CONDITIONAL_BOUNDS_MET` |
| Distinct heat-capacity successor from the exact accepted delivered-heat parent | One attempt; reaches `review`; no inherited acceptance or authority |

Each of the first three results rejected a wrong review digest without adding a
journal event, then accepted the exact local review. Each reopened in a fresh
Python process and retained its state, result digest, one-attempt count, and
journal checkpoint. Reopening can invoke validation; the assertion is that it
does not append an execution attempt or new result/event. This is not an
interrupted-process or source-upgrade experiment.

The reviews are the same local operator's test actions. They explicitly retain
`independent: false`. These numerical results use declared simulated fixtures,
including independently declared **simulated** extension quantities. They keep
physical validity `NOT_ESTABLISHED`, accepted capability false, admission `HOLD`,
authority empty, and settlement `NOT_CONNECTED`.

A valid compiled one-job FusionPlan was then passed to both unchanged
`enterprise.handoff` and `enterprise_ascension.prepare`. Both returned:

> This executor supports only the installed fixed workbench families

The before/after journal checkpoint and filesystem file list were identical;
there were no Studio records. No RPC service, EVM, wallet, transaction, funding,
grant, institutional review, or settlement was used. This is an observed
integration boundary, not a completed thermal Ascension journey.

## Retained evidence

- `criteria.json`: acceptance criteria written before execution.
- `probe.py`: exact executed thermal-specific probe; no source monkeypatches.
- `result.json`: machine-readable observations and limits.
- `commands.jsonl` and `logs/`: exact acquisition, composition, dependency, probe,
  and source-verification commands with unabridged stdout/stderr and exit codes.
- `artifacts/`: actual configurations, results, wrong-digest rejections, local
  review records, fresh-process receipts, signed exports, compiled plan, and
  Studio rejection evidence. Public journal events retain signatures.
- `setup-observations.json`: earlier read-only lookup and inventory failures.
- `dependency-inventory` log: actual installed package versions, without
  credential-bearing package-source URLs.
- `evidence-index.json`: SHA-256 and size of each retained evidence file.

`private-homes/` contains disposable test operator journals and their private
local test keys. It is not part of the public evidence index or evidence archive.
`checkout/` contains the held source composition and is also excluded. Neither
directory is intended for publication.

The failed local shared clone and failed fully scrubbed public fetch are
preserved as setup/environment failures. The later authorized public fetch
succeeded using the existing proxy, with TLS verification unchanged. No source
conflict or dependency-install failure occurred, and the actual probe ran once.

## Reproduction and scope

The exact executable invocation is recorded under `thermal-facade-probe` in
`commands.jsonl`: the reused isolated Python interpreter executes `probe.py`
with `-I -B` from the disposable checkout. The runner uses exclusive output-file
creation; reproduce in a new evidence directory and a new disposable checkout
using the exact commit pair and composition commands. Do not rerun into retained
evidence directories.

This is additional local preparation for the existing owners. It does not
supersede their earlier 39-case campaign, resolve #4863's configured-review
restriction, qualify a release, establish four-repository compatibility, or
authorize a production adapter. Full thermal Studio admission and verdict
semantics remain owner integration work.
