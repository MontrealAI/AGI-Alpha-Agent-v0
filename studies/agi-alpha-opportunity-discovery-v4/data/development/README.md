# Plate development evidence

This directory contains actual public NIST source artifacts in a compact ZIP, their individual hashes,
the one-part viability pilot, and the retained instrument's development request and compressed report.
It is development evidence, not protected confirmation or customer delivery.

From the repository root:

```sh
python studies/agi-alpha-opportunity-discovery-v4/data/development/prepare_inputs.py
python studies/agi-alpha-opportunity-discovery-v4/instrument/cli.py \
  --request studies/agi-alpha-opportunity-discovery-v4/data/development/request.json \
  --output studies/agi-alpha-opportunity-discovery-v4/data/development/report.json
python -m unittest discover -s studies/agi-alpha-opportunity-discovery-v4/instrument/tests -v
```

The input ZIP is distinct from the retained runtime closure. Expanded geometry/reference data is mounted
separately and is not claimed to fit inside or transfer with the two-million-byte capability bridge.
All actual incoming cylindrical features are matched only under the instrument's explicit mm/common-frame
profile. This does not establish revision authority or cross-provider feature identity.

`pilot_receipt.json` and `PILOT_REPORT.md` preserve the earlier scratch pilot. `report.json.gz` is the later
core's last Plate development report. `development_receipt.json` records checks and relevant outcome counts.
The `failed_candidates/` archive preserves the initial overbroad geometry-unit rule and its rejected report.
The report's rerun timing excludes the extensive research, construction, correction and evaluation work.
No paid job or earned collection occurred; this work belongs to additional research, not paid-job learning.

Source provenance:

- NIST–MTC archive: https://doi.org/10.18434/T4/1503154 ; SHA256
  `6bc4693f4b072116329decb0d07ac126eaaac86aa7c09e1276942279fbdb567c`.
- NIST STEP/QIF reference V2: https://doi.org/10.18434/M32146 ; SHA256
  `9ae303335274645f14d8ceacf56f8defd174271fd645308905f0395d82ef1085`.
- Exact QIF 2.1 unit schema: standards owner https://qifstandards.org/qif-2-1/ ; archive
  https://qifstandards.org/wp-content/uploads/2015/03/QIF-2.1.zip ; nested schema identity is in instrument/policy.json.

The NIST notices are retained alongside this file and in the compact source ZIP. Attribute NIST,
retain modification notices, and do not imply endorsement or use its logo. The original source bytes are
unchanged. The standards schema retains its own DMSC notice. New instrument code is Apache-2.0.
AI assistance constructed and checked the study artifacts; these are not autonomous customer discoveries.
