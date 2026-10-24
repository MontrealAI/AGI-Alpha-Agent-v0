# Publication integration handoff

**Prepared for the existing publication coordinator; shared workers remain unchanged.** These files are reviewable proposals, not deployment evidence. The complete scientific package and its PDF remain immutable.

The unchanged gallery generator at the scientific source pin `197147ffd22c5ae13113162afffaf3ce9c10aa2e` reproduced all three original service workers byte for byte from the complete selected input dictionary. Adding the two report HTML pages changes the selected asset count from 436 to 438 and proposes cache `agialpha-gallery-a67ed70b6eedb6ef` without changing release 1.40.0. The generated patch passed `git apply --check` and actual application in a disposable three-file fixture, with exact resulting hashes.

- [Proposed worker patch](OWNER_ONLY_GALLERY.patch): 3,036 bytes; SHA-256 `d07f464b87756e0efcb9e431a9e9f96d4746398040685f02fc8bc75be1192e6c`.
- [Detailed preparation receipt](OWNER_ONLY_GALLERY_RECEIPT.json): all verified source identities, selected HTML identities, baseline reproduction, retrieval limits, generated output identities and retained initial inventory stop.
- The generator selects the two HTML files but excludes the PDF, ZIP, TeX, replay JavaScript and these metadata files. This patch does not establish complete offline availability.

The pure `render_scripts(asset_bytes, release)` entry point received the exact complete tree-selected input dictionary. The disk-scanning CLI was not run. The detailed receipt records 442 verified input paths and 295 unique public blobs totaling 15,071,839 bytes fetched in memory. Large source bodies were not persisted. The scientific package, frozen files and shared source were not changed by this preparation.

## Receiving boundary

[Issue 4850, comment 6377105309](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6377105309) assigns acknowledgment, shared-index changes, qualified merge and Pages publication to the existing coordinator. [Release order 6379384418](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6379384418) leaves Writers 7–11 outside the current 1.41 release. The author does not apply this patch to the shared workers or claim any gate waived.

Before integration, the coordinator must confirm the actual receiving base and source-specific requirements. A changed selected HTML body, selected main-tree asset, generator, template, catalog release or original worker invalidates this patch and requires regeneration. Preserving the generator's outputs is only one qualification condition; normal gallery rebuild behavior, full repository checks, required review and live Pages acceptance remain separate.

## Current-base qualification and required preservation proposal

[Current-base compatibility](CURRENT_BASE_COMPATIBILITY_c627413.json) verifies that main `c6274131b3bfda4e3b8f8d3eb77cd11a35d9bf5a` retains exactly the same 436 selected asset identities, gallery-worker generator, catalog and three original workers as the scientific source pin. The worker patch remains applicable to those raw source bytes.

The normal gallery build has a separate obstruction: its unchanged backlink generator rewrites both new report indexes before generating workers. The [exact regeneration disposition](GALLERY_REGENERATION_DISPOSITION_c627413.json) records this behavior on private exact copies. The landing changes from 17,559 to 17,620 bytes and the demo from 34,136 to 34,200 bytes, invalidating the prepared HTML identities and corresponding worker digest.

A [minimal proposed preservation patch](OWNER_ONLY_MAINTAINED_REPORT_PRESERVATION.patch) follows the current maintained-guide convention and protects only these two exact report paths. It is 938 bytes, SHA-256 `d2ee0d403cece84010d753a37f155945cff493ea030b56f74470013e54709548`. Fifteen scoped checks cover the original rewrite, proposed byte preservation, unrelated and lookalike paths, existing maintained-guide behavior, and exact private patch application. These checks do not replace a complete site build or repository CI.

**Both proposals remain unapplied.** The existing coordinator must review and admit any shared generator change before using the worker patch and must rerun applicable whole-source checks on the actual receiving base. These proposals do not alter the final scientific archive or clear the release exclusion.
