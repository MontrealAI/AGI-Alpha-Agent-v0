# Frozen construction protocol v1

Status: supporting conventional software construction; not a transformational flagship.
Frozen before any generated geometry or baseline execution. Authoritative source
examples are CadQuery educational examples, not actual customer parts.
The three upstream source files and license are byte-identical to Git blobs at
8178185a24a035c9af7f4679033be14267f6a6ef; see SOURCE_MANIFEST.json.

## Scope
Manually extract nominal feature programs from Ex002, Ex003, Ex019. Construct
editable solids, STEP/STL/SVG outputs and nominal feature tables using one
primitive-based generator. Compare to the exact unmodified upstream programs
run with only show_object replaced by a no-op. Both arms use CadQuery 2.7.0 and
the same OpenCascade kernel. This is a geometry equivalence check, not a
matched frontier-model experiment and not independent physical validation.

## Prospective acceptance
For each case: exactly one valid solid; source-matched bounding dimensions;
source-matched nominal hole centers/types; analytic net volume within
max(1e-6 model-unit^3, 1e-8 relative); Boolean symmetric-difference volume
against the native reference within the same tolerance; STEP export/reimport
preserves solid validity, bounding box and volume within the same tolerances.
Fresh confirmation must be specified by a separate recipient after the feature
program and generator freeze; same-source reexecution is not fresh evidence.
Stop on input hash change, ambiguous unsupported operation, missing units for
production use, invalid solid, mismatch, or a correction that exceeds this scope.
Preserve original failure before an amendment. No metric is an estimated
physical manufacturing tolerance.

## Independent nominal expectations from inspected source
Ex002: centered 80 by 60 by 10 stock, centered 22-diameter through hole.
Volume: 80*60*10 - pi*11^2*10. Source comment explicitly says millimeters.

Ex003: centered 80 by 100 by 10 stock; four outer vertical corner fillets,
radius 2; center hole diameter 22; four holes diameter 2.4 through at
(+/-34,+/-44); top counterbores diameter 4.4 and depth 2.1.
Source executable rectangle is (80-12) by (100-12), so its corner centers
are 6 units from each stock edge. The comment calling 12 the edge inset
does not match that executable geometry; this discrepancy is preserved.
Volume: (80*100-(4-pi)*2^2)*10 - pi*11^2*10
-4*pi*1.2^2*10 -4*pi*(2.2^2-1.2^2)*2.1.

Ex019: centered 4 by 2 by 0.5 stock; four through holes diameter 0.125 at
(+/-1.75,+/-0.75); top countersinks diameter 0.25 included angle 82 degrees.
Countersink axial depth h=(0.125-0.0625)/tan(41 degrees).
Volume: 4*2*0.5 -4*pi*0.0625^2*0.5
-4*pi*h*((0.125^2+0.125*0.0625+0.0625^2)/3-0.0625^2).
Source does not specify physical units. Exporter uses millimeter-tagged
coordinates as a representation convention, not evidence of intended units.
Production remains blocked until a legitimate specification resolves units.

## Offering boundary
Deliverable: reusable nominal feature program, geometry, source provenance,
reexecution instructions and acceptance evidence. No material, tolerances,
feeds/speeds, machine program, physical inspection, machine release, customer
acceptance, paid demand, trained specialist, live ENS or Alpha superiority.
Same assets in an ordinary library remain a valid competing delivery.

## Attribution
Source code/license: CadQuery contributors, Apache-2.0. The source code was
manually read by an assistant to extract feature intent. This is not an
autonomous drawing/STEP interpreter. NIST drawings were investigated but
not used because they require model dimensions and the apparent missing-model
gap was historical. Existing AGI ALPHA PR #4980's evidence audit remains intact.
