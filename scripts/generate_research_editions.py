# SPDX-License-Identifier: Apache-2.0
"""Render three bilingual guides around the original research implementations."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
from typing import Any

from scripts.research_papers import CATALOG, parse_catalog

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/"
ARCHIVE = (
    "https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/"
    "4c412aff8cb41505dcc03e4ccd26d63db7362cb6/docs/research/editions/2026-10-23/"
)
RELEASE = REPO + "releases/"
DISCOVERY = "9d7339e2f3da9d46bb9d7dd948519519cba1c73b"
EDITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "autonomous-enterprises-foundry-v2",
        "directory": "research-foundry-v2",
        "name": "Foundry v2",
        "pages": 33,
        "journey": "../../reports/thermal-fluid-foundry-v2/experience.html",
        "action": ("Explore the recorded foundry", "Explorer la fonderie documentée"),
        "scope": (
            "An interactive evidence reader for a simulated thermal-fluid foundry. It presents retained results and downloads; opening the page does not construct a physical instrument or launch a new native run.",
            "Un lecteur interactif des preuves d’une fonderie thermo-fluidique simulée. Il présente les résultats conservés et leurs téléchargements; ouvrir cette page ne construit pas d’instrument physique et ne lance pas d’exécution native.",
        ),
        "steps": (
            (
                "Inspect the beneficiary requirement and retained instrument construction.",
                "Examiner le besoin du bénéficiaire et la construction d’instrument conservée.",
            ),
            (
                "Compare calibration, qualification, calorimetry and the distinct simulated successor.",
                "Comparer l’étalonnage, la qualification, la calorimétrie et le successeur simulé distinct.",
            ),
            (
                "Download the method, capability and original evidence records from the reader. Preserve their source bindings.",
                "Télécharger la méthode, la capacité et les preuves originales depuis le lecteur. Conserver leurs liens aux sources.",
            ),
        ),
        "downloads": (
            (
                "Complete LaTeX source ZIP",
                "Sources LaTeX complètes ZIP",
                RELEASE + "download/study-foundry-v2-2026-10-22-r1/Autonomous_Enterprises_Foundry_v2_LaTeX_Source.zip",
            ),
            (
                "Complete research companion ZIP",
                "Compagnon de recherche complet ZIP",
                RELEASE
                + "download/study-foundry-v2-2026-10-22-r1/Autonomous_Enterprises_Foundry_v2_Research_Companion.zip",
            ),
            (
                "Original source and evidence release",
                "Publication originale des sources et preuves",
                RELEASE + "tag/study-foundry-v2-2026-10-22-r1",
            ),
        ),
        "limits": (
            "The 4.9477% runtime prediction/observation difference passes its 5% rule while true-heat error is 8.6964%. Conventional engineering ties useful accuracy with 384 rather than 672 readings; the centralized lab is CAD 460 cheaper. Physical construction, market demand and realized profit remain unestablished.",
            "L’écart opérationnel prédiction/observation de 4,9477 % respecte son seuil de 5 %, tandis que l’erreur sur la chaleur vraie atteint 8,6964 %. L’approche classique égale la précision utile avec 384 lectures contre 672; le laboratoire centralisé coûte 460 CAD de moins. Construction physique, demande du marché et profit réalisé restent non établis.",
        ),
    },
    {
        "id": "autonomous-enterprises-capability-inheritance-v1",
        "directory": "research-capability-inheritance-v1",
        "name": "Capability Inheritance",
        "pages": 25,
        "journey": "../../successor/work/",
        "action": ("Open the existing capability workbench", "Ouvrir l’atelier de capacités existant"),
        "scope": (
            "Use the existing browser workbench for its supported mathematical families and evidence packs. The new thermal-witness adapter is a separate native candidate in PR#4871; it is not made browser-executable by this guide.",
            "Utiliser l’atelier Web existant pour ses familles mathématiques prises en charge et ses paquets de preuves. Le nouvel adaptateur thermal-witness est un candidat natif distinct dans la PR nº4871; ce guide ne le rend pas exécutable dans le navigateur.",
        ),
        "steps": (
            (
                "Choose one of the workbench’s supported mathematical missions and inspect its declared inputs.",
                "Choisir une mission mathématique prise en charge par l’atelier et examiner ses entrées déclarées.",
            ),
            (
                "Execute that bounded browser computation and inspect the resulting source-bound evidence pack.",
                "Exécuter ce calcul Web borné et examiner le paquet de preuves lié aux sources.",
            ),
            (
                "Read the edition’s retained 48-task and successor comparisons below. These research records are separate from the new browser run.",
                "Lire les comparaisons conservées des 48 tâches et du successeur ci-dessous. Ces preuves de recherche sont distinctes de la nouvelle exécution Web.",
            ),
        ),
        "downloads": (
            (
                "Complete supplied source and evidence ZIP",
                "Sources et preuves complètes fournies ZIP",
                ARCHIVE + "Autonomous_Enterprises_SUCCESSOR_Omega_Complete_Source.zip",
            ),
            (
                "Original vector figures ZIP",
                "Figures vectorielles originales ZIP",
                ARCHIVE + "Autonomous_Enterprises_SUCCESSOR_Omega_Figures.zip",
            ),
            ("Original implementation and evidence", "Implémentation et preuves originales", REPO + "pull/4871"),
        ),
        "limits": (
            "The retained 48-task treatment uses 63,196 counted work units versus 915,136 for rebuilding, while the supplied expert uses 5,760. Inherited successor qualification loses 7,918 versus 2,030 directly. The distinct thermal witness is simulated; its conditional 1.8862% bound is not physical validation. Complete monetary, energy and human costs are unknown.",
            "Le traitement conservé des 48 tâches utilise 63 196 unités comptées contre 915 136 pour reconstruire, tandis que l’expert fourni en utilise 5 760. La qualification héritée du successeur coûte 7 918 unités contre 2 030 directement. Le témoin thermique distinct est simulé; sa borne conditionnelle de 1,8862 % n’est pas une validation physique. Les coûts monétaires, énergétiques et humains complets sont inconnus.",
        ),
    },
    {
        "id": "autonomous-enterprises-discoverability-v1",
        "directory": "research-discoverability-v1",
        "name": "The Discoverability Compiler",
        "pages": 24,
        "journey": "../../research/discoverability/",
        "action": ("Open the synthetic measurement compiler", "Ouvrir le compilateur de mesures synthétiques"),
        "scope": (
            "The original compiler experience performs new synthetic computation locally: construct a decision-separating measurement, acquire modeled observations and inspect the decoded decision. Settlement is NOT CONNECTED. This is the corrected implementation from the original PR#4872.",
            "L’expérience originale du compilateur réalise un nouveau calcul synthétique local : construire une mesure séparant les décisions, acquérir des observations modélisées et examiner la décision décodée. Le règlement financier est NON CONNECTÉ. Il s’agit de l’implémentation corrigée de la PR originale nº4872.",
        ),
        "steps": (
            (
                "Choose a supported digital, mixture or network mission; construct its bounded measurement program.",
                "Choisir une mission numérique, de mélange ou de réseau prise en charge; construire son programme de mesure borné.",
            ),
            (
                "Acquire synthetic observations, inspect decisions and costs, then change the requirement or nuisance model to examine reuse or refusal.",
                "Acquérir des observations synthétiques, examiner décisions et coûts, puis modifier l’exigence ou les perturbations pour étudier réutilisation ou refus.",
            ),
            (
                "Stop at a bounded checkpoint or export evidence. A restored export is inert and confers no execution, admission or financial authority.",
                "Arrêter à un point de contrôle borné ou exporter les preuves. Une exportation restaurée reste inerte et ne confère aucune autorité d’exécution, d’admission ou financière.",
            ),
        ),
        "downloads": (
            (
                "Frozen edition source and evidence ZIP ·32485e07",
                "Sources et preuves figées de l’édition ZIP ·32485e07",
                ARCHIVE + "Autonomous_Enterprises_Discoverability_Compiler_Source_32485e07.zip",
            ),
            (
                "Current corrected source ·9d7339e",
                "Sources corrigées actuelles ·9d7339e",
                REPO + "tree/" + DISCOVERY + "/examples/successor-discoverability",
            ),
            (
                "Current correction and retained evidence",
                "Correction actuelle et preuves conservées",
                REPO + "tree/" + DISCOVERY + "/docs/research/discoverability/evidence",
            ),
        ),
        "limits": (
            "Conventional baselines tie development acquisition costs; an adaptive control wins. Reuse reduces counted construction work, but timing reverses between runs and centralized direct execution wins both. The ≤US$100→US$10,000 challenge is UNPROVEN. The frozen ZIP predates the strict decision-mode correction; use the separately linked current source and amendment for that correction.",
            "Les références classiques égalent les coûts d’acquisition en développement; un témoin adaptatif gagne. La réutilisation réduit le travail compté, mais le classement temporel s’inverse entre exécutions et l’exécution centralisée directe gagne les deux fois. Le défi ≤100 $US→10 000 $US reste NON DÉMONTRÉ. Le ZIP figé précède la validation stricte des modes; utiliser les sources actuelles et l’amendement liés séparément pour cette correction.",
        ),
    },
)

STYLE = """
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#071321;color:#e7edf7;line-height:1.65}
*{box-sizing:border-box}body{margin:0}a{color:#98c7ff;text-underline-offset:.22em;overflow-wrap:anywhere}
a:focus-visible{outline:3px solid #ffd486;outline-offset:5px}a:hover{color:#fff}header,main,footer{max-width:1120px;margin:auto;padding:24px}
header{display:flex;justify-content:space-between;gap:20px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #30445e}
.languages{display:flex;gap:18px}.languages [aria-current=true]{color:#fff;font-weight:700}
.eyebrow{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:#a8bce0}.hero{padding:36px 0 25px}
h1{font-size:clamp(2rem,5vw,3.8rem);line-height:1.12;max-width:900px;margin:.35em 0}h2{font-size:1.45rem;margin:0 0 15px}p{max-width:80ch}
.subtitle{color:#c1d0e4;font-size:1.15rem}.grid{display:grid;grid-template-columns:1.35fr 1fr;gap:24px}
section{background:#102139;border:1px solid #30445e;border-radius:16px;padding:26px;margin-bottom:24px;min-width:0}
.actions{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}.button{display:inline-block;padding:11px 18px;border:1px solid #719dd4;border-radius:9px;text-decoration:none;font-weight:650}.primary{background:#c0d9ff;color:#102139;border-color:#c0d9ff}.primary:hover{background:white;color:#102139}
li{margin:12px 0}ul,ol{padding-left:22px}.note{color:#c5d0e0;font-size:.93rem}.scope{border-left:4px solid #e9be75;padding-left:16px}.digest{font-family:monospace;overflow-wrap:anywhere;font-size:.82rem}
footer{border-top:1px solid #30445e;color:#b7c7de}.skip{position:absolute;left:20px;top:-80px;background:white;color:black;padding:12px;z-index:2}.skip:focus{top:12px}
html[data-ui-language=en] [data-language=fr],html[data-ui-language=fr] [data-language=en]{display:none}
@media(max-width:700px){.grid{grid-template-columns:1fr}header,main,footer{padding:18px}section{padding:20px}.hero{padding:24px 0}.actions .button{width:100%;text-align:center}}
@media(prefers-reduced-motion:no-preference){a{transition:background-color .15s,color .15s}}
"""
SCRIPT = """
const links=[...document.querySelectorAll('[data-set-language]')];
function setLanguage(language){
  const lang=language==='fr'?'fr':'en';document.documentElement.lang=lang;
  document.documentElement.dataset.uiLanguage=lang;
  for(const a of links)a.setAttribute('aria-current',String(a.dataset.setLanguage===lang));
  for(const a of document.querySelectorAll('[data-site-language]')){const u=new URL(a.href);u.searchParams.set('lang',lang);a.href=u.href}
  const u=new URL(location.href);u.searchParams.set('lang',lang);history.replaceState(null,'',u);
}
setLanguage(new URL(location.href).searchParams.get('lang')||(navigator.language||'en').slice(0,2));
for(const a of links)a.addEventListener('click',event=>{event.preventDefault();setLanguage(a.dataset.setLanguage)});
"""


def bilingual(english: str, french: str) -> str:
    """Escape both translations; the no-script fallback shows both."""
    return (
        '<span data-language="en" lang="en">' + escape(english) + "</span>"
        '<span data-language="fr" lang="fr">' + escape(french) + "</span>"
    )


def render(edition: dict[str, Any], row: dict[str, Any]) -> str:
    """Keep original routes and bytes; navigation never grants execution authority."""
    pdf = "../../" + row["pdf"]["path"].removeprefix("docs/")
    tex = "../../" + row["tex"]["path"].removeprefix("docs/")
    items = "".join("<li>" + bilingual(*step) + "</li>" for step in edition["steps"])
    downloads = "".join(
        '<li><a href="' + escape(url, quote=True) + '">' + bilingual(en, fr) + "</a></li>"
        for en, fr, url in edition["downloads"]
    )
    related = "".join(
        '<li><a data-site-language href="../'
        + other["directory"]
        + '/index.html">'
        + escape(other["name"])
        + "</a></li>"
        for other in EDITIONS
        if other["id"] != edition["id"]
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{escape(row["subtitle"], quote=True)}"><title>{escape(edition["name"])} · Research reading and resources</title>
<style>{STYLE}</style></head><body>
<a class="skip" href="#main">{bilingual("Skip to content", "Aller au contenu")}</a>
<header><a data-site-language href="../../#papers">← {bilingual("Research library", "Bibliothèque de recherche")}</a>
<nav class="languages" aria-label="Language / Langue"><a href="?lang=en" data-set-language="en" lang="en">English</a><a href="?lang=fr" data-set-language="fr" lang="fr">Français</a></nav></header>
<main id="main"><div class="hero"><p class="eyebrow">{bilingual("Autonomous Enterprises · research edition", "Autonomous Enterprises · édition de recherche")} · {edition["pages"]} pages</p>
<h1 lang="en">{escape(edition["name"])}</h1><p class="subtitle" lang="en">{escape(row["subtitle"])}</p>
<p>{bilingual(row["summary"]["en"], row["summary"]["fr"])}</p>
<div class="actions"><a class="button primary" type="application/pdf" href="{pdf}">{bilingual("Read the original PDF", "Lire le PDF original")} ↗</a>
<a class="button" href="{tex}" download>{bilingual("Download TeX", "Télécharger le TeX")}</a></div></div>
<noscript><p>{bilingual("Both languages are shown without JavaScript. All reading and download links work.", "Les deux langues sont affichées sans JavaScript. Tous les liens de lecture et de téléchargement fonctionnent.")}</p></noscript>
<div class="grid"><div><section aria-labelledby="journey"><h2 id="journey">{bilingual("Explore the supported journey", "Explorer le parcours pris en charge")}</h2>
<p>{bilingual(*edition["scope"])}</p><ol>{items}</ol>
<a class="button" data-site-language href="{escape(edition["journey"], quote=True)}">{bilingual(*edition["action"])} →</a>
<p class="note">{bilingual("The original experiment interfaces may use English. This reading guide is available in English and French. These experimental interfaces run modeled workloads. The new native four-repository and physical journeys are not available here.", "Les interfaces originales peuvent utiliser l’anglais. Ce guide est disponible en anglais et en français. Ces interfaces expérimentales exécutent des tâches modélisées. Les nouveaux parcours natifs à quatre dépôts et les parcours physiques ne sont pas disponibles ici.")}</p></section>
<section aria-labelledby="limits"><h2 id="limits">{bilingual("Results and limits", "Résultats et limites")}</h2><p class="scope">{bilingual(*edition["limits"])}</p>
<p>{bilingual("Modeled transactions are separate from live integrations. No funds, credentials, physical construction or commercial outcome are activated here.", "Les transactions modélisées sont distinctes des intégrations réelles. Aucun fonds, identifiant, dispositif physique ni résultat commercial n’est activé ici.")}</p></section></div>
<aside><section aria-labelledby="downloads"><h2 id="downloads">{bilingual("Complete source and evidence", "Sources et preuves complètes")}</h2><ul>{downloads}</ul>
<p class="note">{bilingual("The single TeX file needs its complete source package to reproduce the manuscript. Original archives and unfavorable results are preserved.", "Le fichier TeX seul nécessite son paquet de sources complet pour reproduire le manuscrit. Les archives originales et résultats défavorables sont conservés.")}</p>
<details><summary>{bilingual("Original PDF identity", "Identité du PDF original")}</summary><p class="digest">SHA-256 {row["pdf"]["sha256"]}</p></details>
<p><a href="./index.html" download>{bilingual("Save this reading guide", "Enregistrer ce guide de lecture")}</a></p></section>
<section aria-labelledby="related"><h2 id="related">{bilingual("The other research editions", "Les autres éditions de recherche")}</h2><ul>{related}</ul>
<a data-site-language href="../../#papers">{bilingual("All historical papers", "Toutes les publications historiques")} →</a></section></aside></div></main>
<footer><p>{escape(row["author"])} · {bilingual("Original manuscript in English. Research software and models are experimental.", "Manuscrit original en anglais. Les logiciels et modèles de recherche sont expérimentaux.")}</p>
<a href="../../DISCLAIMER_SNIPPET.md">{bilingual("Research prototype notice", "Avis de prototype de recherche")}</a></footer>
<script>{SCRIPT}</script></body></html>
'''


def generate(root: Path, check: bool = False) -> None:
    """Render without running an experiment, model, browser or native worker."""
    path = root / CATALOG
    catalog = parse_catalog(path.read_bytes())
    rows = {row["id"]: row for row in catalog["papers"]}
    for edition in EDITIONS:
        row = rows[edition["id"]]
        relative = "docs/reports/" + edition["directory"] + "/index.html"
        content = render(edition, row).encode()
        binding = {"path": relative, "sha256": hashlib.sha256(content).hexdigest()}
        target = root / relative
        if check:
            if (
                not target.is_file()
                or target.read_bytes() != content
                or row.get("resources", {}).get("reading") != binding
            ):
                raise ValueError("Research reading guide or identity is stale: " + relative)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            row.setdefault("resources", {})["reading"] = binding
    if not check:
        parse_catalog(json.dumps(catalog).encode())
        path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(args.root, args.check)


if __name__ == "__main__":
    main()
