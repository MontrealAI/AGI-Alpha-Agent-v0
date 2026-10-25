# SPDX-License-Identifier: Apache-2.0
"""Render publication tables and editable figures from immutable raw analysis."""
from pathlib import Path
import json
import math
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/foundry-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT / "results/analysis.json").read_text())
D = json.loads((ROOT / "development/callsite-benchmark/summary.json").read_text())
P = ROOT / "paper"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.titlesize":12,"svg.fonttype":"none","pdf.fonttype":42})
purple, teal, gray, amber = "#452474", "#126F72", "#797582", "#A65D15"
fig, axes = plt.subplots(1,2,figsize=(7.2,3.15))
for ax, key, method, title in zip(axes,("A","B"),("candidate","selected"),
    ("A · committed companion", "B · gallery workers")):
    orig=D[key]["original"]["median_total_cpu_seconds"]
    new=D[key][method]["median_total_cpu_seconds"]
    ax.bar([0,1],[100,100*new/orig],color=[gray,purple],width=.55)
    ax.set_xticks([0,1],["Original","Selected"])
    ax.set_ylim(0,115);ax.set_ylabel("CPU, original = 100")
    ax.set_title(title,loc="left",fontweight="bold")
    ax.text(0,103,f"{orig*1000:.1f} ms",ha="center",fontsize=9)
    ax.text(1,100*new/orig+3,f"{new*1000:.1f} ms",ha="center",fontsize=9,color=purple)
    ax.text(.5,.83,f"{100*(1-new/orig):.1f}% less CPU",transform=ax.transAxes,ha="center",color=purple,fontweight="bold")
fig.text(.5,.015,"Five interleaved development trials per method; exact required outputs preserved.",ha="center",fontsize=8,color=gray)
fig.tight_layout(rect=(0,.06,1,1))
for suffix in ("pdf","svg","png"):fig.savefig(FIG/f"verified_callsite_improvements.{suffix}",dpi=170,bbox_inches="tight")
plt.close(fig)

names=["no_asset","history","flywheel","conventional","equivalent","reconstruction"]
labels=["No retained asset","Ordinary saved tooling","Proposed flywheel","Conventional constructor","Equivalent asset","Reconstruction"]
fig,ax=plt.subplots(figsize=(7.2,3.9))
for i,(name,label) in enumerate(zip(names,labels)):
    value=A["comparisons_to_specialist"][name]
    mid=value["geometric_cpu_ratio"];lo,hi=value["ci95"]
    color=purple if name=="flywheel" else gray
    ax.errorbar(mid,i,xerr=[[mid-lo],[hi-mid]],fmt="o",capsize=4,color=color,markersize=7 if name=="flywheel" else 5)
    ax.text(1.153,i,f"{mid:.3f}",va="center",fontsize=9,color=color)
ax.axvline(1,color=teal,linewidth=1.2,label="Direct specialist")
ax.axvline(.95,color=amber,linestyle="--",linewidth=1.1,label="Required upper bound")
ax.set_xlim(.92,1.185);ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis()
ax.set_xlabel("Whole-instance CPU ratio to direct specialist · lower is cheaper")
ax.set_title("The stronger flywheel claim fails",loc="left",fontweight="bold",color=purple)
ax.grid(axis="x",alpha=.15)
handles, legend_labels = ax.get_legend_handles_labels()
fig.legend(handles,legend_labels,loc="lower center",bbox_to_anchor=(.5,.055),ncol=2,fontsize=8,frameon=False)
fig.text(.5,.015,"24 generated instances; paired 95% bootstrap intervals. Secondary contrasts are descriptive.",ha="center",fontsize=8,color=gray)
fig.tight_layout(rect=(0,.17,1,1))
for suffix in ("pdf","svg","png"):fig.savefig(FIG/f"strong_comparator_confirmation.{suffix}",dpi=170,bbox_inches="tight")
plt.close(fig)

primary=A["primary"];ratio=primary["geometric_cpu_ratio"];lo,hi=primary["ci95"]
repeats=4;outputs=24*7*repeats*2
macros=r"\newcommand{\AbstractResult}{All 1,344 outputs qualify, and the flywheel produces 96 verified selected-parent diagnostic invocations across 24 generated instances. Its geometric mean whole-instance CPU ratio to the direct specialist is 1.0574 (95\% interval 1.0246--1.0899), failing the preregistered superiority gate.}"+"\n"
macros+=r"\newcommand{\ConclusionResult}{The practical batching improvement survives exact output checks, while the proposed flywheel does not outperform the direct specialist after measured pipeline costs. Useful reusable engineering is demonstrated; a superior improvement process is not.}"+"\n"
(P/'results_macros.tex').write_text(macros)

