from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'publication'
FIG = OUT / 'figures'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.titlesize': 12, 'figure.facecolor': 'white', 'axes.labelcolor': '#30213e'})
COLORS = {'A': '#3f6978', 'B': '#9d79d0', 'C': '#65349a', 'D': '#ce9549'}


def distribution(values):
    array = np.asarray(values, dtype=float)
    return {'n': len(array), 'mean': float(array.mean()), 'median': float(np.median(array)), 'min': float(array.min()),
            'max': float(array.max()), 'q05': float(np.quantile(array, .05)), 'q95': float(np.quantile(array, .95))}


def transfer_figure():
    source = json.loads((ROOT / 'independent/acquisition/comparison_summary.json').read_text())
    rows = [r for r in source['rows'] if r['family'] == 'design']
    fig, ax = plt.subplots(figsize=(7.3, 3.35), layout='constrained')
    y = np.arange(len(rows))
    old = [r['original_root_method_wall_seconds'] for r in rows]
    new = [r['retained_method_wall_seconds'] for r in rows]
    ax.barh(y + .16, old, .3, color='#a995c4', label='Original recipient implementation')
    ax.barh(y - .16, new, .3, color='#513072', label='Contributed low-rank implementation')
    ax.set_yticks(y, [f"{r['nodes']:,} nodes" for r in rows])
    ax.set_xscale('log')
    ax.set_xlabel('Solver-call elapsed seconds (log scale)')
    ax.set_title('A useful transfer to one recipient; no rarity claim')
    ax.legend(loc='lower right', fontsize=8, frameon=False)
    for i, r in enumerate(rows):
        ax.text(old[i] * 1.08, y[i] + .16, f"{r['original_root_over_retained_wall_ratio']:.2f}x", va='center', fontsize=9)
    ax.set_xlim(.008, 90)
    fig.savefig(FIG / 'transfer.png', dpi=220)
    fig.savefig(FIG / 'transfer.pdf')
    plt.close(fig)
    return source


def primary_analysis():
    rows = [json.loads(line) for line in (ROOT / 'evidence/primary/records.jsonl').read_text().splitlines()]
    assert len(rows) == 144 and len({(r['id'], r['arm']) for r in rows}) == 144
    chains = sorted({r['chain'] for r in rows})
    summary = {'statistical_units': len(chains), 'stage_jobs': 36, 'arm_stage_evaluations': 144, 'arms': {}, 'paired': {}}
    totals = {}
    for arm in COLORS:
        own = [r for r in rows if r['arm'] == arm]
        totals[arm] = [sum(r['cpu_seconds'] for r in own if r['chain'] == chain) for chain in chains]
        summary['arms'][arm] = {'accepted_stages': sum(r['accepted'] for r in own),
                                'accepted_chains': sum(all(r['accepted'] for r in own if r['chain'] == chain) for chain in chains),
                                'complete_cpu': distribution([r['cpu_seconds'] for r in own]),
                                'complete_elapsed': distribution([r['elapsed_seconds'] for r in own]),
                                'chain_cpu': distribution(totals[arm]),
                                'families': {f: {'accepted': sum(r['accepted'] for r in own if r['family'] == f),
                                                'cpu': distribution([r['cpu_seconds'] for r in own if r['family'] == f]),
                                                'elapsed': distribution([r['elapsed_seconds'] for r in own if r['family'] == f])}
                                             for f in ['forward', 'inverse', 'design']}}
    random = np.random.default_rng(20261026)
    indices = random.integers(0, len(chains), (10000, len(chains)))
    for left, right in [('B', 'A'), ('C', 'B'), ('C', 'A'), ('B', 'D'), ('A', 'D')]:
        delta = np.asarray(totals[left]) - np.asarray(totals[right])
        boot = delta[indices].mean(axis=1)
        summary['paired'][left + '-' + right] = {**distribution(delta), 'bootstrap_chain_mean_interval': np.quantile(boot, [.025, .975]).tolist(),
                                                 'meaning': 'Positive consumes more CPU; conditional descriptive paired-chain interval, not population-wide causal inference'}
    (OUT / 'primary-analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), layout='constrained')
    x = np.arange(3)
    for j, arm in enumerate(COLORS):
        heights = [summary['arms'][arm]['families'][f]['cpu']['mean'] for f in ['forward', 'inverse', 'design']]
        axes[0].bar(x + (j - 1.5) * .19, heights, .18, color=COLORS[arm], label=arm)
    axes[0].set_xticks(x, ['Forward', 'Inverse', 'Design'])
    axes[0].set_ylabel('Mean complete CPU seconds per stage')
    axes[0].set_title('Equal acceptance does not imply equal cost')
    axes[0].legend(ncol=4, frameon=False)
    for j, arm in enumerate(COLORS):
        axes[1].plot(np.arange(1, 13), totals[arm], 'o-', ms=3, lw=1.2, label=arm, color=COLORS[arm])
    axes[1].set_xlabel('Frozen chain (in increasing size strata)')
    axes[1].set_ylabel('Complete CPU seconds per chain')
    axes[1].set_title('Twelve paired engineering chains')
    axes[1].legend(ncol=4, frameon=False)
    fig.savefig(FIG / 'primary.png', dpi=220)
    fig.savefig(FIG / 'primary.pdf')
    plt.close(fig)
    return summary


if __name__ == '__main__':
    transfer_figure()
    if (ROOT / 'evidence/primary/summary.json').exists():
        print(json.dumps(primary_analysis(), indent=2))
