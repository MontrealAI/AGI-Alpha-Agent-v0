# Additive snapshot-reader patch

This patch adds two files only. It does not replace a publisher, change a security gate, or modify the original release/verifier implementation. The source helper is byte-identical to the development-selected retained reader. The adapters were executed against pinned original functions on commit `f836f06e8351e64db1da770e16e304b5feb01f28`.

Review/apply through the existing source owner. Explicit call sites may use:

```python
from scripts.foundry_snapshot_reader import read
from scripts.foundry_snapshot_adapters import committed_files, expected_workers
files = committed_files(root, exact_commit, read)
workers = expected_workers(root, exact_commit, exact_inventory, read, is_cache_asset, render_scripts, MAX_BLOB)
```

The paper adapter keeps mode `100644`, the original MAX_BLOB and renderer. The companion adapter preserves configuration-derived payload names and per-file bounds. Calls split at 256 paths. Total limits are the original per-file bound times the bounded chunk size; actual measured inventories are much smaller. The reader refuses its documented unsupported path forms. Do not silently expand its applicability; retain the original route or obtain explicit review for other inputs. Production integration, full platform/release qualification, merge and deployment have not been performed by this patch.
