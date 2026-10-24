# Final raw-output seal

Reviewed approach for run `discoverability-20261022-v1`, 2026-10-22 23:12:28 UTC.

1. Finish all writes and close/sync `history.jsonl` before sealing. The runner already closes the history before writing its root.
2. Recursively enumerate every regular file in the selected completed output directory. Use sorted relative POSIX paths. Reject symlinks and paths outside the directory.
3. Read exact bytes; record byte length and SHA-256 for each file, including execution-source.json, report.json, history.jsonl, history-root.json, every raw load result, controls.json, conventional.json, sample-packs.json and restart-pack.json.
4. Write the seal outside that enumerated directory, or explicitly exclude only the seal itself and its separately recorded checksum. A manifest cannot include its own changing hash. Put any final ZIP outside the raw directory and hash it separately.
5. The manifest should include schema, runId, observation/seal time, executionSourceHash, sorted members with path/bytes/sha256, exact exclusions and scope. Retain the failed first run separately and include its files in the reconciled package manifest rather than overwriting them.
6. Verify both the file set and every byte identity. A changed, missing or unexpected file should fail verification; checking only listed files would miss unlisted additions.
7. Retain the seal's exact bytes and hash in the final public commit or another independently retained anchor. This supports later change detection. It does not authenticate the actor, prove the observations, establish independent review or imply immutable hosting.

Suggested shape:

```json
{
  "schema": "discoverability-output-seal/v1",
  "runId": "discoverability-20261022-v1",
  "sealedAt": "<observed UTC timestamp>",
  "executionSourceHash": "21925fa8a90337572cd6e4dbc5b652864fd05b8244837848784d8c2d7c8a42f8",
  "rootScope": "one explicitly named completed run directory",
  "exclusions": [],
  "files": [
    {"path": "report.json", "bytes": "<actual integer>", "sha256": "<actual exact-byte SHA-256>"}
  ],
  "claim": "Complete file inventory and exact-byte change detection relative to this retained manifest; no authentication or institutional acceptance"
}
```

The existing hash chain can remain summary-oriented. Its role is ordered event linkage; the complete file seal supplies raw-output byte binding. Neither replaces the other. The inspected amended runner checks the 13 supplied closure members and adds runner/reference; independent current static-import inspection confirmed all 15 source modules are covered. This establishes the current source set, not a general guarantee that future added imports will be discovered automatically.
