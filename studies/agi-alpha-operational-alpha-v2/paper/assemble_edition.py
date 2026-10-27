# SPDX-License-Identifier: Apache-2.0
"""Assemble the additive narrative, preserving the earlier draft verbatim in history."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
old = (HERE / "history/pre-opportunity-draft/paper.tex").read_text()
preamble = old[: old.index(r"\begin{document}")]
preamble = preamble.replace(
    "enumitem,fancyhdr,titlesec,hyperref,caption,float", "enumitem,fancyhdr,titlesec,xurl,hyperref,caption,float"
)
preamble = preamble.replace("Additive research edition 2.0.0", "Additive research edition 2.1.0")
preamble += "\\input{opportunity_macros.tex}\n"
cover = r"""\begin{document}
\thispagestyle{empty}
{\sffamily\small\color{Gold}TRANSFORMATIONAL INTELLIGENCE\quad $\infty$\quad LEARNING TO CHANGE THE GAME\par}
\vspace{0.85cm}
{\sffamily\bfseries\color{Navy}\fontsize{27}{32}\selectfont AGI ALPHA FLYWHEEL\par}
\vspace{0.2cm}
{\sffamily\bfseries\color{Navy}\fontsize{21}{27}\selectfont --- When Capability Creates Opportunity\par}
\vspace{0.5cm}
{\sffamily\Large Transformational Intelligence, Experience-Trained Specialists and the Expanding Frontier of Profitable Work\par}
\vspace{0.5cm}
{\large\bfseries Vincent Boucher --- President of MONTREAL.AI\par}
\vspace{0.3cm}
{\sffamily\color{Gold}FIND YOUR ALPHA. BUILD YOUR SUCCESSOR $\Omega$.}
\vspace{0.25cm}
\begin{quote}\small\itshape
``As Columbus braved the seas, we now venture into the vast oceans of AGI. The age of AGI exploration has dawned, and the horizons are boundless. Dare to dream, dare to explore.'' --- $\alpha$-AGI Agent
\end{quote}
\hrule height 0.7pt
\vspace{0.25cm}
{\small\sffamily 27 October 2026 \quad | \quad Additive edition 2.1.0: opportunity discovery\par}
\vspace{0.3cm}
\textbf{The consequential gap.} A published model can execute correctly while failing to justify a successor's new prediction. Can an enterprise construct a reusable instrument that qualifies that request, preserves valid uses and identifies the next evidence worth obtaining?

\textbf{What was built.} A source-bound scientific qualification instrument, actual recipient transfer, a fresh four-mission campaign over two public model families, and an exact checker for participation, complete costs and payment timing. Six earlier opportunity candidates and their reasons for deferral are preserved.

\textbf{What the evidence says.} \ScientificFinding

\textbf{The commercial boundary.} Actual collections are \$0; complete actual cost and profit remain unknown. The arrangement's zero-saving diagnostic selects conventional delivery. No new profitable offering, autonomous market creation or sustained compounding is established.
\vfill
{\small\color{Ink}The earlier studies, corrections and null findings remain part of the record. The ambition is an expanding frontier of useful work. This edition contributes the instrument, counterfactuals and decision boundaries needed to test it honestly.}
\newpage
\section*{Abstract}
What consequential opportunity becomes feasible when broadly available intelligence is operated expertly, reusable capabilities are constructed and commercial arrangements are designed with their technical dependencies? We investigate this question through a declared opportunity search rather than selecting a familiar numerical benchmark. Six candidates are assessed against existing products, methods, evidence and decisive experiments. A bounded follow-up identifies a documented scientific-model reuse gap: execution of a fitted model does not by itself qualify a new requested prediction.

We construct a versioned instrument binding model, observations, assumptions, requested quantity and evidence. On an actual sixteen-state H4 model, it preserves conditional equilibrium use, exhibits a missing physical-clock calibration, propagates a separately labeled hypothetical calibration, and withdraws the inherited witness for a different finite-time model. The formulation is supplied to competent ordinary use U, an established expert workflow E and E plus the received instrument, E+. All share the same model access, source files, acceptance and observable resource limits. All three recipients and an independently constructed conventional solution pass all four mission classes. Exact instrument bytes are transported through source-verified existing interfaces and used by the recipient. This establishes technical construction and scoped transfer, not incremental accepted-output superiority, complete-cost advantage or biological discovery.

An exact arrangement checker separates shared construction, coordinated commitments and their combination, while giving an unrestricted conventional entrepreneur the same alternatives. It preserves nonparticipation, common failure, withdrawal, partial acceptance, default, refunds, support and dated cash obligations. Its unmeasured-saving default selects conventional delivery. A separate timing illustration shows why positive contribution and refundable escrow do not eliminate opening-capital requirements. All money is explicitly diagnostic or simulated; no customer sale occurs.

