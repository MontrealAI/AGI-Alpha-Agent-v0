# Non-overwriting rerun of the preserved scientific audit

This additive helper addresses [review P2 4370984659 on #4903](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4903#discussion_r4370984659). The archived reproduction README invokes an audit whose fixed output already exists in the published archive. The original audit intentionally refuses overwriting it.

The helper preserves that guard, the complete original archive, every frozen input and the archived audit receipt. It extracts the exact archive into a temporary area and creates a new verification copy containing unchanged inputs and source. The recorded receipt is copied into the new output directory as `RECORDED_AUDIT.json`; its fixed output name starts absent only in the new verification copy. The unchanged original audit then creates a fresh receipt there, which is saved separately as `RECOMPUTED_AUDIT.json`.

No original file is deleted, renamed, rewritten or patched. The input archive is bound to SHA256 `0fa00aadc1df63f55e5c5985bc90b4c3851862f8b6567d65b66bbc2368e92015`. The helper separately pins the preserved audit source, archived receipt and freeze manifest, verifies all 110 frozen files, and checks every copied input before and after execution. This is verification of saved outcomes, not a new mission or scientific confirmation sample.

## Run

Use the reference Python environment and dependencies documented in the preserved study. Download the exact original `AGI_ALPHA_Capability_Construction_Research_Evidence.tar.gz` archive alongside this helper, or pass its actual local path. Choose a **new** destination whose parent already exists:

```sh
python rerun_scientific_audit.py \
  --archive AGI_ALPHA_Capability_Construction_Research_Evidence.tar.gz \
  --destination capability-audit-verification-001
```

The helper performs no network request. It refuses a different archive or an existing destination. It records subprocess stdout/stderr and returns failure if the unchanged audit fails, any copied source changes, or its result differs from the archived audit after excluding only the declared `created_utc` timestamp. It does not retry failed checks. Temporary extraction and working copies are removed after the new evidence has been saved; the original archive remains unchanged.

The completed directory contains:

- `RECORDED_AUDIT.json`: byte-exact archived receipt.
- `RECOMPUTED_AUDIT.json`: fresh report from the unchanged audit source.
- `VERIFICATION.json`: identity, preservation and comparison checks.
- `stdout.txt` and `stderr.txt`: exact subprocess output.

## Verification performed

`verification-run-001/VERIFICATION.json` records a successful execution from the exact original archive: **1,101/1,101 scientific audit checks**, all 110 frozen inputs verified, and all **4,909 archived study files** preserved. The **4,908 working input files** are unchanged; the only omitted initial file is the recorded audit at its fixed output destination. The original source script is unchanged. Recomputed and recorded reports match exactly apart from `created_utc`.

`EXISTING_DESTINATION_REFUSAL.json` separately records that a second invocation pointing at the completed output directory refuses without modifying any output or the archive. This is a check of non-overwrite behavior; it does not rerun the scientific audit.

These files are a proposed additive reproduction aid outside the sealed edition. They have not been committed to the public source PR, and the review thread has not been resolved. Publication/review of this helper remains a separate step; no original archive or canonical PDF needs revision.
