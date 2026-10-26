# Public practical case: package dependency impact

This fixture asks a concrete maintenance question: **which public package build
roots have a declared dependency path from a changed locked package?** It uses
the Alpha web client and AGIJobManager inventories. The input is public and
nonpersonal; each dependency path is inspectable against exact declarations.

This is a practical acceptance example, excluded from development selection,
confirmation, and independent reproduction statistics. It does not establish
that a package change breaks a build, that selected tests are regression safe,
or that an operator has a prospective performance advantage.

## Reproduce

From the `bloom_study` directory:

```sh
python3 public_case/acceptance.py --check
```

The command checks source hashes, reconstructs the canonical graph, verifies
every dependency resolution using Node's native ancestry algorithm, and
recomputes the independent BFS and exhaustive cover reference. It prints `PASS`
or a readable error and exits nonzero on failure. It does not install or run
locked packages, execute repository scripts, access a network, or submit work
externally. It requires Python and Node with no extra packages. The captured
execution used Python 3.12.14 and Node v24.19.0. Runtime version differences are
reported and do not invalidate equal structural results.

To rebuild outputs after intentionally changing fixture code, run
`python3 public_case/parser.py` and then `python3 public_case/acceptance.py`.
Different source bytes require a new reviewed source receipt. A stale receipt
is an error, not permission to silently accept new packages.

## Input and observable outcomes

| Quantity | Value |
|---|---:|
| Locked package locations, including two roots and one local source target | 1,136 |
| Unique dependency → dependent edges | 2,000 |
| Package-manifest build roots represented as applications | 2 |
| Fixed change queries | 17 |
| Unresolved peers, all source-marked optional | 16 |
| Explicit local-link edges | 1 |
| Synthetic coverage options | 3 |

The roots are `agi-web-client` 0.1.0 and `agijobmanager` 1.20.1. Their install
contexts are distinct. Nested versions and scoped names retain exact locations;
packages are not merged merely because their names match.

A change to `vite` has a direct declared development dependency on the Alpha
root. A longer inspected path is `@babel/parser` → `@babel/core` →
`@vitejs/plugin-react` → `agi-web-client`. Every edge has a source receipt in
`acceptance.json`. Manager's local link is `ui/vendor/zod` → `node_modules/zod`
→ `agijobmanager`. No cross-project dependency is asserted.

The primary query changes `alpha-web::node_modules/vite`. The independent
reference finds the Alpha root affected and an illustrative cover of weight 7.
A combined `vite` and Manager `solc` query affects both roots and has an
illustrative cover of weight 10. The no-change query affects neither root and
requires no successor cover.

The three options are **synthetic coverage labels with strictly positive
weights**: Alpha 7, Manager 5, both 10. They are not executable tests, measured
coverage, durations, fees, cash savings, or economic opportunity costs. The
reference outputs supply expectations for downstream candidate comparison.
Actual operator qualification and compute cost belong to the main demo run.

## Exact sources

Raw bytes came from a public GitHub read connector and match the recorded Git
blob SHA1 and SHA256. No repository was cloned and no package was installed.

| Repository and source | Pinned commit | Role |
|---|---|---|
| [Alpha web package lock](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/dfc79c4ae81ac612cbff9865a0af8389b6ff3de9/alpha_factory_v1/core/interface/web_client/package-lock.json) | `dfc79c4ae81ac612cbff9865a0af8389b6ff3de9` | Graph input: 901 entries |
| [Manager root package lock](https://github.com/MontrealAI/AGIJobManager/blob/c5958eae872458c2f3cac48fea0b4bbfadc6ac6c/package-lock.json) | `c5958eae872458c2f3cac48fea0b4bbfadc6ac6c` | Graph input: 235 entries |
| [Jobs root package lock](https://github.com/MontrealAI/AGIJobsv0/blob/9983478d42c32fe399f28dd9b0e0173f904b8a11/package-lock.json) | `9983478d42c32fe399f28dd9b0e0173f904b8a11` | Verified source only: 2,605 entries |

Jobs alone exceeds the 2,000-node practical-case envelope, so its preserved
snapshot contributes no graph edges and implies no contract/runtime execution.

## Resolution and limits

The parser resolves ordinary, optional, and peer declarations to the nearest
matching `node_modules/<request-name>` location in each project's ancestry.
Root development dependencies are included for build scope. Transitive package
development dependencies are omitted; none occur in these two snapshots.
Optional declarations override same-name ordinary declarations and peer
optionality is retained. A local link contributes a target-to-link edge; its
target's declarations resolve from that source location.

The independent JavaScript check uses the installed Node runtime's
`Module._nodeModulePaths` to reconstruct all 2,016 resolved/unresolved records.
This private helper is a bounded verification reference, not a production
interface. The independently reconstructed edge set must equal the case graph.
The separate Python `independent/reference.py` supplies reachability and
exhaustive subset-cover expectations.

The result is a **static declared dependency inventory**. Platform variants are
included without evaluating OS/CPU/engine conditions. It does not evaluate peer
semver satisfaction, conditional exports, package self-reference, bundler
aliases, dynamic imports, generated files, native build steps, or
`preserve-symlinks` variants. Missing peers remain unresolved. Lockfiles alone
cannot establish a complete build or runtime graph.

Production change-impact use needs an actual installation, source/import/build
analysis, measured project test coverage, and accepted real outcomes. Restore
does not provide runtime trust, authority, or deployment credentials.

## Evidence

- `raw/` and `source_receipt.json`: unchanged snapshots, URLs, commits, Git
  identities, byte counts, and SHA256 checks.
- `case.json`: the study API input.
- `graph_audit.json.gz` and `audit_manifest.json`: losslessly compressed canonical
  node/edge/missing-peer records with both stored and uncompressed-byte hashes.
- `parser.py`: deterministic converter with source hash verification.
- `verify_node_resolution.cjs`: independent native-ancestry structural check.
- `acceptance.py` and `acceptance.json`: revalidation command, expected outcomes,
  traced paths, source/code hashes, and observed runtime versions.

The audit is gzip-compressed to conserve space. Its decompressed canonical JSON
SHA256 is `b825d1c3b269d5b510440df56bada259eace3a8934f8485a0ab0a710c756e55b`,
identical to the initially generated uncompressed audit. No declaration was
dropped during compact storage.
