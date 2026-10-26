# Full evidence companion: packaging and portable reproduction

The companion is a **repository-shaped snapshot**, not a shortened paper appendix. It retains the complete study
source, protocols, public inputs and licenses, successes and failures, outputs, cost records, paper and bilingual
demo. The exact upstream Workbench runtime files from the primary source freeze are retained at their original
`examples/` and `docs/` paths, with the repository `LICENSE` and vendored Jobs license/provenance. Thus the original
relative imports resolve without changing frozen source.

## Full archive and separate publication review list

The complete ZIP additionally includes:

- GTFS validator 8.0.1 JAR at
  `studies/agi-alpha-work-discovery-v1/discovery/gtfs/tools/gtfs-validator-8.0.1-cli.jar`.
- The exact swagger2openapi 7.0.8 `package.json`, lock file, 411 regular installed dependency files and four
  contained `.bin` symlinks under `external-tools/swagger2openapi/`.
- The original Linux x86-64 oasdiff 1.34.1 executable, release tar and license inside the study.
- Public input archives and historical exploratory-source tarballs, including the unsuccessful trials.

The separate `review-files*.json` is a publication review aid. It excludes native executables, JARs and tarballs
while the full companion retains them. It distinguishes existing repository files from externally mapped converter
files. It does not publish, upload, stage or modify any source. Archive dependencies must not be inferred from that
smaller review list: use the complete manifest instead.

The following are intentionally omitted from both deliverables:

- Repository metadata, interpreter/formatter/typechecker caches and virtual environments.
- Browser binaries and development Python tooling installations.
- Temporary LaTeX build products and transient build stdout/stderr.
- Browser screenshots and PDF inspection page images used for internal visual QA. Their JSON QA reports and
  explicit omission records remain; publication figures and the final paper PDF remain included.

The builder inventories omissions by path and reason. Existing QA JSON may name an intentionally omitted image;
the omission is explicit and is not silently treated as a missing qualification check.

## Plan, release and build

From the study directory, using new filenames:

```sh
python publication/test_package_evidence.py
python publication/package_evidence.py plan \
  --plan publication/package-plan-final.json \
  --review publication/review-files-final.json
```

Planning verifies active source freezes, the external validator hash and the complete locked converter closure.
It hashes all payload bytes and checks safe archive paths, contained symlinks and extraction collisions. It executes
no producer, validator, browser, economic simulation or other job. Missing or changed dependencies fail the plan.

After the final paper and demo are accepted, the root creates a release record with this shape. The hashes must
come from the final plan; the record is a local packaging disposition, not a live identity attestation:

```json
{
  "schema": "agi-alpha.work-discovery.companion-release.v1",
  "status": "ROOT_RELEASED_FOR_ARCHIVE_BUILD",
  "plan_sha256": "SHA256_OF_EXACT_PLAN_FILE",
  "final_artifacts": [
    {"path": "studies/agi-alpha-work-discovery-v1/paper/main.pdf", "sha256": "FINAL_PDF_SHA256"},
    {"path": "studies/agi-alpha-work-discovery-v1/demo/index.html", "sha256": "FINAL_DEMO_SHA256"}
  ]
}
```

Then build and verify, without overwriting earlier artifacts:

```sh
python publication/package_evidence.py build \
  --plan publication/package-plan-final.json \
  --release publication/package-release-final.json \
  --output /ABSOLUTE/NEW/AGI_ALPHA_Flywheel_Evidence.zip \
  --receipt publication/package-receipt-final.json
python publication/package_evidence.py verify /ABSOLUTE/NEW/AGI_ALPHA_Flywheel_Evidence.zip
```

The ZIP contains `COMPANION-MANIFEST.json` and `COMPANION-RELEASE.json` at its root. Every payload member has its
original source path, portable archive path, type, byte count and SHA-256. The release binds the exact manifest and
final PDF/demo. The external receipt hashes the entire ZIP, avoiding self-referential checksums. Generated plans,
release records and final ZIPs are not recursively swept into the payload.

