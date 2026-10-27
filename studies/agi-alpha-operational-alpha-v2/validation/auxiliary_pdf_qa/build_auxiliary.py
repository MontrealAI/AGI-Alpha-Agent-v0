"""Build the two self-contained auxiliary LaTeX sources from frozen evidence.

This file does not alter scientific inputs, scorers, historical results or the main paper.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper"
QA = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


summary = read("opportunity/results/confirmation_summary.json")
missions = {m["id"]: m for m in read("opportunity/results/trials/S3_U/frozen_submission/qualification/packet.json")["missions"]}
econ = read("economics/results/summary.json")
hold = read("economics/value_results/summary.json")["value_minus_original_same_fresh_worlds"]["reference/shared_retention"]
prescreen = read("economics/prescreen_results/prescreen_summary.json")
arrangement = read("opportunity/arrangement/results/reference_selection.json")["selection"]
model_manifest = read("sources/official_model_manifest.json")

facts = {
    "edition": "2.1.0",
    "s3": summary,
    "scientific_mean": missions["equilibrium"]["mean_acetylation"],
    "tau_model": missions["calibrated_clock"]["tau_model"],
    "tau_interval": missions["calibrated_clock"]["tau_physical_interval"],
    "original_reference_profit": {k: econ["groups"]["reference/" + k]["mean_profit_usd"] for k in ["ordinary_U", "expert_E", "enhanced_Eplus"]},
    "hold_increment": hold,
    "prescreen": prescreen,
    "arrangement_expected_usd": arrangement["expected_contribution_cents"]["numerator"] / arrangement["expected_contribution_cents"]["denominator"] / 100,
    "arrangement_success_usd": arrangement["success_contribution_cents"] / 100,
    "arrangement_opening_usd": arrangement["required_opening_cash_cents"] / 100,
}
macros = [r"% Numerical macros derived from archived JSON; see auxiliary_pdf_qa/facts.json."]
def macro(name, value):
    macros.append("\\newcommand{\\" + name + "}{" + str(value) + "}")
for arm, short in [("U", "U"), ("E", "E"), ("E_plus", "Plus")]:
    a = summary["arms"][arm]
    for k, label, fmt in [("elapsed_seconds", "Wall", ".1f"), ("operations", "Ops", "d"), ("logged_python_executions", "Runs", "d"), ("recorded_test_methods_including_public", "Tests", "d"), ("tool_elapsed_seconds", "Tool", ".3f")]:
        macro("S" + short + label, format(a[k], fmt))
macro("ScientificMean", f'{facts["scientific_mean"]:.10f}')
macro("TauModel", f'{facts["tau_model"]:.10f}')
macro("TauLow", f'{facts["tau_interval"][0]:.10f}')
macro("TauHigh", f'{facts["tau_interval"][1]:.10f}')
for k, name in [("ordinary_U", "OriginalU"), ("expert_E", "OriginalE"), ("enhanced_Eplus", "OriginalPlus")]:
    macro(name, f'{facts["original_reference_profit"][k]:,.2f}')
macro("HoldGain", f'{hold["mean_increment_usd"]:.5f}')
macro("HoldLow", f'{hold["conditional_monte_carlo_95_interval_usd"][0]:.5f}')
macro("HoldHigh", f'{hold["conditional_monte_carlo_95_interval_usd"][1]:.5f}')
macro("PrescreenGain", f'{prescreen["paired_mean_net_increment_usd"]:.6f}')
macro("ArrangementExpected", f'{facts["arrangement_expected_usd"]:.2f}')
macro("ArrangementSuccess", f'{facts["arrangement_success_usd"]:.0f}')
macro("ArrangementOpening", f'{facts["arrangement_opening_usd"]:.0f}')
MACROS = "\n".join(macros)

PREAMBLE = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern,microtype,amsmath,amssymb}
\usepackage[margin=0.76in,headheight=15pt,headsep=16pt,footskip=25pt]{geometry}
\usepackage[table]{xcolor}
\usepackage{booktabs,tabularx,array,longtable}
\usepackage{enumitem,fancyhdr,titlesec,xurl}
\usepackage{hyperref}
\definecolor{Navy}{HTML}{142C46}
\definecolor{Teal}{HTML}{087E8B}
\definecolor{Gold}{HTML}{B58A2A}
\definecolor{Pale}{HTML}{EAF4F5}
\definecolor{Ink}{HTML}{243444}
\hypersetup{colorlinks=true,urlcolor=Teal,linkcolor=Teal,pdfauthor={Vincent Boucher -- President of MONTREAL.AI},pdftitle={AGI ALPHA FLYWHEEL -- When Capability Creates Opportunity},pdfsubject={Additive opportunity-first research edition 2.1.0, 27 October 2026}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5.2pt plus 0.6pt}
\setlength{\emergencystretch}{2em}
\renewcommand{\arraystretch}{1.18}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\setlist[itemize]{leftmargin=15pt,itemsep=2.5pt,topsep=3pt,parsep=0pt}
\setlist[enumerate]{leftmargin=18pt,itemsep=3pt,topsep=3pt,parsep=0pt}
\titleformat{\section}{\Large\bfseries\color{Navy}}{}{0em}{}
\titleformat{\subsection}{\normalsize\bfseries\color{Teal}}{}{0em}{}
\titlespacing*{\section}{0pt}{8pt}{6pt}
\titlespacing*{\subsection}{0pt}{7pt}{3pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{Navy}{\textbf{AGI ALPHA FLYWHEEL}}}
\fancyhead[R]{\small\textcolor{Teal}{AUXILIARYLABEL\enspace |\enspace 2.1.0}}
\fancyfoot[L]{\footnotesize\textcolor{Navy}{27 October 2026\enspace\textbullet\enspace Additive opportunity-first edition}}
\fancyfoot[R]{\footnotesize\textcolor{Navy}{\thepage}}
\renewcommand{\headrulewidth}{0.5pt}
\renewcommand{\footrulewidth}{0pt}
\newcommand{\src}[1]{\textcolor{Teal}{\scriptsize[#1]}}
\newcommand{\keybox}[1]{\par\smallskip\noindent\begingroup\setlength{\fboxsep}{9pt}\colorbox{Pale}{\parbox{\dimexpr\linewidth-18pt\relax}{#1}}\endgroup\par\smallskip}
\newcommand{\eyebrow}[1]{{\small\bfseries\color{Gold}\MakeUppercase{#1}}\par}
\newcommand{\pagename}[2]{\eyebrow{#1}\section*{#2}}
\newcommand{\sourceline}[1]{{\footnotesize\color{Ink}#1\par}}
\newcommand{\capline}[1]{{\small\color{Ink}#1\par}}
\newcommand{\fulltitle}{\textcolor{Navy}{\LARGE\bfseries AGI ALPHA FLYWHEEL ---\\[3pt]When Capability Creates Opportunity}\par\vspace{5pt}{\large Transformational Intelligence, Experience-Trained Specialists\\and the Expanding Frontier of Profitable Work}\par\vspace{5pt}{\normalsize\bfseries Vincent Boucher --- President of MONTREAL.AI}\par}
"""

