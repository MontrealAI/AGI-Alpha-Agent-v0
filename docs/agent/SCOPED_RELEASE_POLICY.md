# Conservative release scope

This policy adds one operational scope, not a general impact-analysis engine.
An ordinary UTF-8 edit to `docs/CHANGELOG.md` can use the existing passive lane
without rerunning unrelated software jobs. Corrections, headings and Markdown
links are allowed. Both Git objects must remain ordinary non-executable files;
creation, deletion, executable modes, symlinks and invalid UTF-8 fall back to full
qualification. The existing 25 MB Git-proof bound still applies.

The policy compares complete exact Git trees and every introduced transition,
including side-branch history. A code change followed by a revert cannot hide
behind an editorial net diff. Unknown files, shared configuration, dependencies,
security, finance, authorization, runtime, build inputs, AGENTS instructions and
validation-policy changes retain full qualification. The classifier executes
only policy extracted from the pre-change base. If that base lacks this module,
including the introducing commit, classification falls back to full.

The versioned plan records exact source identities and planned actions, not
invented test results. Passive software checks and publication are explicitly
not applicable: no new software package, acceptance claim or source identity is
published. Pure editorial preparation defers before any site download or update.
It does not erase existing failures or certify an unqualified software baseline.
This document is not a service-worker cache asset and is never copied by the
paper overlay. A combined proved paper/editorial change retains the existing
immutable-paper, artifact, live-source and homepage checks; only approved paper
assets and their deterministic presentation can change the public site.

The compatibility workflow mode is still `paper`; the typed plan distinguishes
`passive-editorial`, `paper` and `full`. A plan alone never authorizes skipping:
consumers must derive it from the trusted Git proof. Omitted or altered fields,
wrong source identities, extra acceptance claims and coercible types are rejected
against the independently derived plan.

No component test evidence is reused by this slice. A later, separately reviewed
component catalog must identify complete source/test/lock/toolchain/environment/
hardware/build/policy inputs, authenticate the successful main/tag producer and
bind the immutable original run/attempt/source/artifact digest to the new source.
Unknown runtime image identity or changed closure must force fresh execution.
Current browser, container, security, finance, authorization and external-state
acceptance remains fresh. The initial deterministic MuZero substep pilot is not
enabled here and does not replace the broader component-selection work.