rows=[]
for name,label in zip(["specialist",*names],["Direct specialist",*labels]):
    r=A['arms'][name]
    cr=A['comparisons_to_specialist'].get(name)
    interval="reference" if cr is None else f"{cr['geometric_cpu_ratio']:.4f} [{cr['ci95'][0]:.4f}, {cr['ci95'][1]:.4f}]"
    rows.append(f"{label} & 192/192 & {r['total_cpu_seconds']:.4f} & {interval} \\\\")
conditions=[]
for name,label in [("specialist","Direct specialist"),("history","Saved tooling"),("flywheel","Flywheel")]:
    r=A['conditions'][name]
    values=[1000*r[k]['mean_cpu_seconds'] for k in ('read_fresh_process','read_warm_process','child_fresh_process','child_warm_process')]
    conditions.append(label+' & '+' & '.join(f'{v:.3f}' for v in values)+r' \\')

tex=r"""\subsection{Value delivered on the real call sites}
The selected adapter preserves the exact original output in every timed development run. Mission A's median CPU falls from 72.202 ms to 11.562 ms (83.99\% lower), while its process count falls from 39 to four. The independent specialist reaches 11.877 ms with the same four-process caller structure. The small A-only difference selects the retained candidate; it is not confirmation evidence of superiority. The supplied sequential verified method takes 67.674 ms and is retained as an unsuccessful candidate for this bottleneck.

Mission B changes both the inventory and the downstream construction: the accepted reader now supplies a catalog and 437 assets to the unchanged service-worker renderer. Median CPU falls from 1.510538 s to 0.172914 s (88.55\% lower); median wall latency falls from 1.459169 s to 0.154720 s. Six Git processes replace 876. Every one of the three generated worker bodies is byte-identical in all five original and five adapted trials. The already acquired tree costs a further 0.009155 CPU seconds and is recorded separately, equally applicable to both methods. These are whole-call-site measurements, not full-release or full-CI speedups.

\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{../figures/verified_callsite_improvements.pdf}
\caption{A useful engineering improvement exists against the pinned original implementations. The reader selection precedes Mission B. No security, mode, size, output or release check is removed.}
\end{figure}

\subsection{Fresh confirmation and the strongest alternative}
The single frozen campaign completes all 168 instance/treatment pairs. Each arm qualifies 96 source reads and 96 archive diagnoses, giving 192 outputs per arm and 1,344 total. All byte, diagnostic, lineage and budget checks pass. Every generated input lock and all 29 frozen scientific file identities remain unchanged. No confirmation result is discarded, and no method is revised after inspection.

The primary result is \textbf{HOLD for flywheel superiority}. The geometric mean instance CPU ratio is 1.0574 with a paired 95\% interval [1.0246, 1.0899]. Thus the measured flywheel pipeline costs 5.74\% more CPU than the direct specialist on this conditional workload; even the lower interval endpoint exceeds parity. The required upper bound below 0.95 is not approached. Mean paired additional cost is 9.087 ms per instance. This statement concerns total CPU, not wall latency or monetary expenditure.

\begin{table}[htbp]\centering\footnotesize
\caption{Fresh confirmation. CPU totals cover all 24 instances for each arm. The paired ratio is a geometric mean, so it need not equal the ratio of aggregate totals. Intervals are conditional instance bootstrap intervals.}
\begin{tabularx}{\textwidth}{@{}X r r l@{}}\toprule
Treatment & Qualified & Total CPU (s) & Ratio to specialist [95\% interval]\\\midrule
"""+'\n'.join(rows)+r"""
\bottomrule\end{tabularx}
\end{table}

\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{../figures/strong_comparator_confirmation.pdf}
\caption{The strongest practical comparator defeats the proposed process claim. Ordinary saved tooling is close to the direct specialist. The conventional constructor receives the same content and construction mechanism as the flywheel.}
\end{figure}

Ordinary saved tooling has ratio 1.0047 [0.9712, 1.0409] to the specialist, and the asset-free control has ratio 1.0074 [0.9725, 1.0411]. Their intervals span parity. The flywheel-to-history ratio is 1.0525 [1.0115, 1.0960], so retaining a more elaborate child artifact does not justify its measured overhead against a simple saved tool in this trial.

The flywheel-to-conventional ratio is 0.9683 [0.9305, 1.0017]. These arms intentionally execute the same mechanism and carry equivalent resources; the observed difference cannot identify a unique flywheel policy. The reconstruction and independently equivalent interventions are also disclosed: flywheel ratios are respectively 0.9622 [0.9322, 0.9938] and 0.9620 [0.9205, 0.9986]. These secondary timing differences are not independent tests of autonomous learning. Reconstruction uses the supplied legitimate template and almost the same materialization work; no ancestry-only advantage or commercial claim is drawn from its small observed difference.

\subsection{Fresh and warm behavior}
Table~\ref{tab:conditions} reports mean per-call CPU after averaging the three warm repetitions within each instance. It is a descriptive breakdown of the registered full-instance primary, not a replacement endpoint. Physical disk cache is uncontrolled. The whole pipeline includes Python startup, source loading, construction, verification and intermediate persistence, so these inner call costs cannot be substituted for the primary result.

\begin{table}[htbp]\centering\small
\caption{Inner operation CPU in milliseconds; 24 instance means per cell. Fresh means the first call in a new Python worker, not a cold operating-system cache.}
\label{tab:conditions}
\begin{tabularx}{\textwidth}{@{}Xrrrr@{}}\toprule
Treatment & Read fresh & Read warm & Diagnose fresh & Diagnose warm\\\midrule
"""+'\n'.join(conditions)+r"""
\bottomrule\end{tabularx}
\end{table}

\subsection{What the child actually contributes}
The flywheel constructs one scoped child binding per instance and executes 96 qualifying diagnoses across the 24 instances and four repetitions. Each selected execution invokes the retained reader once; the external evaluator checks its source, input, output and actual accepted-parent binding. Across the four bound-child treatments there are 384 such invocations. These counts are executions and scoped bindings, not 96 independently discovered algorithms or 96 independent tasks.

The source reader and archive diagnostician have distinct contracts: one supplies committed bytes; the other reports complete missing, changed and unexpected sets for a supplied archive. This is a real executable composition. The independent direct specialist nevertheless supplies the same useful diagnosis at lower total measured CPU. Ordinary history and asset-free controls have no bound-child lineage trace; they still execute competent reader code. A zero trace count must not be read as absence of algorithmic reuse.

The independent development suites pass 29 reader cases and 19 child cases for both proposed and specialist implementations. The child captures bytes safely, detects drift and refuses unsupported or corrupted cases; it does not repair or publish an archive. The rejection behavior is a successful boundary outcome. Correctness and constructive succession therefore execute, while a superior improvement process, earned feedback and full-investment payback remain unproved.
"""
(P/'results_generated.tex').write_text(tex)
dev_floor=D['measured_attempts_total_cpu_seconds']+sum(D[k]['total_cpu_seconds'] for k in ['preparation_cost','reference_A_cost','reference_B_cost','retention_cost','B_tree_cost'])
generation=json.loads((ROOT/'results/generation-cost.json').read_text())
confirm_cpu=sum(v['total_cpu_seconds'] for v in A['arms'].values())
saving_A=D['A']['original']['median_total_cpu_seconds']-D['A']['candidate']['median_total_cpu_seconds']
saving_B=D['B']['original']['median_total_cpu_seconds']-D['B']['selected']['median_total_cpu_seconds']
floor=dev_floor+generation['total_cpu_seconds']+confirm_cpu
cost={'schema':'foundry-cost-account/v1','development_measured_cpu_floor_seconds':dev_floor,
      'confirmation_instance_cpu_seconds':confirm_cpu,'input_generation_cpu_seconds':generation['total_cpu_seconds'],
      'sum_of_these_measured_cpu_categories_seconds':floor,
      'excluded_or_unknown':['prefreeze source search and code authoring','interactive model usage','reviewer engineering time',
          'some setup and development correctness checks','publication compilation and browser setup','integration',
          'future maintenance and operator review','storage/retrieval billing','shared orchestration outside per-instance timing'],
      'money':None,'human_seconds':None,'model_provider_calls_inside_benchmark':0,
      'model_provider_cost_inside_benchmark':0,'interactive_model_cost':None,
      'per_compatible_use_cpu_opportunity_vs_legacy':{'A':saving_A,'B':saving_B},
      'recurrence_sensitivity':[{'compatible_B_uses':n,'gross_cpu_opportunity_seconds':saving_B*n,
          'after_measured_cpu_subset_only':saving_B*n-floor,'full_net_value':None} for n in [1,10,100,1000,10000,100000]],
      'machine_subset_break_even_B_uses':math.ceil(floor/saving_B),
      'break_even_warning':'lower bound on unperformed future compatible legacy-callsite uses; excludes unknown costs, not demonstrated recovery',
      'against_strongest_specialist_positive_savings':False,'full_investment_break_even':None,
      'earned_capacity_allocated':False,'feedback_status':'all work uses external research allowance; no realized service-capacity or cash release witness'}
(ROOT/'results/cost-account.json').write_text(json.dumps(cost,sort_keys=True,indent=2)+'\n')
print(json.dumps({'primary_ratio':ratio,'all_outputs':outputs,'measured_cpu_subset_seconds':floor,'B_subset_break_even':cost['machine_subset_break_even_B_uses']}))
