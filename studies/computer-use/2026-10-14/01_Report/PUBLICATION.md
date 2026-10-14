# Publication notes

This directory publishes an editorial web edition of the 14 October 2026 advanced computer-use study. It is a report addition, not an agent release or a rerun of the underlying experiment.

## What is included

- An English/French visual reader with large-text controls, keyboard navigation and print styles.
- The reviewed English report in Markdown.
- Curated study results with the original protocol, all ten owner-workflow records, all nineteen recovery records, acceptance counts and source fingerprints.
- A generated portable `report-pack.zip` and `SHA256SUMS` for this edition.

The compact pack is not the original 98-file archive. The original PDF, Word, Excel, screenshots, application files and full reproduction harness are not included in this public edition. No broken or placeholder download for that archive is advertised.

## What has not changed

The study's measurements have not been reinterpreted as real-user savings. Its fixture defects are not described as repository defects. Its source-inspection baseline remains `8c027575c850bf5a872e6b11f81933b5e77b6be2`; its observed release remains a historical observation, not a current-status badge. No runtime, contract, wallet, production permission or model integration is modified by this publication.

## Maintain the edition

From the repository root, run `python scripts/publish_computer_use_study.py --build` after changing the report sources, then `python scripts/publish_computer_use_study.py --check`. The builder creates a deterministic ZIP and checks recorded headline values. Its optional `--link-entrypoints` flag adds idempotent discovery links without deleting existing documentation. It never deploys the website or changes a release.

Pages publication remains subject to the repository's existing release/Pages workflow. A merged report source is not proof of a successful public-site deployment. The publication workflow does not bypass those gates. A small MkDocs post-build hook preserves the raw Markdown downloads alongside the generated documentation pages.

## Trust

SHA-256 and ZIP checks detect differences against recorded bytes. They do not establish independent authenticity, correctness, participant identity or current operational authority. This public edition contains no credentials, payment request or execution authorization.
