# AGI Alpha Agent — original baseline

This checkpoint preserves the repository before completion work. The original
source is in `source/`; all 4,845 original branches and their 10,343 reachable
commits are in `history/AGI_Alpha_Agent_Original_History.bundle`.

The baseline commit is `ac9b112a44670f67d53fc3d188ef73fa16e90894`.
The release tag is `baseline-2026-09-24`. Keep this archive and its separate
`SHA256SUMS.txt` in your own backup location as well as GitHub.

## Verify the download

Download all release assets into one directory. On Linux run
`sha256sum -c SHA256SUMS.txt`; on macOS run `shasum -a 256 -c SHA256SUMS.txt`.
These hashes check consistency with the published files; obtain the release
and expected checksums from a trusted source.

Extract the ZIP. With Python 3.11+ and Git installed, run the included verifier
against the original ZIP:

```bash
python3 VERIFY.py /absolute/path/AGI_Alpha_Agent_Baseline_2026-09-24.zip
```

It checks every source byte and executable mode in the archive, the complete
branch inventory, the bundle hash, Git object integrity, the baseline tree,
and a fresh restoration of the history. It does not run the application.

## Recover into new directories

Run from the extracted archive directory. Choose new directory names so no
existing checkout is overwritten.

```bash
git clone --mirror history/AGI_Alpha_Agent_Original_History.bundle recovered.git
git -C recovered.git fsck --full --strict
git clone recovered.git recovered-work
git -C recovered-work switch --detach ac9b112a44670f67d53fc3d188ef73fa16e90894
git -C recovered-work status --short
```

The detached checkout is the exact original baseline. The mirror retains all
original branches; recover any other branch into a new working checkout when
needed. File permissions are restored by Git. Do not use a mirror push over an
active repository: that can replace or delete its newer references.

## What is preserved

All 2,125 tracked files, including the complete README, styled feedback loops,
flywheel diagrams, presentations, notebooks, demos, generated assets, code,
tests, licenses and existing workflows. Original bytes and executable modes
are retained. The preservation tools live on a separate publication branch;
the original `main` content is unchanged.

## Baseline status

This is an archival prerelease, not a completed or production-qualified build.
The existing PR CI passed on the baseline commit, while full Integration CI
failed in Python tests, pre-commit checks and documentation checks. The
current CI watchdog reports that integration failure. Detailed run references
are in `preservation/PRESERVATION_MANIFEST.json`.

No baseline defects or historical claims were rewritten for this checkpoint.
The source package still declares `0.1.0-alpha`, while existing documentation
contains other component versions. Those original labels remain intact.

GitHub issues, pull-request discussions, repository settings, secrets, running
deployments, external model weights and remotely linked resources are outside
this source/history archive. Existing installation requirements still apply;
the archive is not a bundled offline runtime.
