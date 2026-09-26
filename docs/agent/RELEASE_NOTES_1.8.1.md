# Version 1.8.1 — Accessible experiment resets

A final live review found that switching scenarios cleared the Compounding Lab chart visually while
leaving the previous prediction in its screen-reader description. The chart now resets its accessible
description whenever the associated run is cleared, including when costs change.

Real browser acceptance checks both paths on the minimal gallery, full gallery and published HTTPS
site. Current package metadata, gallery versions and operating guides identify 1.8.1. The changelog
also records the final-manuscript release.

This patch preserves the 198-page manuscript and all 1.8.0 behavior: A-only learning, frozen capabilities,
four measured future-task arms, negative controls, cost accounting, explicit review, complete Evidence
Dockets and exact Python/JavaScript replay. Existing evidence and native journal formats remain compatible.

The full release pipeline reruns against the patch commit before publication. The release manifest and
validation archive contain its results; previous release assets remain immutable. Repository branch
protection still requires the administrator action documented in [release readiness](RELEASE_READINESS.md#repository-administration).