Archive paths never contain an absolute prefix, parent traversal, Windows drive, backslash or control character.
Unix symlinks are retained only when their targets remain inside the declared dependency tree and are also
manifested. Some ZIP extractors do not restore symlinks; the direct Node entry point below avoids relying on `.bin`.
The builder verifies the finished ZIP in place, without extracting or executing it. A failed partial archive is not
a qualified deliverable and must not receive a successful receipt.

The archive binds the captured repository base and source freezes. A later PR identifier or post-build replay
receipt is additive external provenance; it does not require rewriting frozen evidence or inserting a circular
archive hash into the archive itself.

## Installed prerequisites

The companion supplies source/data/tool payloads, not a complete operating system:

| Reproduction activity | Prerequisite |
| --- | --- |
| Workbench, skills admission, economic model, converter | Node; observed version v24.22.1 |
| Normalized-JSON comparator/oracle and package verification | Python standard library; observed Python 3.12.14 |
| Acquisition/production driver import and YAML normalization | PyYAML 6.0.3 in that Python environment |
| Canonical GTFS validator | Java; observed OpenJDK 17.0.20 |
| Bundled oasdiff executable | Linux x86-64; other platforms need the corresponding upstream build |
| Rebuild the paper | Compatible LaTeX and the paper builders' plotting dependencies; completed PDF/figures are included |
| Re-run browser QA | A separately installed compatible browser and automation package; static HTML works without the QA environment |

No Chrome binary, virtual environment, credentials, live ENS authentication, funded Jobs execution or financial
settlement is included or enabled. Existing local execution bounds and held operations remain in force.

## Original paths and portable mappings

Historical commands, working directories, runtime paths and stdout/stderr are preserved exactly. They describe
what ran during the study and are not rewritten to imply execution on the reader's machine. Apply these mappings
to a separate new command when reproducing:

| Recorded location | Portable location after extracting the ZIP |
| --- | --- |
| Original `.../agi-alpha/` | Extracted archive root |
| Original `.../agi-alpha/studies/agi-alpha-work-discovery-v1/` | `<archive-root>/studies/agi-alpha-work-discovery-v1/` |
| Original `.../research-inputs/gtfs-prototype/` | `<archive-root>/studies/agi-alpha-work-discovery-v1/discovery/gtfs/` |
| Original `.../research-inputs/api-baseline/tools/node_modules/` | `<archive-root>/external-tools/swagger2openapi/node_modules/` |
| Original `.../research-inputs/api-baseline/tools/package*.json` | `<archive-root>/external-tools/swagger2openapi/package*.json` |
| Original `/opt/.../python` | Your installed compatible Python with the stated dependencies |
| Original `/opt/.../node` | Your installed compatible Node |

The public source licenses remain at their original file locations. The MobilityData v8.0.1 upstream license is
also retained under `publication/licenses/`. The untouched JAR retains its embedded dependency licenses/notices.
The original `tr46` 0.0.3 package declares MIT in `package.json` but contains no standalone license text; the manifest
reports that absence, retains the original metadata and does not invent a replacement license file.

From the extracted archive root, the portable converter entry point is:

```sh
node external-tools/swagger2openapi/node_modules/swagger2openapi/swagger2openapi.js --help
```

From the extracted study directory, bounded checks use the included original source:

```sh
node --test --test-isolation=none tests/economics.test.mjs
node tests/schema-independent.test.mjs
```

The final package check is **one disposable replay of the development v25→v26 pair**, not an additional primary,
transfer or economic outcome. Use a new output directory, run each command under the existing 60-second cap,
and keep the replay receipt separate from the archived experiment records:

```sh
node src/run_service.mjs \
  inputs/discovery-docker-v25.0.0.json inputs/discovery-docker-v26.0.0.json \
  /ABSOLUTE/NEW/development-replay full
python tests/accept_dossier.py \
  inputs/discovery-docker-v25.0.0.json inputs/discovery-docker-v26.0.0.json \
  /ABSOLUTE/NEW/development-replay --receipt /ABSOLUTE/NEW/development-replay-acceptance.json
```

Do not replay into an existing evidence folder. Do not add replay results to the six-question primary denominator,
the transfer campaign or the 384-world economic campaign. A successful packaging replay establishes that the
included development path executes and passes its structural verifier in the stated environment; it does not
establish paid demand, live authentication, a new capability advantage or runtime/API compatibility.
