# Reproducing this additive edition

This directory is a self-contained study overlay for repository parent
`231834269599d85e49cfe1ca9917a1a874522d44`. The inherited runtime bridge and
vendored closure remain in that repository; their original research pin is
`80b345828f34fd8a6e592977dd17ef37141305f4`. The historical v3 helper required by
v4 integration is restored from the exact archive described below. Do not
substitute another helper or weaken a source/dependency hash check to make a
rerun pass.

**Every rerun is reproduction of already known cases, not fresh confirmation.**
The original 0.1.0 primary 5/8, original recipient transfer, separate 0.1.1
prospective 4/4, hosted comparisons and economic results remain distinct.
Restoration itself executes no scientific experiment, model call, permission
grant, customer transaction or external download.

## 1. Restore exact files without downloading the large source archives

Run from the repository root containing this published study overlay:

```sh
python studies/agi-alpha-opportunity-discovery-v4/prepare_reproduction.py
python studies/agi-alpha-opportunity-discovery-v4/prepare_reproduction.py --verify-only
```

The script uses only the Python standard library. It verifies archive hashes,
exact member lists, member sizes and SHA256 values, and deterministic gzip
objects before writing. It restores the preserved v3 study beside v4, the four
Plate development inputs, the ten Box/Cover public evaluation inputs, and the
large generated evidence files omitted from Git's loose-file selection.

Existing identical files are left unchanged. A different user file, symlink
ancestor, unsafe path, undeclared ZIP member, or changed compressed payload is
rejected. All destination collisions are checked before restoration writes.
The script creates only missing files and never executes an extracted file.
This is careful local file handling, not a hostile-host sandbox claim.

For a separate destination, use `--target-repo /absolute/path/to/repository`.
This restores the declared data/fixture paths only; it does not clone the parent
repository or copy all v4 source files. The normal workflow is a checkout of the
published edition first, followed by restoration in that checkout.

| Package | Contents | Compressed bytes |
|---|---|---:|
| `historical/v3_fixture.zip` | All 480 ordinary v3 files, including sources, old/revised results, notices and failures; no environments or caches | 2,667,395 |
| `data/public_evaluation_inputs.zip` | Ten exact NIST/MTC/reference inputs, combined original notices and authoritative input manifest | 1,079,053 |
| `data/development/plate_public_inputs.zip` | Existing unchanged four-input Plate package and two original notices | 533,315 |
| `reproduction/packed/` | 31 large JSON/log paths represented by 29 content-addressed lossless gzip objects | 1,986,078 total |

The 31 loose generated files occupy 52,816,118 raw bytes. Identical raw Plate
snapshots share one gzip object, while retaining every original path and raw
hash. Including archives, restoration verifies **529 files / 98,470,738 raw
bytes**. It does not discard unsuccessful trials, protected answers disclosed
after freeze, unsupported cases, exact literals or custody records.

`reproduction/RESTORE_MANIFEST.json` binds every compressed object and archive
member manifest. The original full source data, raw results and v3 files remain
unchanged in the authors' workspace. The narrow study `.gitignore` excludes
only the named loose generated files, exact expanded input paths, bytecode
caches and the two disposable runtime-pilot environments. Source code, readable
summaries, freeze files, notices and failed candidates remain included.

Archive SHA256 values:

- v3: `f41d6fbdb926cf3b21b86f45bed117874c032379d4012c1459d7233336331bc9`.
- Evaluation inputs: `06436d12c48b11c360af43b5dc1d53ba1c25967c934d28ad983ce224c8651719`.
- Restore manifest: `db32c180e67e3ef45289156fc89d19218191d63f078792094c05a759df3601a6`.

The existing official-source fallback remains available. It fetches or consumes
the exact two NIST archives and verifies both archive and member identities:

```sh
python studies/agi-alpha-opportunity-discovery-v4/evaluation/restore_inputs.py \
  --archive-dir /absolute/path/to/pinned-nist-archive-cache --download
```

Omit `--download` to use an existing cache. This fallback can require about
260MB; the compact source package avoids that download. The source manifest
records the official URLs, archive hashes and exact original member names.
NIST attribution/no-endorsement notices are retained. The exact DMSC QIF schema
retains its separate copyright/permission notice; it is not relicensed Apache
or asserted to be NIST public-domain data.

## 2. Provision the recorded execution environment

File restoration requires no third-party package. Scientific/CAD execution uses
**Python 3.12.14** and the exact five instrument declarations:

| Distribution | Version |
|---|---|
| cadquery | 2.7.0 |
| cadquery-ocp | 7.8.1.1.post1 |
| lxml | 6.1.1 |
| numpy | 2.3.2 |
| jsonschema | 4.25.0 |

`reproduction/requirements-runtime.txt` records all **53** observed mandatory
transitive and local trust-harness distributions, including cryptography 50.0.2
and pydantic 2.11.7. `reproduction/environment.json` records the original Python
binary identity and installed dependency-inventory reference. These are exact
version pins, not a portable wheel hash lock or an operating-system image.
The original execution separately rehashed 1,088,987,406 installed package/native
bytes; those dependencies are not contained in the small transferred code ZIP.

A compatible environment can be provisioned separately, for example:

```sh
python3.12 --version
python3.12 -m venv /tmp/agi-alpha-v4-environment
/tmp/agi-alpha-v4-environment/bin/python -m pip install \
  -r studies/agi-alpha-opportunity-discovery-v4/reproduction/requirements-runtime.txt
```

Check that the selected interpreter is exactly 3.12.14 before executing a frozen
instrument; the instrument rejects a different Python/package identity. A new
Python build, platform or package binary may change the fuller dependency
identity even when versions match. Requalify that environment and recheck the
current mission; do not reuse the historical generic receipt or authority grant
as proof for changed bytes.

