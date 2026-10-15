# SPDX-License-Identifier: Apache-2.0
"""Build the source kit; never modify the historical 98-file archive."""

from __future__ import annotations
import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSS = (
    ":root{color-scheme:dark;font:18px/1.65 system-ui,-apple-system,sa"
    "ns-serif;background:#100b20;color:#f7f3ff}*{box-sizing:border-box"
    "}body{margin:0;background:radial-gradient(ellipse at 80% 0,#36214"
    "f,transparent 55%)}main,header,footer{width:min(1100px,calc(100% "
    "- 40px));margin:auto}header{padding:22px 0;display:flex;flex-wrap"
    ":wrap;justify-content:space-between;gap:16px;border-bottom:1px so"
    "lid #614e76}a{color:#e1c6ff;text-underline-offset:4px;overflow-wr"
    "ap:anywhere}.brand{text-decoration:none;font-weight:750;letter-sp"
    "acing:.1em}.eyebrow{letter-spacing:.15em;font-size:.72rem;color:#"
    "d2b6ef}h1{font-size:clamp(2.2rem,6vw,4.2rem);line-height:1.1;lett"
    "er-spacing:-.045em;margin:.35em 0}h2{font-size:1.6rem;line-height"
    ":1.3}h3{font-size:1.12rem;line-height:1.3}.hero{padding:60px 0 32"
    "px;max-width:900px}.lead{font-size:1.13rem;color:#e1d7ee}.grid{di"
    "splay:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px"
    "}.card,.notice{border:1px solid #65517c;border-radius:18px;paddin"
    "g:24px;background:#1c142e}.card{margin:12px 0}.badge{display:inli"
    "ne-block;padding:3px 10px;border-radius:20px;border:1px solid #92"
    "70af;font-size:.75rem}.pending{color:#ffe4ab}.actions{display:fle"
    "x;gap:12px;flex-wrap:wrap;margin:20px 0}.button,button{display:in"
    "line-flex;align-items:center;justify-content:center;min-height:48"
    "px;padding:10px 18px;border:1px solid #9375ae;border-radius:10px;"
    "font:inherit;background:#2a1e3d;color:#f7f3ff;text-decoration:non"
    "e;cursor:pointer}.primary{background:#e0c3ff;color:#160c23;font-w"
    "eight:720}.muted{font-size:.9rem;color:#ccbedb}.steps{padding-lef"
    "t:24px}.steps li{margin:15px 0}section{padding:22px 0;scroll-marg"
    "in-top:20px}pre{font:14px/1.6 ui-monospace,monospace;white-space:"
    "pre-wrap;overflow-wrap:anywhere;border:1px solid #614e76;backgrou"
    "nd:#0f0b1b;padding:18px;border-radius:12px}details{padding:16px 0"
    "}summary{cursor:pointer;min-height:44px}iframe{width:100%;height:"
    "780px;border:1px solid #66537a;border-radius:16px;background:whit"
    "e}footer{padding:32px 0;border-top:1px solid #614e76}.skip{positi"
    "on:absolute;left:10px;top:-200px}.skip:focus{top:8px;z-index:10;b"
    "ackground:#100b20;padding:10px}:focus-visible{outline:3px solid #"
    "ffe4ab;outline-offset:4px}.large{font-size:22px}nav{display:flex;"
    "gap:10px;flex-wrap:wrap}[hidden]{display:none!important}.status-r"
    "ow{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}@media(max-"
    "width:680px){.grid{grid-template-columns:1fr}.hero{padding-top:34"
    "px}.card,.notice{padding:19px}iframe{height:760px}}@media print{h"
    "tml,body{color:#111!important;background:#fff!important;color-sch"
    "eme:light}header,footer,nav,.actions,iframe,button{display:none!i"
    "mportant}main{width:100%;max-width:none}h1{font-size:30pt}.card,."
    "notice,pre{background:#fff!important;color:#111!important;border:"
    "1px solid #bbb;break-inside:avoid}.muted,.lead,.eyebrow,.pending,"
    "a{color:#222!important}.grid{display:block}section{padding:8px 0}"
    "@page{margin:16mm}}"
)
BODY = (
    '<a class="skip" href="#main">Skip to content / Aller au contenu</'
    'a><header><a class="brand" href="https://github.com/MontrealAI/AG'
    'I-Alpha-Agent-v0">Ω AGI ALPHA</a><nav aria-label="Reading prefere'
    'nces"><button id="language">Français</button><button id="size" ar'
    'ia-pressed="false">Larger text</button></nav></header><main id="m'
    'ain"><section class="hero"><p class="eyebrow">EVIDENCE & RECOVERY'
    ' KIT · 14 OCTOBER 2026</p><h1 data-fr="Essayez le travail.<br>Exa'
    'minez les preuves.">Try the work.<br>Inspect the evidence.</h1><p'
    ' class="lead" data-fr="Deux sites fonctionnels, leurs sources et '
    "les tests. Une récupération guidée. Un protocole pour mesurer l’u"
    'tilité avec de vraies personnes — sans inventer les résultats.">T'
    "wo working websites, their source and the checks behind them. Gui"
    "ded recovery. A protocol to measure usefulness with real people—w"
    'ithout inventing results.</p><div class="actions"><a class="butto'
    'n primary" href="#examples" data-fr="Essayer les exemples ↓">Try '
    'the examples ↓</a><a class="button" href="https://github.com/Mont'
    "realAI/AGI-Alpha-Agent-v0/releases/tag/study-computer-use-2026-10"
    '-14-r1" data-fr="Téléchargements de l’étude ↗">Study downloads ↗<'
    '/a><a class="button" href="#reproduce" data-fr="Reproduire les te'
    'sts ↓">Reproduce the checks ↓</a></div><p class="muted" data-fr="'
    "Exemples synthétiques. Aucun compte, portefeuille, achat ni appel"
    " à un modèle. Ce kit n’est pas un service autonome en production."
    '">Synthetic study examples. No account, wallet, purchase or model'
    " call. This kit is not a production autonomous service.</p></sect"
    'ion><div class="status-row"><span class="badge" data-fr="01 · Liv'
    'rables fonctionnels">01 · Working artifacts</span><span class="ba'
    'dge" data-fr="02 · Sources consultables">02 · Inspectable source<'
    '/span><span class="badge" data-fr="03 · Outils de reproduction">0'
    '3 · Replay tools</span><span class="badge pending" data-fr="04 · '
    'Étude humaine : NON COMMENCÉE">04 · Human evidence: NOT STARTED</'
    'span></div><section id="examples"><h2 data-fr="Commencez par un r'
    'ésultat concret.">Start with something concrete.</h2><div class="'
    'grid"><article class="card"><span class="badge" data-fr="TÂCHE A '
    '· SYNTHÉTIQUE">TASK A · SYNTHETIC</span><h3>Atelier North</h3><p '
    'data-fr="Choisissez AI Foundations et 10 participants. L’estimati'
    'on attendue est de 445,50 CAD après la remise de 10 %.">Choose AI'
    " Foundations and 10 participants. The expected estimate is CAD 44"
    '5.50 after the 10% discount.</p><div class="actions"><a class="bu'
    'tton primary" href="02_Work_Products/Task_A/after/index.html" dat'
    'a-fr="Ouvrir le site A">Open website A</a><a href="02_Work_Produc'
    'ts/Task_A/OWNER_BRIEF.txt" data-fr="Voir la demande">Inspect the '
    'brief</a></div></article><article class="card"><span class="badge'
    '" data-fr="TÂCHE B · NOUVELLES EXIGENCES">TASK B · NEW REQUIREMEN'
    'TS</span><h3>Studio Horizon</h3><p data-fr="Un catalogue différen'
    "t : choisissez l’offre Design et 8 participants. Résultat attendu"
    " : 433,50 CAD. Les offres gratuites et complètes ont leurs propre"
    's règles.">A different catalogue: choose the Design offering and '
    "8 participants. Expected result: CAD 433.50. Free and sold-out of"
    'fers have their own rules.</p><div class="actions"><a class="butt'
    'on primary" href="02_Work_Products/Task_B/after/index.html" data-'
    'fr="Ouvrir le site B">Open website B</a><a href="02_Work_Products'
    '/Task_B/OWNER_BRIEF.txt" data-fr="Voir la demande">Inspect the br'
    'ief</a></div></article></div><p class="muted" data-fr="Ces deux l'
    "ivrables ont été produits pendant l’étude. Les ouvrir ne lance pa"
    "s AGI Alpha pour générer un nouveau site. Aucun atelier réel n’es"
    't vendu.">These deliverables were produced during the study. Open'
    "ing them does not run AGI Alpha to generate a new website. No rea"
    'l workshop is being sold.</p></section><section id="recover"><h2 '
    'data-fr="Sauvegardez. Fermez. Retrouvez le travail.">Save it. Clo'
    'se it. Bring it back.</h2><ol class="steps"><li data-fr="Ouvrez l'
    "e site A, choisissez l’offre et le nombre de places, puis calcule"
    'z.">Open website A, select the offer and number of places, then c'
    'alculate.</li><li data-fr="Examinez l’estimation, cochez la révis'
    'ion et téléchargez le résultat.">Inspect the estimate, check the '
    'review box and download the result.</li><li data-fr="Enregistrez '
    "aussi le brouillon de récupération. Gardez le fichier JSON dans u"
    'n dossier que vous retrouverez.">Also save the recovery draft. Ke'
    'ep its JSON file somewhere you can find.</li><li data-fr="Fermez '
    "l’exemple. Rouvrez-le et utilisez le contrôle de restauration pou"
    'r choisir le brouillon sauvegardé.">Close the example. Reopen it '
    "and use the restore control to select your saved draft.</li><li d"
    'ata-fr="Recalculez et révisez à nouveau. La révision précédente n'
    'e doit pas être héritée.">Calculate and review again. Previous ap'
    'proval must not carry over.</li><li data-fr="Essayez maintenant l'
    "e site B. Ses prix, capacités et permissions ne viennent pas du s"
    'ite A.">Now try website B. Its prices, capacities and permissions'
    ' do not come from website A.</li></ol><div class="notice"><strong'
    ' data-fr="Le fichier de travail n’est pas une autorisation.">A sa'
    'ved work file is not permission.</strong><p data-fr="Le travail n'
    "on sauvegardé peut être perdu. Une empreinte n’est ni une identit"
    "é, ni un chiffrement. Les tests de récupération contrôlés ne prou"
    'vent pas la résistance à une panne électrique.">Unsaved work can '
    "be lost. A hash is neither identity nor encryption. Controlled re"
    "covery tests do not establish power-loss resilience.</p></div></s"
    'ection><section id="inspect"><h2 data-fr="Ouvrez les pièces, pas '
    'seulement le résumé.">Open the evidence, not just the summary.</h'
    '2><div class="grid"><article class="card"><h3 data-fr="Sources et'
    ' exigences">Source and requirements</h3><p><a href="SOURCE_PROVEN'
    'ANCE.json">SOURCE_PROVENANCE.json</a> · <a href="04_Reproduce/sit'
    'e_template.html" data-fr="Modèle partagé original">Original share'
    'd template</a> · <a href="README.md" data-fr="Guide du kit">Kit g'
    'uide</a></p><p class="muted">The original source files are finger'
    "printed. The repaired apps are rebuilt byte-for-byte. Existing re"
    'port: <a href="01_Report/report.html">read the detailed English r'
    'eport</a>.</p></article><article class="card"><h3 data-fr="Compar'
    'aisons, y compris les échecs">Comparisons, including failures</h3'
    '><p><a href="02_Work_Products/Task_A/before/index.html" data-fr="'
    'A : exemple volontairement défectueux">A: defective fixture</a> ·'
    ' <a href="02_Work_Products/Task_B/before/index.html" data-fr="B :'
    ' exemple volontairement défectueux">B: defective fixture</a> · <a'
    ' href="02_Work_Products/Task_B/without-portability-fix/index.html'
    '" data-fr="B : une correction retirée">B: one fix removed</a></p>'
    '<p class="muted">These are intentionally failing comparisons, not'
    " recommended versions. One export defect caused six dependent fai"
    "lures. Do not interpret that as six independently repaired defect"
    's.</p></article></div></section><section id="reproduce"><h2 data-'
    'fr="Des résultats que l’on peut retester.">Results you can test a'
    'gain.</h2><p data-fr="Pour les personnes techniques : le kit cons'
    "erve le moteur de tests original et ajoute une vérification qui r"
    "efuse les résultats manquants ou différents. Les tests s’exécuten"
    't dans un nouveau dossier.">For technical readers: the kit preser'
    "ves the original harness and adds a checker that rejects missing "
    "or different outcomes. Tests run in a new directory.</p><pre>pyth"
    "on verify_and_replay.py --verify-only\npython verify_and_replay.py"
    " --output /absolute/path/to/new-replay</pre><p>Python 3.11–3.13 a"
    'nd reviewed Chromium/Playwright are required. <a href="README.md"'
    ">Installation and limitations</a>. Expected mechanical results: A"
    " 31/31; B 35/35; one-fix removal 29/35; recovery 19/19; owner con"
    "trols 14 versus 11. A replay tests existing code; it does not gen"
    'erate a new AI solution or measure human time.</p><p class="muted'
    '">Fresh CI evidence is a separate download on the study release. '
    "Historical results stay historical. This source kit is not the or"
    "iginal 98-file Office/PDF experiment archive.</p></section><secti"
    'on id="people"><h2 data-fr="La prochaine preuve vient de vraies p'
    'ersonnes.">The next evidence comes from real people.</h2><div cla'
    'ss="notice"><span class="badge pending">NOT STARTED · 0 OBSERVED '
    'PARTICIPANTS</span><p data-fr="Aucun gain humain n’a encore été m'
    "esuré. Le protocole distingue l’utilisabilité des exemples et l’e"
    "xécution réelle par AGI Alpha. Les résultats restent vides tant q"
    'ue les séances n’ont pas eu lieu.">No human benefit has yet been '
    "measured. The protocol separates usability of the examples from a"
    "ctual AGI Alpha execution. Results remain empty until sessions oc"
    'cur.</p><div class="actions"><a class="button" href="PILOT_PROTOC'
    'OL.html" data-fr="Lire le protocole">Read the protocol</a><a href'
    '="pilot/status.json" data-fr="Voir le statut">Inspect status</a><'
    'a href="pilot/session-template.csv" download data-fr="Modèle de m'
    'esure vierge">Blank observation template</a></div><p class="muted'
    '">Do not post personal details, workplace files, credentials or p'
    "articipant recordings in public issues. No compensation is promis"
    "ed. A public self-report is not an independently observed result."
    '</p></div></section><section><h2 data-fr="Ce qui fonctionne aujou'
    'rd’hui">What works today</h2><p>The example applications and mech'
    "anical replay are available here. The published repository's isol"
    "ated Computer Use adapter has its own setup, permissions and limi"
    "ts. A broad hybrid code-and-browser executor and real-user outcom"
    "es are separate qualification tasks, not enabled by downloading t"
    'his kit.</p><a href="https://github.com/MontrealAI/AGI-Alpha-Agen'
    't-v0/blob/main/docs/agent/SUCCESSOR_COMPUTER_USE.md">Current Comp'
    "uter Use guide ↗</a></section></main><footer><p>Useful work. Reco"
    'vered. Reused.</p><a href="https://github.com/MontrealAI/AGI-Alph'
    'a-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md">Project notice</'
    'a> · <a href="LICENSE">License</a> · <a href="SHA256SUMS">Checksu'
    "ms</a></footer>"
)
JS = (
    "(()=>{'use strict';\nconst root=document.documentElement,language="
    "document.getElementById('language'),size=document.getElementById("
    "'size');\nconst nodes=[...document.querySelectorAll('[data-fr]')],"
    "saved=nodes.map(n=>n.innerHTML),params=new URLSearchParams(locati"
    "on.search);\nlet fr=params.get('lang')==='fr';root.classList.toggl"
    "e('large',params.get('text')==='large');\nfunction remember(){try{"
    "const url=new URL(location.href);fr?url.searchParams.set('lang','"
    "fr'):url.searchParams.delete('lang');root.classList.contains('lar"
    "ge')?url.searchParams.set('text','large'):url.searchParams.delete"
    "('text');history.replaceState(null,'',url)}catch(_){} }\nfunction "
    "render(){root.lang=fr?'fr':'en';nodes.forEach((n,i)=>{n.innerHTML"
    "=fr?n.dataset.fr:saved[i]});language.textContent=fr?'English':'Fr"
    "ançais';language.lang=fr?'en':'fr';language.setAttribute('aria-la"
    "bel',fr?'Read in English':'Lire en français');size.textContent=fr"
    "?'Texte plus grand':'Larger text';size.setAttribute('aria-pressed"
    "',String(root.classList.contains('large')));document.querySelecto"
    "r('nav').setAttribute('aria-label',fr?'Préférences de lecture':'R"
    "eading preferences');document.title=fr?'Essayez le travail | Kit "
    "de preuves AGI Alpha':'Try the work | AGI Alpha Evidence & Recove"
    "ry Kit'}\nlanguage.onclick=()=>{fr=!fr;render();remember()};size.o"
    "nclick=()=>{root.classList.toggle('large');render();remember()};r"
    "ender()})();"
)


