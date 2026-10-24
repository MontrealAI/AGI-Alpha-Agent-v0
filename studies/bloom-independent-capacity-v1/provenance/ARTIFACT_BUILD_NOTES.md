# Artifact production notes

Scientific code, thresholds and outcomes were not changed during publication. All24finalPDFpages were rendered and inspected; cover overlap, a quotation, punctuation, interrupted text and reproduction directory examples were corrected before finalreview. Two forced builds reproduce the exact final PDF bytes.

The workspace and sharedRAM reached capacity during production. Only owned already-persisted checkpoint copies and recreatable render caches were removed. No scientific raw result was deleted. A log write failed with ENOSPC; the exact PDF hash remained unchanged.

An initial local assertion rejected every PDFOpenAction. Inspection showed a benign internalGoTo to the first page/Fit, explicitly permitted by repository policy. Final local structural checks admit that navigation; the required pinned repository validator remains NOT_RUN_DEPENDENCY_MISMATCH.

Automatic approval review rejected the initial public-archive construction before execution because older local test journals contain signing-key/token files. The final publicexport omits20direct credential files and recursively removes28archive entries, with6explicitly renamed direct backup variants. Unchanged historical receipts retain their original backup hashes. PUBLIC_EXPORT.md and the export manifest explain the inspection-only variants and actual local restoration via the unchanged demo. No privatekey/token bytes are intentionally published and no credential rotation or security setting was changed.

HTMLbrowser rendering was unavailable. Syntax, embedded data and source-link checks passed; deployed-byte verification was not claimed. Required external review, full qualification, qualified merge and Pages verification remain separate.
