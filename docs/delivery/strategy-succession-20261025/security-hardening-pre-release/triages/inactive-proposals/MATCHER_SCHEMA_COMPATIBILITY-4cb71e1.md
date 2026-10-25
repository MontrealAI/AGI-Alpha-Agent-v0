# Inactive matcher compatibility review

No map or approval was created. The observed matcher has `APPROVED_MAP_SHA256=None`; it does not currently clear any finding. The proposal remains evidence data, rather than the exact future map schema.

Mechanical checks of the actual 54-finding report confirm every start/end byte offset, line and column. **All 54 exact-span hashes differ from the full reported-line hashes.** Proposal `finding_snippet_sha256` corresponds to matcher `reported_lines_sha256`; matcher `snippet_sha256` must instead hash source bytes `[start.offset:end.offset]`. The identity now also requires `rule_start_byte` and `rule_end_byte`, alongside the exact raw YAML-definition hash and whole pack pin.

Actual selected-path SHA256 is `e529fd521525c901b6bf3db741a2680ffe6f680025a51ee15f8803812518024a` for the sorted 1,549 selected Python paths. The capture contains 1,550 entries because it also records `semgrep.yml`; that extra configuration must not accidentally enter the target-path digest. The final helper/test/matcher additions require a fresh final target digest and scan.

One substantive schema decision remains before activation: the current exact map binds target names and finding-file bodies, but does not bind other consumer-file bodies. A previously nonsecurity helper could acquire a security consumer in a different already-selected file while target names and all finding identities remain unchanged. Before/after captures ensure stability during that new scan, not equality to previously reviewed consumer context. This does not meet the proposal's explicit changed-consumer/source-inventory expiry condition by itself.

The integration lead and source owner have been informed. A reviewed finite content/dependency binding is needed, including an explicit treatment of the future literal map-pin self-reference. Policy code must not be silently excluded. The legacy `semgrep.yml` configuration also belongs in the context decision; unknown surrounding configurations must remain unqualified. This is an activation concern, not a current bypass.

The inactive matcher otherwise preserves raw findings/exit status, exact identities and one-to-one cases, whole-pack binding, and unknown/duplicate/missing refusal. The proposal supplies no independently approved `review_reference`; one cannot be invented during translation. No product, policy or test source was edited or executed in this compatibility review. Fresh frozen-source scanning and separate final review remain required.
