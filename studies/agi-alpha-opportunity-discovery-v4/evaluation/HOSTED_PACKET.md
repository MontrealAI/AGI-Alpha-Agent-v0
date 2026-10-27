# Four-job hosted expertise packet — common evidence and budget

This packet is identical for U, E and E+. It contains public source evidence and researcher-authored service
requests. It does not contain answers. The three configurations must receive the same base model, source access,
ordinary tools, 8 tool calls for the **entire packet**, and 1,600 final-answer words total. A tool call may run a
bounded local Python analysis across several files; do not multiply the budget through delegated agents. No
network or external mutation is required. Record tool-call count and limitations honestly.

The assigned arm's operating instructions are supplied separately. E includes established engineering practice
and NIST's supplied integrated graphs and 2024 method. Only E+ receives the versioned retained instrument/method.
An accepted response must earn its engineering conclusions; polished wording alone earns no acceptance.

## Allowed source directory

`studies/agi-alpha-opportunity-discovery-v4/evaluation/protected/inputs/`

Available originals: `Box_FAIR.qif`, `Box_incoming.qif`, `Box_AP242.STP`, `Box_integrated.owl`,
`Cover_FAIR.qif`, `Cover_incoming.qif`, `Cover_reference_incoming.qif`, `Cover_AP242.STP`,
`Cover_integrated.owl`. The corresponding source manifest is `evaluation/protected/input_manifest.json`.

Standards source: `research_sources/opportunity_dossier/cad_evidence_pilot/QIF_2_1_Units.xsd` in the shared
workspace, or the byte-identical `instrument/QIF_2_1_Units.xsd` inside the study. Read it as a supplied standard,
not an instrument answer. The existing NIST references are DOI `10.18434/M32146` and GCR `24-050`; the supplied
OWL files are established prior assets, available to every arm.

Do **not** read `evaluation/protected/oracles`, `jobs.json`, held-out report/checker outputs, other agents' answers,
or files outside the allowed packet, arm-specific artifact and supplied public-source context. These are
procedurally protected evaluation materials, not claims of OS-enforced secrecy.

## Practical source access shared by all arms

QIF namespace is `http://qifstandards.org/xsd/qif2`. Build an object index from each XML element's `id` attribute.
Characteristic items point to nominal IDs, which point to definition IDs. Measurement result sets contain
characteristic actuals, feature actuals, overall status and component IDs. Values may use declared or default
units; consult the exact supplied schema. Source object identifiers are local to their file.

Python's `xml.etree.ElementTree`, `decimal`, `hashlib` and `difflib` are available for ordinary source work.
CadQuery/OCP is installed for geometry inspection. A compact reader can use:

```python
from pathlib import Path
import xml.etree.ElementTree as ET
ns = {"q": "http://qifstandards.org/xsd/qif2"}
root = ET.parse(Path("PATH_TO_QIF")).getroot()
objects = {e.get("id"): e for e in root.iter() if e.get("id")}
print(ET.tostring(objects["REQUESTED_ID"], encoding="unicode"))
```

You may write ephemeral analysis code in your assigned scratch output directory, but never alter inputs.
Full files are available; the selected IDs below narrow the customer request, not the accepted answer.

## Job H1 — Does a supplier's passing family support a narrower obligation?

A receiving engineer asks about Box source characteristic IDs `14, 20, 26, 32` and incoming characteristic ID
`33`. Compute the destination interval and evaluate **all recorded source values** under the actual formal QIF
units. Separately evaluate the explicit research hypothesis that the source values and source limits were meant
to be millimetres. Is each family-wide claim supported or refuted? Give the value count and a concrete source
counterexample whenever a universal assertion fails. Explain whether source PASS labels suffice and what remains
before physical substitution. Do not modify the source or treat the hypothesis as an authorized correction.

## Job H2 — Can a useful family result survive unknown individual labels?

A Cover engineer asks about every source `DiameterCharacteristicItem` whose raw nominal target is `4.5` and
incoming characteristic `23`. Under the same explicitly hypothetical millimetre repair, assess all recorded
values against the incoming interval. Give count, range and an auditable reason why unknown permutations do or
do not matter to that **family-wide** statement. Then answer whether it identifies a particular hole for rework.
List the necessary unresolved conditions for physical reuse; do not assume the selected records cover the
destination physical feature set.

## Job H3 — What evidence must a successor obtain before reusing this packet?

A new recipient receives `Cover_incoming.qif`, `Cover_reference_incoming.qif` and the existing Cover integrated
graph. It also receives Cover FAIR data and a claim that a past graph qualification plus plausible millimetre
numbers authorizes reuse. Compare exact source identities and the actual differing content of the two incoming
files. Distinguish byte identity, semantic impact, numerical unit hypothesis and current mission authorization.
Give a specific, ordered evidence-acquisition plan for a cross-provider investigation; do not declare the graph
wrong solely because the source bytes differ, and do not invent a corrected export, specimen map or permission.

## Job H4 — Trace a local result without promoting it to part acceptance

The Box investigation names incoming characteristic actual `534`. Recover its value, characteristic item,
nominal and definition, linked actual feature, feature item, feature nominal/definition, containing measurement
result, specimen identifier and relevant recorded statuses. State exactly which local requirement can be checked
numerically and what the record does and does not establish about whole-part release, FAIR correspondence and
the physical feature for investigation. Use source identifiers as evidence; give an actionable next step for each
claim the supplied trace does not establish. Do not infer a machining cause from an inspection association.

## Required answer shape

Use four headings H1–H4. Under each, state the decision, precise supporting quantities/source IDs, remaining
conditions and the next useful action. Include a short final resource statement: tool calls used, any unexecuted
check, and unknown token/billing telemetry. Total answer at most 1,600 words. No self-assigned performance score.

The independent evaluator will require each job's complete mandatory criteria and reject materially unsupported
physical equivalence, automatic unit repair, false universal claims, lost parent status, invented measurements or
inherited authority. A correct refusal must still supply the useful source work the request asks for.