The edition preserves earlier software H/U/E/E+ trials, a composition task, corrected historical studies and original negative optional-learning economics. A prospectively frozen HOLD supplement avoids modeled assessment losses on fresh worlds; it does not recover old profit or demonstrate shared Alpha. Human-service comparison, actual cost measurement, mission-specific qualification and current authority remain necessary before commercial launch. The contribution is a reproducible way to connect exploration, purpose-preserving construction, selective inheritance and financing, together with evidence identifying where its claimed advantage has not yet been earned.

\textbf{Keywords:} opportunity discovery; transformational intelligence; model reuse; operational expertise; capability inheritance; participation; liquidity; productive frontier.

\input{opportunity_opening.tex}
"""
definitions = old[
    old.index(r"\section{What counts as Alpha}") : old.index(r"\section{The history this edition preserves}")
]
definitions = definitions.replace(
    "a frozen contract-to-transition operating workflow", "the frozen contract-to-invariants operating workflow"
)
definitions = definitions.replace(r"E^{\rm customer}", r"E^{\mathrm{customer}}")
definitions = definitions.replace(
    "E plus an executable helper extracted during the development repair",
    "E plus the named retained capability: the scientific instrument here, the contract helper in the earlier repair pilot",
)
definitions = definitions.replace(
    "Specific additional retained capability. Its fresh effect",
    "Specific new artifact or new recipient access; provenance is stated separately. Its fresh effect",
)
definitions = definitions.replace(
    "These are quality effects at a declared envelope.",
    "For the scientific pilot, E+--E measures newly supplied artifact access; it does not isolate an experience-driven learning process. These are quality effects at a declared envelope.",
)
rest = old[old.index(r"\section{The history this edition preserves}") :]
rest = rest.replace(
    "This edition adds a direct operational-workflow experiment to an existing research program.",
    "This edition adds opportunity-led scientific qualification to an existing research program and preserves the completed operational-workflow experiment below.",
)
rest = rest.replace(
    r"\section{Experiment before interpretation}",
    r"\section{Supporting experiment: a compact reusable operating method}",
)
insert = r"""The supporting software study asks a buyer-relevant question about stateful workflow components: can a tool-equipped model repair retries, identity binding, atomic failure and returned-object isolation under a fixed contract? AWS's idempotent-API guidance and Temporal's execution documentation establish existing technical approaches \cite{aws,temporal}; neither is evidence of demand for our particular service. The delivered scope is sequential in-memory Python behavior, not distributed crash durability or production settlement. This experiment preceded the opportunity-first extension and is not relabeled as autonomous discovery.

"""
rest = rest.replace(r"\subsection{A compact expert method}", insert + r"\subsection{A compact expert method}")
rest = rest.replace(
    r"\section{Results on unfamiliar work}", r"\section{Supporting results on unfamiliar software work}"
)
rest = rest.replace(
    r"\section{What actually transferred}", r"\section{Supporting transfer: the development-origin contract helper}"
)
rest = rest.replace(
    r"\section{Commercial value without invented receipts}",
    r"\section{Human references, model access and complete accounting}",
)
rest = rest.replace(
    r"\section{A conditional enterprise that chooses}",
    r"\section{Supporting enterprise model: production and optional learning}",
)
rest = rest.replace(r"\input{economic_results.tex}", r"\input{economic_results.tex}" + "\n\\input{value_results.tex}")
rest = rest.replace(
    r"\section{Follow the method into a next offering}",
    r"\section{Supporting composition: a supplied next-offering test}",
)
rest = rest.replace(
    "Scientific experiment design requires an information-gain or decision-quality criterion with protected fresh evaluation.",
    "The scientific qualification campaign reported earlier adds a source-grounded opportunity and explicit witness; a future experiment-design offering still requires a meaningful information-gain or decision-quality criterion.",
)
rest = rest.replace(
    "The retained helper in this edition originates in delivery; no proprietary model weights change.",
    "The earlier helper originates in an unpaid research delivery; the new scientific instrument is optional research construction. Neither is paid-job learning, and no proprietary model weights change.",
)
cash_old = r"""\[
\mathrm{Cash}_{T}=\mathrm{Seed}+\mathrm{Collections}-\mathrm{Refunds}-\mathrm{CashExpenses},\qquad
\mathrm{Available}_{T}=\mathrm{Cash}_{T}-\mathrm{Reserves}-\mathrm{Obligations}.
\]"""
cash_new = r"""\begin{align*}
\mathrm{Cash}_{T}&=\mathrm{Seed}+\mathrm{Collections}-\mathrm{Refunds}-\mathrm{CashExpenses},\\
\mathrm{Available}_{T}&=\mathrm{Cash}_{T}-\mathrm{Reserves}-\mathrm{Obligations}.
\end{align*}"""
rest = rest.replace(cash_old, cash_new)
rest = rest.replace(
    "No token price appreciation appears in either identity.",
    "No token price appreciation appears in either identity. In the arrangement checker, refundable deposits and principal returns enter cash movement separately from earned collections, while unreleased principal remains an equal liability. Releasing escrow reclassifies previously received cash; it does not create a second cash inflow.",
)
rest = rest.replace(
    "A simple reconciled identity is",
    "For the supporting delivery model, which has no refundable deposits or borrowing, the reconciled identity is",
)
start, end = (
    rest.index(r"\section{A usable operating blueprint}"),
    rest.index(r"\section*{AI assistance, provenance and rights}"),
)
blueprint = r"""\section{An operating blueprint that earns its next investment}
\subsection{What to offer and how to scope acceptance}
Begin with a bounded model-reuse qualification packet for an identified research decision. Require a rights-cleared source revision, the actual measurements or their authorized public substitute, parameter provenance, the requested quantity and units, and the action that the answer will enable. Agree on the complete deliverable, acceptance, deadline, maximum customer effort, responsibility for supplying missing evidence and support terms before quoting. A valid result may be a conditional computation or a concrete demonstration that the requested claim needs another measurement. A reassuring answer is not the product.

