These additive records preserve the final regression failure from main f836f06e8351e64db1da770e16e304b5feb01f28, tree 6aa458f1dad73205fe61ab8277abae785cb76fe4, Agent release acceptance run 40157168357 / regression job 121061031945. State: **FAILED_NOT_QUALIFIED**. The original 18 files above this directory, including their MANIFEST.json and README.md, are unchanged.

The final all-jobs snapshot reports 40 completed jobs: 32 success, 3 failure, 5 skipped. Regression reports **2 failed, 4939 passed, 80 skipped, 4 deselected, 4 xfailed, 192 warnings in 3805.88 seconds** and coverage 82.35%. Strict types and repository checks were **SKIPPED**. The two failures are the paper-workflow and release-queue policy checks for the same missing `strategy-engineering` prerequisite already exposed by the original quality gate. These records preserve the failed source; corrective source and required later gates retain their own identities. Nothing here qualifies corrective source 739, a release, installation, capability growth, held Harness/Fleet operation, or any authority.

The original regression ZIP is split into four 4 MiB-or-smaller binary chunks solely for transport. Its 13,862,948 bytes and SHA-256 f637ebc47d6b34bc812a9719105702da4bc3160db4fc8ea52cbadfee660085db are preserved. The full original log is copied without edits (994,499 bytes, SHA-256 42779f6c666ecd254686287b37cc384c2761c034d362a8e02cdf5a92fe9ad711). Original final-job, artifact and step metadata are retained alongside the derived final-run.json.

A data-only audit CRC-checked all 541 entries across 11 ZIP containers with explicit per-file/total/depth bounds and zero skips. No unsafe paths, duplicate names, symlinks, encryption or executable modes were found. All 34 image entries (18 unique bodies) exactly match images in the previous two archives' visually audited set of 80; no novel image audit was presumed. The previous audit includes two JPGs of signed-in public MontrealAI workflow-dispatch UI with no account settings, tokens or notifications. Credential candidates resolve to source expressions, public token addresses, deliberately synthetic negative tests, package versions or masked Basic auth headers. No exposed credentials or private pages/settings were found within the described coverage. Candidate literals are omitted from audit.json. See audit.json, archive-entry-inventory.json and image-byte-matches.json for precision and limits. No archive content, product, browser, protected evaluation or held code was executed.

The 3805.88 seconds is the declared pytest test-run elapsed time only. Whole-CI elapsed cost, CPU, money, human effort and total engineering/QA costs remain unknown; no synthetic savings or profit is inferred. The raw JUnit elapsed field is separately preserved in final-run.json rather than substituted for the console summary.

To reconstruct only the archive in a new empty directory, copy its four parts and MANIFEST.json there, then perform ordinary byte concatenation and identity verification before any extraction:

```python
import hashlib, json
from pathlib import Path
manifest = json.loads(Path("MANIFEST.json").read_text())
archive = manifest["artifact"]
digest = hashlib.sha256()
size = 0
with Path(archive["archive"]).open("xb") as output:
    for part in archive["parts"]:
        path = Path(part["path"])
        assert path.name == str(path)
        data = path.read_bytes()
        assert len(data) == part["bytes"]
        assert hashlib.sha256(data).hexdigest() == part["sha256"]
        output.write(data)
        digest.update(data)
        size += len(data)
assert size == archive["bytes"]
assert digest.hexdigest() == archive["sha256"]
```
