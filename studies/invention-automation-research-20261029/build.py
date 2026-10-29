# SPDX-License-Identifier: Apache-2.0
"""Build synchronized local LaTeX/PDF and complete self-contained HTML editions."""

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
D = json.loads((P / "data/audited.json").read_text())


def table(headers, rows, caption):
    return (
        "\n"
        + "| "
        + " | ".join(headers)
        + " |\n"
        + "| "
        + " | ".join("---" for _ in headers)
        + " |\n"
        + "".join("| " + " | ".join(str(x).replace("|", "/") for x in row) + " |\n" for row in rows)
        + "\n: "
        + caption
        + "\n"
    )


def fmt(x, n=6):
    return f"{float(x):,.{n}f}"


M = {}
new = D["raw_reaggregated"]["pilot-v2"]
old = D["raw_reaggregated"]["pilot-v1"]
M["cpu_corrective"] = fmt(new["corrective"]["deployment_cpu_per_attempt"])
M["cpu_lp"] = fmt(new["strong_lp"]["deployment_cpu_per_attempt"])
names = {
    "strong_lp": "Complete LP",
    "selection_only": "Partial-model selection",
    "irrelevant_criticism": "Invalid-criticism control",
    "corrective": "Verified correction",
}
M["new_results_table"] = table(
    ["Arm", "v1 accepted", "v2 accepted", "v2 new rows", "v2 CPU/attempt (s)"],
    [
        [
            names[k],
            f"{old[k]['accepted']}/36",
            f"{new[k]['accepted']}/36",
            new[k]["cuts"],
            fmt(new[k]["deployment_cpu_per_attempt"]),
        ]
        for k in names
    ],
    "New raw-record reaggregation. Both panels retain every attempted task. CPU is an all-record deployment proxy, not complete monetary cost. The complete LP is the primary competent comparator.",
)
M["continuity_table"] = table(
    ["Earlier claim / artifact", "Demonstrated scope", "Unresolved limitation", "Reuse and new test"],
    [
        [
            "Purpose-preserving formulation; *Transformational Intelligence*",
            "Exact passive/interventional finite model; unrestricted planner matches",
            "No autonomous discovery or physical experiment",
            "Keep intent and final acceptance fixed while compiling corrections",
        ],
        [
            "Contractual + technical complementarity; *Invent the Economy*",
            "Supplied buyer-value grid and cash-timing checks",
            "Demand and participation remain modeled",
            "Audit escrow, reserves and complete-cost crossing separately",
        ],
        [
            "Construct means of discovery; *Out-Evolve*",
            "Conditional low-order response family and retained operation",
            "Physical family membership and complete editable source not recovered",
            "Treat prerequisites and revalidation as obligations, not inherited truth",
        ],
        [
            "Capability-producing inheritance; *Autonomous Enterprises*",
            "Measured arithmetic construction/qualification; joint planner matches",
            "Canonical companion not rerun; no external business validation",
            "Compare constructed successor against competent funded control",
        ],
    ],
    "Continuity matrix. Earlier numerical claims retain their original evidence class; this edition does not count them as new experiments.",
)
M["lineage_table"] = table(
    ["Lineage", "Available evidence", "What this edition verified"],
    [
        [
            "Original A/S/C and learning study",
            "Source + aggregate tables; full 2,184-record archive missing",
            "71 tests; mechanism inspection; aggregate arithmetic only",
        ],
        [
            "Structural transfer version 3",
            "Raw tasks, artifacts, source freezes, SIM databases",
            "128 certificates; three latest financial snapshots",
        ],
        [
            "Invention-automation first cycle",
            "Opportunity registry + three-case fixture",
            "Five tests; no real admitted cohort",
        ],
        [
            "Writer correction versions 1 and 2",
            "72 tasks, 288 records, all traces and native packs",
            "288 native replays; 1,220 generated rows; 72 optimum rechecks",
        ],
    ],
    "Separate evidence lineages. Records, tasks, constraints, and orders are different denominators.",
)
M["opportunity_table"] = table(
    ["Prospect / intended beneficiary", "Binding candidate bottleneck", "Required competent alternative", "Admission"],
    [
        [
            "Battery repurposer / storage operator",
            "Qualification, remaining life, handling and liability",
            "Whole-pack reuse, qualified repurposing, recycling, life-adjusted new storage",
            "UNKNOWN: no fixed asset cohort or complete obligations",
        ],
        [
            "Difficult-textile sorter / recycler",
            "Observable composition at accepted yield and throughput",
            "Existing NIR and spectral references; feasible sorting routes",
            "UNKNOWN: no validated new observable or all-cohort prices/costs",
        ],
        [
            "Small-building service / owner",
            "Transaction and execution costs for accepted savings",
            "Current contractor approach, CBES, competent AI-assisted service",
            "UNKNOWN: current cohort, costs and demand absent",
        ],
    ],
    "Opportunity-screen audit. Beneficiaries and bottlenecks are hypotheses to qualify, not invented customers or verified industry losses.",
)
M["supplied_table"] = table(
    ["Element", "Supplied / implemented by writer", "Generated or verified at runtime"],
    [
        [
            "Task and analogy",
            "Known scalar recurrence; three unit-labelled model domains",
            "No autonomous analogy discovery",
        ],
        [
            "Construction grammar",
            "Task-bound linear inequalities and bounded solve loop",
            "Scenario/time-specific numerical rows and schedules",
        ],
        [
            "Criticism",
            "Inventory-bound witness search and scalar adjudicator",
            "Reproduced failures; wrong-unit criticisms rejected",
        ],
        [
            "Acceptance",
            "Unchanged direct checker and separate optimum formulation",
            "Original-contract quality/resource verdict",
        ],
        [
            "Economic / physical instruments",
            "No new sensor, reagent, purchase or customer contract",
            "No new physical or commercial result",
        ],
        [
            "Cumulative invention",
            "No cross-task learner in the new pilot",
            "Task-specific rows are not claimed as transferable learning",
        ],
    ],
    "Attribution of supplied mathematics, engineered code, and generated artifacts.",
)
M["learning_table"] = table(
    ["Control − cumulative", "Reported saving (s)", "Reported interval (s)", "Decision"],
    [
        [r["control_minus_cumulative"], fmt(r["estimate"]), f"[{fmt(r['lower'])}, {fmt(r['upper'])}]", "Includes zero"]
        for r in D["learning-final-contrasts"]
    ],
    "Inherited final-panel comparison. Twenty-four reported pairing clusters; interval computation not independently reproduced because raw pairs are missing.",
)
for mode in ("cumulative", "frozen", "reset", "retrieval"):
    M[f"learning_{mode}_total"] = fmt(
        sum(float(r["lifecycle_cpu_proxy"]) for r in D["learning-lifecycle"] if r["mode"] == mode)
    )
