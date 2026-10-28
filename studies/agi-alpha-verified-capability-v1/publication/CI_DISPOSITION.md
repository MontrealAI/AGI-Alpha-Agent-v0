# Hosted CI disposition and publication source overlay

PR4942 remains a draft and is not eligible for merge or release. Hosted run40393144646 passed its full smoke checks but failed Ruff0.12.5 with115findings in the newly added study. Of these,78occur in four files fixed by both scientific source manifests. The existing release policy keeps these findings blocking; no exceptions or scope reductions have been added.

The37findings in the unfrozen paper/build.py have been corrected under the unchanged repository policy. Its AST is identical after ignoring locations and two unused assignment-name changes; the right-hand-side operations remain. Scoped lint, formatter and Python compilation pass. No paper builder, production or simulation was rerun. This does not claim a new full hosted pass.

The original companion remains immutable at SHA256 9dd3d4defbef15c6b66f9559e1778fa596d729d35dcb4689ff3a6cdc770776e0. Its original builder created the delivered21-page PDF, and the original source also remains available at commit a98276d09f92f5ef9dafe8c63c360296d1e1448d. The current public source differs only by this unfrozen publication-source overlay and its disclosure. The primary193-file and market194-file freezes remain byte-identical.

See lint-correction-01.json and paper-build-lint.patch for exact original/corrected identities, diagnostics, AST/compile/lint evidence and known limits. The public review manifest distinguishes the corrected builder from its original companion identity. Resolving the remaining78requires a separately reviewed successor-source or compatible preservation disposition; this contribution does not waive the gate or rewrite frozen evidence.