BRIEF = r"""
\begin{document}
\eyebrow{Executive brief\enspace |\enspace Edition 2.1.0}
\fulltitle
\vspace{3pt}
{\small\bfseries\color{Gold}FIND YOUR ALPHA. BUILD YOUR SUCCESSOR $\Omega$.}

\keybox{\textbf{A consequential opportunity: qualify a scientific model for its next use.} A published model may support an equilibrium result while lacking the evidence needed for a physical-time prediction. This edition constructs an executable qualification instrument, transfers it, and tests whether expert operation changes accepted outcomes. All four routes pass: ordinary use, expert operation, the enhanced recipient and a conventional construction. The result is useful scoped capability, with commercial advantage still unestablished.}

\subsection*{Explore before constructing}
Six materially different candidates were investigated: biological mechanism discovery, laboratory protocol portability, elevation/datum qualification, legacy PLC migration, security qualification and physical measurement qualification. Their prior art, missing evidence and smallest decisive tests were retained. A bounded follow-up selected \textbf{S3: scientific-model reuse qualification}. The 2026 PEtab Select paper identifies the cost of comprehensive identifiability analysis and selective automation as an unresolved direction. This motivates selective qualification; it does not establish novelty or paying demand. \src{S1--S3}

\subsection*{The proposed service and its decision}
Research software teams, core facilities and modeling services would receive a source-bound packet answering: \emph{Which requested predictions are supported, what assumptions remain, and which measurement or analysis is needed next?} The packet includes executable calculations, source and request fingerprints, a specific unsupported-use witness, a calibration obligation and a fresh-scope decision. It preserves valid uses of the original model. It grants no execution authority and makes no biological validation claim. \src{S4--S6}

\begin{tabularx}{\linewidth}{@{}L{0.25\linewidth}Y@{}}
\toprule
\textbf{Constructed asset} & \textbf{What it makes inspectable} \\
\midrule
Reuse qualification instrument & Equilibrium, an external-clock ambiguity, conditional calibration and a changed-mission boundary. \\
Fresh recipient capsule & The exact retained code can be consumed without inheriting the prior mission's meaning or permission. \\
Arrangement checker & Participation, rights, acceptance, cash timing, withdrawals and failure are separate gates. \\
\bottomrule
\end{tabularx}

\subsection*{Decision for the enterprise}
Retain this edition as a reproducible research instrument and a customer-discovery proposition. \textbf{Do not claim an economic feasibility crossing or admit the scientific capability to production.} A matched human-service quote, actual full-cost measurement, mission-specific scientific review and evidence of buyer acceptance remain necessary. Current native admission is unsupported for this scope, the evidence contains fewer than six independent task clusters, and its monetary denominator is unknown. \src{S5--S8}

\newpage
\pagename{Evidence that changes the decision}{A useful witness; no exclusive advantage}

The original H4 source contains \textbf{252 public measurement rows at equilibrium}, 15 observable identifiers and a normalized 16-state model. Its selected eight-parameter fit is not disproved by the broader 33-parameter candidate space. The original study's fixed normalization remains valid. The new restriction concerns \emph{reuse for a physical-time prediction}: a clock calibration is absent from the supplied source. \src{S3--S4}

\begin{tabularx}{\linewidth}{@{}L{0.27\linewidth}Y@{}}
\toprule
\textbf{Frozen mission} & \textbf{Computational result and meaning} \\
\midrule
Preserve equilibrium use & Mean acetylation \ScientificMean{}, conditional on the supplied fit; no new biological observation. \\
Challenge unsupported clock & Common rate scaling preserves equilibrium but changes a finite-time state by up to 0.1433168194. It exposes missing external time calibration, not a new fitted mechanism. \\
Propagate supplied calibration & An \emph{assumed} conversion interval $[0.4,1.6]$ per minute maps model relaxation time \TauModel{} to $[\TauLow{},\TauHigh{}]$ minutes. This is not a measured confidence interval. \\
Recheck a new purpose & The Boehm finite-time source requires fresh dynamic qualification. The recipient withdraws the inherited equilibrium witness; no new nonlinear fit is claimed. \\
\bottomrule
\end{tabularx}

\subsection*{Fair access to the formulation and conventional methods}
All three hosted arms received the same scientific inputs, discovered formulation and acceptance requirements, with a 1,200-second/48-operation outer envelope. U had a reasonable brief and tools; E added the established expert workflow; E+ added the frozen instrument. A separately written conventional solution also qualified. \src{S5--S6}

\begin{center}
\begin{tabular}{@{}lrrrr@{}}
\toprule
 & \textbf{U} & \textbf{E} & \textbf{E+} & \textbf{Conventional} \\
\midrule
Accepted missions & 4/4 & 4/4 & 4/4 & 4/4 \\
Recorded wall time, s & \SUWall & \SEWall & \SPlusWall & not matched \\
Logged operations & \SUOps & \SEOps & \SPlusOps & not matched \\
Python executions & \SURuns & \SERuns & \SPlusRuns & separate control \\
\bottomrule
\end{tabular}
\end{center}

\textbf{Operational Alpha, E--U: 0 accepted-outcome percentage points. Additional learned Alpha, E+--E: 0 points.} These descriptive ties do not prove population equivalence. One campaign over two public source families, one recipient per arm and nonrandomized timings cannot establish a general latency effect or ordinary-human-user performance. Tokens, hidden compute, residual human attention and accepted-output dollar cost are unobserved. \src{S5}

The E+ recipient received byte-identical code and executed five instrument functions. The existing transport/access fixture passed \textbf{31/31 controls} with synthetic identities. This establishes technical transfer and fixture conformance, not live ENS authentication, production admission, a graph premium or independently possessed specialist intelligence. \src{S7}

\newpage
\pagename{Commercial blueprint}{Sell an accepted decision; earn the next step}

\textbf{Offer.} Begin with a tightly scoped, reproducible model-reuse qualification packet. Agree on the prediction, evidentiary standard, turnaround, customer effort and acceptable deferral before work. Obtain a comparable human quote and a buyer's alternative; price useful accepted work rather than marking up compute. Harvard Chan's published FY26 consulting rates of \$193/hour for external academic clients and \$265/hour for industry are a sequencing-analysis analogue, \emph{not an S3 quotation}. No H4 price is inferred from them. \src{S8}

\textbf{Deliver and account.} Automate source preparation, supported calculations, evidence binding and packaging. Charge each activity once: A covers complete contracted delivery including learning required for that outcome; B covers additional assessment, retention, sharing and upkeep; C covers optional further research or Gym work. This edition's research was unpaid. Actual collections are \textbf{\$0}; complete actual cost and profit remain unknown. \src{S5; S9--S10}

\begin{tabularx}{\linewidth}{@{}L{0.27\linewidth}Y@{}}
\toprule
\textbf{Conditional experiment} & \textbf{Decision-relevant result} \\
\midrule
New arrangement diagnostic & With zero assumed technical saving, conventional coordinated delivery is selected: \$\ArrangementExpected{} expected contribution, \$\ArrangementSuccess{} successful contribution and \$\ArrangementOpening{} required opening cash. Inputs are arbitrary diagnostic conditions, not an S3 forecast. Seventeen of 32 fresh synthetic stress cases lose money. \\
Payment timing illustration & A separately useful accepted milestone can reduce required opening cash from \$470 to \$370, with successful contribution unchanged at \$200. A ten-day release delay raises all tested routes to \$840. Refundable principal remains encumbered. \\
Preserved enterprise evidence & The original simulation and its failures remain. A separately frozen controller chooses HOLD and improves modeled net value by \$\HoldGain{} versus the original shared policy on the same fresh worlds. This avoids assumed assessment losses; it is not new learned Alpha or recovered historical profit. \\
\bottomrule
\end{tabularx}

\subsection*{A bounded next decision}
Run an independently reviewed pilot with actual prospective beneficiaries and fresh model families, including unsupported cases. Record complete cost and acceptance, obtain the human outside option, and test whether reusable construction saves adaptation work. Test shared construction and coordinated commitments separately and together. Preserve HOLD, conventional delivery and buyer nonparticipation as real options. \src{S9--S11}

\textbf{Retain or expand only if} prospective reusable benefits exceed additional costs and risks, current admission is supported, and available funds cover every dated obligation. A feasibility crossing requires the enhanced route alone to satisfy frozen useful-quality, deadline, customer-effort and price conditions at positive complete margin. No such crossing is observed here.

\vfill
\sourceline{\textbf{Evidence map.} S1--S11 identify the dossier, public scientific sources, frozen instrument/protocol/results, native transfer, human-rate analogue, arrangement checker, preserved economics and foundations in the accompanying evidence companion. Complete paths, provenance, assumptions and reproduction steps are included there.}
\sourceline{\textbf{Provenance.} AI-assisted researcher construction and internal review; no autonomous invention, new biology, new algorithm, model-weight training, live customer sales or token valuation is asserted. Earlier papers, corrections and failed trials are preserved.}
\end{document}
"""

