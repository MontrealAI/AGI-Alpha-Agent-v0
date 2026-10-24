# BLOOM public evidence export

This publication contains a credential-free public evidence export. Original local files and authenticated backup archives are preserved privately. The scientific observations, native execution receipts, source freeze and analysis are unchanged.

## What is omitted and what is renamed

20 direct identity.key/api.token files are omitted. Five native recovery archives and the all-attempts archive have new filenames ending in _PUBLIC_EXPORT.zip. Nested recovery archives are recursively sanitized and renamed as explicit public variants. 28 credential archive entries are removed, counting duplicated nested copies.

PUBLIC_EXPORT_MANIFEST.json maps each original archive path and SHA-256 to its public variant path and SHA-256, records removed entry names and counts, and documents config/SQLite inspection. No credential value or digest of a standalone secret is printed in the manifest.

The preserved native receipts still describe the original historical runs, original backup names and original backup hashes. Those receipts have not been edited to describe a different archive. Use the export mapping to locate the public history variant. A historical backup hash must not be claimed as the hash of the public variant.

## SQLite and configuration

Retained SQLite databases have an events table with seq, mission, body, hash and signature columns. Internal scans found no removed credential bytes or their hexadecimal/base64 encodings in retained databases/configs. Configuration contains an environment-variable reference rather than a model credential, has no URL userinfo, disables remote-model calls and has no chain configuration. Original database/config bytes are retained unchanged. Public signatures and identity identifiers are evidence, not secret signing keys.

The sole permitted source match is an explicitly documented deterministic PUBLIC TEST/FIXTURE token literal in unchanged frozen integration/native_workflow.py. This is a source-defined local test value, not an operational credential. Private journal identity.key/api.token files are still omitted even when a run used deterministic fixture material.

## Restoration and a working recovery path

**The sanitized historical archives cannot be supplied as complete authenticated inputs to Journal.restore.** They omit signing keys and local API tokens. They retain inspectable history, configuration and provenance; they do not confer identity, active proof or authority.

To exercise actual local backup and stopped restoration, run the unchanged frozen demonstration in a fresh directory after installing its documented prerequisites:

    python3 demo.py --case public_case/case.json --method expert --output runs/public-demo

The demo regenerates local test-only identity material and produces a new original-format backup that it actually restores in stopped/paused form. Keep newly generated identity.key/api.token files and complete backup ZIPs local. To share its history, apply the public-export rule again. Source/package environment, policy, artifact conditions and current authority must be revalidated; historical proof is not inherited.

## Packaging rule

Apply PUBLIC_EXPORT_PLAN.json to the study root: omit all exclude_exact_paths; add each variant_file under include_public_path; copy remaining selected scientific/source files without alteration. Add this document and the export manifest. Do not copy a private original ZIP under its old filename, do not silently replace original archive bytes, and do not retain credential files in a second nested archive.

No remote publication, transaction, credential rotation or security configuration change is performed by this export. It changes only newly created public copies.
