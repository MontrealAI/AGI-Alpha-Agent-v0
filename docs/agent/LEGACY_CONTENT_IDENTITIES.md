# Versioned legacy content identities

These changes harden three existing core components. They do not qualify the held
Successor Harness/bridge, Fleet operations, or general autonomous execution.

Memory Fabric uses `memory-content-v2:sha256:` identities over a domain, agent and
exact content. SQLite adds a nullable `content_id` column and unique index without
rewriting the legacy `hash`, content, timestamps, vectors or row identities. New
rows leave the old hash NULL. Exact legacy content remains readable and an exact
same-agent repeat is idempotent; distinct content or agents are not discarded by
an old SHA-1 identity. A conflicting strong identity raises `MemoryIdentityConflict`
and retains the existing body. RAM and the FAISS Python route compare full bodies.
SQLite migration, reopen, duplicate connections and conflicts were exercised with
controlled embeddings. Actual FAISS and PostgreSQL/pgvector were not qualified;
the PostgreSQL additive schema and conflict checks were not executed against a live
server. No providers, network databases or model downloads were used in these tests.
Do not point an old five-column positional-insert writer at the expanded table.
The tested rollback boundary is: stop and close writers, take a pre-upgrade
SQLite backup, and retain that snapshot. After upgrading and writing, stop writers
again and preserve a separate upgraded backup. Restore the pre-upgrade backup to
a separate database path before using the old five-column insert/read contract.
The fixed-SQL procedure test verifies that the pre-upgrade snapshot remains intact,
that the restored old writer can insert and read its own records, and that the
retained upgraded snapshot still contains both legacy and post-upgrade records.
Post-upgrade records are not automatically present in the restored old database
or adapted for the old writer. Keep the upgraded snapshot; reconciling those later
records requires a separately reviewed forward procedure. This is backup/restore
with two preserved histories, not seamless rollback or automatic reconciliation.

Patch Manager creates `archive-patch-v2:sha256:` IDs binding a domain, exact diff
and parent. Its atomic insert-or-compare operation stores the body and archive row
in one SQLite transaction. Identical retries retain the accepted timestamp, scores
and parent. Admission compares archive and body state in one committed read
snapshot, so a concurrent atomic commit cannot be mistaken for partial history.
Genuine partial or conflicting records are refused. Existing SHA-1 keys,
legacy JSON migrations, rows and ancestral links remain intact and readable.
No old IDs are relabelled. SQLite history, duplicate connections and conflict
refusals were exercised; generic archive APIs keep their existing behavior.

The existing self-evolution module creates `self-evolution-v2:sha256:` vote IDs
binding a domain, resolved repository, exact diff, baseline metric text and a
source fingerprint. The snapshot reads ordinary files only, excludes `.git`, and
limits each pass to 10,000 files, 20,000 entries, 64 MiB total and 8 MiB per file.
Symlinks, special files, unreadable or changing snapshots fail closed. Repository
content is hashed locally and is not exported by this identity helper. The source
fingerprint is checked again before recording/using votes and immediately before
copying an accepted patch. The proposal also passes its expected fingerprint to
`apply_patch`, which checks the actual copied base before applying any diff,
preflight or tests. A copied-base mismatch is cleaned up and refused even when
the original source changed only transiently during copying and was restored.
Direct legacy `apply_patch` calls without that optional expected fingerprint keep
their execution API and gain no new source-binding qualification.
Changed source causes abstention. Registry legacy vote
and threshold maps remain intact; no SHA-1 votes or unknown new-key votes become
authority for the new namespace. Conflicting body bindings are refused.

Tests mock patch application, preflight and test execution. They exercise fixed
local fixtures and source changes, not generated code, Docker or external actions.
This identity fence does not make the legacy copy/merge lifecycle crash safe or
safe against concurrent writers. Its broader lifecycle remains unqualified; use
an exclusively owned workspace. The bounded snapshot is a source identity check,
not proof that a patch is safe or authority to run it.
