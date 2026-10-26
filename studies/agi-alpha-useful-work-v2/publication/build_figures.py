# SPDX-License-Identifier: Apache-2.0
"""Descriptive scientific figures from the fixed completed campaign."""
import datetime
import hashlib
import json
from pathlib import Path
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
wall, cpu = time.perf_counter(), time.process_time()
summary = json.loads((ROOT / 'results/economic-analysis-01/summary.json').read_text())
order = ['starlette-1', 'starlette-2', 'starlette-3', 'pydantic-1', 'pydantic-2', 'pydantic-3']
labels = ['S1', 'S2', 'S3', 'P1', 'P2', 'P3']
arms = [('manual', 'A: researcher-assisted', '#8a7e99', 'o'),
        ('retained', 'B: retained builder', '#62389d', 's'),
        ('conventional', 'C: conventional builder', '#197b75', '^')]
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.labelcolor': '#352345', 'text.color': '#352345',
                     'xtick.color': '#5b4e67', 'ytick.color': '#5b4e67', 'axes.edgecolor': '#c2b8cd',
                     'pdf.fonttype': 42, 'savefig.facecolor': 'white'})
out = ROOT / 'publication/figures'
out.mkdir(exist_ok=True)
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), constrained_layout=True)
for ax, field, title, ymax in zip(axes, ['mechanical_wall_seconds', 'measured_local_cpu_seconds'],
                                ['Mechanical delivery time (seconds)', 'Measured local CPU (seconds)'], [18, 2.7]):
    for offset, (arm, label, color, marker) in zip([-.18, 0, .18], arms):
        values = [next(row[field] for row in summary['runs'] if row['mission_id'] == mission and row['arm'] == arm)
                  for mission in order]
        ax.scatter(np.arange(6) + offset, values, color=color, marker=marker, s=36, label=label, zorder=3)
    ax.set(xticks=np.arange(6), xticklabels=labels, ylim=(0, ymax), title=title, xlabel='Frozen mission order')
    ax.grid(axis='y', color='#e9e3ef', linewidth=.8)
axes[0].axhline(15, color='#a393b5', linestyle='--', linewidth=.9)
axes[0].text(.03, .78, 'Original 15-second timeout retained', transform=axes[0].transAxes, fontsize=8,
             color='#776485', bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 2})
axes[0].legend(loc='lower left', frameon=False, fontsize=8)
fig.savefig(out / 'resource-comparison.pdf', bbox_inches='tight')
fig.savefig(out / 'resource-comparison.png', dpi=180, bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(9.8, 3.9), constrained_layout=True)
colors = np.full((6, 3), 1)
ax.imshow(colors, cmap=ListedColormap(['#e2efe9']), vmin=0, vmax=1, aspect='auto')
for i in range(6):
    for j in range(3):
        row = next(row for row in summary['runs'] if row['mission_id'] == order[i] and row['arm'] == arms[j][0])
        if not row['accepted']:
            raise ValueError('Figure requires observed accepted status, not a hardcoded positive')
        ax.text(j, i, 'Complete / preserved', ha='center', va='center', fontsize=9, color='#29594b')
ax.set_xticks(range(3), ['A: researcher-assisted', 'B: retained builder', 'C: conventional builder'])
ax.set_yticks(range(6), ['Starlette 1.5.1 → 1.6.0', 'Starlette 1.6.0 → 1.8.0', 'Starlette 1.8.0 → 1.9.0',
                        'Pydantic 2.13.2 → 2.13.3', 'Pydantic 2.13.3 → 2.13.4', 'Pydantic 2.13.4 → 2.14.0'])
ax.set_xticks(np.arange(-.5, 3, 1), minor=True)
ax.set_yticks(np.arange(-.5, 6, 1), minor=True)
ax.grid(which='minor', color='white', linewidth=3)
ax.tick_params(which='both', length=0, pad=10)
for spine in ax.spines.values():
    spine.set_visible(False)
fig.savefig(out / 'outcome-matrix.pdf', bbox_inches='tight')
fig.savefig(out / 'outcome-matrix.png', dpi=180, bbox_inches='tight')
plt.close(fig)
record = {'schema': 'publication-figure-construction/v1', 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'input_sha256': hashlib.sha256((ROOT / 'results/economic-analysis-01/summary.json').read_bytes()).hexdigest(),
          'files': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                    for p in sorted(out.iterdir()) if p.is_file()], 'wall_seconds': time.perf_counter() - wall,
          'process_cpu_seconds': time.process_time() - cpu, 'money_usd': None,
          'scope': 'Descriptive primary outcomes/resources only; no inferential significance or attention/currency conversion.'}
(ROOT / 'publication/figure-construction.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'files': len(record['files']), 'wall_seconds': record['wall_seconds']}))
