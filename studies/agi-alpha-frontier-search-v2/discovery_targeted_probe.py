"""Post-freeze exploratory identifiability probes; not a performance study."""
import cmath
import json
import math
import random
from pathlib import Path

rng = random.Random(20261027)
n = 8
x = [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(n)]
pairs = [([complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(n)],
          [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(n)]) for _ in range(64)]
def ordinal(v):
    return [abs(sum(a*z for a, z in zip(u, v)))**2 > abs(sum(a*z for a, z in zip(w, v)))**2 for u, w in pairs]
scaled = [2*z for z in x]
rank_result = {
    "seed": 20261027, "complex_dimensions": n, "paired_measurements": len(pairs),
    "equal_ordinal_codes": ordinal(x) == ordinal(scaled),
    "physical_power_ratio": sum(abs(z)**2 for z in scaled)/sum(abs(z)**2 for z in x),
    "interpretation": "Pairwise intensity ranks cannot identify absolute signal scale. This does not refute recovery up to norm or phase."
}
n = 16
starts = [0, 1, 2, 9, 10, 11]
f = [0j]*n
for j in list(range(5)) + list(range(9, 14)):
    f[j] = cmath.exp(0.2j*j)
g = f.copy()
for j in range(9, 14):
    g[j] *= -1

def diffraction(v):
    outputs = []
    for start in starts:
        masked = [v[j] if start <= j < start+3 else 0j for j in range(n)]
        outputs.extend(abs(sum(z*cmath.exp(-2j*math.pi*k*j/n) for j,z in enumerate(masked)))**2 for k in range(n))
    return outputs

a, b = diffraction(f), diffraction(g)
inner = sum(v.conjugate()*w for v,w in zip(f,g))
power_f, power_g = sum(abs(z)**2 for z in f), sum(abs(z)**2 for z in g)
aligned_error = math.sqrt(max(0, power_f+power_g-2*abs(inner))/power_f)
scan_result = {
    "complex_dimensions": n, "probe_width": 3, "scan_starts": starts,
    "diffraction_measurements": len(a), "max_intensity_difference": max(abs(u-v) for u,v in zip(a,b)),
    "best_global_phase_aligned_relative_object_error": aligned_error,
    "both_objects_have_identical_known_support": True,
    "within_component_probe_overlap": True, "global_probe_overlap_graph_connected": False,
    "interpretation": "Local overlap and coverage of known support do not identify relative phase between disconnected components. This is an obstruction, not a solution to Phasebook Q8.5."
}
assert rank_result['equal_ordinal_codes']
assert abs(rank_result['physical_power_ratio']-4) < 1e-12
assert scan_result['max_intensity_difference'] < 1e-12
assert aligned_error > 1.4
out = {"evidence_label": "executed finite synthetic counterexamples, post-freeze exploratory", "rank_scale": rank_result, "disconnected_scans": scan_result}
path = Path(__file__).with_name('discovery_targeted_probe_results.json')
path.write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out, indent=2))