The inherited lifecycle also uses Node. Packaging observed Node **v24.22.1**;
that is an execution-environment observation, not a claim that the repository's
full web/release matrix was qualified on it. Native helper source hashes remain
mandatory. The optional numerical rerun of the older v3 fixture additionally
uses SciPy 1.17.0, recorded in `requirements-historical-v3.txt`; the fixture's
supplied microgrid formulation remains historical, not the v4 flagship.

No API credential is needed for the deterministic evidence instrument,
evaluation or economic model. The hosted model responses are preserved evidence;
this edition cannot reproduce the unavailable served API snapshot, hidden
reasoning-token telemetry, account entitlement or exact model billing. A new
hosted trial needs new stated model/settings/budgets and cannot become the old
prospective trial retrospectively.

## 3. Targeted reproduction without overwriting preserved results

These commands are examples for a separately provisioned interpreter. The
packaging work did not execute them. Use a fresh output directory and retain the
original receipts.

Plate-only construction checks:

```sh
python -B -m unittest discover \
  -s studies/agi-alpha-opportunity-discovery-v4/instrument/tests -v
python -B -m unittest discover \
  -s studies/agi-alpha-opportunity-discovery-v4/instrument_v0_1_1/tests -v
```

Reproduce one known 0.1.0 Box audit and its independent check:

```sh
TASK_REPRO_DIR=$(mktemp -d /tmp/agi-alpha-v4-known-case.XXXXXX)
python -B studies/agi-alpha-opportunity-discovery-v4/instrument/cli.py \
  --request studies/agi-alpha-opportunity-discovery-v4/evaluation/protected/requests/box-counterfactual-family-v1.json \
  --output "$TASK_REPRO_DIR/report.json"
python -B studies/agi-alpha-opportunity-discovery-v4/evaluation/checker.py \
  --request studies/agi-alpha-opportunity-discovery-v4/evaluation/protected/requests/box-counterfactual-family-v1.json \
  --report "$TASK_REPRO_DIR/report.json" \
  --oracle studies/agi-alpha-opportunity-discovery-v4/evaluation/protected/oracles/box-counterfactual-family-v1.json \
  --output "$TASK_REPRO_DIR/check.json"
```

A successful command only means execution/report creation. Inspect independent
acceptance and the original-purpose disposition: this Box audit refutes the
requested numerical substitution even under its explicit hypothetical-mm input.
It is not physical acceptance. For the corrected version use the separate
`instrument_v0_1_1/cli.py`, `checker_v0_1_1.py` and a matching request/oracle from
`evaluation/prospective-v1/`; do not mix original and corrected freeze identities.
Execution time, process IDs, fresh signatures and paths may differ on rerun;
original source hashes and substantive expected semantics remain binding.

The original all-job runners deliberately refuse to replace their preserved
confirmation directories. To use those runners, first create an isolated copy
of the entire edition, preserve its old result directories elsewhere in that
copy, and label newly generated directories as known-case reproductions. Their
historical schema names do not make the rerun a new first confirmation.

The frozen economic program supports a new output path through its existing
Python API. The following reruns the known assumed-world cases into a temporary
directory while retaining all original results:

```python
from pathlib import Path
import json
import sys
import tempfile

study = Path("studies/agi-alpha-opportunity-discovery-v4").resolve()
sys.path.insert(0, str(study / "economics"))
from model import execute

output = Path(tempfile.mkdtemp(prefix="agi-alpha-v4-economic-reproduction-"))
(output / "REPRODUCTION_LABEL.json").write_text(json.dumps({
    "status": "reproduction_of_known_simulated_cases_not_fresh_confirmation",
    "actual_customer_collections_usd": 0,
    "actual_earned_revenue_usd": 0,
}) + "\n")
execute(range(21000, 21080), output, confirm=True)
```

The six-horizon diagnostic and adverse solvency audit have their own immutable
protocols. The latter intentionally refuses an existing `RESULTS.json`; run it
only in an isolated copy where the original result has been preserved under a
different filename. Keep its post-confirmation label and unchanged original
financeability assumptions visible. It does not estimate a rejection probability
or recover profit.

For actual received-code/native-interface reproduction, use the explicit command
and new `--out` directory documented in `integration/README.md`. Restoration
places the exact v3 `integration/inheritance.py` at the path that v4 checks.
The pinned parent repository supplies the v1 bridge and vendored runtime. Each
reproduction issues a new local research grant and rechecks the source,
dependency, mission and evaluator identity. It is not live ENS authorization,
a production scope extension or a replayable customer permission.

## 4. Packaging verification and remaining boundaries

`reproduction/VERIFICATION.json` records 11 passing file-handling checks:
restoration into an empty temporary directory; all 529 exact byte matches;
idempotence; refusal of a differing user file before any write; refusal of a
symlink ancestor; and traversal/absolute/ambiguous path rejection. The test
restored 98,470,738 raw bytes and then verified them independently against the
manifest. No scientific experiment was rerun and no original file was changed.
Ruff passed on the two packaging scripts.

`reproduction/build_packages.py` preserves the exact selection and deterministic
compression procedure. It refuses to replace a different existing package. ZIP
metadata dates are fixed, member order is sorted, and new gzip headers contain
neither a source filename nor a timestamp. The zlib version is recorded. The
preexisting Plate/confirmation gzip evidence remains unchanged rather than being
rewritten merely to alter its container metadata.

The package makes code, data and historical receipts inspectable. It does not
supply actual buyer demand, physical measurements, a scope-matched human trial,
complete research costs, rights to new customer records, legal contract approval
or production authority. Actual collections and earned revenue remain zero.