COMPANION = r"""
\begin{document}
\eyebrow{Evidence companion\enspace |\enspace Edition 2.1.0}
\fulltitle
\vspace{3pt}
{\small\bfseries\color{Gold}FIND YOUR ALPHA. BUILD YOUR SUCCESSOR $\Omega$.}

\section*{1. What this edition establishes}
This additive edition investigates scientific-model reuse qualification after a six-candidate opportunity dossier and a bounded follow-up. The constructed instrument preserves an original equilibrium use, exposes an unsupported physical-time interpretation, propagates an explicitly assumed calibration and withdraws an inherited witness on a fresh finite-time source. It leaves executable capability and a cash-feasibility checker. It establishes neither a new biological finding nor superior invention, learned superiority or profitable commercial expansion. \src{S1--S7; S9}

\keybox{\textbf{The decisive comparison is tied.} U, E, E+ and a conventional construction each satisfy all four frozen missions. E+ consumes the unchanged retained code, but incremental accepted outcomes and complete-cost benefit are unestablished. Actual collections are \$0. Actual complete cost, profit and customer effort are unknown.}

\begin{tabularx}{\linewidth}{@{}L{0.22\linewidth}Y@{}}
\toprule
\textbf{Evidence class} & \textbf{Application in this edition} \\
\midrule
Observed execution & Archived hosted submissions, recorded operations, accepted outputs, actual capsule bytes and local cryptographic/access controls. \\
Sourced facts & Public scientific files, official model documentation and published service-rate analogues; each has a source and retrieval/pin record. \\
Computed consequence & Stationary distribution, clock witness and necessary dimension bound, conditional on the specified source and mathematical scope. \\
Assumed input & New requests, external-clock conversions, calibration interval, hypothetical buyers, prices, costs, outside options and scenario weights. \\
Simulated result & Conditional enterprise histories, arrangement outcomes, synthetic losses and cash prefixes. These are not customers or earned revenue. \\
Unmeasured quantity & Actual model billing/tokens, full labor and research cost, buyer willingness to pay, real authentication and production obligations. \\
\bottomrule
\end{tabularx}

\subsection*{Interpretive boundaries}
The unit of S3 inference is \textbf{one four-mission campaign over two public source families, with one hosted recipient per arm}. Changed requests and numerical assertions do not create independent opportunities. H4 informed instrument development. Boehm supplies a fresh scope-withdrawal check; it is not a new nonlinear-fit challenge. Public sources prevent a contamination-proof claim. Separate internal implementations do not constitute external institutional replication. \src{S5--S6}

\subsection*{Additive chronology}
The previous software pilot, C5 supplied composition study, native fixture and original enterprise simulation remain intact. The opportunity dossier precedes S3 selection; selection precedes the instrument; protocol and exact S3 prompts precede participant exposure. Pre-exposure identity corrections and previous freezes remain archived. A later HOLD controller and prospective admission prescreen preserve the old economic outcomes. \src{S1; S5; S10}

\newpage
\pagename{Opportunity selection}{2. The unresolved gap and the search that found it}
The initial exploration examined six materially different possibilities, with beneficiaries, prior art, missing evidence, a smallest decisive test and a falsifier. It did not declare entire industries exhausted or infer novelty from absent search results. The initial directions and their negative findings are part of the evidence, not discarded setup. \src{S1}

\begin{tabularx}{\linewidth}{@{}L{0.14\linewidth}L{0.30\linewidth}Y@{}}
\toprule
\textbf{Candidate} & \textbf{Useful outcome sought} & \textbf{Selection consequence} \\
\midrule
S1 & Discover an H4 biological mechanism & Broad question already addressed; new biological evidence absent. Redirect to model-use qualification. \\
S2 & Port a laboratory protocol across settings & Close prior art and no physical oracle; do not equate a computational rewrite with validated transfer. \\
ENG1 & Qualify mixed elevation/datum inputs & Twelve metadata fixtures and strong existing GIS alternatives; a paying service gap remains unestablished. \\
ENG2 & Qualify legacy PLC migration & Formal-service precedent exists; no authorized vendor execution oracle for a decisive test. \\
M1 & Qualify security capabilities & Existing tools and funding are substantial; the specific unmet gap was not isolated. \\
M2 & Qualify a physical measurement & Missing laboratory evidence and overlap with the previous Harness example. \\
\bottomrule
\end{tabularx}

\subsection*{Why the bounded S3 follow-up was selected}
PEtab Select already supplies model-space specification, model-selection support and integrations. Its 2026 paper describes comprehensive identifiability analysis across large model spaces as costly and selective automation as future work. That documented gap supports a \emph{selective reuse-qualification instrument}: bind a new scientific request to source evidence, identify a concrete unsupported interpretation, and specify the missing evidence. It does not justify claiming a novel identifiability algorithm or an empty market. \src{S2}

The beneficiary is a team deciding whether a published model can safely support a \emph{particular next prediction}. The costly dependency is expert source interpretation and requalification across data, equations, units, requested meanings and missing observations. The smallest test preserves a supported use while refusing an unsupported one, then transfers to a changed source without carrying over the old conclusion. It is falsified if competent conventional work already produces the same accepted packet at no greater complete burden, or if prospective buyers do not value the decision enough to fund delivery. \src{S1; S3}

\subsection*{Declared exploration and construction limits}
Selection was recorded at 16:16:24 UTC on 27 October 2026 before instrument construction. The bounded construction allocated 30 minutes to the developer, 30 minutes to internal independent review, and a 1,200-second/48-operation envelope to each fresh hosted arm. No large simulator or full model-selection search was built to rescue an unconvincing opportunity. These are protocol limits, not a priced research budget or complete labor measurement. \src{S1; S5}

\textbf{What was discovered versus supplied.} The reuse gap was sharpened through source investigation. Researchers supplied the eventual requests, clock-scale examples, calibration interval and benchmark composition. All confirmatory arms received the discovered formulation. The observed experiment evaluates execution and transfer after that discovery; it does not compare autonomous discovery policies.

\newpage
\pagename{Transformation witness}{3. Preserve the science; expose the missing clock}
\textbf{Original purpose.} The H4 source models stationary combinatorial acetylation patterns. The recovered public package has 252 measurement rows at $t=\infty$, 15 observable identifiers, 16 normalized states and a selected eight-parameter fit. The fixed $d_{a,b}=1$ normalization is legitimate. The larger 33-parameter superset is a model-space declaration, not the selected fit. No physical time-unit declaration or independent clock calibration is supplied. \src{S3--S4}

\textbf{New requested purpose.} A recipient asks for physical relaxation time. Equilibrium data alone leave the common physical clock unspecified. Removing that information restriction requires additional calibration; computing harder cannot manufacture it. The instrument turns an ambiguous request into a preserved equilibrium result, an explicit counterexample and a bounded evidence obligation.

For the supported linear conversion model, let $Q$ be its rate matrix and $\pi$ a normalized stationary state. The witness is elementary:
\[
Q\pi=0 \Longrightarrow (cQ)\pi=0,\qquad
e^{cQt}x_0=x(ct),\qquad c>0.
\]
Two external conversions, $c=0.5$ and $c=3$, preserve equilibrium to numerical tolerance while producing a maximum finite-state difference of 0.1433168194 at the requested time. This scales the external mapping from model time to physical time; it does not treat the fixed source normalization as a new fitted free parameter. \src{S4--S6}

\begin{tabularx}{\linewidth}{@{}L{0.27\linewidth}Y@{}}
\toprule
\textbf{Accepted output} & \textbf{Meaning and falsifier} \\
\midrule
Equilibrium summary & Mean acetylation \ScientificMean{}, conditional on the supplied fit. A different valid source interpretation or failed numerical conservation check would invalidate the calculation. \\
Necessary dimension bound & At most 15 independent equilibrium mean coordinates for the normalized 16-state distribution. The 33-rate superset has a dimension deficit of at least 18. This does not prove the selected eight-parameter model unidentifiable. \\
Calibrated interval & $\tau_{\rm model}=\TauModel{}$. An assumed $c\in[0.4,1.6]$ per minute yields $\tau_{\rm physical}\in[\TauLow{},\TauHigh{}]$ minutes. Unsupported calibration invalidates the physical interpretation. \\
Fresh-source withdrawal & The Boehm source has 48 rows, three observables and 16 finite times from 0 to 240. Its reference simulation contrasts block automatic reuse of the stationary-only witness. \\
\bottomrule
\end{tabularx}

\subsection*{Scope that keeps the witness honest}
The instrument covers closed, irreducible, first-order one-to-one conversion networks with one constant unit-volume compartment, a normalized initial total of one, constant parameters and no condition overrides. It is not a general SBML/PEtab engine or complete structural-identifiability analysis. Its spectral time is the inverse slowest nonzero decay rate, not a half-life, settling guarantee or biological confidence interval. The fixed $10^{-9}$ zero threshold and ordinary floating-point intervals limit very slow or poorly separated modes. Boehm contrasts come from supplied reference simulations; no new nonlinear fit or biological experiment occurred. \src{S4; S6}

\newpage
\pagename{Causal comparison}{4. Same formulation, fresh acceptance, tied outcomes}
\begin{tabularx}{\linewidth}{@{}L{0.10\linewidth}Y@{}}
\toprule
\textbf{Arm} & \textbf{What it contains} \\
\midrule
H & An equivalent human service matched on deliverable, acceptance, deadline and customer effort. No matched S3 quotation or delivery trial was obtained. \\
U & The inherited hosted frontier model, a complete reasonable brief, public scientific inputs, ordinary tools and permission to construct conventional alternatives. No sampled ordinary human users. \\
E & U plus the previously frozen contract-oriented expert workflow: explicit requirements, decomposition, execution, verification and correction. It was not optimized on S3 confirmation. \\
E+ & E plus the new frozen generic reuse instrument received in a fresh context. The recipient may invoke it but must recheck source, request, calibration and scope. \\
\bottomrule
\end{tabularx}

The same outer budget applies to U, E and E+: 1,200 seconds, 48 logged operations and a 45-second subprocess limit. The runner records successful reads, writes, executions, elapsed time and output bytes; it does not observe hidden reasoning compute, all unsuccessful invocations or billed tokens. Participants have a shared-host protocol boundary rather than adversarial OS isolation. The model is the inherited hosted GPT-6 Astra Pro environment; exact API snapshot and configured effort are not verified. \src{S5; S12}

\begin{center}
\begin{tabular}{@{}lrrr@{}}
\toprule
\textbf{Observed quantity} & \textbf{U} & \textbf{E} & \textbf{E+} \\
\midrule
Accepted missions & 4/4 & 4/4 & 4/4 \\
Recorded wall time (seconds) & \SUWall & \SEWall & \SPlusWall \\
Logged operations & \SUOps & \SEOps & \SPlusOps \\
Python executions & \SURuns & \SERuns & \SPlusRuns \\
Nonzero Python exits & 0 & 0 & 0 \\
Recorded test methods, including public & \SUTests & \SETests & \SPlusTests \\
Subprocess time (seconds) & \SUTool & \SETool & \SPlusTool \\
Actual accepted-output dollar cost & unknown & unknown & unknown \\
\bottomrule
\end{tabular}
\end{center}

All inputs remain unchanged and all arms stay within the declared envelope. Each mission also receives a changed request. Those variants test binding and generalization within the mission; they are not independent samples. E--U and E+--E accepted-outcome differences are both zero. One nonrandomized run per arm cannot estimate a stable speed advantage. Equal acceptance at an outer budget is observed; matched-accepted-quality complete-cost dominance is unmeasured. \src{S5}

\subsection*{Conventional control and evaluator independence}
The independent conventional construction also passes 4/4. It uses file inspection, linear solves, matrix exponentials and eigenvalues without importing the retained instrument. The protected oracle independently uses an SVD stationary solution and Poisson uniformization, and checks changed source/request identities and empty authority. It imports neither candidate nor conventional code. Both remain internal researcher constructions; conventional authoring cost is unknown. Automated acceptance is paired with explanatory-prose review. \src{S6}

\textbf{No discovery effect is identified.} Giving the discovered formulation to every arm is a fair execution comparison and a useful conventional control. A later study of learning to invent must independently vary discovery policy and inherited artifact across fresh opportunity campaigns.

\newpage
\pagename{Capability lineage and access}{5. Inherit an instrument, re-earn the mission}
\begin{tabularx}{\linewidth}{@{}L{0.24\linewidth}Y@{}}
\toprule
\textbf{Lineage element} & \textbf{Provenance and evidence} \\
\midrule
Established expert operation & A versioned contract-oriented workflow predates S3 confirmation. It is not credited as newly learned scientific expertise. \\
New instrument v1.0.0 & Researcher-authored unpaid construction using established mathematics. Scope, prerequisites, rights, costs, limitations and executable code travel together. \\
Separate E+ recipient & Fresh context receives the E card and capsule; exact received bytes match and instrument code remains unchanged. \\
Actual recipient use & Executes \texttt{inventory}, \texttt{stationary}, \texttt{dimension\_bound}, \texttt{clock\_witness} and \texttt{qualify}. All four mission packets are accepted. \\
Boundary retained & New source and changed request cause requalification. No earlier acceptance or membership grants consequential authority. \\
\bottomrule
\end{tabularx}

\subsection*{What transferred}
The capsule contains executable qualification code, manifest, capability card and documentation. Every receipt binds current source files, full supplied evidence, request semantics and calibration evidence; authority is empty. The instrument's bounded inventory capability extends beyond its dynamics. An unsupported model must be deferred to an appropriate method, not declared scientifically invalid. Calibration labels remain supplied metadata rather than authenticated experimental evidence. \src{S4--S7}

The recipient's observed technical use is meaningful, but the accepted-outcome comparison is tied. Service invocation would provide access rather than independent possession of the service's intelligence; this edition actually transfers a local executable capsule. No proprietary model weights were changed, and no optional Gym campaign produced the scientific result. Training is an available future decision only when evidence supports expected net benefit.

\subsection*{Reuse the existing protected network}
The existing native fixture transports the actual scientific capsule and passes 31/31 controls. It exercises actual local cryptography and the existing authority/lifecycle/accounting interfaces. Identities, membership and role records are synthetic. The fixture is not live \texttt{*.agent.agi.eth} authentication, deployed governance or settlement. The ordinary-library comparison uses identical capsule bytes and permissions; no graph-specific performance value is established. \src{S7; S10}

\keybox{\textbf{Current production admission remains unsupported.} The scientific scope is outside the unchanged native admission scope, fewer than six independent evidence clusters are available, and complete monetary evidence is missing. A passing transport fixture or capability graph entry cannot bypass these gates. New production scope requires authorized owner work, not a competing registry.}

\subsection*{Conditions for selective sharing}
Admitted rights-cleared content should be eligible for all currently authorized members through the existing protected network. Membership permits access, not blanket execution. Retention must exclude customer secrets, restricted IP, protected cases and scorer internals. Assess expected reusable benefit against additional packaging, testing, rejected-candidate, serving, upkeep and revocation costs. Requalify after material source, tool, model, dependency or mission changes; preserve fresh inputs, semantics and authority even when a generic check can be reused. \src{S7; S11}

The capsule digest begins \texttt{87875aa445146965}; the complete SHA-256 and exact file inventory are in the transfer receipt. Transport equality proves which artifact arrived. It does not prove economic value, scientific validity outside scope or an entitlement to use it on a new mission.

\newpage
\pagename{Commercial evidence and costs}{6. A complete denominator, with unknowns left visible}
The proposed paid outcome is a qualified scientific decision and reproducible packet. A buyer may choose human delivery, an existing tool, deferral or no purchase. Price must be tested against the useful outcome and outside option. There is no S3 customer commitment, matched human quote, observed sale or accepted customer effort/deadline envelope. Actual collections are zero; full cost, profit, obligations and freely available operating funds have not been established. \src{S5; S8--S10}

\begin{tabularx}{\linewidth}{@{}L{0.11\linewidth}Y@{}}
\toprule
\textbf{Ledger} & \textbf{Disjoint responsibility} \\
\midrule
A & Complete paid-job delivery, including preparation, model/tool use, necessary learning, verification, corrections, failures, refunds, customer support and genuine residual obligations. \\
B & Additional candidate assessment, retention, admission, distribution and upkeep beyond what A already paid for. Include rejected candidates, false admissions and failed transfer. \\
C & Optional further Gym development or research beyond contracted delivery, including unsuccessful experiments and prototypes. \\
\bottomrule
\end{tabularx}

Unpaid research cannot be relabeled paid-job learning, and unobserved labor is not zero cost. Cash expense and displaced-work opportunity cost remain separate. Seed capital, escrow principal, customer savings, token issuance and speculative opportunity value are never earned revenue. A method's contribution is measured once; adding Operational Alpha again to profit that already assumes E would double count it.

\subsection*{Human reference: useful context, not an invented quote}
Harvard Chan's published FY26 bioinformatics consulting rates are \$193/hour for external academic clients and \$265/hour for industry. They concern high-throughput sequencing analysis and require project-specific scoping; they are a professional-service analogue, not a matched S3 price. The older software fixture's Arc backend range of \$61--80/hour and assumed hours remain attached to that fixture. Neither rate establishes a particular prompt's value or justifies arbitrary routine reviewer staffing. \src{S8; S10}

\subsection*{Preserved modeled enterprise results}
The original reference profile's simulated mean profits are U \$\OriginalU{}, E \$\OriginalE{} and E+ \$\OriginalPlus{}. Their difference includes supplied setup and assessment costs. They are not observed S3 economics. Original policies, rejected assessments, failed prototypes and corrections remain archived. The graph and ordinary library with the same content and permissions tie in the modeled comparisons. No Gym investment is selected. \src{S10}

A separately frozen controller searches production, pricing, optional learning and HOLD, then chooses HOLD for the optional learning decisions. Against the old shared policy on the \emph{same fresh worlds}, mean modeled net value improves by \$\HoldGain{}; the conditional Monte Carlo interval is [\$\HoldLow{}, \$\HoldHigh{}]. It avoids assumed assessment losses. This is neither newly learned capability nor retrospective recovered profit.

The prospective reachability prescreen reduces structurally unreachable assessments from 1,412 to zero across 128 artificial worlds. Modeled net value rises by \$\PrescreenGain{} per world; all admission counts are preserved and 25 false admissions remain under each policy. Reachability prevents an impossible test; it does not establish that a reachable candidate is worth assessing. Simulation intervals quantify random-world variation under assumptions, not whether those assumptions describe a market. \src{S10}

\newpage
\pagename{Joint capability and arrangement}{7. Contribution is different from financing}
The exact arrangement checker represents a joint package: technical construction, participants, uniform price, useful accepted portions, rights, dates, financing and evidence. It permits nonparticipation, withdrawal after construction, common technical failure, partial acceptance, default, refunds and support costs. It checks participant value against supplied outside options and preserves HOLD. The unrestricted conventional entrepreneur gets the same alternatives and permissions. \src{S9}

The finite search contains 60 configuration records and 4,320 candidate plans, including repeated plans in restricted menus. Four cells separate neither intervention, technical construction alone, coordinated demand alone and both. A 50\% saving case is an explicit sensitivity, not measured adaptation benefit. The default saving is zero and quality uplift is zero. This is neither a global contract optimum nor a calibrated market model.

\begin{center}
\begin{tabular}{@{}lr@{}}
\toprule
\textbf{Zero-saving reference diagnostic} & \textbf{Conditional value} \\
\midrule
Selected technical route & conventional delivery \\
Selected participants / mission price & P2 and P3 / \$300 \\
Expected contribution & \$\ArrangementExpected{} \\
Successful contribution & \$\ArrangementSuccess{} \\
Worst named contribution & $-\$40$ \\
Required opening cash, including reserve & \$\ArrangementOpening{} \\
Declared opening cash / protected reserve & \$500 / \$50 \\
Fresh synthetic stress cases with loss & 17 of 32 \\
\bottomrule
\end{tabular}
\end{center}

All these prices, values, costs and weights are arbitrary diagnostic inputs. The selected plan does not invest in the new instrument. Its actual-business status remains \emph{unestablished because costs, values and commitments are unmeasured}. None of the 32 stress cases exceeds its supplied opening-cash cap; the losses remain. The sample is not a market loss-probability estimate.

\subsection*{Cash-prefix discipline}
Let $C(t)$ be cumulative cash inflow less cash expense before opening capital, $E(t)$ refundable escrow liability, $S(t)$ support reserve and $R$ protected reserve. Required opening capital is
\[
L_{\min}=\max_t\bigl\{0,E(t)+S(t)+R-C(t)\bigr\}.
\]
A deposit increases cash and refund liability equally. Only an actually accepted, earned release can finance later obligations, subject to the agreed terms and reserves. Successful contribution, scenario-weighted expected contribution, cash balance, unpaid invoices, refunds and available funds are separate outputs.

\begin{tabularx}{\linewidth}{@{}Yrr@{}}
\toprule
\textbf{Post-confirmation timing illustration} & \textbf{Opening cash} & \textbf{Success} \\
\midrule
Post-acceptance / refundable escrow, immediate & \$470 & \$200 \\
Independently useful accepted milestone, immediate & \$370 & \$200 \\
Any tested route with ten-day release delay & \$840 & \$200 \\
\bottomrule
\end{tabularx}
The milestone's independent usefulness is assumed, not demonstrated buyer acceptance. This arithmetic illustration changes financing timing without claiming a technical improvement or an additional confirmation sample. The checker independently reproduces the historical Invent the Economy quantities without copying them into S3. \src{S9; S11}

\newpage
\pagename{Foundations and historical corrections}{8. Preserve the studies that constrain the claim}
\textbf{Transformational Intelligence} separates authorized purpose, inherited formulation and evaluation instrument. Its supplied causal example moves from a 50\% passive limit to $8191/8192$ accuracy with at most twelve interventions; an unrestricted Bellman planner matches it. The lesson is a removable information restriction, not a novel planner or autonomous discovery. Here, the clock witness preserves the original purpose and gives all arms the formulation. \src{S11, TI pp. 3--15, 19--24}

\textbf{Invent the Economy} couples capability with counterparties, arrangements, financing, rights and evidence. Its synthetic four-buyer example has \$300,000 successful contribution, \$120,000 expected contribution and \$900,000 opening cash. These differ because common failure destroys construction cost and delivery precedes collection. A conventional unrestricted enumerator ties. Its successor's \$60,000 expected contribution still requires \$450,000, exceeding \$300,000 earned available surplus; assumed lower setup changes both. These are supplied buyers and learning gains, not observed market creation. \src{S11, ITE pp. 7--9}

\textbf{SUCCESSOR $\Omega$} reuses stable generic structure while rechecking each mission's meaning and granting authority separately. The graph Harness reduces generic checks from 1,600 to 64, but the direct specialist is faster on the supplied tasks. The separate detector Harness matches ordinary caching: 32,675 observation calls versus 37,422 for rebuilding and 32,583 for a direct expert. Five physical intervals fail under hidden model violations. S3 inherits the discipline of scoped reuse, not those tasks' qualification. \src{S11}

\begin{tabularx}{\linewidth}{@{}L{0.23\linewidth}Y@{}}
\toprule
\textbf{Preserved study} & \textbf{Finding and correction that survive this edition} \\
\midrule
Software repair pilot & U/E/E+ each pass 4/4 paired task families. Each deliverable has ten protected categories; those assertions do not create ten independent tasks. Actual accepted-output dollar costs are unknown. \\
C5 composition control & All three arms pass one supplied audit job, 14/14 categories each. Common components and the proposed service were supplied; this is not autonomous invention or an exclusive feasible offering. \\
Thermal, scheduling and control & Gains depend on comparator and envelope. Stronger ordinary methods erase some reported benefits; raw accuracy or speed gains do not automatically cross the original acceptance gate. Corrections and adverse transfer remain. \\
Earlier opportunity study & A restricted-budget advantage disappears when the ordinary route receives a larger declared search budget. Conditional transfer cannot be made universal by assuming a larger market. \\
Admission diagnosis & An impossible earlier hurdle rejects all candidates within its bounds. Historical assessment losses stand; a later feasible rule needs fresh prospective evidence. \\
\bottomrule
\end{tabularx}

\subsection*{No favorable rewriting of history}
Earlier ``competent Beta'' definitions may already include expert operation and retain their meaning. Frontier model capability remains Beta; E--U isolates operational expertise only when the actual configurations differ as declared. E+--E isolates new retention only if no unrelated model upgrade or extra resources explain the result. Growing a graph, adding agents or spending more compute alone establishes neither net Alpha nor compounding. \src{S10--S11}

The foundations were read as distinct sources, including the supplied 28-page detector Harness and the different repository graph Harness. The source audit records their version and byte-identity limitations. An instrument that helps a successor does not by itself prove that the enterprise learned to invent better.

\newpage
\pagename{Operating blueprint}{9. A bounded path to a live decision}
\begin{enumerate}
\item \textbf{Specify the useful decision.} With a prospective beneficiary, freeze the requested prediction, scientific acceptance, turnaround, required inputs, customer effort and outside options. Obtain a matched human-service quote and explicit willingness-to-pay hypothesis. A rate card alone is insufficient.
\item \textbf{Qualify the source and authority.} Ingest licensed public or authorized data, check provenance and scope, and separate the right to read from the right to act. Unsupported physics, nonlinear dynamics or calibration triggers an explicit specialist or deferral route.
\item \textbf{Deliver through the cheapest qualifying method.} Permit conventional tools and competent ordinary operation. Use the expert workflow when it measurably helps. Record retries, failures, correction, model/tool charges, latency, customer burden and actual residual human obligations.
\item \textbf{Measure the candidate's incremental benefit.} Compare E+ with E on fresh model families at fixed resources and at matched accepted quality. Separate technical construction, coordinated commitments and their combination. Include negative transfer, shifted requirements and improving model defaults.
\item \textbf{Choose retention or HOLD.} Check admission feasibility before costly assessment. Estimate reusable demand only from information available then. Charge extra rights review, retention, distribution and maintenance once. Use optional Gym practice only with a stated artifact, environment, feedback, update rule, budget and stopping condition.
\item \textbf{Fund dated obligations.} Verify real commitments, acceptance and refund terms, milestone usefulness, support reserves and each cash prefix. Do not spend refundable principal as earned surplus. Preserve conventional delivery, no coalition and stopping as choices.
\end{enumerate}

\subsection*{Define a frontier crossing before comparison}
An offering crosses the economic frontier only when the enhanced configuration alone meets the frozen useful-quality, deadline, customer-effort and selling-price conditions at positive complete margin within the same operating envelope. If both qualify, report improved economics. S3 currently has \textbf{zero observed exclusive technical crossings and zero observed commercial crossings}. No unlimited demand or physical product follows from a computational packet. \src{S5; S9}

\subsection*{Verified model information versus this run}
The official documentation snapshot dated 27 October 2026 lists \texttt{gpt-6-astra}, \texttt{gpt-6.1-sol} and \texttt{gpt-6.1-terra}. Standard short-context uncached input/output prices per million tokens are respectively \$10/\$50, \$2/\$10 and \$1/\$5. The manifest records tool support, reasoning settings, context limits, cache/long-context charges and published limits. These sourced aliases are not evidence of account entitlement or the identity of hosted calls. ChatGPT Pro is a plan, not an API model. No API billing, API-key entitlement or proprietary weight training was established in this study. \src{S12}

\subsection*{Live stop conditions}
Stop or change scope if buyers decline, conventional delivery is already sufficient at lower complete burden, unsupported models dominate demand, correlated verification failures emerge, current admission cannot authorize the service, or payment timing exceeds available funds. A changed model default can make a previously valuable method ordinary Beta. Requalification and retirement are productive decisions, not research failures.

\newpage
\pagename{Reproduction and evidence index}{10. Sources, frozen bytes and provenance}
\small
\begin{tabularx}{\linewidth}{@{}L{0.06\linewidth}Y@{}}
\toprule
\textbf{ID} & \textbf{Source and repository location, relative to this study} \\
\midrule
S1 & Opportunity selection and six-candidate dossier: \path{opportunity/SELECTION.json}; \path{opportunity/discovery/}; follow-up \path{opportunity/discovery/science/s3_assessment.md}. \\
S2 & PEtab Select, PLOS Computational Biology (2026), DOI \href{https://doi.org/10.1371/journal.pcbi.1014774}{10.1371/journal.pcbi.1014774}; Availability and future-directions discussion. \\
S3 & Public scientific evidence under \path{opportunity/protocol/public_case/sources/}; H4 repository pin \texttt{7b1a1528cee61} (full pin and file/license hashes in manifests). Boehm source is separately bound. \\
S4 & Instrument \path{opportunity/instrument/}; development freeze \path{opportunity/development/INSTRUMENT_FREEZE.json}; accepted calculations in \path{opportunity/results/trials/S3_U/frozen_submission/qualification/packet.json}. \\
S5 & \path{opportunity/results/confirmation_summary.json}; archived trials; \path{opportunity/protocol/PARTICIPANT_PROMPTS.json}; exposure/protocol freezes and correction histories in \path{opportunity/protocol/}. \\
S6 & \path{opportunity/private/evaluate.py}; separate conventional implementation \path{opportunity/conventional/direct_method.py}; protocol and conventional READMEs. \\
S7 & Actual-byte transfer \path{opportunity/integration/TRANSFER_RECEIPT.json}; existing native interfaces under \path{integration/} and pinned prior-edition source closure. \\
S8 & Harvard Chan Bioinformatics Core, \href{https://hsph.harvard.edu/research/bioinformatics/consulting/}{published FY26 consulting rates}, checked 27 October 2026; service analogue only. \\
S9 & \path{opportunity/arrangement/README.md}; exact checker, audit and tests; \path{opportunity/arrangement/results/} including selection, fresh stress, timing and historical regressions. \\
S10 & \path{results/pilot_summary.json}; \path{results/composition_summary.json}; \path{economics/results/}; \path{economics/value_results/}; \path{economics/prescreen_results/}; \path{validation/final_supporting_review.md}. \\
S11 & \path{opportunity/discovery/foundations/synthesis.md} and \path{sources.json} in that directory: supplied TI, ITE and detector Harness page references; distinct repository graph Harness and corrected historical guide. \\
S12 & \path{sources/official_model_manifest.json}; \href{https://developers.openai.com/api/docs/pricing}{official model pricing} and linked model documentation, retrieved 27 October 2026. \\
\bottomrule
\end{tabularx}

\subsection*{Reproduce without replacing evidence}
Preserve the repository-relative source closure. Run \texttt{python reproduce.py} for the earlier supporting studies; \path{REPRODUCTION.md} describes exact replay, limitations and optional full economic regeneration. For S3, consult \path{opportunity/protocol/README.md}, re-evaluate frozen submissions with \path{opportunity/private/evaluate.py}, and write new reports to new paths. Run \texttt{python opportunity/arrangement/test\_checker.py} and its independent \texttt{audit.py}. Replay verifies artifacts and conditional arithmetic; it does not regenerate hosted reasoning or validate economic assumptions. Python 3.12.14, NumPy 2.3.2 and SciPy 1.17.0 were observed for the scientific instrument.

\subsection*{Freeze identity and disclosure}
Full SHA-256 commitments are stored with each source. Short prefixes: selection \texttt{4f590ec358bf}; instrument \texttt{02509ddfc613}; exposure \texttt{373291a47c6e}; protocol \texttt{25382ce07429}; capsule \texttt{87875aa44514}. The S3 exact prompts are archived; the older primary trial's messages are transcript-derived reconstructions, not byte-precommitted prompts. Source changes and earlier failed tests remain visible.

AI assistance supported research, code, drafting and internal review. The instruments, benchmark requests and market scenarios are researcher constructions. Public source/license notices accompany recovered files; public availability does not waive downstream rights. No customer secrets, protected tests or scorer internals belong in a shared production capability. Repository provenance is pinned to the recorded parent and source manifests, not a claim that every present upstream file was executed. The original AGI Alpha vision motivates exploration; its market-size projections, IP superlatives and token speculation are not validation, revenue or enterprise cash. This document prepares a reviewable edition and authorizes no deployment or publication.
\end{document}
"""


def write_doc(name, label, body):
    preamble = PREAMBLE.replace("AUXILIARYLABEL", label)
    if name == "evidence_companion.tex":
        preamble = preamble.replace("[11pt,letterpaper]", "[10pt,letterpaper]").replace("margin=0.76in", "margin=0.72in").replace("5.2pt plus 0.6pt", "4.2pt plus 0.5pt").replace("{1.18}", "{1.08}")
        body = body.replace(r"\begin{document}", r"\begin{document}" + "\n" + r"\fontsize{10.5}{12.4}\selectfont", 1)
    text = preamble + "\n" + MACROS + "\n" + body
    (OUT / name).write_text(text)


write_doc("executive_brief.tex", "Executive brief", BRIEF)
write_doc("evidence_companion.tex", "Evidence companion", COMPANION)
(QA / "facts.json").write_text(json.dumps(facts, indent=2) + "\n")
receipt = {}
for name in ["executive_brief.tex", "evidence_companion.tex"]:
    data = (OUT / name).read_bytes()
    receipt[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
(QA / "source_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