recon = D["cost_reconciliation"]["rows"]["instrument"]
repair = D["budget_repair"]
snaps = [recon["before"], recon["after"], repair["after"]]
M["cost_bridge_table"] = table(
    ["Recorded stage", "Revenue", "Expense", "Profit"],
    [
        [label, *[fmt(s[k] / 1e6) for k in ("revenue", "expenses", "profit")]]
        for label, s in zip(
            ["Earlier positive checkpoint", "Late-cost reconciliation", "Later seed-repair receipt"], snaps
        )
    ],
    "Versioned instrument cost bridge, SIM USD. No prices or demand were improved to repair the result.",
)
financial = D["financial"]["replayed"]
M["financial_table"] = table(
    ["Latest audited quantity", "Instrument", "Funded control", "Instrument refund branch"],
    [
        [label, *[fmt(financial[a]["snapshot"][key] / 1e6) for a in ("instrument", "control", "refund")]]
        for key, label in [
            ("revenue", "Earned SIM revenue"),
            ("expenses", "Recorded expenses"),
            ("profit", "Operating profit"),
            ("cash", "Cash"),
            ("tailReserve", "Tail reserve"),
            ("workingCapital", "Working capital"),
            ("available", "Available cash"),
            ("unrestrictedEarned", "Unrestricted earned"),
        ]
    ],
    "Read-only latest-snapshot reconciliation, SIM USD. Financing capital and reserves are not revenue.",
)
M["decisions_table"] = table(
    ["Decision", "Current finding", "Exact missing condition"],
    [
        [
            "Technical component",
            "GO, bounded compiler; 36/36 in v2",
            "Not superior capability: full LP matches at lower measured compute",
        ],
        [
            "Commercial profitability",
            "Not established; recorded instrument SIM loss",
            "Calibrated same-cohort complete-cost positive profit",
        ],
        [
            "Transformational Blue Sky",
            "NOT ESTABLISHED",
            "Verified technical cause and negative-to-positive crossing on the same cohort",
        ],
        [
            "Investment",
            "HOLD for current instrument earned funds",
            "Unrestricted settled surplus, feasible additional build, justified outside-option comparison",
        ],
        ["Experience", "NOT ESTABLISHED", "Fresh causal invention benefit after acquisition/reuse costs"],
        ["AGI ALPHA value capture", "UNKNOWN", "Evidence of willingness to pay and a valid captured-value route"],
        ["Full flywheel", "NOT COMPLETE", "All preceding links plus useful fresh successor advantage"],
    ],
    "Separate decisions. Passing document production does not promote the scientific or commercial mission.",
)
repos = [
    ("Alpha", "12770c22b4a9f90f2013bbfb64242f912ba5071e", "Required sparse dependencies used locally"),
    ("Fleet", "45759fb096faf8988f58ae5ea71248d0f35a97c7", "Instructions/head inspected; no native execution"),
    ("Jobs", "bc4abbd5c28f3672275b13300e40ea26c820b8ee", "AGIALPHA18 inspection source, not settlement"),
    ("Manager", "5d5670df9dbbc79da115e0a44b71989f34df58c1", "USDC6 inspection source, not settlement"),
]
M["repo_table"] = table(
    ["Repository", "Inspected commit", "Scope"],
    [[a, f"`{b}`", c] for a, b, c in repos],
    "Source snapshots observed 29 October 2026. These identifiers are not new publication or deployment receipts.",
)
M["series_table"] = table(
    ["Series source", "Canonical identity / local scope", "Reproduction boundary"],
    [
        [
            "Autonomous Enterprises",
            "Git blob `e0ba91b0de31b764ca568b1d903adb9a92f09f75`; full local TeX matches",
            "Canonical foundry companion not recovered",
        ],
        [
            "Invent the Economy",
            "Git blob `36d366b57c777fc85c5cd61e9c705b2a63e76e04`; full TeX/code/results inspected",
            "Existing supplied-model findings, not new demand",
        ],
        [
            "Transformational Intelligence",
            "Git blob `83f834fbbabfc0680cf560e5e96852cc8f4fa9e7`; full TeX/bibliography/code",
            "Finite exact model, not physical validation",
        ],
        [
            "Out-Evolve",
            "Retained full 29-page PDF; include-only TeX root",
            "Missing section inputs and editable bibliography; no full rebuild claim",
        ],
    ],
    "Series-source continuity. Full source identities and file hashes are in the companion manifest.",
)
M["protocol_table"] = table(
    ["Item", "Frozen setting / status"],
    [
        ["v2 protocol digest", "`459c24263b5134b4e59eeadeae9b8a951a44142c056322f0c26b9d866d81e04a`"],
        ["Registration", "2026-10-29T12:37:43Z; EXPLORATORY"],
        ["Base seeds", "88101, 88202, 88303; version 1 seeds retired"],
        ["Panel", "3 unit-labelled domains × 4 structures × 3 seeds = 36 tasks"],
        ["Task", "48 steps; 5 supplied scenarios; same complete specification"],
        ["Arms", "Full LP; partial selection; wrong-unit criticism; verified correction"],
        ["Candidate bounds", "2 CPU seconds; 128 added cuts; 100,000,000 abstract-work ceiling"],
        ["Acceptance", "Original direct recurrence, units, bounds, ramp, quality ≥ 0.999, resources"],
        ["History", "No cross-task memory update; no model-weight training"],
        ["Uncertainty", "Finite observed counts; no new campaign-wide confirmatory claim"],
        ["Practical economic threshold", "Unset: no admitted economic cohort"],
    ],
    "New pilot protocol. Full frozen source map and raw data are included.",
)
M["historical_factorial_table"] = table(
    ["A/S/C", "Accepted", "Mean usefulness", "CPU/accepted (s)", "Extra adversarial searches"],
    [
        [
            r["arm"],
            f"{r['accepted']}/{r['n']}",
            f"{float(r['mean_usefulness']):.9f}",
            fmt(r["cpu_seconds_per_accepted"]),
            r["adversarial_searches"],
        ]
        for r in D["factorial-arms"]
    ],
    "Original reported factorial aggregates. A = structural transfer; S = supplied-method composition; C = additional adversarial search.",
)
M["historical_contrast_table"] = table(
    ["Reported contrast", "Estimate", "Lower", "Upper"],
    [
        [
            r["contrast"].replace("_", " "),
            f"{float(r['estimate']):.3e}",
            f"{float(r['lower']):.3e}",
            f"{float(r['upper']):.3e}",
        ]
        for r in D["factorial-contrasts"]
    ],
    "Original reported additive-scale contrasts; all use 48 reported clusters. The pure three-way contrast is zero.",
)
lifecycle = []
for mode in ("cumulative", "frozen", "reset", "retrieval"):
    rs = [r for r in D["learning-lifecycle"] if r["mode"] == mode]
    lifecycle.append(
        [
            mode,
            *[
                fmt(sum(float(r[k]) for r in rs))
                for k in (
                    "deployment_cpu_proxy",
                    "lifecycle_cpu_proxy",
                    "equal_history_collection_sensitivity_cpu_proxy",
                )
            ],
        ]
    )
