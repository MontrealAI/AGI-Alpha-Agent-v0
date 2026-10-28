<!-- SPDX-License-Identifier: Apache-2.0 -->
# Scope hardening 1.2 before fresh confirmation

The original v1 source and failed 0/3 report remain unchanged. The measurement
amendment v1.1 already ran on the same historical cases and accepted 3/3;
its exact source is retained as src/produce_v1_1_measurement.py. Version1.2
therefore has a separate identity and result directory. It retains the exact
construction and acceptance arithmetic while narrowing input admission.

Root review identified that additive analytic volumes assume nonintersecting
holes and features wholly within stock. Version1.2 refuses intersecting or
touching outer hole envelopes, exterior intersections, and any circle whose
envelope could enter a rounded-corner region. The corner rule is deliberately
sufficient and conservative; it does not claim to admit every valid geometry.
Counterbore depths/diameters, countersink diameters/angles, stock dimensions,
hole coordinates and corner radii must be finite numeric values (not booleans).

These restrictions do not change the original source cases or their rubric.
They define the admitted family before separate fresh confirmation. No fresh
request or result has been supplied to the constructor at this freeze.
The new current source includes an Apache-2.0 SPDX notice; preserved failed
source remains byte-identical. This is ordinary software robustness work,
not a demonstrated specialist-training or retained-Alpha gain.
