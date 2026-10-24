# Main-source disclaimer and checkout correction

Source diagnosed: `197147ffd22c5ae13113162afffaf3ce9c10aa2e`, the actual merge of
PR #4869. The original failures remain recorded in Integration
[40053804836](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40053804836):
[blocking hooks / 120752269389](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40053804836/job/120752269389)
and [Windows / 120752269482](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/40053804836/job/120752269482).
This correction does not retry either failed run unchanged.

## Disclaimer diagnosis

All three new research guides already contain an actual anchor to
`../../DISCLAIMER_SNIPPET.md`. From their `docs/reports/<edition>/index.html`
locations, that resolves to the required `docs/DISCLAIMER_SNIPPET.md` notice.
The old validator only searched for that literal root-relative string anywhere
in the document; it rejected the working links and accepted an inert text
mention or comment.

The corrected validator parses anchors and checks their resolved destination:
the local source notice, its rendered documentation page, or either existing
canonical public notice URL. Comments, script text, non-link attributes, wrong
depths, other files, other repositories/sites and malformed URLs do not qualify.
Missing links still fail the CLI. An inert-byte source scan covers all 96
tracked documentation index pages, with no missing notice link.

## Windows diagnosis and precise limits

Every original raw Git HTML blob matches its catalogue SHA-256. The original
Windows failure reports the first mismatched path but does not print its
observed hash; its discarded checkout bytes are not available here. An isolated
Git checkout with `core.autocrlf=true` reproduces the mismatch without executing
any research or native code. The guide's 55 LF endings become 55 CRLF endings;
no other bytes change. The existing experience is also affected (94 endings).

| Catalogue-bound HTML | Raw Git bytes / SHA-256 | Reproduced CRLF checkout bytes / SHA-256 |
| --- | --- | --- |
| `research-foundry-v2/index.html` | 13,790 / `8135d15dc96bb160ec97a759e10474690c667c3f46f9c9c2b2aedbe0b9139509` | 13,845 / `6e56883a9350f85c1152d0a45969b600caf5c8951d303e2d33178dce944ec712` |
| `research-capability-inheritance-v1/index.html` | 13,584 / `58e2750c133dc8c5d1881238c9e5577361aed4c7eda95a7c6ff57cb5eeca4473` | 13,639 / `3f36423688e51a305ccc221a6f3254851e4e4bdb10816e1d312b6e5de6ae14d7` |
| `research-discoverability-v1/index.html` | 14,342 / `ef305f3a38babbf280b18726134fda379ad1b6ce4cc1e3328d7dc0128816ee57` | 14,397 / `c41c7c997545a0a71e3deb1fd1a9c3255a4f21ab23fbb2a0a15c0a24bb6a0b31` |
| `thermal-fluid-foundry-v2/experience.html` | 5,505,370 / `683061e042d72d360c95551939df67a45f8c7a04c9776055fbca126bcbf61a74` | 5,505,464 / `fc222ea2dc1ee9f549f6236b5252ee30dbb3380b50a5be1b80b3bda86e839e62` |

All paths in this table are beneath `docs/reports/`. Four explicit
`.gitattributes` entries now retain their LF bytes. The regression uses an
actual Git index and a fresh `core.autocrlf=true` checkout, comparing every
catalogued HTML resource against its unchanged authoritative hash. It fails on
the old attributes and passes on the correction. No hash reader normalizes
input or repairs the checkout. Catalogue identities, generator, HTML, original
PDF/TeX, frozen archives and historical evidence stay byte-identical.

## Qualification boundary

Focused local tests exercise the corrected validator and checkout contracts;
the full unchanged Linux/Windows and aggregate source gates still apply to the
final PR and resulting main. Scoped local tests use `--noconftest`, not the full
runtime campaign. Optional environment integrations are unavailable locally;
the offline environment check reports them explicitly. No full local
pre-commit or software release acceptance is claimed by this record.

The five-file held-native identity guard, its conditions and its accepted
bounded experimental coverage disposition are unchanged. All four excluded
outcomes remain unqualified. No held probe, Fleet/Harness review or merge,
browser-internal downloads-page inspection, financial action, credential or
security change is performed. Prepare-only paper run `40053804787` remains
separate from actual deployment and public acceptance. The accepted Alpha
1.39 / Jobs rc.20 / Manager 1.20.1 history is not a four-installed-product result,
and prospective Alpha 1.40 does not silently replace that compatibility input.

## Additional actual-main Agent failures

The same source's Agent run `40053804835` separately exposed release defects. They are corrected in this same existing lane rather than hidden by retries or unrelated research.

- `runtime (3.11/3.12/3.13)` fails `test_core_preserves_every_gallery_precache_dependency`. Exact source inventory identifies `research/discoverability/index.html` as the only precached path classified outside core. Gallery navigation HTML now remains in the core pack; a real pack/restore regression retains it when optional research packs are absent. Model-cache classification stays separate.
- `gallery (full)` fails exact Foundry guide identity in `validate_homepage.py`. The gallery's `insert_back_link` rewrites each new reading guide before MkDocs. The same finite generator-owned page preservation already used for portable workspaces now covers these three original guides, whose existing research-library links remain intact. Three actual-file regressions prove their exact bytes and catalogue hashes survive the gallery pass. No catalogue identity is changed or normalized.
- `dependency-audit` retains artifact `12544866489`, 2,143 bytes, SHA-256 `62f862dc9a79a6b6c16d37329c28c154d5332b7659cb37fc79be6891179aacc9`. The operator lock's 41 packages pass; the separate paper parser pypdf6.21.1 has three advisories, each fixed in6.21.2. The selected official6.21.2 wheel is407766 bytes and SHA-256 `1d44d1a3a200f25062adff0085b02040e4646431ac2ccac22e42679e91466084`; its exact wheel bytes are the lock commitment. Original papers are parsed and never rewritten. [Upstream patch](https://github.com/py-pdf/pypdf/releases/tag/6.21.2).
- `browser-contracts` retains artifact `12543908913`,16,397,683 bytes, SHA-256 `1a3286471313a1639e4a9292885ffa340dc8765090d000990aa64db6adc0ca27`. Its actual insight audit identifies fast-uri3.1.8 moderate advisories and serialize-javascript7.1.2 low findings. `npm update fast-uri serialize-javascript --package-lock-only --ignore-scripts --no-audit` changes ONLY those two lock records, to3.1.9 and7.1.4; package manifests and all other948 lock records are unchanged. Full and production-filtered package-lock audits now report zero findings without waivers. [Upstream fast-uri advisory](https://github.com/fastify/fast-uri/security/advisories/GHSA-w74x-v6f9-j3xg).
- `gallery (minimal)` retains an infrastructure failure: the bounded official installer times out while apt-get continues, then the existing single retry encounters its held dpkg lock. No lock is forcibly removed, no package manager is killed and no browser gate is waived. A fresh corrected-source campaign remains necessary.

Updated local qualification:248 focused cases pass under pypdf6.21.2, including original PDF safety/import cases, real pack/restore, guide/backlink identity and real Git checkout tests. Ruff/Black pass on six affected Python files; strict mypy passes on all three affected scripts. The initial broader local pack-test collection lacked the unchanged successor_evidence module; the sparse materialization was completed and the original failure retained. The local paper-audit install and its attempted invocation failed because disk was exhausted; no local pip-audit success is claimed. The unchanged hosted paper audit must pass on final source. Previous 8d7125bf PR checks/review remain tied to that earlier source and do not qualify this child.
