# SPDX-License-Identifier: Apache-2.0
"""Bind publication sections to explicit data; draft generation never invents results."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
GEN = PAPER / "generated"


def tex(value):
    text = str(value if value is not None else "")
    for old, new in {"–": "--", "—": "---", "−": "-", "’": "'", "‘": "'", "“": "``", "”": "''", "\u00a0": " ", "→": " to ", "≥": ">=", "≤": "<=", "Ω": "Omega", "∞": "infinity"}.items():
        text = text.replace(old, new)
    chars = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(chars.get(c, c) for c in text)


def prose(value):
    parts = value if isinstance(value, list) else str(value).split("\n\n")
    return "\n\n".join(tex(part.strip()) for part in parts if part.strip())


def money(value):
    n=float(value)
    return ("-" if n<0 else "") + r"\$" + f"{abs(n):,.2f}"


def cell(value, kind="text"):
    if value is None:
        return r"\textemdash{}"
    if kind == "money":
        return money(value)
    if kind == "percent":
        return f"{100 * float(value):.1f}" + r"\%"
    if kind == "number":
        return f"{float(value):,.2f}".rstrip("0").rstrip(".")
    return tex(value)


def table(spec, path):
    columns = spec["columns"]
    widths = spec.get("widths")
    is_long = spec.get("long", False)
    if widths:
        fmt = "".join(r">{\raggedright\arraybackslash}p{" + str(w) + r"\linewidth}" for w in widths)
    else:
        fmt = "Y" + "r" * (len(columns) - 1)
    if is_long and not widths:
        fmt = r">{\raggedright\arraybackslash}p{.33\linewidth}" + "".join(r">{\raggedright\arraybackslash}p{" + str(.54 / (len(columns) - 1)) + r"\linewidth}" for _ in columns[1:])
    header = " & ".join(tex(c["label"]) for c in columns) + r"\\\midrule"
    if is_long:
        lines = [r"\begingroup\small\begin{longtable}{" + fmt + "}", r"\caption{" + tex(spec["caption"]) + r"}\\", r"\toprule", header, r"\endfirsthead\toprule", header, r"\endhead"]
    else:
        lines = [r"\begin{table}[!htbp]\centering\small", r"\caption{" + tex(spec["caption"]) + "}", r"\begin{tabularx}{\linewidth}{" + fmt + r"}\toprule", header]
    for row in spec["rows"]:
        lines.append(" & ".join(cell(row.get(c["key"]), c.get("kind", "text")) for c in columns) + r"\\")
    lines += [r"\bottomrule", r"\end{longtable}\endgroup" if is_long else r"\end{tabularx}"]
    if spec.get("note"):
        lines.append(r"\par\smallskip{\footnotesize\color{muted}" + prose(spec["note"]) + r"}\par")
    if not is_long:
        lines.append(r"\end{table}")
    path.write_text("\n".join(lines) + "\n")


def static_tables():
    d = json.loads((ROOT / "evidence" / "market_calibration.json").read_text())
    teams = d["human_team"]["scenarios"]
    rows = []
    for i, role in enumerate(d["human_team"]["roles"]):
        rows.append({"role": role["role"].replace("_", " "), "rate": role["usd_per_hour"], **{k: teams[k]["rows"][i]["hours"] for k in teams}})
    rows += [{"role": "Total assumed person-hours", "rate": None, **{k: teams[k]["hours"] for k in teams}}, {"role": "Human service estimate (USD)", "rate": None, **{k: teams[k]["labor_service_estimate_usd"] for k in teams}}]
    table({"caption": "Matched multidisciplinary service estimate. Current reported SIM&S bill rates; all hours are assumed. Low, central and high describe comparator effort, not empirically estimated distributions.", "columns": [{"key": "role", "label": "Role"}, {"key": "rate", "label": "USD/h", "kind": "money"}] + [{"key": k, "label": k.title(), "kind": "number"} for k in teams], "rows": rows, "note": "US schedule, effective 1 October 2026–30 September 2027; IFF included. Hours are per accepted package, including an assumed allocation for failed search. Half of the low estimate is $7,167.10. These are ceiling-rate-based scope estimates, not comparable contingent-service quotes."}, GEN / "human_team_table.tex")
    short_ids = {"SIMS2026": "SIMS 2026", "GSA_GUIDANCE": "GSA guide", "ECONOMETRICA2026": "Econometrica", "GSI2026": "GSI 2026", "AWS_FARGATE": "AWS Fargate", "HEXALY_BLUEFACES": "Hexaly case", "ORTOOLS_JOBSHOP": "OR-Tools", "UPS_ORION": "UPS ORION", "NASA_CREDIBILITY": "NASA", "DAFNY": "Dafny"}
    source_rows = [{"id": short_ids.get(s["id"], s["id"].replace("_", " ")), "basis": s["title"], "use": s.get("scope_limit", s.get("claim", ""))} for s in d["sources"]]
    table({"caption": "Market and scope evidence. Full URLs, exact dates, rates and retrieval hashes are in evidence/market_calibration.json.", "columns": [{"key": "id", "label": "Source ID"}, {"key": "basis", "label": "Reported basis"}, {"key": "use", "label": "Inference boundary"}], "rows": source_rows, "widths": [.16, .31, .45], "long": True}, GEN / "source_table.tex")


def references():
    entries = [
        ("TI", "Vincent Boucher", "Transformational Intelligence: Learning to Change the Game", "October 2026 research manuscript; inspected immutable source", "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/098117379f2920ebe37ab23dad77b7314a32518c/docs/Transformational_Intelligence.pdf"),
        ("Gym", "Vincent Boucher", "Gym, Specialist ASI & Successor Ω: The Sovereign Mission Environment, the Proven Intelligence Institution, and the Successor to the Successor in Singularity Time", "Version 2.1.0, 10 August 2026; 83 PDF pages; theoretical/design source, synthetic examples excluded from calibration", "https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/GoalOS_Gym_Specialist_ASI_Successor_Omega_v2_1_0_US_LETTER.pdf"),
        ("SIMS", "Systems Integration / Modeling & Simulation, Inc.", "GSA Multiple Award Schedule GS-07F-0011V", "5 May 2026; current rates 1 October 2026–30 September 2027", "https://www.gsaadvantage.gov/ref_text/GS07F0011V/GS07F0011V_GSAMass_Supply_Schedule_TC_05062026.pdf"),
        ("GSA", "US General Services Administration", "CALC+ pricing information and ceiling-rate guidance", "Accessed 26 October 2026", "https://buy.gsa.gov/pricing/qr/know-more"),
        ("ORTools", "Google", "The Job Shop Problem: OR-Tools documentation", "Accessed 26 October 2026", "https://developers.google.com/optimization/scheduling/job_shop"),
        ("Hexaly", "Hexaly", "How Blue Faces solves complex project scheduling problems in minutes with Hexaly", "1 July 2021; vendor case; accessed 26 October 2026", "https://www.hexaly.com/customers/how-bluefaces-solves-complex-project-scheduling-problems-in-minutes-with-hexaly"),
        ("AWS", "Amazon Web Services", "AWS Fargate Pricing", "US East Linux/x86 example; accessed 26 October 2026", "https://aws.amazon.com/fargate/pricing/"),
        ("NASA", "NASA", "Modeling and Simulations: FAQ and credibility definitions", "Accessed 26 October 2026", "https://public.ksc.nasa.gov/mns/faq/"),
        ("Dafny", "Dafny project", "Dafny: verification-aware programming language", "Accessed 26 October 2026", "https://dafny.org/"),
        ("FunSearch", "B. Romera-Paredes et al.", "Mathematical discoveries from program search with large language models", "Nature, 2023/2024", "https://www.nature.com/articles/s41586-023-06924-6"),
        ("AlphaEvolve", "A. Novikov et al.", "AlphaEvolve: A coding agent for scientific and algorithmic discovery", "2025; original authors' report", "https://arxiv.org/html/2506.13131v1"),
        ("EoH", "F. Liu et al.", "Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model", "ICML 2024; version 3", "https://arxiv.org/html/2401.02051v3"),
        ("Harness", "Ishibashi, Yano and Oyamada", "Effective Harness Engineering for Algorithm Discovery with Coding Agents", "13 May 2026; narrow independent study", "https://arxiv.org/html/2605.15221v1"),
        ("OpenAIModels", "OpenAI", "Latest model guide", "Accessed 26 October 2026; configurations pinned in evidence register", "https://developers.openai.com/api/docs/guides/latest-model"),
        ("OpenAIPrices", "OpenAI", "API pricing", "Accessed 26 October 2026", "https://developers.openai.com/api/docs/pricing"),
        ("Foundations", "MontrealAI", "AGI ALPHA coordination record and inspected implementation foundations", "Issue 4850; source hashes in companion inventory", "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850"),
        ("V93", "Montreal.AI Research", "GoalOS V93 RSI Validated Skill Graph Ascension Lab", "Local interactive research draft; full HTML and embedded program inspected 26 October 2026", "https://github.com/MontrealAI/MontrealAI.github.io/blob/a9cc143bc05495405ac63b0e2645c425d66410b8/goalos-v93-rsi-validated-skill-graph-ascension-lab-interface.html"),
        ("V97", "Montreal.AI Research", "GoalOS V97.4: Private On-Chain Validated Skill Graph", "Research draft, 8 PDF pages; inspected immutable source 26 October 2026", "https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/goalos_private_onchain_zk_vsg.pdf"),
        ("Merkle", "MONTREAL.AI", "Merkle Roots for the Validated Skill Graph", "GoalOS V114; source inspected 26 October 2026", "https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/Merkle_Roots_for_the_Validated_Skill_Graph_v114.pdf"),
        ("ProofLoops", "MONTREAL.AI", "PROOF LOOPS", "Author edition v2; source inspected 26 October 2026", "https://github.com/MontrealAI/goalos-agialpha-sovereign-machine-economy/blob/1e9a5675b1662e98074fb1c71cf2c5b94c7d259f/docs/paper/PROOF_LOOPS_research_paper_v2_author_edition.pdf"),
    ]
    lines = [r"\begin{thebibliography}{99}\small\setlength{\itemsep}{3pt}"]
    for key, who, title, when, url in entries:
        lines.append(r"\bibitem{" + key + "}" + tex(who) + ". " + r"\emph{" + tex(title) + "}. " + tex(when) + ". " + r"\url{" + url + "}.")
    lines.append(r"\end{thebibliography}")
    (GEN / "references.tex").write_text("\n".join(lines) + "\n")


NARRATIVE = ["Executive", "Abstract", "Protocol", "MainResults", "Pricing", "Investment", "NewOpportunities", "Network", "MovingBeta", "Admission", "Witness", "Campaigns", "Automation", "Fragility", "Conclusion", "French", "Audit"]
TABLES = ["transformation", "job_class", "contrast", "model", "policy", "primary", "pricing", "investment", "accounting", "network", "moving_beta", "campaign", "sensitivity", "parameter", "workflow", "construction", "threshold"]
FIGURES = ["Economics", "Profit", "Pricing", "Investment", "Cash", "Network", "MovingBeta", "Campaign", "Sensitivity"]


def bind(data, draft):
    if not draft:
        for key in NARRATIVE:
            if not data.get("narrative", {}).get(key):
                raise ValueError("Missing final result narrative: " + key)
        for key in TABLES:
            if key not in data.get("tables", {}):
                raise ValueError("Missing final table: " + key)
        if data.get("status") != "bound_to_frozen_results":
            raise ValueError("Final data must declare bound_to_frozen_results")
    lines = [r"\newcommand{\StudyVersion}{" + tex(data.get("version", "working draft; results not bound")) + "}"]
    for key in NARRATIVE:
        body = data.get("narrative", {}).get(key, "Working draft: this section awaits the frozen simulator and fresh confirmation. No economic outcome is asserted.")
        lines.append(r"\newcommand{\Result" + key + "}{" + prose(body) + "}")
    for name in FIGURES:
        spec = data.get("figures", {}).get(name)
        value = ""
        if spec:
            file = ROOT / spec["path"]
            if not file.exists():
                raise ValueError("Missing figure " + str(file))
            value = r"\studyfigure{../" + spec["path"] + "}{" + str(spec.get("width", 1)) + "}{" + tex(spec["caption"]) + "}"
        lines.append(r"\newcommand{\Result" + name + "Figure}{" + value + "}")
    (GEN / "results.tex").write_text("\n\n".join(lines) + "\n")
    for name in TABLES:
        spec = data.get("tables", {}).get(name)
        if spec:
            table(spec, GEN / (name + "_table.tex"))
        else:
            (GEN / (name + "_table.tex")).write_text("% Draft: table awaiting frozen inputs/results.\n")
    (GEN / "reproduction.tex").write_text(prose(data.get("reproduction", "Working draft: reproduction commands and exact freeze identities will be bound after registration.")) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=PAPER / "paper_data.json")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    GEN.mkdir(exist_ok=True)
    data = json.loads(args.data.read_text()) if args.data.exists() else {}
    static_tables()
    references()
    bind(data, args.draft)
    if args.compile:
        for i in range(2):
            proc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex"], cwd=PAPER, text=True, capture_output=True)
            (PAPER / f"build-pass-{i + 1}.log").write_text(proc.stdout + proc.stderr)
            if proc.returncode:
                print(proc.stdout[-6000:])
                raise SystemExit(proc.returncode)
        name = "working_draft.pdf" if args.draft else "beyond_beta_network.pdf"
        (PAPER / name).write_bytes((PAPER / "main.pdf").read_bytes())
        print(PAPER / name)


if __name__ == "__main__":
    main()
