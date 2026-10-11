[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.26.2 — A welcoming homepage and a clear first step

**[Make your first plan](../start/index.html)** or explore the
**[homepage](../index.html)**. No technical experience, account, wallet, payment or installation is
needed for the first-plan experience. The [simple guide](ONBOARDING.md) is available in English and French.

## What changes

The homepage now introduces one useful task in everyday language. A purple-and-cream design,
readable spacing and a visible example help visitors understand what they can do before they begin.
Three short steps describe choosing tasks, reviewing a plan and keeping a copy. Plain-language
questions explain cost, privacy and what the planner does.

English/French and larger-text controls are visible at the top. Their choices follow the first-plan
link through `?lang=fr&text=large`, so visitors can continue comfortably. The page supports keyboard
navigation and narrow screens. The advanced workspaces, documentation, research and original
experiments remain available farther down the homepage.

The planner still compares all 16 combinations of four independent tasks to fit the available time.
It calculates a plan; it does not perform tasks or call an AI service. Explicit review is still needed
before saving. Text, JSON, readable on-page and printable copies remain available. The homepage
preferences need no account or browser storage; the planner's task entries remain only on the current
page until downloaded. Reloading clears them.

## Acceptance and delivery

Homepage browser acceptance runs against the generated site and the public deployment. It checks
language and larger-text controls, their handoff to the first-plan page, keyboard access, mobile
layouts, help and preserved advanced links. Reports must match the release commit and version.
Existing first-plan, runtime, contract, preservation, package and public-site gates remain required.

These are publication requirements, not a claim that an untested revision has passed. The published
`release-manifest.json` and matching validation archive identify the accepted commit and actual results.
Automated checks do not establish comprehensive accessibility conformance or replace usability studies
with older and nontechnical people. Browser coverage and hosting capacity retain their documented
[readiness limits](RELEASE_READINESS.md); no billion-user capacity qualification is asserted.

## Compatibility and recovery

This update changes the public entry experience and its acceptance checks. There is no native journal,
identity, contract or deployment migration. Original media, diagrams, research and demonstrations are
preserved. Use matching release assets and retain a verified private backup when upgrading a local
agent; see [operator recovery](OPERATIONS.md).

The [recorded Ethereum deployment](MAINNET_DEPLOYMENT.md) remains the historical deployment documented
in 1.26.1. Its deployed bytecode predates the current settlement fixes and does not change with a website
or software release. Participant commissioning, current-source review and any separately approved fresh
deployment retain their existing requirements. This release performs no on-chain transaction.
