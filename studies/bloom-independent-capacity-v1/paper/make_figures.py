#!/usr/bin/env python3
"""Render publication figures from frozen BLOOM evidence; never refit analysis.

From the study root:
    python3 paper/make_figures.py --results results --out build/figures

Dependencies: Python >=3.10, matplotlib >=3.6, numpy >=1.23.
Each figure has CSV data and an entry in plot_provenance.json. The input analysis
contains the preregistered confidence intervals; this script only changes their
scale from a ratio to a percentage saving. No scientific source is imported.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys

PURPLE = '#6d3dc2'
INK = '#1d1430'
GREEN = '#27856b'
AMBER = '#b77819'
MUTED = '#7d7789'
GRID = '#e7e3ec'
METHODS = ('bloom', 'expert', 'reverse')
METHOD_NAMES = {'bloom': 'BLOOM', 'expert': 'Expert', 'reverse': 'Reverse'}
SPLITS = ('confirmation', 'reproduction')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_file(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f'No data for {path.name}')
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_records(path: Path) -> list[dict]:
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def prepare_style(plt) -> None:
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 8,
        'text.color': INK, 'axes.labelcolor': INK, 'axes.edgecolor': GRID,
        'xtick.color': INK, 'ytick.color': INK, 'axes.titlesize': 10,
        'axes.labelsize': 8, 'xtick.labelsize': 7.5, 'ytick.labelsize': 8,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'svg.fonttype': 'none', 'svg.hashsalt': 'bloom-frozen-evidence-v1',
        'lines.solid_capstyle': 'round', 'axes.linewidth': 0.7,
    })


def clean_axes(ax, *, horizontal=True) -> None:
    for name in ('top', 'right', 'left'):
        ax.spines[name].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=3, width=0.6)
    ax.set_axisbelow(True)
    ax.grid(axis='x' if horizontal else 'y', color=GRID, linewidth=0.55)


def save_figure(fig, out: Path, stem: str, title: str, plt) -> list[str]:
    names = []
    for ext in ('pdf', 'svg', 'png'):
        path = out / f'{stem}.{ext}'
        metadata = {'Creator': 'BLOOM frozen-evidence figure builder', 'Title': title}
        if ext == 'pdf':
            metadata.update(CreationDate=None, ModDate=None)
        elif ext == 'svg':
            metadata['Date'] = None
        else:
            metadata = {'Software': 'BLOOM frozen-evidence figure builder', 'Title': title}
        fig.savefig(path, dpi=200, metadata=metadata)
        names.append(path.name)
    plt.close(fig)
    return names


def effect_figure(analysis, out, plt, Line2D):
    rows = []
    for split in SPLITS:
        items = [
            ('expert', 'competitive_total_cpu', analysis[split]['competitive_contrasts']['expert']),
            ('reverse', 'competitive_total_cpu', analysis[split]['competitive_contrasts']['reverse']),
            ('withheld', 'receiver_artifact_effect', analysis[split]['artifact_dependence']),
        ]
        for contrast, estimand, d in items:
            rows.append({
                'split': split, 'contrast': contrast, 'estimand': estimand,
                'worlds': d['independent_graph_worlds'],
                'ratio': d['geometric_mean_ratio'], 'ratio_ci_lower': d['ci_lower'],
                'ratio_ci_upper': d['ci_upper'],
                'saving_percent': 100 * (1 - d['geometric_mean_ratio']),
                'saving_ci_lower_percent': 100 * (1 - d['ci_upper']),
                'saving_ci_upper_percent': 100 * (1 - d['ci_lower']),
                'required_saving_percent': 100 * (1 - d['practical_threshold']),
                'interval_level': d['interval_level'], 'family_size': d['family_size'],
                'bootstrap_replicates': d['bootstrap_replicates'],
                'gate_passed': d['pass_threshold'], 'coverage': d['coverage'],
            })
    write_csv(out / 'fig01_effects.data.csv', rows)
    fig, axes = plt.subplots(2, 1, figsize=(6, 4.7), sharex=True,
                             gridspec_kw={'height_ratios': [1.6, 1]})
    fig.subplots_adjust(left=.285, right=.955, top=.705, bottom=.24, hspace=.85)
    fig.text(.045, .955, 'Measured savings, unmet gates', fontsize=12, weight='bold')
    fig.text(.045, .907, 'Confirmation is primary; fresh reproduction is a separate sample.', fontsize=8, color=MUTED)
    handles = [
        Line2D([], [], color=PURPLE, marker='o', lw=1.5, markersize=5,
               label='Confirmation · 48 worlds'),
        Line2D([], [], color=MUTED, marker='D', markerfacecolor='white', lw=1.0,
               markersize=4.4, label='Fresh reproduction · 24 worlds'),
    ]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.04, .865),
               ncol=2, frameon=False, fontsize=7.5, handlelength=1.7, columnspacing=1.4)
    labels = {'expert': 'Against expert', 'reverse': 'Against reverse', 'withheld': 'Retained / withheld'}
    for ax, contrasts, threshold, title, gate in (
        (axes[0], ['expert', 'reverse'], 10, 'A  Complete operational CPU', 'G3'),
        (axes[1], ['withheld'], 20, 'B  Receiver CPU only', 'G4'),
    ):
        clean_axes(ax)
        ax.set_xlim(-10, 31)
        ax.set_xticks([-10, 0, 10, 20, 30])
        ax.axvline(0, color=INK, lw=.8, zorder=1)
        ax.axvline(threshold, color=AMBER, lw=1.1, ls=(0, (3, 3)), zorder=1)
        ax.text(threshold + .8, 1.10, f'{threshold}% gate', transform=ax.get_xaxis_transform(),
                color=AMBER, fontsize=7.4, va='bottom')
        ax.text(-.36, 1.30, title, transform=ax.transAxes, fontsize=8.8, weight='bold')
        ax.text(1, 1.30, f'{gate}: not met', transform=ax.transAxes,
                color=AMBER, fontsize=8, ha='right')
        ys = list(reversed(range(len(contrasts))))
        for contrast, y in zip(contrasts, ys):
            for split, dy, color, marker in (
                ('confirmation', .17, PURPLE, 'o'),
                ('reproduction', -.17, MUTED, 'D'),
            ):
                r = next(r for r in rows if r['split'] == split and r['contrast'] == contrast)
                estimate = r['saving_percent']
                ax.errorbar(estimate, y + dy,
                            xerr=[[estimate-r['saving_ci_lower_percent']],
                                  [r['saving_ci_upper_percent']-estimate]],
                            color=color, marker=marker,
                            markerfacecolor=color if split == 'confirmation' else 'white',
                            markeredgewidth=1, markersize=4.8 if split == 'confirmation' else 4.1,
                            elinewidth=1.6 if split == 'confirmation' else 1.0,
                            capsize=2.3, zorder=3)
                ax.annotate(f'{estimate:.1f}%', (estimate, y+dy),
                            xytext=(0, 7 if split == 'confirmation' else -12),
                            textcoords='offset points', ha='center', color=color, fontsize=7.1)
        ax.set_yticks(ys, [labels[c] for c in contrasts])
        ax.set_ylim(-.63, len(contrasts)-.37)
    axes[1].set_xlabel('CPU saving (%)  ·  larger values favor retention or BLOOM', labelpad=8)
    fig.text(.045, .027,
             '98.33% two-sided percentile-bootstrap intervals for three predeclared contrasts.\n'
             'Multiplicity coverage is nominal, not guaranteed. Each interval must clear its gate.\n'
             'Receiver savings do not include predecessor creation; panel A includes it.',
             fontsize=7.1, color=MUTED, va='bottom', linespacing=1.4)
    outputs = save_figure(fig, out, 'fig01_effects', 'Measured savings, unmet gates', plt)
    return {'outputs': outputs, 'data': ['fig01_effects.data.csv'],
            'aggregation': 'Frozen preregistered ratio and CI transformed by saving = 100*(1-ratio); CI endpoints reverse. No recomputation or pooling.',
            'interpretation': 'Neither competitive superiority nor the receiver benefit threshold passed in confirmation or fresh reproduction.'}


PHASE_GROUPS = [
    ('Input + transport', ('parse', 'input_validation', 'serialization', 'export', 'restore', 'replacement_export', 'replacement_restore'), '#d9cceb'),
    ('Select + build', ('selection', 'construction'), '#aa8cd4'),
    ('Proof + revalidation', ('producer_qualification', 'receiver_revalidation'), PURPLE),
    ('Impact + plan', ('impact_execution', 'successor_construction'), '#548c82'),
    ('Result checking', ('result_checking',), '#abc7c1'),
    ('Other measured', (), '#d8d6de'),
]


def phase_figure(records, analysis, out, plt, Patch):
    source = records['confirmation']
    choices = [('bloom', 'stable'), ('expert', 'stable'), ('reverse', 'stable'), ('bloom', 'withheld')]
    phase_names = sorted({p for r in source for p in r.get('phases', {})})
    known = {p for _, parts, _ in PHASE_GROUPS for p in parts}
    if set(phase_names) - known:
        raise ValueError(f'Unmapped phases: {set(phase_names)-known}')
    raw_rows, group_rows, values, totals = [], [], [], []
    for method, treatment in choices:
        by_world = defaultdict(list)
        for r in source:
            if r['method'] == method and r['treatment'] == treatment and r['verification']:
                by_world[r['seed']].append(r)
        world_groups = []
        for seed, trials in sorted(by_world.items()):
            assert len(trials) == 3
            # Selecting the observed median-total replicate preserves phase additivity.
            r = sorted(trials, key=lambda v: (v['total_cpu_ns'], v['replicate']))[1]
            assert r['status'] == 'COMPLETED' and r['external_audit']['correct']
            phases = {p: r['phases'].get(p, {}).get('cpu_ns', 0) for p in phase_names}
            residual = r['total_cpu_ns'] - sum(phases.values())
            if residual < 0:
                raise ValueError('Phase timers are not additive; negative residual.')
            raw = {'split': 'confirmation', 'method': method, 'treatment': treatment,
                   'seed': seed, 'case_sha256': r['case_sha256'],
                   'selected_replicate': r['replicate'], 'total_cpu_ns': r['total_cpu_ns']}
            raw.update({f'{k}_cpu_ns': v for k, v in phases.items()})
            raw['other_measured_cpu_ns'] = residual
            raw_rows.append(raw)
            grouped = [sum(phases[p] for p in parts) if parts else residual for _, parts, _ in PHASE_GROUPS]
            assert sum(grouped) == r['total_cpu_ns']
            world_groups.append(grouped)
        assert len(by_world) == 48
        means = [statistics.mean(v[i] for v in world_groups)/1e6 for i in range(len(PHASE_GROUPS))]
        total = sum(means)
        if treatment == 'stable':
            assert abs(total/1000-analysis['confirmation']['primary_mean_cpu_seconds'][method]) < 1e-12
        values.append(means); totals.append(total)
        for (name, parts, _), mean in zip(PHASE_GROUPS, means):
            group_rows.append({'split': 'confirmation', 'method': method, 'treatment': treatment,
                               'worlds': len(by_world), 'phase_group': name,
                               'included_phases': ';'.join(parts) if parts else 'total_cpu_ns-minus-all-recorded-phases',
                               'mean_cpu_ms': mean, 'mean_total_cpu_ms': total,
                               'fraction_total': mean/total})
    write_csv(out/'fig02_cpu_phases.data.csv', group_rows)
    write_csv(out/'fig02_cpu_phases.worlds.csv', raw_rows)
    fig, ax = plt.subplots(figsize=(6, 3.95))
    fig.subplots_adjust(left=.245, right=.94, top=.75, bottom=.365)
    fig.text(.045, .945, 'Where the measured CPU goes', fontsize=12, weight='bold')
    fig.text(.045, .888, 'Shared verification and overhead remain part of every comparison.', fontsize=8, color=MUTED)
    ys = [3.15, 2.15, 1.15, -.25]
    left = [0.0]*len(choices)
    for i, (_, _, color) in enumerate(PHASE_GROUPS):
        widths = [v[i] for v in values]
        ax.barh(ys, widths, left=left, height=.58, color=color, edgecolor='white', linewidth=.6)
        left = [x+y for x,y in zip(left, widths)]
    for y, total in zip(ys, totals):
        ax.text(total+.08, y, f'{total:.2f} ms', va='center', fontsize=8, weight='bold')
    ax.set_yticks(ys, ['BLOOM', 'Expert', 'Reverse', 'BLOOM\nartifact withheld'])
    ax.set_xlim(0, max(totals)+.85)
    ax.set_ylim(-.9, 3.9)
    ax.set_xlabel('Mean total CPU per world (ms)', labelpad=6)
    clean_axes(ax)
    ax.axhline(.45, color=GRID, linewidth=.8)
    handles = [Patch(facecolor=c, label=n) for n, _, c in PHASE_GROUPS]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.12, .125),
               ncol=3, frameon=False, fontsize=7.2, handlelength=1.25,
               handleheight=.8, columnspacing=1.3, labelspacing=.6)
    fig.text(.045, .025,
             '48 worlds; phases from each world’s median-total-CPU cold replicate.\n'
             'Predecessor work is included. Other = measured total − recorded phases; external audit is separate.',
             fontsize=6.8, color=MUTED, va='bottom', linespacing=1.4)
    outputs = save_figure(fig, out, 'fig02_cpu_phases', 'Where the measured CPU goes', plt)
    return {'outputs': outputs, 'data': ['fig02_cpu_phases.data.csv', 'fig02_cpu_phases.worlds.csv'],
            'aggregation': 'For each method, treatment and world select the middle of three total-CPU cold replicates. Sum phases from that same record; residual is total minus all recorded phases. Plot unweighted means over 48 worlds. Stable totals exactly reconcile with frozen primary means.',
            'interpretation': 'Operational CPU is measured; these bars do not establish complete monetary cost. All predecessor work is included; symmetric external scientific audit is separate.'}


OUTCOMES = {
    'productive': ('Qualified plans', '#dcefe8', GREEN),
    'infeasible': ('Correct infeasibility', '#e9e1f6', PURPLE),
    'refusal': ('Correct refusal', '#e3e9f1', '#5b6f8e'),
    'incomplete': ('Incomplete input: omissions', '#f8e9ca', AMBER),
    'unsafe': ('Bypass: wrong output', '#efceb0', '#9b4c14'),
    'not_run': ('Not run', '#f1eff4', MUTED),
}
ROBUST_ROWS = [
    ('stable', True, 'Stable handoff'), ('withheld', True, 'Artifact withheld'),
    ('replacement', True, 'Equivalent replacement'), ('graph_change', True, 'Graph changed'),
    ('policy_change', True, 'Policy changed'), ('tampered_artifact', True, 'Artifact tampered'),
    ('scarce_storage', True, 'Storage cap: 2 KiB'), ('component_outage', True, 'Constructor unavailable'),
    ('withheld_outage', True, 'Withheld + unavailable'), ('infeasible_cover', True, 'Cover infeasible'),
    ('authority_revoked', True, 'Authority revoked'), ('malformed_input', True, 'Malformed graph'),
    ('missing_edge', True, 'Hidden dependency edges'), ('tampered_artifact', False, 'Tampered · proof bypass'),
]


def classify_record(r):
    audit = r['external_audit']
    if audit.get('false_safe_queries_against_complete_graph', 0) > 0:
        return 'incomplete'
    if not audit['correct'] or r['status'] == 'FAILED':
        return 'unsafe'
    if r['status'].startswith('REFUSED_'):
        return 'refusal'
    if r['status'] == 'COMPLETED' and any(not o['feasible'] for o in r.get('outputs', [])):
        return 'infeasible'
    if r['status'] == 'COMPLETED' and audit['correct']:
        return 'productive'
    raise ValueError(f'Unclassified trial {r["seed"]} {r["method"]} {r["treatment"]}')


def robustness_figure(records, out, plt, Rectangle, Patch):
    raw_rows, cells = [], []
    for treatment, verification, label in ROBUST_ROWS:
        for method in METHODS:
            by_world = defaultdict(list)
            for r in records['confirmation']:
                if (r['method'], r['treatment'], r['verification']) == (method, treatment, verification):
                    by_world[r['seed']].append(r)
            counts = Counter()
            false_safe = full_queries = 0
            for seed, trials in sorted(by_world.items()):
                categories = {classify_record(r) for r in trials}
                if len(categories) != 1:
                    raise ValueError('Replicate outcome disagreement requires explicit display.')
                outcome = next(iter(categories))
                counts[outcome] += 1
                qfalse = sum(r['external_audit'].get('false_safe_queries_against_complete_graph', 0) for r in trials)
                qfull = sum(r['external_audit'].get('queries_against_complete_graph', 0) for r in trials)
                false_safe += qfalse; full_queries += qfull
                raw_rows.append({'split': 'confirmation', 'treatment': treatment,
                                 'verification': verification, 'method': method, 'seed': seed,
                                 'case_sha256': trials[0]['case_sha256'], 'outcome': outcome,
                                 'replicates': len(trials), 'artifact_accepted_any': any(r['artifact_accepted'] for r in trials),
                                 'false_safe_queries_against_complete_graph': qfalse,
                                 'queries_against_complete_graph': qfull})
            if not counts:
                counts['not_run'] = 0
            cells.append({'treatment': treatment, 'verification': verification,
                          'label': label, 'method': method, 'worlds': len(by_world),
                          **{f'{o}_worlds': counts[o] for o in OUTCOMES},
                          'false_safe_queries_against_complete_graph': false_safe,
                          'queries_against_complete_graph': full_queries})
    write_csv(out/'fig03_robustness.data.csv', cells)
    write_csv(out/'fig03_robustness.worlds.csv', raw_rows)
    fig, ax = plt.subplots(figsize=(6, 5.95))
    fig.subplots_adjust(left=.405, right=.955, top=.84, bottom=.235)
    fig.text(.045, .962, 'Correct resolution has several meanings', fontsize=11.7, weight='bold')
    fig.text(.045, .919, 'Confirmation · world counts, with boundary and failure arms kept visible', fontsize=7.8, color=MUTED)
    for i, (treatment, verification, label) in enumerate(ROBUST_ROWS):
        y = len(ROBUST_ROWS)-i-.5
        ax.text(-.09, y, label, ha='right', va='center', fontsize=7.6)
        for j, method in enumerate(METHODS):
            cell = next(c for c in cells if (c['treatment'], c['verification'], c['method']) == (treatment, verification, method))
            present = [o for o in OUTCOMES if cell[f'{o}_worlds']]
            outcome = present[0] if present else 'not_run'
            if len(present) > 1:
                raise ValueError('Mixed cell requires a segmented figure; refuse to hide it.')
            _, fill, color = OUTCOMES[outcome]
            ax.add_patch(Rectangle((j+.035, y-.425), .93, .85,
                                   facecolor=fill, edgecolor='white', linewidth=.7))
            text = f'{cell[f"{outcome}_worlds"]} / {cell["worlds"]}' if present else 'not run'
            ax.text(j+.5, y, text, ha='center', va='center', fontsize=8, color=color,
                    weight='bold' if outcome in ('incomplete', 'unsafe') else 'normal')
    ax.set_xlim(0,3); ax.set_ylim(0,len(ROBUST_ROWS))
    ax.set_xticks([.5,1.5,2.5], ['BLOOM', 'Expert', 'Reverse'])
    ax.xaxis.tick_top(); ax.tick_params(axis='x', length=0, pad=7, labelsize=8.2)
    ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)
    for after in (9,12):
        ax.axhline(len(ROBUST_ROWS)-after, xmin=-.02, xmax=1, color=GRID, lw=.8)
    handles = [Patch(facecolor=fill, edgecolor=color, linewidth=.45, label=name)
               for name, fill, color in OUTCOMES.values()]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.045, .105),
               ncol=2, frameon=False, fontsize=7.1, handlelength=1.2,
               columnspacing=1.4, labelspacing=.7)
    missing = next(c for c in cells if c['treatment']=='missing_edge' and c['method']=='bloom')
    fig.text(.045, .022,
             '48 worlds per cell; stable/withheld repeats are collapsed within each world.\n'
             f'Incomplete graphs: {missing["false_safe_queries_against_complete_graph"]:,}/{missing["queries_against_complete_graph"]:,} query outputs omit a true impact per method.\n'
             'That query count is descriptive and clustered. Supplied-graph correctness cannot certify missing facts.',
             fontsize=6.9, color=MUTED, va='bottom', linespacing=1.4)
    outputs = save_figure(fig, out, 'fig03_robustness', 'Correct resolution has several meanings', plt)
    return {'outputs': outputs, 'data': ['fig03_robustness.data.csv', 'fig03_robustness.worlds.csv'],
            'aggregation': 'Confirmation only. Group by method, treatment, verification and world; repeated outcomes must agree. A cell denominator is 48 worlds, not independent queries or the number of logical replicates. Unsafe bypass was run only for BLOOM.',
            'interpretation': 'Qualified plans, correct infeasibility and correct refusal are distinct. The missing-edge arm is correct only relative to supplied incomplete input; every world omits some complete-graph impact. Unsafe bypass accepts corrupt artifacts and produces wrong outputs.'}


STRATEGIES = [('scc', 'SCC closure', PURPLE), ('reverse', 'Reverse index', '#647f8c'),
              ('memo', 'Source memo', '#b49bd7'), ('walk', 'Graph walk', '#c3d5d2')]


def strategy_figure(records, out, plt, Patch):
    treatments = [('stable', 'Standard\ncomplete graph'),
                  ('scarce_storage', 'Scarce storage\n2 KiB cap'),
                  ('withheld_outage', 'Artifact withheld\nconstructor unavailable')]
    world_rows, counts = [], []
    for treatment, _ in treatments:
        for method in METHODS:
            by_world = defaultdict(list)
            for r in records['confirmation']:
                if (r['method'], r['treatment'], r['verification']) == (method,treatment,True):
                    by_world[r['seed']].append(r)
            counter = Counter()
            for seed, trials in sorted(by_world.items()):
                operators = {r['operator_strategy'] for r in trials}
                if len(operators) != 1:
                    raise ValueError('Operator choices differ across repeated world.')
                strategy = next(iter(operators)); counter[strategy] += 1
                world_rows.append({'split':'confirmation','treatment':treatment,'method':method,
                                   'seed':seed,'case_sha256':trials[0]['case_sha256'],
                                   'operator_strategy':strategy,'logical_replicates':len(trials)})
            assert len(by_world)==48
            for strategy,_,_ in STRATEGIES:
                counts.append({'split':'confirmation','treatment':treatment,'method':method,
                               'operator_strategy':strategy,'worlds':counter[strategy],
                               'worlds_total':len(by_world),'percent':100*counter[strategy]/len(by_world)})
    write_csv(out/'fig04_operator_choices.data.csv',counts)
    write_csv(out/'fig04_operator_choices.worlds.csv',world_rows)
    fig, axes = plt.subplots(1,3,figsize=(6,3.65),sharey=True)
    fig.subplots_adjust(left=.085,right=.965,top=.70,bottom=.28,wspace=.24)
    fig.text(.045,.945,'Changing constraints, familiar operators',fontsize=11.7,weight='bold')
    fig.text(.045,.887,'BLOOM and the expert choose the same SCC operator on all standard worlds.',fontsize=7.6,color=MUTED)
    for ax,(treatment,title) in zip(axes,treatments):
        bottom=[0.0]*3
        for strategy,_,color in STRATEGIES:
            cells=[next(c for c in counts if (c['treatment'],c['method'],c['operator_strategy'])==(treatment,m,strategy)) for m in METHODS]
            heights=[c['percent'] for c in cells]
            ax.bar(range(3),heights,bottom=bottom,width=.66,color=color,edgecolor='white',linewidth=.6)
            for j,(base,h,c) in enumerate(zip(bottom,heights,cells)):
                if h>0:
                    ax.text(j,base+h/2,str(c['worlds']),ha='center',va='center',fontsize=7.7,
                            color='white' if strategy in ('scc','reverse') else INK)
            bottom=[b+h for b,h in zip(bottom,heights)]
        ax.set_title(title,fontsize=8.2,pad=9,linespacing=1.4)
        ax.set_xticks(range(3),[METHOD_NAMES[m] for m in METHODS],fontsize=7.1)
        ax.set_ylim(0,100);ax.set_yticks([0,25,50,75,100])
        clean_axes(ax,horizontal=False)
    axes[0].set_ylabel('Share of worlds (%)')
    handles=[Patch(facecolor=color,label=label) for _,label,color in STRATEGIES]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.13),ncol=4,
               frameon=False,fontsize=7.0,handlelength=1.2,columnspacing=1.1)
    fig.text(.045,.025,
             'Numbers inside segments are counts; 48 worlds per method and scenario.\n'
             'Final operators include charged fallback. All methods share construction primitives and qualification.',
             fontsize=6.9,color=MUTED,va='bottom',linespacing=1.4)
    outputs=save_figure(fig,out,'fig04_operator_choices','Changing constraints, familiar operators',plt)
    return {'outputs':outputs,'data':['fig04_operator_choices.data.csv','fig04_operator_choices.worlds.csv'],
            'aggregation':'Confirmation only. One final operator choice per method, treatment and world; choices must agree across repeated stable trials. Show counts and fractions, without inferential claims.',
            'interpretation':'The stable result is a comparison of selection and surrounding costs with a shared SCC capability. Under storage or constructor constraints conventional memoization and walking remain useful fallbacks.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parent.parent
    parser.add_argument('--results',type=Path,default=root/'results')
    parser.add_argument('--out',type=Path,default=root/'build/figures')
    args=parser.parse_args()
    results=args.results.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(out.parent/'mplconfig'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch, Rectangle
    import numpy
    prepare_style(plt)
    inputs={};analysis={};records={}
    for split in SPLITS:
        for filename in ('analysis.json','records.jsonl.gz'):
            path=results/split/filename
            inputs[f'results/{split}/{filename}']={'sha256':sha256(path),'bytes':path.stat().st_size}
        analysis[split]=json_file(results/split/'analysis.json')
        records[split]=load_records(results/split/'records.jsonl.gz')
        assert analysis[split]['split']==split
        assert len(records[split])==analysis[split]['trials']
        assert all(r['freeze_sha256']==analysis[split]['freeze_sha256'] for r in records[split])
    assert analysis['confirmation']['freeze_sha256']==analysis['reproduction']['freeze_sha256']
    receipt=results/'independent_reproduction_review/INDEPENDENT_REPRODUCTION_REVIEW.json'
    review=None
    if receipt.exists():
        inputs['results/independent_reproduction_review/INDEPENDENT_REPRODUCTION_REVIEW.json']={'sha256':sha256(receipt),'bytes':receipt.stat().st_size}
        review=json_file(receipt)
    figures={
        'fig01_effects':effect_figure(analysis,out,plt,Line2D),
        'fig02_cpu_phases':phase_figure(records,analysis,out,plt,Patch),
        'fig03_robustness':robustness_figure(records,out,plt,Rectangle,Patch),
        'fig04_operator_choices':strategy_figure(records,out,plt,Patch),
    }
    output_files={}
    for details in figures.values():
        for name in details['outputs']+details['data']:
            p=out/name;output_files[name]={'sha256':sha256(p),'bytes':p.stat().st_size}
    manifest={
        'schema':'bloom-publication-figure-provenance/v1',
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'script':{'path':'paper/make_figures.py','sha256':sha256(Path(__file__))},
        'command':'python3 paper/make_figures.py --results results --out build/figures',
        'environment':{'python':platform.python_version(),'matplotlib':matplotlib.__version__,'numpy':numpy.__version__},
        'freeze_sha256':analysis['confirmation']['freeze_sha256'],
        'analysis_refit':False,'fresh_reproduction_pooled_with_confirmation':False,
        'g1_original_analysis_field':analysis['confirmation']['gates']['G1'],
        'g1_independent_receipt_verdict':review.get('G1_verdict') if review else None,
        'g1_note':'Independent receipt is an overlay; the frozen analysis field remains unchanged.',
        'inputs':inputs,'figures':figures,'outputs':output_files,
        'total_output_bytes':sum(x['bytes'] for x in output_files.values()),
        'scope':'Synthetic dependency graphs and coverage plans. These figures establish no actual test runtime savings, revenue, market demand, complete monetary cost or unrestricted regression safety.',
    }
    (out/'plot_provenance.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    notes=['# Publication figure notes','',
           'All four figures are 6 inches wide. PDF and SVG retain vector geometry; PNG previews are 200 dpi.',
           'The plotting script reads frozen analysis and raw evidence and imports no scientific kernel.',
           'The source and all input/output SHA-256 hashes are recorded in `plot_provenance.json`.',
           'Raw science files are never changed. The independent G1 receipt is recorded as an overlay, preserving the original pending field.', '']
    for name,details in figures.items():
        notes.extend([f'## {name}','',details['aggregation'],'',details['interpretation'],''])
    (out/'figure_notes.md').write_text('\n'.join(notes),encoding='utf-8')
    print(json.dumps({'output_directory':str(out),'figures':list(figures),
                      'bytes':manifest['total_output_bytes'],
                      'script_sha256':manifest['script']['sha256'],
                      'manifest_sha256':sha256(out/'plot_provenance.json')},indent=2))


if __name__=='__main__':
    main()
