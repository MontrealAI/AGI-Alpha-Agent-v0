# Correction: The Next Upgrade companion archive

**The original companion ZIP is incomplete. Use the separately named corrected edition below.** This is a packaging recovery, with no new experiment, revised result, source edit or improved scientific claim.

## Corrected edition

- File: `AGIALPHA_The_Next_Upgrade_Companion_Corrected_20261026.zip`
- Size: **55,187,621 bytes**
- SHA256: `33e06fe9ac41d308c543a5f50974c7d88039d5cea8afe8d822ca6520614d6818`
- Entries: **1,873** (1,872 original manifest files and the unchanged manifest itself).
- Original manifest SHA256: `4dff312c85171687b61f57edd7af27921a8e9d8c1a143e91bac032a9179cf8c3`.
- Uncompressed entry bytes: **1,311,887,088**.

The temporary archive was completely closed and fsynced before atomic rename. Its central directory was read after close. The final archive was then reopened, passed `ZipFile.testzip()` with no CRC error, and all 1,873 entries were actually extracted into a separate verification directory and checked for exact recorded length and SHA256. A further independent process reopened the final path, checked the central directory and CRCs, and reconfirmed all 1,872 original staging files remained unchanged. This supports the corrected archive's integrity; it is not a re-execution of the research.

## Original edition and withdrawn completion assertion

The original `AGIALPHA_The_Next_Upgrade_Companion.zip` remains preserved, including its advertised size **54,175,529 bytes** and SHA256 `fedd0d11955345a3820e1f8d796a1b52e7fcfb5dd94ea1d016f43741e02232b2`. That exact file is an incomplete prefix of the corrected ZIP. It ends immediately after the 1,856th local entry, has no central directory, and omits 17 expected entries, including `COMPANION_MANIFEST.json` and the final support/test files. Python's `zipfile.is_zipfile()` correctly returns false for it.

The preserved original `AGIALPHA_Companion_Verification.json` reports 1,873 verified entries and zero archive errors for this incomplete file. **Those original completion and verification assertions are incorrect and withdrawn.** A matching advertised hash identifies bytes; it does not establish a usable archive. The precise process event that left the original prefix and its contradictory receipt cannot be established from the preserved records. No claim is made that a transfer, external owner or downstream tool caused the defect.

The original ZIP, original receipt, original manifest, prior public source identities, earlier editions and experimental results are preserved. The corrected archive supersedes the original ZIP for practical use under a new name and hash. It does not silently replace the historical artifact or change any study conclusion. The publication owner identified the defect in issue #4850, [comment 6419770074](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850#issuecomment-6419770074).

## Reproducible recovery and evidence

`rebuild_original_companion.py` reconstructs only the exact original inventory, refuses pre-existing output paths, checks source bytes before writing, closes and fsyncs the temporary ZIP, atomically renames it, and verifies actual extracted files. Original source and result files are read-only inputs. The exact invocation was:

```sh
python research/useful-work-v2/publication/v1-companion-correction/rebuild_original_companion.py \
  --source research/value-compounds \
  --original deliverables/AGIALPHA_The_Next_Upgrade_Companion.zip \
  --out deliverables/AGIALPHA_The_Next_Upgrade_Companion_Corrected_20261026.zip \
  --records research/useful-work-v2/publication/v1-companion-correction \
  --meter research/useful-work-v2/metering/prior-delivery-recovery.jsonl
```

A replay must use fresh output and extraction locations. The existing corrected edition must not be overwritten. `original-diagnosis.json` records every staging identity and every missing original entry; `corrected-verification.json` records every extracted identity; `independent-final-readback.json` records the subsequent fresh-process check. A machine-readable copy is delivered as `AGIALPHA_Companion_Correction_Verification_20261026.json`.

## Recovery costs

This work is charged to **Prior V1 delivery recovery; separate from V2 primary experiment**. Reconstruction and extraction verification used 13.913046665 seconds wall and 13.850331489 seconds process CPU. The successful diagnostic used 1.326029991 seconds wall and 1.322027292 seconds CPU; final readback quantities are in its separate record. The first diagnostic failed because an inspection assumed the source-freeze file map was a list; that failed attempt and its unmeasured resource cost remain recorded. Model/inference charges, researcher attention and monetary costs remain unknown. These recovery costs do not fund or burden the unrelated V2 tested capability's repayment calculation.