M["historical_lifecycle_table"] = table(
    ["Mode", "Deployment CPU (s)", "Own-history lifecycle (s)", "Equal-history sensitivity (s)"],
    lifecycle,
    "Sum of three reported learning-stream CPU proxies. This is not complete monetary accounting.",
)
claims = [
    (
        "C01",
        "mechanism",
        "Verified criticism produces executable task-bound constraints",
        "writer_extension/corrective.py",
        "Implemented component; supplied linear model, no autonomous analogy discovery",
    ),
    (
        "C02",
        "technical-results",
        "Revised correction and full LP each accept 36/36",
        "writer_extension/evidence/pilot-v2/summary.json",
        "Exploratory finite panel; no population claim",
    ),
    (
        "C03",
        "technical-results",
        "Corrective deployment CPU proxy exceeds full LP",
        "papers/invention-automation-v1/data/pilot-v2-arms.csv",
        "Observed compute, not full cost or invoice",
    ),
    (
        "C04",
        "methods",
        "First correction version accepts 33/36; three CPU refusals",
        "writer_extension/evidence/pilot-v1/summary.json",
        "Segmented execution; incomplete controller cost",
    ),
    (
        "C05",
        "methods",
        "288 saved native records and 1,220 cuts replay",
        "@audit/new-pilot-constraint-replay.json",
        "Procedural separation; shared machine and HiGHS",
    ),
    (
        "C06",
        "economics",
        "128 developer transfer/successor certificates replay",
        "@audit/structural-saved-replay.json",
        "Saved replay, not new confirmation or physical proof",
    ),
    (
        "C07",
        "economics",
        "Current instrument recorded operating profit −8.574947 SIM USD",
        "@audit/latest-financial-replay.json",
        "Shadow-cost SIM with estimated authoring; not real revenue",
    ),
    (
        "C08",
        "economics",
        "Current instrument unrestricted earned funds are zero",
        "@audit/latest-financial-replay.json",
        "Available financed cash is not earned surplus",
    ),
    (
        "C09",
        "successor",
        "Successor accepted-output advantage over funded control is zero",
        "@recovered/AGI_ALPHA_Structural_Transfer_Evidence_2026-10-29/campaign/transfer_v3/evaluation/actual/successor-confirmation.json",
        "Four finite pairs; old-interface gain distinct from treatment gain",
    ),
    (
        "C10",
        "experience",
        "Historical experience intervals cross zero",
        "papers/learning-final-contrasts.csv",
        "Reported intervals only; missing raw pairing",
    ),
    (
        "C11",
        "technical-results",
        "Historical practical A/S/C synergy not established",
        "papers/factorial-contrasts.csv",
        "Tiny additive interaction, not multiplication; raw missing",
    ),
    (
        "C12",
        "opportunities",
        "All three real prospects remain UNKNOWN",
        "@recovered/AGI_ALPHA_Feasibility_FirstCycle_2026-10-29/agi_alpha_feasibility_20261029/REGISTRY.md",
        "No admitted cohort or physical/market measurements",
    ),
    (
        "C13",
        "custody",
        "Original source unchanged; v2 freeze matches",
        "@audit/new-pilot-constraint-replay.json",
        "Sparse workspace, not full release qualification",
    ),
    (
        "C14",
        "continuity",
        "Original Omega source recovered and 51 tests pass",
        "@audit/omega-unit-tests.log",
        "Not installed general discovery; large old panel not replayed",
    ),
    (
        "C15",
        "decisions",
        "Mission NOT COMPLETE",
        "@audit/latest-financial-replay.json",
        "Technical superiority, cohort crossing, experience and successor causality unestablished",
    ),
]
B = next((a for a in P.parents if (a / "dev_source/AGI-Alpha-Agent-v0").is_dir()), P)
S = P.parents[1] if len(P.parents) > 1 else P
claimmap = []
for cid, loc, claim, path, lim in claims:
    source = B / path[1:] if path.startswith("@") else S / path
    if not source.exists():
        cached = {x["id"]: x for x in json.loads((P / "claim-map.json").read_text())}
        claimmap.append(cached[cid])
        continue
    refs = [{"path": str(source.relative_to(B)), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]
    if cid == "C05":
        q = B / "audit/new-pilot-native-replay.json"
        refs.append({"path": str(q.relative_to(B)), "sha256": hashlib.sha256(q.read_bytes()).hexdigest()})
    claimmap.append(
        {
            "id": cid,
            "manuscript_location": loc,
            "claim": claim,
            "claim_type": (
                "reported historical result"
                if cid in ("C10", "C11")
                else ("scope/decision" if cid in ("C12", "C15") else "executed code or audit")
            ),
            "evidence": refs,
            "source_revision": D["alpha_sha"],
            "experiment_or_derivation": "See named raw record or audit; all derivations described in manuscript",
            "comparator": "Full conventional LP / funded no-instrument control where applicable",
            "uncertainty": "Exploratory; historical interval limitations retained",
            "verification_status": (
                "RAW_REPLAYED"
                if cid in ("C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C13")
                else "SOURCE_INSPECTED_OR_REPORTED"
            ),
            "limitations": lim,
        }
    )
(P / "claim-map.json").write_text(json.dumps(claimmap, indent=2) + "\n")
M["claim_table"] = table(
    ["ID / location", "Claim", "Evidence boundary"],
    [[f"{x['id']} / {x['manuscript_location']}", x["claim"], x["limitations"]] for x in claimmap],
    "Human-readable claim map. The JSON map supplies full artifact paths, hashes, source identity, comparator, and verification status.",
)
(P / "claim-map.md").write_text(
    "# Claim–evidence map\n\n" + M["claim_table"] + "\nFull artifact hashes and scopes are in `claim-map.json`.\n"
)
text = (P / "manuscript.template.md").read_text()
for k, v in M.items():
    text = text.replace("{{" + k + "}}", str(v))
assert not re.search(r"\{\{\w+\}\}", text), "Unexpanded field"
text = re.sub(r"(# Appendix [A-F]\..*?)\{#", r"\1{.unnumbered #", text)
(P / "manuscript.md").write_text(text)
# Primary inputs and outputs remain local; no external assets or scripts.
args = [
    "pandoc",
    "manuscript.md",
    "--from=markdown+tex_math_dollars+raw_tex",
    "--citeproc",
    "--number-sections",
    "--resource-path=.",
]
subprocess.run(args + ["--to=latex", "--output=all-body.tex"], cwd=P, check=True)
body = (P / "all-body.tex").read_text()
body = re.sub(r"(figures/[A-Za-z0-9-]+)\.png", r"\1.pdf", body)
# Label long hexadecimal identities breakably in LaTeX while retaining the exact text.
body = re.sub(r"\\texttt\{([a-f0-9]{40,64})\}", r"\\path{\1}", body)
marker = body.find("\\section{The missing link")
assert marker > 0, "Missing body start"
(P / "abstract.tex").write_text(body[:marker])
(P / "body.tex").write_text(body[marker:])
main = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[T1]{fontenc}\usepackage[utf8]{inputenc}
\usepackage[margin=0.86in,headheight=15pt]{geometry}
\usepackage{lmodern,microtype,amsmath,amssymb,booktabs,longtable,array,graphicx,xurl,calc}
\usepackage{fancyhdr,enumitem,etoolbox,caption,float,needspace}
\usepackage[hidelinks,unicode,breaklinks]{hyperref}
\hypersetup{pdftitle={AGI ALPHA FLYWHEEL: The Enterprise That Invents Its Next Economy},pdfauthor={Vincent Boucher, President, MONTREAL.AI},pdfsubject={From verified criticism to executable repair; audited limits of economic compounding},pdfkeywords={invention automation, structural transfer, counterexamples, executable constraints, simulated economics}}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small AGI ALPHA FLYWHEEL}\fancyhead[R]{\small Research edition 1.0.0}\fancyfoot[C]{\thepage}
\setlength{\parindent}{0pt}\setlength{\parskip}{0.42em}\setlength{\emergencystretch}{3em}\raggedbottom
\setlist{nosep,leftmargin=1.5em}\captionsetup{font=small,labelfont=bf}
\AtBeginEnvironment{longtable}{\small\setlength{\tabcolsep}{4pt}}
\renewcommand{\topfraction}{.92}\renewcommand{\bottomfraction}{.85}\renewcommand{\textfraction}{.07}\renewcommand{\floatpagefraction}{.8}
\setcounter{tocdepth}{1}\setcounter{secnumdepth}{2}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\newcommand{\passthrough}[1]{#1}
\newcommand{\pandocbounded}[1]{#1}
\makeatletter\def\maxwidth{\ifdim\Gin@nat@width>\linewidth\linewidth\else\Gin@nat@width\fi}\def\maxheight{\ifdim\Gin@nat@height>0.82\textheight0.82\textheight\else\Gin@nat@height\fi}\makeatother
\setkeys{Gin}{width=\maxwidth,height=\maxheight,keepaspectratio}
\NewDocumentCommand\citeproctext{}{}
\NewDocumentCommand\citeproc{mm}{\begingroup\def\citeproctext{#2}\cite{#1}\endgroup}
\makeatletter\let\@cite@ofmt\@firstofone\def\@biblabel#1{}\def\@cite#1#2{{#1\if@tempswa , #2\fi}}\makeatother
\DeclareUnicodeCharacter{2265}{\ensuremath{\geq}}
\DeclareUnicodeCharacter{2264}{\ensuremath{\leq}}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\newlength{\cslhangindent}\setlength{\cslhangindent}{1.5em}
\newlength{\csllabelwidth}\setlength{\csllabelwidth}{3em}
\newenvironment{CSLReferences}[2]{\interlinepenalty=10000\begin{list}{}{\setlength{\itemindent}{0pt}\setlength{\leftmargin}{0pt}\setlength{\parsep}{0.45em}\ifodd #1\setlength{\leftmargin}{\cslhangindent}\setlength{\itemindent}{-1\cslhangindent}\fi}}{\end{list}}
\newcommand{\CSLBlock}[1]{\hfill\break#1}\newcommand{\CSLLeftMargin}[1]{\parbox[t]{\csllabelwidth}{#1}}\newcommand{\CSLRightInline}[1]{\parbox[t]{\dimexpr\linewidth-\csllabelwidth\relax}{#1}}\newcommand{\CSLIndent}[1]{\hspace{\cslhangindent}#1}
\begin{document}
\thispagestyle{plain}
\begin{center}
{\small MONTREAL.AI\quad /\quad TRANSFORMATIONAL INTELLIGENCE}\par\vspace{0.7em}
{\fontsize{25}{29}\selectfont\bfseries AGI ALPHA FLYWHEEL}\par\vspace{0.35em}
{\Large\bfseries The Enterprise That Invents Its Next Economy}\par\vspace{0.6em}
{\large From Verified Criticism to Executable Repair}\par
{\normalsize An Operating Experiment and the Limits of Economic Compounding}\par\vspace{0.8em}
{\large Vincent Boucher}\par
President, MONTREAL.AI\par\vspace{0.4em}
29 October 2026\quad$\cdot$\quad Research edition 1.0.0\par
\end{center}
\input{abstract.tex}
\clearpage\begingroup\small\setlength{\parskip}{0pt}\tableofcontents\endgroup\clearpage
\input{body.tex}
\end{document}
"""
(P / "main.tex").write_text(main)
# Use highlighting-free output to keep LaTeX dependency surface small.
# Regenerate LaTeX with no highlighting if pandoc emitted environments.
if "Shaded" in body:
    subprocess.run(args + ["--to=latex", "--no-highlight", "--output=all-body.tex"], cwd=P, check=True)
    body = (P / "all-body.tex").read_text()
    body = re.sub(r"(figures/[A-Za-z0-9-]+)\.png", r"\1.pdf", body)
    body = re.sub(r"\\texttt\{([a-f0-9]{40,64})\}", r"\\path{\1}", body)
    marker = body.find("\\section{The missing link")
    (P / "abstract.tex").write_text(body[:marker])
    (P / "body.tex").write_text(body[marker:])
for i in range(2):
    with (P / f"qa/latex-pass-{i+1}.log").open("w") as log:
        cp = subprocess.run(
            ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            cwd=P,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if cp.returncode:
        print((P / f"qa/latex-pass-{i+1}.log").read_text()[-6000:])
        raise SystemExit(cp.returncode)
subprocess.run(
    args
    + [
        "--standalone",
        "--to=html5",
        "--mathml",
        "--toc",
        "--toc-depth=2",
        "--css=assets/style.css",
        "--embed-resources",
        "--metadata=pagetitle:AGI ALPHA FLYWHEEL — Research Edition 1.0.0",
        "--output=index.html",
    ],
    cwd=P,
    check=True,
)
h = (P / "index.html").read_text()
h = h.replace("<body>", '<body>\n<a class="skip" href="#abstract">Skip to the paper</a>\n<main>')
h = re.sub(
    r"<table([^>]*)>",
    r'<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable data table"><table\1>',
    h,
)
h = h.replace("</table>", "</table></div>")
h = re.sub(
    r'(<math[^>]*display="block"[\s\S]*?</math>)',
    r'<div class="equation-scroll" tabindex="0" role="region" aria-label="Scrollable equation">\1</div>',
    h,
)
h = re.sub(
    r'(<nav id="TOC"[\s\S]*?</nav>)',
    r'<details class="contents"><summary>Contents and navigation</summary>\1</details>',
    h,
)
h = h.replace("</body>", "</main>\n</body>")
(P / "index.html").write_text(h)
(P / "qa/build-record.json").write_text(
    json.dumps(
        {
            "latex_compiled": True,
            "passes": 2,
            "shell_escape": False,
            "html_full": True,
            "html_math": "embedded MathML",
            "figure_count": 7,
            "claim_count": len(claimmap),
            "shared_source": "manuscript.md + data/audited.json + references.bib",
        },
        indent=2,
    )
    + "\n"
)
print("Built main.pdf, editable LaTeX and complete offline index.html")
