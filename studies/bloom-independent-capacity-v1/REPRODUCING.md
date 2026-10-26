# Reproducing BLOOM independent-capacity-v1

The commands below were checked against the actual command-line parsers. Run
from the study directory containing `demo.py`, `core.py` and `protocol/`.
They preserve shipped evidence by choosing new output locations. A rerun uses
already disclosed cases; it is reproduction, not fresh confirmation.

## Environment and setup

The recorded environment was CPython **3.12.14**, Linux x86_64,
`Linux-6.18.55-x86_64-with-glibc2.39`, with nine reported logical CPUs.
Scientific execution is single-process Python; this is one inherited host, not
isolated hardware or a representative machine sample. The runner uses the POSIX
`resource` module; Linux is the documented reproduction target.

| Component | Requirement / recorded version |
|---|---|
| Numerical study and analysis | Python 3.12; standard library only |
| Native dispatcher demonstration | `pydantic==2.14.0`, `cryptography==50.0.2` |
| Independent npm ancestry check | Node; recorded `v24.19.0`; built-in modules only |
| PDF publication validator | Separate repository requirement `pypdf==6.21.1`; not needed to run the study or demo |
| Solidity local fixture | Not installed or run in this edition; see `integration/EVM_NOT_RUN.json` |

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r integration/requirements.txt
```

Dependencies are version-pinned but this two-package integration file is not a
hash-locked wheel distribution. Record the resolved environment on a new
machine. No LLM service, API credential, RPC endpoint or paid service is required.
The compiled scientific operator binds Python implementation/major-minor and
both kernel and independent-checker source digests. Native fixtures additionally
record their actual environment and source snapshots.

## Verify the original freeze first

The source freeze was recorded at `2026-10-24T02:02:15.373234+00:00`, before
confirmatory case generation. Its SHA256 is
`ecd3df2706d034d17a1441c62fd4dba0c7c92f5ea4d22327011bf5e1116bcfbe`.
The original protocol SHA256 is
`41c363fafa89c387f941aca9338689443f1c5cf1eae705659fd88d818993e625`.
The [public registration](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6378518568)
also records the durable preconfirmation checkpoint and its verification.

```sh
python3 - <<'FROZEN'
from pathlib import Path
import hashlib, json
root = Path('.')
freeze_path = root / 'protocol/FREEZE.json'
assert hashlib.sha256(freeze_path.read_bytes()).hexdigest() == 'ecd3df2706d034d17a1441c62fd4dba0c7c92f5ea4d22327011bf5e1116bcfbe'
freeze = json.loads(freeze_path.read_text())
for row in freeze['files']:
    data = (root / row['path']).read_bytes()
    assert len(data) == row['bytes'], row['path']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
