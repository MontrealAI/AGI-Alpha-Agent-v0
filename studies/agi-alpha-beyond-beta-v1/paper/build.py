# SPDX-License-Identifier: Apache-2.0
"""Build source-linked publication tables from released artifacts."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, subprocess
os.environ.setdefault("MPLCONFIGDIR", "/tmp/invent-economy-mpl")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
GEN = PAPER / "generated"
GEN.mkdir(exist_ok=True)
COST_PATH = 'evidence/workflow_costs_v3.json'

def esc(s):
    trans = {"\\": r"\textbackslash{}", "&":r"\&", "%":r"\%", "$":r"\$", "#":r"\#", "_":r"\_\allowbreak{}", "{":r"\{", "}":r"\}", "~":r"\textasciitilde{}", "^":r"\textasciicircum{}"}
    return ''.join(trans.get(c,c) for c in str(s)).replace('–','--').replace('—','---').replace('’',"'").replace('“','``').replace('”',"''").replace('×',r'$\times$').replace('≤',r'$\leq$').replace('≥',r'$\geq$').replace('Ω',r'$\Omega$').replace('∞',r'$\infty$')

def money(x, digits=0): return r'\usd{'+f'{float(x):,.{digits}f}'+'}'
def pct(x, digits=1): return f'{100*float(x):.{digits}f}'+r'\%'
def number(x, digits=1): return f'{float(x):,.{digits}f}'
def load(p): return json.loads((ROOT/p).read_text())
def write(name, content): (GEN/name).write_text(content+'\n')
def table(headers, rows, widths=None):
    align = widths or ('l'+'r'*(len(headers)-1))
    return r'\begin{tabular}{'+align+'}\n'+r'\toprule'+'\n'+' & '.join(headers)+r'\\\midrule'+'\n'+'\n'.join(' & '.join(map(str,row))+r'\\' for row in rows)+'\n'+r'\bottomrule\end{tabular}'

def bib():
    entries = [
      ('TI','Boucher, V.','Transformational Intelligence: Learning to Change the Game. October 2026; exact source edition preserved.','https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/cb1d232668564fec281dfb0ac834ddbb83ab5115/docs/Transformational_Intelligence.pdf'),
      ('GymOmega','Boucher, V.','Gym, Specialist ASI and Successor Omega: The Executable Succession Institution. Version 2.1.0, 10 August 2026. Architecture foundation, not deployed empirical validation.','https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/Gym_Specialist_ASI_Successor_Omega_v2_1_0_Print.pdf'),
      ('EnterpriseOmega','Boucher, V.','Autonomous Enterprises: Activate. Evolve. Scale. SUCCESSOR Omega Harness. 22 October 2026.','https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/d28818dc89a92c40d525d7f0c805e95d8be5978a/docs/Autonomous_Enterprises_SUCCESSOR_Omega.pdf'),
      ('GSA','4S Silversword / U.S. GSA','Authorized service schedule 47QRAA24D0077, rates effective May 2026--April 2027.','https://www.gsaadvantage.gov/ref_text/47QRAA24D0077/0ZBWRZ.3V29MN_47QRAA24D0077_47QRAA24D0077.PDF'),
      ('AlphaEvolve','Novikov et al.','AlphaEvolve: A coding agent for scientific and algorithmic discovery. 2025.','https://arxiv.org/abs/2506.13131'),
      ('Optimus','AhmadiTeshnizi, Gao and Udell','OptiMUS: Scalable Optimization Modeling with (MI)LP Solvers and Large Language Models. 2024.','https://arxiv.org/abs/2402.10172'),
      ('OptEngine','Chen et al.','OPT-Engine: Benchmarking the Limits of LLMs in Optimization Modeling via Complexity Scaling. Version 2, May 2026.','https://arxiv.org/abs/2601.19924v2'),
      ('Astra','OpenAI','GPT-6 Astra model specification and Standard API tariffs.','https://developers.openai.com/api/docs/models/gpt-6-astra'),
      ('Terra','OpenAI','GPT-6.1 Terra model specification and Standard API tariffs.','https://developers.openai.com/api/docs/models/gpt-6.1-terra'),
      ('Latest','OpenAI','Using GPT-6: Pro execution mode and workflow guidance.','https://developers.openai.com/api/docs/guides/latest-model'),
      ('SciPy','SciPy developers','linear_sum_assignment documentation. Local runtime: SciPy1.17.0.','https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html'),
      ('Flow','Google OR-Tools','Assignment as a Minimum Cost Flow Problem.','https://developers.google.com/optimization/flow/assignment_min_cost_flow'),
      ('Alpha','MontrealAI','AGI Alpha Agent v0, inspected source.','https://github.com/MontrealAI/AGI-Alpha-Agent-v0/tree/cb1d232668564fec281dfb0ac834ddbb83ab5115'),
      ('Fleet','MontrealAI','AGI Fleet Linux, inspected source.','https://github.com/MontrealAI/AGI-Fleet-Linux/tree/45759fb096faf8988f58ae5ea71248d0f35a97c7'),
      ('Jobs','MontrealAI','AGI Jobs v0, inspected source.','https://github.com/MontrealAI/AGIJobsv0/tree/bc4abbd5c28f3672275b13300e40ea26c820b8ee'),
      ('Manager','MontrealAI','AGI Job Manager, inspected source.','https://github.com/MontrealAI/AGIJobManager/tree/5d5670df9dbbc79da115e0a44b71989f34df58c1'),
      ('V93','MontrealAI','GoalOS V93 RSI Validated Skill Graph Ascension Lab. Draft HTML, not operational proof.','https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/goalos-v93-rsi-validated-skill-graph-ascension-lab-interface.html'),
      ('V974','MontrealAI','GoalOS V97.4 Private On-Chain Validated Skill Graph. Architecture/research draft.','https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/goalos_private_onchain_zk_vsg.pdf'),
      ('Merkle','MontrealAI','Merkle Roots for the Validated Skill Graph v114.','https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/Merkle_Roots_for_the_Validated_Skill_Graph_v114.pdf'),
      ('Proof','MontrealAI','PROOF LOOPS, version 2 author edition.','https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/PROOF_LOOPS_research_paper_v2_author_edition.pdf')]
    write('bibliography.tex',r'\begin{thebibliography}{99}'+'\n'+'\n'.join(r'\bibitem{'+key+'} '+esc(author)+'. '+esc(title)+r' \url{'+url+'}. Accessed 26 October 2026.' for key,author,title,url in entries)+'\n'+r'\end{thebibliography}')

def calibration():
    w=load(COST_PATH)
    rows=[[esc(s['id'].replace('_',' ')),money(s['derived_usd'],2),number(s['resource_minutes'],0)] for s in w['stages']]
    text=r'\begin{table}[htbp]\centering\small'+'\n'+table(['Activity','USD','Minutes'],rows,'p{.62\\linewidth}rr')+'\n'+r'\caption{Assumed metered usage quantities at official tariffs, per initial complete attempt. Resource minutes are unmeasured workbench occupancy. Construction, retries, storage and overhead are additional.}\end{table}'
    text+='\n\nThe initial attempt sums to '+money(w['totals']['first_complete_attempt_usd'],2)+'. Each correction costs '+money(w['correction']['derived_usd'],2)+' plus '+money(w['revalidation']['derived_usd'],2)+' for revalidation; recovery costs '+money(w['recovery']['derived_usd'],2)+'. Aggregated billed tokens include Pro subwork and reasoning. They are spread across multiple requests; no free cache or subscription allowance is deducted.'
    rows=[]
    for a,c in w['incremental_retention_options'].items():
        rows.append([esc(a),money(c['derived_budget_usd'],2),number(c['resource_minutes'],0),number(sum(c[k] for k in ['astra_input','astra_output','terra_input','terra_output'])/1e6,2)])
    text+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Retention option','Extra USD','Workbench min.','Billed tokens (M)'],rows)+r'\caption{Primary ledger B: additional one-domain extraction, generalization, fresh validation and portable packaging. Source-job construction remains in ledger A and is not charged again. Candidate scans, later reuse and upkeep are additional.}\end{table}'
    r=w['totals']['R_avoidable_reconstruction_usd'];v=w['totals']['V_avoidable_reconstruction_usd']
    text+='\n\nA paid candidate scan costs '+money(w['paid_job_emergence_scan']['derived_usd'],2)+', including scans that find no useful skill. An optimistic direct-cost-only screen requires '+number(w['incremental_retention_options']['R']['derived_budget_usd']/r,1)+' compatible R uses, '+number(w['incremental_retention_options']['V']['derived_budget_usd']/v,1)+' V uses, or '+number(w['incremental_retention_options']['bundle']['derived_budget_usd']/(r+v),1)+' joint uses. These bounds exclude acquisition, failed extraction, overlap, ongoing checks, maintenance, erosion and delay. They are not observed demand or guaranteed repayment.'
    rows=[]
    for a,c in w['investment_campaigns'].items():
        rows.append([esc(a),money(c['derived_budget_usd'],2),number(c['resource_minutes'],0),number(sum(c[k] for k in ['astra_input','astra_output','terra_input','terra_output'])/1e6,2)])
    text+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Separate campaign','USD','Workbench min.','Billed tokens (M)'],rows)+r'\caption{Optional ledger C: deliberate separate research, not a mandatory fee per job-born skill. All attempts and construction are charged once. These broader campaigns are distinct from the primary domain-specific retention options.}\end{table}'
    r=w['totals']['R_avoidable_reconstruction_usd'];v=w['totals']['V_avoidable_reconstruction_usd']
    text+='\n\nFor optional separate research, an optimistic reconstruction-only screen requires '+number(w['investment_campaigns']['R']['derived_budget_usd']/r,1)+' compatible uses for R, '+number(w['investment_campaigns']['V']['derived_budget_usd']/v,1)+' for V and '+number(w['investment_campaigns']['bundle']['derived_budget_usd']/(r+v),1)+' for the bundle. These are different activities and scopes from the primary job-born capsules. They omit failed construction, acquisition, overlap, maintenance, obsolescence and delay. This calculation cannot establish demand.'
    rows=[[esc(k.replace('_',' ')),money(w[k]['derived_usd'],2),number(w[k]['resource_minutes'],0)] for k in w['network_unit_order']]
    text+='\n'+r'\begin{table}[htbp]\centering\small'+table(['Network activity','USD / unit','Workbench min.'],rows,'p{.62\\linewidth}rr')+r'\caption{Additional network lifecycle work. Quantities and small non-model allowances are assumptions, priced using the same official tariffs. The simulator states the triggering event and frequency; these are not observed graph-service fees.}\end{table}'
    write('calibration.tex',text)

def flatten(data, prefix=''):
    for k,v in data.items():
        key=(prefix+' / '+k.replace('_',' ')).strip(' /')
        if isinstance(v,dict):
            yield from flatten(v,key)
        else:
            yield key,json.dumps(v,ensure_ascii=False) if isinstance(v,list) else str(v)

def evidence(config=None, summary=None):
    pre=r'''\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{lmodern,microtype,booktabs,longtable,tabularx,array,graphicx,xcolor,fancyhdr,xurl}
\usepackage[margin=.82in,headheight=15pt]{geometry}
\definecolor{ink}{HTML}{142B42}\usepackage[colorlinks=true,urlcolor=ink,linkcolor=ink,breaklinks=true]{hyperref}
\hypersetup{pdftitle={Paid Work, Retained Alpha: Evidence and Reproduction Companion}}
\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}\setlength{\emergencystretch}{2em}\renewcommand{\arraystretch}{1.12}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{Paid Work, Retained Alpha / Evidence}\fancyfoot[C]{\thepage}
\newcommand{\usd}[1]{\$#1}
\begin{document}
\begin{center}{\LARGE\bfseries Evidence and Reproduction Companion}\\[9pt]{\large Profitable Work First. Compounding Capability When Worthwhile.}\\[7pt]27 October 2026 / Evidence cutoff: 26 October 2026\end{center}
\section{Evidence hierarchy}
The simulator and deterministic mechanism were executed locally. Enterprise projects, purchases, collection, frontier reasoning, validation, inventions and investments are simulated. Observed local computation is kept distinct from external reported evidence, arithmetic calibration from sources, and unmeasured behavioral/performance assumptions. No copied benchmark score supplies customer acceptance or demand.
\section{Sources, relevance and limits}
'''
    chunks=[pre]
    for s in load('evidence/foundation_source_register.json')['sources']:
        chunks.append(r'\subsection*{'+esc(s['id']+' / '+s['title'])+'}')
        chunks.append(r'\textbf{Class:} '+esc(s['evidence_class'].replace('_',' ').lower())+r'. \textbf{Date:} '+esc(s.get('publication_date') or 'undated')+'.')
        chunks.append(esc(s['supports'])+' '+esc(s['does_not_support']))
        if s.get('scope'):chunks.append(esc(s['scope']))
        chunks.append(r'\url{'+s['url']+'}')
    for s in load('evidence/model_register.json')['sources']:
        chunks.append(r'\subsection*{'+esc(s['id']+' / '+s['title'])+'}')
        chunks.append(esc(s['claim'])+' '+esc(s['limits'])+r' \url{'+s['url']+'}')
    chunks.append(r'\section{Paid-work and successor foundations}')
    for s in load('evidence/paid_job_foundation_source_register.json')['sources']:
        chunks.append(r'\subsection*{'+esc(s['id']+' / '+s['title'])+'}')
        chunks.append(esc(s.get('edition',''))+'. '+esc(s.get('read_scope',''))+' '+esc(s.get('status','').replace('_',' ').lower()))
        for key in ['used_for','semantic_differences','authority_difference']:
            if key in s:
                value=s[key];chunks.append(esc('; '.join(value) if isinstance(value,list) else value))
        for f in s.get('files',[]):
            if f.get('url'):
                chunks.append(r'\url{'+f['url']+'}'+r'\par SHA-256: \nolinkurl{'+f['sha256']+'}.')
    chunks.append('The 86-page Gym Print manuscript is a read and cited research input. Its all-rights-reserved notice means the raw PDF and extracted text are not redistributed. Its synthetic examples, governance proposals and factor-sensitivity definition of Mission Beta are not substituted for this study\'s user-defined competent frontier baseline, admission rules or commercial evidence.')
    chunks.append(r'\section{Graph drafts, exact provenance and implementation boundary}')
    for s in load('evidence/graph_foundation_source_register.json')['sources']:
        chunks.append(r'\subsection*{'+esc(s['id']+' / '+s['title'])+'}')
        chunks.append(esc(s['evidence_status'].replace('_',' ').lower())+'. '+esc(s.get('read_scope','')))
        chunks.append(' '.join(esc(x) for x in s.get('limits',[])))
        if s.get('attachment_match'):chunks.append(esc(s['attachment_match']))
        if s.get('sha256'):chunks.append(r'Source SHA-256: \nolinkurl{'+s['sha256']+'}.')
        chunks.append(r'\url{'+s['url']+'}')
    chunks.append('The V93 HTML and the V85-labeled dashboard image are preserved as inspected local references with hashes and source links. Their illustrative scores do not calibrate this study. Raw copies without a repository license are not redistributed in the study archive; the new lifecycle implementation is independent. The MIT-licensed GoalOS papers and licenses are preserved. Cryptographic commitments bind bytes, not truth or Alpha.')
    chunks.append(r'\section{Component evidence versus projected commercial value}')
    chunks.append('Initial and recurring assessment units cover bounded synthetic component, version and transfer checks. A reevaluation unit prices a batch of sixteen paired component cases and eight compatibility checks; it does not purchase sixteen complete project pairs. Whole-project acceptance and dollar differences are explicit model extrapolations from component evidence through assumed reliability, demand, scope and collection mappings. These assumptions are stressed, never represented as measured frontier generalization. Prospective graph admission uses remaining incremental retention and reuse costs. Already-accounted-for source-job work is referenced but never charged twice. All job, retention and optional research spending remains in complete enterprise profit.')
    chunks.append(r'\section{Human-team scope and effort}')
    for a in load('evidence/foundation_source_register.json')['assumptions']:
        chunks.append(r'\subsection*{'+esc(a['id'])+'}')
        for key,val in flatten({k:v for k,v in a.items() if k!='id'}):
            chunks.append(r'\textbf{'+esc(key)+':} '+esc(val)+r'\par')
    chunks.append(r'\section{Complete role and stage costs}\input{generated/calibration.tex}')
    w=load(COST_PATH)
    extra=list(dict.fromkeys(['correction','revalidation','recovery','asset_construction_unit','asset_evaluation_unit','asset_integration_unit','paid_job_emergence_scan','incremental_artifact_extraction','incremental_generalization_R','incremental_generalization_V']+w['network_unit_order']))
    for stage in w['stages']+[w[k] for k in extra if k in w]:
        chunks.append(r'\subsection*{'+esc(stage['id'].replace('_',' '))+'}')
        chunks.append(esc(stage['description']))
        chunks.append('Astra billed input/output: '+number(stage['astra_input'],0)+' / '+number(stage['astra_output'],0)+'. Terra: '+number(stage['terra_input'],0)+' / '+number(stage['terra_output'],0)+'. Container sessions: '+number(stage['container_sessions_16gb'],0)+'. Other tools: '+money(stage['tools_usd'],2)+'. Derived cost: '+money(stage['derived_usd'],2)+'. All quantities are assumptions.')
    chunks.append(r'\section{Executed local mechanism and independent QA}')
    m=load('results/mechanism.json')
    chunks.append('The frozen synthetic mechanism run used '+str(m['small_instances'])+' exhaustive small comparisons and '+str(m['large_instances'])+' larger instances. All '+str(m['accepted'])+' passed their original-model checks. The unrestricted rebuild matched every output. The supplied problem family and candidate were researcher designed. Semantic truth, autonomous invention and commercial suitability were not measured.')
    chunks.append('Mutation and negative controls cover objectives, capacities, eligibility, suboptimal assignments, unsupported rules and infeasibility. A shared wrong model passes its own checker. Local median producer/checker times are '+number(m['producer_ms_median'],4)+' / '+number(m['validator_ms_median'],4)+' ms; these exclude model/API work and are not throughput calibration.')
    if (ROOT/'qa/mechanism_independent_audit.json').exists():
        chunks.append('An additional independent QA program enumerated 6,727 assignments across 96 cases and found no mismatch between checker acceptance and actual feasible optimality. This post-protocol QA is not pooled into the 300 primary mechanism instances.')
    if config:
        chunks.append(r'\clearpage\section{Frozen economic parameter register}')
        chunks.append('Entries below reproduce the executed configuration. Except source tariffs and derived arithmetic, these are explicit assumptions or policy choices. A probability in this table is not an empirical confidence interval. The code and complete machine-readable configuration control exact behavior.')
        for group,data in config.items():
            chunks.append(r'\subsection*{'+esc(group.replace('_',' '))+'}')
            if not isinstance(data,dict):
                chunks.append(esc(json.dumps(data,ensure_ascii=False)))
            else:
                chunks.append(r'\begin{longtable}{p{.44\linewidth}p{.50\linewidth}}\toprule Parameter & Value \\\midrule\endhead')
                for key,val in flatten(data):chunks.append(esc(key)+' & '+esc(val)+r'\\')
                chunks.append(r'\bottomrule\end{longtable}')
    chunks.append(r'\section{Results, audit and reproduction}')
    for filename in ['lifecycle_results.tex','protocol.tex','results.tex','thresholds.tex','sensitivity.tex','exploratory_coherence.tex','reproduction.tex']:
        if (GEN/filename).exists(): chunks.append(r'\input{generated/'+filename+'}')
    chunks.append(r'\end{document}')
    (PAPER/'evidence.tex').write_text('\n\n'.join(chunks))

def compile_pdfs():
    for source,name in [('main.tex','AGI_ALPHA_Flywheel_Profitable_Work_First.pdf'),('evidence.tex','AGI_ALPHA_Flywheel_Evidence_Companion.pdf')]:
        for _ in range(2):
            r=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',source],cwd=PAPER,capture_output=True,text=True)
            if r.returncode:
                print(r.stdout[-7000:]);raise RuntimeError('PDF compilation failed: '+source)
        (PAPER/name).write_bytes((PAPER/source.replace('.tex','.pdf')).read_bytes())
        print(name)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compile',action='store_true');p.add_argument('--config',type=pathlib.Path)
    args=p.parse_args();bib();calibration()
    config=json.loads(args.config.read_text()) if args.config else None
    evidence(config)
    if args.compile:compile_pdfs()
