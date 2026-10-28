# Measurement amendment 1.1

The frozen v1 run accepted 0/3 cases. Each constructed solid was valid and
matched its native reference and the analytic volume, with zero Boolean
symmetric-difference volume. Bounding-box and roundtrip bounding-box checks
failed. The original source and acceptance record remain unchanged as
src/produce_v1_failed.py and results/construction_v1/acceptance.json.

Cause identified before correction: CadQuery BoundingBox calls OpenCascade
BRepBndLib.AddOptimal with useTriangulation=True. STL export populates cached
triangulation and changes the reported box (e.g. Z=10.006838 versus nominal10)
without changing the exact solid volume. The local OCP documentation states
that AddOptimal can compute the box from exact geometry when triangulation
is disabled. Version1.1 uses AddOptimal(shape, box, False, False).

The construction algorithm, sources, feature program and all numeric acceptance
thresholds remain unchanged. The corrected run is a reproduction of the same
historical cases; it is not an independent confirmation. Original v1 remains
a failed delivery. Root supplies fresh post-freeze confirmation separately.