print('PASS:', len(freeze['files']), 'frozen source identities')
FROZEN
```

`confirmation_opened: false` is the immutable historical pre-run state in the
freeze. Completed campaign receipts record the later executions; do not edit the
freeze to change that historical field. Changed frozen source must not be
presented as this edition's original confirmation.

## Run the useful local demonstration

```sh
python3 demo.py --case public_case/case.json --method expert --output runs/public-demo-local
```

The exact available method choices are `bloom`, `expert`, and `reverse`.
`expert` is the default. Omitting `--case` runs deterministic development fixture
107; it does not open a hidden case. The public case is excluded from inferential
results.

Open `runs/public-demo-local/index.html`. The command also creates:

- `case.json`, `operator.json`, `impact.json`, `successor.json`, `summary.json`.
- `native/native_graph.json`, `native/native_graph_history.json`,
  `native/native_institution.json`, `native/native_source_manifest.json`.
- `native/native_workflow_receipt.json`, `native/stage_artifacts/`, the original
  and restored journal directories, and `native/PUBLIC_FIXTURE_RECOVERY.zip`.

The recorded report at `results/public-demo/index.html` is usable without a
rerun. Summary export is available in that report. The successor terminates with
`plan exported; no tests executed`.

To independently check the static public graph and its expected answers:

```sh
python3 public_case/acceptance.py --check
```

This checks raw Git/SHA256 identities, canonical fixture reconstruction, native
Node ancestry resolution, independent BFS and exhaustive cover expectations.
It neither installs packages from the lockfiles nor runs their scripts.
`graph_audit.json.gz` is lossless; `audit_manifest.json` contains the compressed
and canonical decompressed hashes.

## Recompute analysis without overwriting it

```sh
mkdir -p runs
python3 analyze.py results/confirmation --output runs/confirmation-analysis.json
python3 analyze.py results/reproduction --output runs/reproduction-analysis.json
```

The analysis checks the full expected trial-key multiset, ledger counts, and raw
record hash before inference. Missing or altered evidence produces
`INCOMPLETE_EVIDENCE` for all gates. The original analysis files retain
`G1: PENDING_INDEPENDENT_REPLAY`; the later independent review supplies G1's
passing closure. Do not rewrite that chronology.

The evidence browser is derived reporting, separate from frozen analysis. To
rebuild it at its intended relative bundle location after preserving the
original output:

```sh
python3 reporting/build_evidence_index.py --study-root . --output reporting/evidence-index --link-prefix ../../
```

This does not rerun scientific cases or amend frozen source. Choose another
output and an appropriate `--link-prefix` if retaining a second preview.

## Execute deterministic reproduction

Use new output directories under `results/`, so the runner's cumulative
completed-campaign accounting includes them:

```sh
python3 run_study.py --split confirmation --output results/local-confirmation
python3 analyze.py results/local-confirmation
python3 run_study.py --split reproduction --output results/local-reproduction
python3 analyze.py results/local-reproduction
```

Confirmation is seeds 20001–20048, 48 worlds and 2,544 records. Reproduction is
seeds 30001–30024, 24 shifted-size worlds and 1,272 records. Custom seed subsets
are accepted only for `--split development`; do not use them to claim a complete
confirmation. Progress prints every 100 trials and on completion. Preserve a
partially written directory and error if interrupted; choose a new directory for
an explicitly logged infrastructure retry.

The declared scientific ceiling is 1,200 CPU seconds across completed
`development/` and `results/` campaigns, with a 256 MiB evidence envelope.
The five completed scientific campaigns use 47.887703197 CPU seconds. The
final reconciliation additionally identifies five distinct native receipts
(6.198259305 seconds) and three retained early developer calls (0.180152431
seconds), for a **54.266114933-second documented CPU subtotal**. These categories
are counted once; nested stage/kernel timers and archive copies are not extra
incurred compute. Authoring, typesetting, service allocation, unknown lost or
unretained timing and billing remain separate. This is not complete research
cost or a full monetary budget. See the
[economic reconciliation](reporting/economics/ECONOMICS.md) and
[post-study reporting deviations](reporting/economics/POST_STUDY_REPORTING_DEVIATIONS.md).
Repeated demonstrations and reruns are not new independent observations.

For the original confirmation, the deterministic record-stream SHA256 is:

```text
d6fb1cf6a89d24a7cc73ef8dae3c80b3310feb4e3237224c0b21b871a4c5dd68
```

The independently executed confirmation replay reproduced that hash, all 48
case files, and all 480 retained operator files. The fresh reproduction stream
hash is:

```text
70d2005556b88f8a22c95d476981d0c4d75273d65e8d51d4ec2448b6aa8c0f5f
```

Each run's `campaign.json` records its observed deterministic hash and raw
`records.jsonl.gz` hash. Raw gzip bytes include actual timings and will differ
on rerun. The deterministic projection removes top-level nanosecond timings,
phase timing structures and policy-decision CPU measurements while retaining
semantic identities, decisions, counters and outcomes. Native journal
timestamps/identities and per-run custody hashes also vary. Never alter measured
timing fields to manufacture byte identity.

## Readable failure and stop conditions

| Observation | Meaning and next step |
|---|---|
| Existing output directory | Prior evidence is protected. Use a new path. |
| `frozen source changed: ...` | The execution does not match this edition. Restore exact reviewed bytes or identify a new version. |
| `REFUSED_AUTHORITY` | The receiver lacks its current local authority; no predecessor grant is inherited. |
| `REFUSED_INPUT` | Malformed data or a policy-ineligible input was refused. This experimental cover policy requires positive weights. |
| `FAILED` / `stopped-on-failure` | Read the scientific error or native receipt; retain the attempted work and cost. |
| `feasible: false` | No supplied coverage plan exists. This is a correct explicit outcome when verified. |
| Empty affected set | No successor cover is needed; stop normally. |
| Native restore remains stopped/paused | Intended behavior. Restoration is historical custody, not renewed proof or permission. |
| `G3: FAIL`, `G4: FAIL` | The prespecified practical hypotheses were not established; these are retained scientific results. |
| `G5: INCOMPLETE_COSTS_AND_DEMAND` | Full commercial viability cannot be asserted from the present ledger. |

## Scope of the independent check

The conventional policy, proof checkers and reproduction were independently
implemented/executed within the same controlled research session. They are not
external organizational replication, concealed third-party cases, or independent
hardware. Seed ranges and the generator were known before execution; only the
final case outcomes were unopened at freeze. Three cold logical runs per stable
and withheld world reset operators/caches; interpreter warmth was symmetric.
The external BFS/brute-force research audit is excluded symmetrically from each
method's primary latency and included in campaign resources.

For an independent audit, retain original files and compare new outputs before
examining timing differences. Inspect source identity, completeness, all failed
attempts, and altered-world/policy/artifact refusal behavior. The complete ZIP
also retains source licenses and its authoritative PDF; publication-byte hashes
and the outer manifest are separate from scientific record hashes.