def page(body: str, title: str, script: str = "") -> bytes:
    sh = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    ch = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
    return (
        f"<!doctype html>"
        f'<html lang="en">'
        f"<head>"
        f'<meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="description" content="Inspectable study artifacts, repeatable checks and a '
        f'prospective human pilot.">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src '
        f"'sha256-{ch}'; script-src 'sha256-{sh}'; img-src data:; connect-src 'none'; "
        f"base-uri 'none'; object-src 'none'; form-action 'none'\">"
        f"<title>{html.escape(title)}</title>"
        f"<style>{CSS}</style>"
        f"</head>"
        f"<body>{body}<script>{script}</script>"
        f"</body>"
        f"</html>"
    ).encode()


def build() -> None:
    for relative in [
        "02_Work_Products/Task_A/after",
        "02_Work_Products/Task_B/after",
        "02_Work_Products/Task_B/without-portability-fix",
        "03_Evidence/acceptance",
        "03_Evidence/downloads",
        "03_Evidence/screenshots",
        "03_Evidence/recovery",
        "08_Metrics",
    ]:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "04_Reproduce/build_sites.py")], check=True)
    text = (ROOT / "02_Work_Products/Task_B/after/index.html").read_text()
    old = re.search(r"async function hash\(v\)\{[^\n]+", text).group(0)
    new = (
        "async function hash(v){return [...new Uint8Array(await crypto.sub"
        "tle.digest('SHA-256',new TextEncoder().encode(canonical(v))))].ma"
        "p(x=>x.toString(16).padStart(2,'0')).join('');}"
    )
    text = text.replace(old, new, 1)
    code = re.search(r"<script>([\s\S]*?)</script>", text).group(1)
    new_hash = "sha256-" + base64.b64encode(hashlib.sha256(code.encode()).digest()).decode()
    text = re.sub(r"script-src 'sha256-[^']+'", "script-src '" + new_hash + "'", text, count=1)
    (ROOT / "02_Work_Products/Task_B/without-portability-fix/index.html").write_text(text)
    (ROOT / "START_HERE.html").write_bytes(page(BODY, "Try the work | AGI Alpha Evidence & Recovery Kit", JS))
    md = (ROOT / "PILOT_PROTOCOL.md").read_text()
    blocks = []
    for para in md.split("\n\n"):
        match = re.match(r"^(#{1,3}) (.*)", para)
        if match:
            level = len(match[1])
            blocks.append(f"<h{level}>{html.escape(match[2])}</h{level}>")
        else:
            blocks.append("<p>" + html.escape(para).replace("\n", "<br>") + "</p>")
    (ROOT / "PILOT_PROTOCOL.html").write_bytes(
        page(
            '<main><p><a href="START_HERE.html">← Back to the kit</a></p>' + "".join(blocks) + "</main>",
            "Real-user pilot | Not started",
        )
    )
    repo = ROOT.parents[2]
    report = repo / "docs/reports/computer-use-study"
    if report.is_dir():
        for name in [
            "report.html",
            "REPORT.md",
            "study.css",
            "study.js",
            "index.html",
            "results.json",
            "PUBLICATION.md",
        ]:
            target = ROOT / "01_Report" / name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(report / name, target)
    if (repo / "LICENSE").exists():
        shutil.copy2(repo / "LICENSE", ROOT / "LICENSE")
    from verify_and_replay import verify_original_sources

    verify_original_sources(ROOT)


def package(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = {
        p.relative_to(ROOT).as_posix(): p.read_bytes()
        for p in sorted(ROOT.rglob("*"))
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".zip"
        and not p.relative_to(ROOT)
        .as_posix()
        .startswith(("03_Evidence/", "08_Metrics/", "historical/", "05_Retained_Skill/", "06_Developer_Handoff/"))
        and p.name != "original_fixture_construction.py"
        and p.name != "SHA256SUMS"
    }
    sums = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n" for name, data in sorted(files.items()))
    (ROOT / "SHA256SUMS").write_text(sums)
    files["SHA256SUMS"] = sums.encode()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    print(
        json.dumps(
            {
                "path": str(output),
                "files": len(files),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "bytes": output.stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build()
    if args.output:
        package(args.output)
