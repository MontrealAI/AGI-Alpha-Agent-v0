# Independent recipient, before transfer

This source was frozen before reading donor or other baseline implementations. It reconstructs a declared Swagger 2 GET/2xx JSON response structural inventory using ordinary Python, standards and public tools. It is an already capable recipient, pending independent completeness assessment; file absence was never taken as a capability gap.

The exact bounded construction interval is **348.622070 seconds**, from 2026-10-26T20:51:37.235267Z through 20:57:25.857337Z, within a 1,200 second allowance. This is observed agent-session wall time, includes some GTFS context switching, and is not a measured human labor requirement or a known model bill. Input acquisition was shared upstream. Validator installation CPU and inference tokens/dollars are unknown. Construction is charged once.

## Reproduce

From this directory, run `python recipient_inventory.py ../../inputs/discovery-docker-v25.0.0.json ../../inputs/discovery-docker-v26.0.0.json --out result.json` and `python check_recipient.py`. The inventory uses only the Python standard library. Separate original raw-input validation used public `swagger-spec-validator==3.0.4`; install the pinned validator in an isolated environment and call `swagger_spec_validator.validator20.validate_spec(json.load(...))` on each original source. Both originals passed.

The public oasdiff 1.34.1 raw-Swagger diff returned status 0 but is invalid as the practical comparison: its validator rejected the input with 105 errors (482 findings total), because this tool supports OpenAPI 3, not raw Swagger 2. The full failed public-tool output is retained. A correctly converted oasdiff alternative remains a strong comparator.

Construction output: 2,408 old and 2,413 new schema nodes; six changed addresses (one Created declaration and five Subpath additions); nine explicit scope exclusions each. 34 construction assertions passed. Source pointer/fact audit passed; it checks emitted evidence, not completeness. Ruff and strict mypy passed. These checks are construction evidence, not fresh transfer evidence.

Recorded source and evidence hashes are in pretransfer-freeze.json. Frozen source bytes are unchanged in this copy. Receipt command paths refer to the original invocation working directory and are retained as observations; the reproducible invocation above is portable. No dependency vendor directory is copied.
