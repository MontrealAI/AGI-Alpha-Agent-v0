"""Render the requested commercial-first report from retrospective retained accounting."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ORDER=("conservative","central","favorable")
INK,GOLD,TEAL="#342657","#ad8034","#267e83"


def main():
    source=ROOT/"results/commercial_core.json"
    report=json.loads(source.read_text())
    assert report["new_economic_seeds_run"]==0 and not report["scientific_protocol_changed"]
    scenarios=report["scenarios"]
    def metric(s,k):return scenarios[s]["metrics"][k]["mean"]
    def fmt(v,n=0):return f"{v:,.{n}f}"
    def row(label,values):return label+" & "+" & ".join(values)+r" \\"
    lines=[r"\subsection{Useful accepted work, prices and complete costs}",
      r"The answer is positive within the declared model: competent Beta delivers useful accepted coordination-design work, collects customer payments, covers complete delivery and business costs, and leaves operating surplus. It needs no graph advantage or separate R\&D to meet that commercial criterion. The outcome remains conditional on task performance, human-scope equivalence, buyer demand and workload assumptions; it is not realized revenue.",
      r"Customers receive an executable bounded coordination mechanism, task-specific checks and counterexamples, declared assumptions, integration artifacts and a handoff. They do not buy an untested idea or an operational market guarantee. The three human-service references are USD25,329, USD49,857.64 and USD98,114.56 for assumed teams of 100, 196 and 384 hours, using the documented US rates in Table~\ref{tab:human}. They are derived matched-scope scenarios, not actual customer quotations or verified human-only labor.",
      r"\begin{table}[H]\centering\small\caption{Commercial core: Beta-only means over 64 fresh worlds per scenario. USD unless noted; 104 intake weeks plus 16 run-off weeks.}\label{tab:commercial}",
      r"\begin{tabular}{lrrr}\toprule Metric & Conservative & Central & Favorable\\\midrule"]
    lines.append(row("Useful accepted outcomes",[fmt(metric(s,"accepted_useful"),2) for s in ORDER]))
    lines.append(row("Price / human reference",[r"29.8\% adaptive",r"55\% fixed",r"75\% fixed"]))
    lines.append(row("Mean completed-job quote",[fmt(scenarios[s]["pricing"]["completed_job_quotes"]["quoted_price_USD"]["mean"]) for s in ORDER]))
    for key,label in [("collections","Collected receipts"),("A_job_cost","A: full delivery expenses"),
                      ("common_cost","Common setup and business costs"),("closing_obligations","Closing obligations"),
                      ("profit",r"\textbf{Collected operating profit}"),
                      ("available_cash","Available closing cash"),
                      ("available_after_seed_and_operating_floor",r"\textbf{Buffered surplus above seed}")]:
        lines.append(row(label,[fmt(metric(s,key)) for s in ORDER]))
    lines += [r"\bottomrule\end{tabular}\end{table}",
      r"B and C expenses are zero in these Beta arms. A includes learning during delivery, failed work, tools, verification, correction, packaging, refunds and recovery. Common costs include the USD9,500 bootstrap and shared business infrastructure. Initial USD60,000 capital is not revenue or profit. The central closing-obligation mean is deducted conservatively; already-accrued unpaid expense is not deducted twice.",
      r"The policy search used buyer choices among our offer, a human service, postponement and no purchase. These prices were selected in the declared 32-policy network family before confirmation and then applied unchanged to Beta. They are evaluated, economically selected policies, not an independent proof of the globally best Beta price. Conservative realized offer ratios range from 25\% to 45\%; central and favorable fixed ratios are 55\% and 75\%. A lower price alone does not establish real demand.",
      r"\subsection{Surplus, usable cash and correct-outcome receipts}",
      r"Available cash removes the ledger's protected commitments, warranty reserves and unpaid expenses. It is different from profit and includes seed. The final table row is a reporting-only planning measure: $\max(0,\min(\Pi,\text{available cash}-60{,}000)-2{,}640)$. It preserves initial seed, caps the figure by reported profit, and leaves a six-week Beta operating buffer. The USD2,640 buffer is not another expense or a claim that all future liabilities are known.",
      r"\begin{figure}[H]\centering\includegraphics[width=\linewidth]{figures/commercial.pdf}\caption{The commercial core before optional skills. All quantities are modeled; every cost of failed work remains in the accounting.}\end{figure}",
      r"To avoid crediting the commercial conclusion to erroneous deliveries, a retrospective accounting check keeps only receipts linked to on-time, truly correct outcomes and still deducts every enterprise expense and unexpensed closing obligation, including refunds and recovery of incorrect work. This is a deliberately conservative cash-revenue sensitivity, not a newly tuned policy or another sample.",
      r"\begin{table}[H]\centering\small\caption{Commercial checks using only useful-outcome receipts. Pooled per-outcome ratios use the same useful-outcome denominator.}",
      r"\begin{tabular}{lrrr}\toprule Metric & Conservative & Central & Favorable\\\midrule"]
    for key,label in [("useful_collections_USD_per_useful_outcome","Useful receipts per useful outcome"),
                      ("full_cost_USD_per_useful_outcome","All costs per useful outcome"),
                      ("useful_receipt_only_surplus_USD_per_useful_outcome","Conservative surplus per useful outcome")]:
        lines.append(row(label,[fmt(scenarios[s]["pooled_ratios"][key]) for s in ORDER]))
    lines.append(row("Useful-receipt-only total surplus",[fmt(metric(s,"useful_collections_only_surplus")) for s in ORDER]))
    lines.append(row("Worst world in this check",[fmt(scenarios[s]["metrics"]["useful_collections_only_surplus"]["min"]) for s in ORDER]))
    lines += [r"\bottomrule\end{tabular}\end{table}",
      r"Mean surplus remains positive in every scenario under that stricter check: USD343,435, USD3,522,731 and USD6,527,982. The conservative minimum is USD$-30,128.78$, so the result is not a guarantee that every world remains profitable under every accounting sensitivity. Pooled ratios summarize a heterogeneous portfolio; they are not a matched-job quote or an empirical productivity multiple.",
      r"The modeled customer savings on useful outcomes average USD1.67, USD3.43 and USD2.43 million across the three scenarios relative to their declared human references. These are price differences for supported useful outcomes, not measured consumer welfare, willingness to pay or evidence of actual sales. Quality is a simulated latent property. Positive economics cannot certify a real professional service or a real minimum quality floor.",
      r"\subsection{Throughput, capital and commercial downside}"]
    vals=[metric(s,"useful_throughput_per_104_week") for s in ORDER]
    lines.append("The six-producer, two-validator configuration supports mean useful throughput of "+", ".join(fmt(v,2) for v in vals)+r" outcomes per intake week, respectively. Dividing by the full 120-week horizon gives lower rates; neither measure is observed production or a steady-state capacity guarantee. The primary scenarios assume 1.8, 4 and 7 initial qualified leads per week, with repeat demand modeled separately.")
    lines += [r"The primary runs begin with USD60,000 and collect after seven, four and two weeks in the three scenarios. They record no Beta cash shortfall in 64 worlds each; the Wilson 95\% upper bound is nevertheless 5.66\%. A dedicated central-prior stress fails in all 16 worlds at USD10,000 seed and has zero observed shortfalls at USD25,000. This brackets tested outcomes, not an identified minimum required capital or a guarantee at USD25,000.",
      r"Demand sensitivity brackets the mean-profit crossing between 0.05 and 0.25 initial qualified leads per week at the frozen central price and other assumptions. Reducing the human reference to 10\% leaves positive mean Beta surplus of about USD80,204, while the combined low-demand, low-reference, high-cost, low-trust and slow-collection case loses about USD16,661. Thus the commercial core has explicit failure conditions even though the three primary scenario means are positive.",
      r"A split-sample capacity menu selects doubling producers, validators and quotas together. Its eight fresh test worlds improve Beta mean surplus by USD1,331,416, with conditional Monte Carlo interval [USD685,519, USD1,977,314], after the modeled capacity costs. That resource decision does not depend on skill sharing. It tests an initial capacity choice, not global optimal expansion timing. Spending still requires currently available cash.",
      r"These findings support continued modeled Beta delivery and retained reserves as economically meaningful choices. The next sections ask whether a candidate skill, sharing policy or extra investment adds enough value to improve that already-profitable foundation. Optional enhancements are allowed to fail their own tests without discarding the commercial core."]
    (ROOT/"paper/commercial_text.tex").write_text("\n\n".join(lines)+"\n")
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,
                         "axes.spines.top":False,"axes.spines.right":False,"text.color":INK})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(10.7,4.0))
    x=np.arange(3)
    profit=[metric(s,"profit")/1e6 for s in ORDER]
    cost=[(metric(s,"collections")-metric(s,"profit"))/1e6 for s in ORDER]
    ax.bar(x,cost,color=GOLD,label="Complete costs + closing charges")
    ax.bar(x,profit,bottom=cost,color=TEAL,label="Collected operating profit")
    ax.set_xticks(x,[s.capitalize() for s in ORDER]);ax.set_ylabel("USD million per enterprise")
    ax.set_title("Useful delivery supports a profitable core",fontsize=11);ax.legend(frameon=False,fontsize=8)
    for offset,key,label,color in [(-.18,"useful_collections_USD_per_useful_outcome","Useful-outcome receipts",TEAL),
                                    (.18,"full_cost_USD_per_useful_outcome","All enterprise costs",GOLD)]:
        bx.bar(x+offset,[scenarios[s]["pooled_ratios"][key]/1000 for s in ORDER],width=.34,label=label,color=color)
    bx.set_xticks(x,[s.capitalize() for s in ORDER]);bx.set_ylabel("USD thousand per useful outcome")
    bx.set_title("Complete cost remains below useful receipts",fontsize=11);bx.legend(frameon=False,fontsize=8)
    for a in (ax,bx):a.grid(axis="y",alpha=.15);a.set_axisbelow(True)
    fig.subplots_adjust(wspace=.35,bottom=.22)
    fig.text(.5,.015,"Beta only · 64 fresh worlds per scenario · all failed-work costs included · conditional simulation, not actual sales",ha="center",fontsize=9)
    for ext in ("pdf","png"):
        fig.savefig(ROOT/f"paper/figures/commercial.{ext}",bbox_inches="tight",dpi=180,
                    metadata={"CreationDate":None} if ext=="pdf" else None)
    plt.close(fig)
    (ROOT/"paper/figures/commercial_provenance.json").write_text(json.dumps({
        "input_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_kind":"reporting-only postprocessing of frozen confirmation; no new economic worlds"},indent=2)+"\n")
    print("Commercial section and figure generated without new economic execution.")


if __name__=="__main__":main()
