# Source numeric boundary correction

Release review reproduced a false static CONFIRMED verdict on the integrated source:
the synthetic excerpt `high-side voltage of less than 34.5e+3 kVA`, clipped after
`e`, was treated as value `34.5` with an incompatible `e` unit. This is an authored
adversarial modification of an exposed fixture, not a quotation from the source
publisher or a new retrieved observation. The complete request, context, objection
and actual original verdict are in `prior-false-confirmation.json`.

Both separately implemented parsers now check the end of the number against the
complete original excerpt before accepting its unit. Numeric continuation or
unsupported exponent syntax cannot become a literal dimensional claim. Complete
plain decimals, existing separators and unknown units remain supported. The same
stored objection is REFUTED in `corrected-adjudication.json`.

This ports the numeric-boundary correction already proposed in PR #5018 onto the
current #5021 integration. It does not merge the older overlapping runtime or
change installed namespaces, package discovery, dependencies or execution authority.

The oracle declares protocol v5 and retains protocol v4 and the previous source
freeze verbatim here. The current default retained-AST freeze advances explicitly
to the corrected parser, protocol and current CLI source. All other source/input
identities are checked, including the unchanged sandbox. Historical results still
belong to their original commit and freeze; a new freeze is not a renewed Docker
pass or scientific confirmation. `source-verification.json` records actual separate
source/protocol admission and enforced write/socket denial for the corrected files.

Tests cover full/clipped e/E exponent variants and incomplete syntax, refusal to
construct a correction from an unsupported objection, valid unknown units and
guarded candidates. The default release suite collects those cases and a deadline
refusal check. Two earlier direct tests used the real wall clock and failed after
the inherited generation deadline; their setup now supplies an explicit pre-deadline
clock. The additional post-deadline test requires refusal before input reads or
output creation. The production deadline and generation allowance are unchanged.

These are exposed engineering regressions. No new generated candidate, discovery
advantage, commercial benefit, independent external certification or new scientific
confirmation is established. The retained-experience full-cost result remains
NOT_DEMONSTRATED. Exact final-head hosted checks and resulting-main release gates
remain required before publication.
