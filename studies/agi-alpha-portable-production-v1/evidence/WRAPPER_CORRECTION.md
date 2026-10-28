# Supplementary verification correction

The first additive verifier accepted a report with empty case and negative-case
lists when its summary fields still claimed three accepted cases and six
rejections. The false positive, original verifier and original supplementary
report are preserved in `history/`. This did not alter the underlying CAD
results, but invalidated a claim of complete evidence checking by that wrapper.

Version 2 requires the exact frozen case IDs, negative-case IDs, check names,
boolean outcomes and reconstructed totals. It checks protocol, checker,
constructor, feature-program and source identities. Result directory and file
inventories must match, per-case recipes must equal the frozen requests, and
feature CSV rows must match the nominal recipes and their explicit unknown
material/tolerance and no-machine-release fields. All six known STEP outputs
were compared to regeneration using Boolean symmetric difference; all were zero.

Six retrospective probes reject empty evidence, an explicit failure status,
changed protocol bytes, changed constructor bytes, a missing case directory and
a changed output recipe. A separate subprocess using a changed protocol
returned exit status 1 and a FAIL report. One complete reproduction in a new
temporary directory succeeded. These are retrospective software checks and
semantic replay, not additional prospective scientific confirmation.

The archive seal was created after execution. It preserves seven historical
files and is explicitly not preregistration or an independent timestamp.
Frozen experimental source and reports remain unchanged. Missing/duplicate
feature identifiers, lost original parameter relationships, shared-kernel
limitations, absent customer acceptance and absent physical qualification
remain visible. Inputs remain trusted and frozen; this is not a hardened
service for external uploads.