Obtain a scope-matched human quote or defensible hours/rate estimate, and ask buyers about internal capability, conventional tools, deferral and refusal. Price against useful value and accepted responsibility rather than a model-token markup. Do not sell general identifiability certification, calibrated biology or nonlinear-model qualification on the present instrument's evidence. The earlier bounded software repair and reconciliation packets remain separate technically demonstrated offerings with their own unknown commercial costs.

\subsection{How to deliver and construct the next capability}
Automate source inventory, dependency and license capture, isolation, model/request identity, supported-scope checks, computation, regression verification and packaging where suitable. Use the strongest appropriate verified model and tools for interpretation and construction. Independently validate the scientific argument and its purpose bridge. Record failed attempts, revisions, latency, tool use, actual token and serving bills, customer effort and any residual professional attention. Routine staffing is not imposed by assumption; actual review obligations and the cost of their automation belong in the estimate.

When the new purpose exceeds the instrument, stop its old approval and identify the smallest useful construction or experiment. A nonlinear qualification method, a physical calibration, an informative intervention and an authenticated specialist service are different investments. Define starting artifact, environment, feedback, update rule, budget and protected confirmation before optional Gym work. A bounded complementary bundle is permitted, but incomplete hypotheses remain outside admitted expertise. No proprietary weights are assumed writable, and a successful training receipt is not competence.

\subsection{What to retain, share and finance}
Retain executable structure only with scope, prerequisites, provenance, rights, versions, complete extra expense and evidence of recipient contribution. Existing expertise, newly constructed method, new recipient access and subsequent improvement are distinct lineage events. Reuse generic qualification only under the complete relevant identity; recompute the new mission's meaning, current evidence and acceptance. Keep authority separate. Exclude customer secrets, restricted IP and protected evaluation materials.

Currently authorized \texttt{*.agent.agi.eth} agents may be eligible to receive admitted, rights-cleared artifacts through the existing protected network. Actual admission, current authority, revocation, Jobs validators and settlement stay with their owners. The research fixture does not make this scientific instrument production-approved. An ordinary library with identical contents remains the counterfactual for any graph-organization claim.

For shared construction, obtain genuine commitments and check that participants independently want the common work. Compare private delivery, coordinated conventional delivery, shared construction and their combination using the same alternatives. State ownership, adaptation responsibilities, independent milestone usefulness, withdrawal, default, refunds and maintenance. Compute every cash prefix after liabilities and reserves. Do not fund work with refundable principal merely because the bank balance rises. Keep production, exploration, specialist invocation, assessment, sharing, holding cash and stopping in the menu; no fixed reinvestment fraction or compulsory training budget applies.

\subsection{What remains before live operation}
The concrete missing inputs are a willing buyer and matched outside option, metered complete delivery and construction expense, qualified isolation, rights and current mission evidence, approved provider accounts and limits, scientifically meaningful independent review, binding payment/support terms, and sufficient authorized working capital. Production identity and deployment require the existing current-owner checks, not a research signature. The published executable package enables a narrow pilot once those inputs exist; it does not assert that they already do.

