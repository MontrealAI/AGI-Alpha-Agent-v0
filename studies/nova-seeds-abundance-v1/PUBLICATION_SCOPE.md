# Publication scope and receiving boundary

This Writer #10 proposal is confined to `studies/nova-seeds-abundance-v1/`. It publishes an immutable, complete research archive and directly readable paper, figures and selected evidence. The experimental implementation is source material inside that archive; it is not admitted into the repository runtime.

## Frozen study and publication layout

The canonical 20-page PDF, standalone TeX, complete ZIP and all archived payload bytes are unchanged. The ZIP contains the full implementation, pinned source, licenses, protocol, raw records, adverse results, bibliography, figure-generation source and reproduction guides. `ARCHIVE_MANIFEST.json` inventories the extracted archive, not this smaller publication directory.

The original fully unpacked review witness remains publicly readable at source commit `afcdeedd7d7e744cd09d0d4280a4f0f9537c2ee8`. Its hosted Ruff check reported 109 style findings in nine newly introduced Python files. The publication layout removes those loose frozen implementation copies and retains their exact bytes in the canonical archive. This does not correct their style findings, establish archived-code lint conformance or erase the failed check. `HISTORICAL_LINT_FAILURE.json` preserves the recorded diagnostics.

No Ruff configuration, exclusions, workflows, source predicates or required gates change. Introduced history and the current study namespace remain outside the passive paper-only allowlist. The corrected publication head must receive the normal full qualification and review. Scientific verification and custody checks are distinct from repository integration acceptance.

## Reproduction and transport

The public connector has a 16 MiB request-body limit. Two consecutive archive parts preserve the complete ZIP byte for byte. `python ASSEMBLE_ARCHIVE.py` verifies both parts and reconstructs the original ZIP; `README.md` then extracts it into a new directory before running any scientific command. The canonical PDF inside that ZIP is the original compiled edition.

Canonical PDF: 480978 bytes, SHA-256 `405a7f2fdd6d5e3929f9eeb263499a36613d9cc26ecedcc059d113f6c1b3eaf9`.

Canonical complete ZIP: 15317764 bytes, SHA-256 `b8785b08bf0a7d66e50dd28a5729e25705579a8774feb55aa02427710d2dba51`.

Before public upload, the private backup was reopened and all 343 payload digests verified. The separately saved PDF received passive provenance metadata; the public PDF and archive retain the canonical original bytes. Every final PDF page was rendered and inspected. All physical instrument outcomes are simulations.

## Receiving, review and release ownership

Issue #4850 comment 6377105309 reserves shared catalogue, merge and Pages publication to the existing coordinator. Comment 6379384418 excludes Writers #7–#11 from the ongoing software release. The final artifact set and current-main receiving base still need acknowledgement.

This proposal changes no shared catalogue, homepage, service worker, workflow, production authority or historical publication URL. It does not retry held Fleet/Harness objectives. Source-branch accessibility does not establish qualified merge, research-release attachment or live Pages publication.

The coordinator can receive the unchanged PDF and standalone TeX through the existing passive-paper importer and separately review the complete source archive. No archive, scientific-test or PDF-parser receipt waives the applicable review, hosted-check, exact-main release or served-byte acceptance gates.

