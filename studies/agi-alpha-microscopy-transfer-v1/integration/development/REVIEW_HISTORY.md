# Retained input-review history

The first source inspection identified a time-of-check/time-of-use gap: a file
hash was computed before a separate mutable NumPy mmap was loaded. It also
identified that `.npz` input would return an archive object and reach an uncaught
attribute access. The implementation owner repaired both before the reviewer's
first directed probe finished. These initial issues are source-review findings;
this record does not assert that the old source was executed by the reviewer.

`input-review-v1` retains the corrected source `2ec5db05391950239cbbe6753cb91b1b19822304a8b4766fcfc151b5ae72db7c`.
Its old digest-hook injection was not reached by the corrected snapshot loader.
The report's unchanged on-disk hash makes that weakness inspectable. Its NPZ
input was correctly rejected. This is not a successful race-injection test.

The reviewer then changed the probe to replace the file immediately before
NumPy reads its input argument. The corrected program supplies owned BytesIO,
so the source path can change while measurements and source digest remain bound
to the original snapshot. Version 2 adds ten input/meaning refusals and signed
nonzero-label acceptance; all 14 probes pass on its preserved source.

Separate review found an uncaught empty-file EOF, the need to bound declared NPY
shape before allocation, and browser-JSON label identity beyond exact integer
range. The owner corrected these before freeze. Version 3 adds a JSON-unsafe
label HOLD and a tiny oversized NPY header refused before an allocation sentinel.
All 16 probes pass on source
`a04326ce0504bfe3ac290b6cb65ee6f089cc66a607f70b7cc7869099250c77db`.

All probes use synthetic 3x3 arrays or a tiny header. No confirmation specimen,
external file, chain, wallet, paid model, or production endpoint is accessed.
These tests demonstrate specified local behavior under the recorded source;
they are not hostile-host isolation or biological validation.

Two initial strict-typing checks on the review driver found only NumPy typing
annotations/casts missing. Their straightforward annotations were added without
changing the measured instrument or the recorded test inputs. Native adapter
source assertions and all original/corrected result directories remain intact.
