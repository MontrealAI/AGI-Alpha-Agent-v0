# Whole-context scheme assessment

The proposed scheme closes the previously identified consumer/configuration expiry gap in principle. This is a design assessment, **not implementation qualification, map approval or activation clearance**. The matcher remains inactive; fresh final source, tests and separate review are still required.

Independent Git metadata at `4cb71e1e6eee4aba807aaa7035b950661bfe48fd` confirms 4,932 regular blobs, 268,890,313 total bytes and a largest body of 25,068,614 bytes. These fit the proposed 10,000-file / 64-MiB-per-file / 512-MiB-total limits. No archived body or held request was executed.

The accepted design scope is all tracked repository content, including Python consumers, JS, shell, YAML, other configuration and legacy `semgrep.yml`. A deterministic cross-run record needs sorted canonical path, Git mode, effective content length and SHA256. Within-run device/inode/time observations remain separate from reproducible content identity.

The two self-reference treatments must remain exact and explicit:

- Only the fixed map file's content is excluded from the context root; it must remain tracked, regular and separately bound to the literal approved SHA. Path/mode/presence and any recorded metadata remain checked.
- Only the matcher's single exact top-level `APPROVED_MAP_SHA256` literal value is normalized to `None`. Reject multiple, computed or ambiguous assignments. Preserve every other byte. The inventory must use the normalized effective matcher length/hash, or an explicitly reviewed equal-length placeholder construction, so length does not reintroduce a cycle. Retain actual raw hashes separately as evidence.

Normalization deliberately cannot detect a coordinated change of both the map and its excluded literal pin. Those are security-criteria edits and must remain outside candidate authority, independently anchored to approved source and required review. The context root is not a replacement for that approval anchor.

Implementation tests should reject changed consumer/config/JS/shell bytes, modes, path additions/removals, unknown/nonregular entries, map absence/pin mismatch, duplicate or computed pin expressions, changes around the normalized token, bad committed HEAD masked by safe index/worktree overlays, source drift, and budget/partial-read failures. Bind inventory selection/modes and actual bodies to the committed source being qualified; fail closed rather than silently omitting inaccessible content or policy code.

No other matcher bytes or source paths may be silently excluded. No data proposal is active, and no prior source observation authorizes a future source or pack combination. This review changed no product, policy or test code and performed no target import, native execution, financial or remote action.