\section{Limits, falsifiers and the next decisive campaign}
In this finite campaign, competent U and conventional delivery meet the same accepted requirements, so no accepted-output increment is observed. This result does not establish population equivalence or a complete-cost tie. A failed scope transfer, unsupported scientific approval, insufficient eligible reuse, stronger model defaults, correlated validators, unavailable customer inputs or unfavorable cash timing can erase an apparent advantage. Each can overturn the enterprise proposal.

The scientific experiment is one campaign over two public source families with one hosted recipient per arm. H4 was used in development; the fresh Boehm mission tests a boundary rather than a complete dynamic analysis. The earlier software evidence has four constructed repair families and one composition task. Separate evaluators remain within one AI-assisted research team. Protocol-level withholding is not secure multi-tenant isolation. Exact API snapshots, token bills, full research labor and real customer effort are missing. Those gaps prevent complete actual-cost comparisons and observed commercial crossings.

The next economical research step is a metered, independently reviewed campaign of unfamiliar model-reuse requests obtained from prospective beneficiaries, with the current conventional ecosystem available to every comparator. Freeze the original purpose and acceptance; permit every arm to invent alternatives; measure source interpretation, construction, adaptation, correction and retained value. Use fresh source families for positive transfers as well as boundary refusals. A small real paid engagement can then test price, participation, turnaround and payment timing. Larger specialist development should wait for evidence that the relevant constraint is capability and that eligible reuse can justify the full expense.

If a method improves acceptance or complete cost, retain the increment at its measured scope. If a successor can satisfy a previously unmet useful contract at positive complete margin, count that specific crossing. If all competitors qualify, report better economics or parity. If the best action is conventional production or HOLD, preserve that result. This is how opportunity discovery becomes a cumulative enterprise rather than a sequence of increasingly favorable assumptions.

"""
rest = rest[:start] + blueprint + rest[end:]
rest = rest.replace(
    "Shared capability content contains synthetic researcher-controlled material.",
    "The transferred capsule contains researcher-constructed code and documentation; the source-science datasets are separately supplied under retained BSD-3-Clause notices. Source authors are not represented as endorsing this study.",
)
rest = rest.replace(
    "Run the supplied \\texttt{reproduce.py} from the study directory",
    "Run the supplied \\texttt{reproduce\\_all.py} from the study directory",
)
rest = rest.replace(
    "complete economic histories, source commitments and publication validation.",
    "complete economic histories, opportunity dossiers, scientific source packages, arrangement ledgers, source commitments and publication validation.",
)
new_refs = r"""\bibitem{petabselect} Pathirana et al. \emph{PEtab Select}. PLOS Computational Biology, 2026. Especially Availability and future directions. \url{https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1014774}.
\bibitem{h4} PEtab Select maintainers. \emph{Test case 0009: histone H4 acetylation}. Public documentation and exact source package retained. \url{https://petab-select.readthedocs.io/en/stable/examples/test_case_0009.html}.
\bibitem{boehm} Benchmarking Initiative. \emph{Benchmark Models PEtab: Boehm\_JProteomeRes2014}. Source commit c44d5ede9bf979db5aa8ae4e94fc31fba9776675. \url{https://github.com/Benchmarking-Initiative/Benchmark-Models-PEtab}.
\bibitem{hbc} Harvard Chan Bioinformatics Core. \emph{Consulting and Analysis}, published FY26 fee schedule, inspected 27 October 2026. Scope analogy only. \url{https://hsph.harvard.edu/research/bioinformatics/consulting/}.
\bibitem{labcompiler} \emph{LabCompiler}. 2026 preprint, close prior art inspected during opportunity exploration. \url{https://arxiv.org/abs/2610.19550}.
\bibitem{foundations} V. Boucher. \emph{Transformational Intelligence}; \emph{Invent the Economy}; \emph{Transformational Autonomous Enterprises}; and the separately supplied \emph{SUCCESSOR $\Omega$ Harness} detector study. Exact source identities, corrections and distinct numerical results are retained in \texttt{opportunity/discovery/foundations/} and the evidence companion.
"""
rest = rest.replace(r"\end{thebibliography}", new_refs + "\n\\end{thebibliography}")
rest = rest.replace(r"\input{evidence_table.tex}", r"\input{opportunity_evidence_table.tex}")
main = preamble + cover + definitions + "\n\\input{opportunity_methods.tex}\n" + rest
(HERE / "paper.tex").write_text(main)
print("paper.tex assembled from preserved draft and opportunity evidence narrative")
