# Secondary recipient transfer: preserved input HOLD

The separately preregistered exploratory pair was Docker v27.5.1 → v28.0.0. It does not replace either primary transfer pair and is excluded from market calibration.

The recipient's already frozen raw-input gate (`swagger-spec-validator` 3.0.4) rejected the first document. The diagnostic was a required name (`UnpackedSize`) absent from the corresponding `properties` map under `ImageManifestSummary.ImageData`. The second document was not reached. The original, transferred full and transferred incremental arms were all **not run**. Their execution costs are null, not zero; the failed shared validation consumed 0.665432 wall seconds and 0.664342 CPU seconds.

No efficacy retry, source repair, alternative validator or third pair was attempted. Construction and transfer integration remain charged only once in the parent cost account.

A read-only adjudication compared the exact installed validator source with OpenAPI 2 §6.4.18 and JSON Schema Draft 4 §5.4.3–5.4.4. The particular required/properties subset guard is stricter than those normative semantics: required names need not each have a properties declaration when additional properties are allowed. This may expose an authoring inconsistency, but does not establish whole-document invalidity. The whole document was not independently adjudicated and the original HOLD remains unchanged.

The parent A/B/C/D experiment used its own frozen narrow structural acceptance contract and accepted all four outputs on 332 changed addresses. Those results and this recipient HOLD describe different acceptance preconditions. The HOLD is not evidence of donor inferiority, and the parent pass is not evidence that every recipient completed the work.

## Evidence

- `summary.json`: status, input hashes, nonexecution and retained failed-validation cost.
- `shared-raw-swagger-validation-receipt.json`: exact command, exit and timing receipt.
- `validation-adjudication.json`: source fragment, installed-tool source hash and primary normative references.
- `../cost-accounting.json`: construction/integration charged once; this failure added separately.
- `../../../outputs/secondary-transfer/campaign.json`: distinct parent acceptance record.

The original frozen source and wrapper were unchanged. Live Docker execution, customer acceptance, authenticated graph admission and paid collections were not performed.
