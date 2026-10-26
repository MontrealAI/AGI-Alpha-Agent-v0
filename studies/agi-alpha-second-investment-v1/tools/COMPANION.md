# Portable companion editions

The packaging tools operate only on this study directory. They preserve the primary evidence byte for byte,
including historical absolute command paths and `file:` URLs inside receipts. The relative paths in the frozen
job files are used for a new reproduction; old recorded commands are provenance, not relocation instructions.

## Verify without running research

```bash
python tools/verify_companion.py
python tools/verify_companion.py --runtime
```

The first command checks the 25 frozen production files, the six registered jobs, 47 distinct research wheels,
all 18 primary receipts and certificates, captured pip output, B/C capability and economic-effect identities,
the market source freeze, and complete raw and compressed market ledgers. In a packaged edition, it also
checks the manifest against every included file. Neither command downloads, installs, reruns a mission or
starts the application.

The second command additionally requires the exact recorded native runtime: CPython **3.12.14**, pip
**26.2.2**, packaging **26.3**, Node **24.22.1**, and every field in the registered target environment. That
environment includes the Linux kernel identity. The relocation experiment establishes path portability on
the same native runtime; it does not establish support for arbitrary platforms or Python versions.

## Two editions

The **full edition** includes the 47 canonical research wheels once in `inputs/wheels`, two separately
identified execution-tool wheels in `inputs/execution-tools`, and the small synthetic failure-fixture wheels.
The execution tools were added after confirmation for reproducibility. Their addition is not a fresh input,
an improvement to a measured production arm or a credited saving. Wheel-contained licenses and their hashes
are recorded in the tool-closure manifest. Interpreter, Node and OS binaries are external prerequisites.

The **GitHub evidence edition** omits all `.whl` binaries. It retains sources, protocols, primary records,
certificates, logs, preserved failures, papers, figures, demonstrations and market ledgers. It contains a
manifest of all written files and the identities of omitted wheels. The following verification permits the
deliberate absence of wheel binaries and reports that the offline wheel closure is absent:

```bash
python tools/verify_companion.py --edition github
```

An optional network bootstrap is explicit and restores only the 47 public research wheels and two public
execution-tool wheels. It uses saved URLs, exact SHA-256 digests and sizes from `inputs/wheel-sources.json`.
It does not select new versions, alter frozen jobs, install packages or reconstruct synthetic failure fixtures.
Existing mismatched files are rejected. Without both flags, no network request is made.

```bash
python tools/verify_companion.py --bootstrap-wheels --allow-network
python tools/verify_companion.py --edition github --runtime
```

The full edition remains the complete binary evidence archive. After bootstrap, the GitHub edition has the
wheel dependencies needed for primary reproduction; its archived synthetic failure inputs remain omitted.

## Prepare an isolated Python environment, if needed

Use an already available CPython 3.12.14 interpreter. The following optional commands create a disposable
environment and install only the two bundled execution tools, without a package index. They do not install
the 41 application dependencies: the frozen production experiment uses offline `pip --dry-run`.

```bash
python3.12 -m venv /tmp/agialpha-replay-env
/tmp/agialpha-replay-env/bin/python -m pip --isolated --disable-pip-version-check install \
  --no-index --find-links inputs/execution-tools --only-binary=:all: --require-hashes \
  -r inputs/execution-tools/requirements.lock
export PATH="/tmp/agialpha-replay-env/bin:$PATH"
python tools/verify_companion.py --runtime
```

Keep Node 24.22.1 available on `PATH`. The runtime check refuses mismatched target fields; do not edit the
registered targets merely to turn a mismatch into a passing historical reproduction.

## Reproduce once in a disposable copy

```bash
python tools/build_companion.py --edition full --stage /tmp/agialpha-replay-copy
cd /tmp/agialpha-replay-copy
python tools/verify_companion.py --runtime
python tools/run_confirmation.py --phase reproduction --out results/reproduction-new
```

The stage destination and reproduction output must not already exist. The frozen runner repeats the same
six registered questions in the same three branches: **18 reproduction evaluations, zero new research
missions and zero new customer orders**. It invokes the same offline pip and native Workbench workflow; it
does not start the AGI application runtime. Reproduction timings do not replace the primary measurements.

Running reproduction adds new files to that disposable tree, so its original all-files archive manifest no
longer describes the expanded tree. The runner still checks all frozen production identities before and
after each evaluation. Retain the reproduction receipt separately from the immutable primary archive.

The completed relocation check for this study is recorded in
`resources/portable-companion/REPRODUCTION_RECEIPT.json`. It passed all 18 evaluations with identical
decisions on its first and only attempt. Small logs and the campaign receipt are retained, together with
the identities of the remaining reproduction outputs. The original primary campaign remained byte-identical.

An optional rerun of the frozen market campaign repeats the same 1,920 paired worlds and seeds. The frozen
runner retains its original `FROZEN_MARKET_CONFIRMATION` label even when given a reproduction output path.
That label does not turn a replay into additional primary evidence. Keep any such replay in a disposable
copy, preserve the original campaign, and report it separately as reproducibility work.

## Plan, stage or build an archive

Without an action flag, the builder prints the inclusion plan and creates no archive:

```bash
python tools/build_companion.py --edition full
python tools/build_companion.py --edition github
```

The builder excludes exact duplicate per-result wheel views, bytecode/cache directories, hidden environment
files, generated ZIPs, LaTeX temporary outputs, layout screenshots and private Library persistence helpers.
Distinct wheel bytes used as failure fixtures are preserved in the full edition. Logs, recorded failures
and scientific figures remain included. The stage is verified after copying, and every included file is
covered by `COMPANION_MANIFEST.json`. The manifest necessarily excludes its own digest; the outer ZIP
SHA-256 binds it. No archive includes unrelated parent-repository files.

Final archive creation requires the explicit final gate, which checks that the completed market campaign,
README and LaTeX/PDF publication are present. The output must be outside the study directory. Existing
archives and unfinished `.partial` archives are never overwritten.

```bash
python tools/build_companion.py --edition full --final --archive /tmp/agi-alpha-second-investment-full.zip
python tools/build_companion.py --edition github --final --archive /tmp/agi-alpha-second-investment-github.zip
```

ZIP entries use fixed timestamps and permissions, so the same staged bytes produce the same ZIP. Archive
creation does not publish the files, contact customers, obtain credentials or perform financial actions.
