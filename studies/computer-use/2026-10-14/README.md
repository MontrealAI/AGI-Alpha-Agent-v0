[Project notice](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md)

# Try the work — Evidence & Recovery Kit

**Show the work. Inspect the files. Reproduce the checks. Measure with real people.**

Start with `START_HERE.html` after downloading and extracting the kit. No account, wallet, model key or payment is needed for its two synthetic workshop examples. Do not enter private or customer information. The examples do not book, send, publish, charge or calculate taxes.

## 1. Try the actual deliverables

Open `02_Work_Products/Task_A/after/index.html` for Atelier North and `02_Work_Products/Task_B/after/index.html` for Studio Horizon. These are the original study's repaired applications, rebuilt byte-for-byte from its retained template. Read each `OWNER_BRIEF.txt` and `brief.json` to inspect requirements.

For a plain-language journey, open the kit's start page. Choose AI Foundations and 10 participants in A: CAD 445.50. Choose the design offering and 8 participants in B: CAD 433.50. These are study scenarios, not actual offers for sale.

## 2. Recover and inspect

Calculate an estimate, review it and download it. Save a recovery draft separately. Close the example. Reopen it in a fresh browser tab, choose the saved draft using the restore control, calculate again, inspect the result and review again before downloading. Restoration does not inherit approval. Unsaved work cannot be recovered. A checksum is neither identity nor encryption.

The deliberately defective `before/` applications and B's `without-portability-fix/` are comparison material, not recommended working versions. The latter reproduces one export defect in a context without Web Crypto; it does not represent six independent defects.

## 3. Reproduce rather than trust a summary

Use Python 3.11–3.13. In an isolated environment install `playwright==1.57.0` and its matching Chromium with `python -m playwright install chromium` (Linux may require the supported system dependencies). Set BROWSER_EXECUTABLE to the reviewed Chromium executable when needed. Installation may download software; the study tests themselves block external browser requests and make no model API calls.

From this kit directory:

```sh
python verify_and_replay.py --verify-only
python verify_and_replay.py --output /absolute/path/to/a-new-replay
```

From a source checkout, first run `python build_kit.py` to rebuild the application files and reader. The replay destination must not exist and must be outside the source kit. On Windows use a new absolute Windows path. The original harness is preserved; the new wrapper checks individual outcomes and fails on missing results or mismatches. Expected results: A 8/31 then 31/31; B 9/35 then 35/35; B with one fix removed 29/35; recovery 19/19; 105 SHA comparison vectors; five scripted owner runs per condition, 14 versus 11 controls. Expected failing variants remain visible.

A mechanical replay is not fresh model-generated work, independent scientific replication or human testing. The original harness uses supplied HTML in Chromium memory and test-only sandbox flags. Separately inspect hosted and local-file behavior in the publication acceptance record. Do not infer browser-independent support or production isolation.

## 4. Real-user evidence has not been collected

Read `PILOT_PROTOCOL.md` before recruitment. `pilot/status.json` has zero observed participants and null results. The blank measurement template contains no simulated users. A usability pilot on examples must not be presented as AGI Alpha generating work autonomously; the protocol has separate gates for that actual-repository evaluation.

## Contents and provenance

This is a new executable **source kit**, not the original 98-file PDF/Word/Excel archive. It includes 14 exact original source files, rebuilt applications, source hashes, a fail-closed replay wrapper, the published report, and prospective human-study materials. Fresh CI outputs are packaged separately from historical results. SOURCE_PROVENANCE.json identifies the supplied original archive and each retained source. SHA256SUMS records this kit's files. Existing research, contracts and agent permissions are unchanged.

Source code retains its notices; new publication tooling is supplied under the repository's Apache-2.0 license. Review the included LICENSE and source notices before redistribution. No remote fonts, trackers or model calls are needed to read the kit. GitHub and other hosting services still receive ordinary requests when you visit their pages.
