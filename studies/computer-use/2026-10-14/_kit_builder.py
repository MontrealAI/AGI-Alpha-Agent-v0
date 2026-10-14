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
CSS = """:root{color-scheme:dark;font:18px/1.65 system-ui,-apple-system,sans-serif;background:#100b20;color:#f7f3ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% 0,#36214f,transparent 55%)}main,header,footer{width:min(1100px,calc(100% - 40px));margin:auto}header{padding:22px 0;display:flex;flex-wrap:wrap;justify-content:space-between;gap:16px;border-bottom:1px solid #614e76}a{color:#e1c6ff;text-underline-offset:4px;overflow-wrap:anywhere}.brand{text-decoration:none;font-weight:750;letter-spacing:.1em}.eyebrow{letter-spacing:.15em;font-size:.72rem;color:#d2b6ef}h1{font-size:clamp(2.2rem,6vw,4.2rem);line-height:1.1;letter-spacing:-.045em;margin:.35em 0}h2{font-size:1.6rem;line-height:1.3}h3{font-size:1.12rem;line-height:1.3}.hero{padding:60px 0 32px;max-width:900px}.lead{font-size:1.13rem;color:#e1d7ee}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.card,.notice{border:1px solid #65517c;border-radius:18px;padding:24px;background:#1c142e}.card{margin:12px 0}.badge{display:inline-block;padding:3px 10px;border-radius:20px;border:1px solid #9270af;font-size:.75rem}.pending{color:#ffe4ab}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.button,button{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:10px 18px;border:1px solid #9375ae;border-radius:10px;font:inherit;background:#2a1e3d;color:#f7f3ff;text-decoration:none;cursor:pointer}.primary{background:#e0c3ff;color:#160c23;font-weight:720}.muted{font-size:.9rem;color:#ccbedb}.steps{padding-left:24px}.steps li{margin:15px 0}section{padding:22px 0;scroll-margin-top:20px}pre{font:14px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #614e76;background:#0f0b1b;padding:18px;border-radius:12px}details{padding:16px 0}summary{cursor:pointer;min-height:44px}iframe{width:100%;height:780px;border:1px solid #66537a;border-radius:16px;background:white}footer{padding:32px 0;border-top:1px solid #614e76}.skip{position:absolute;left:10px;top:-200px}.skip:focus{top:8px;z-index:10;background:#100b20;padding:10px}:focus-visible{outline:3px solid #ffe4ab;outline-offset:4px}.large{font-size:22px}nav{display:flex;gap:10px;flex-wrap:wrap}[hidden]{display:none!important}.status-row{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}@media(max-width:680px){.grid{grid-template-columns:1fr}.hero{padding-top:34px}.card,.notice{padding:19px}iframe{height:760px}}@media print{html,body{color:#111!important;background:#fff!important;color-scheme:light}header,footer,nav,.actions,iframe,button{display:none!important}main{width:100%;max-width:none}h1{font-size:30pt}.card,.notice,pre{background:#fff!important;color:#111!important;border:1px solid #bbb;break-inside:avoid}.muted,.lead,.eyebrow,.pending,a{color:#222!important}.grid{display:block}section{padding:8px 0}@page{margin:16mm}}"""
BODY = """<a class="skip" href="#main">Skip to content / Aller au contenu</a><header><a class="brand" href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0">Ω AGI ALPHA</a><nav aria-label="Reading preferences"><button id="language">Français</button><button id="size" aria-pressed="false">Larger text</button></nav></header><main id="main"><section class="hero"><p class="eyebrow">EVIDENCE & RECOVERY KIT · 14 OCTOBER 2026</p><h1 data-fr="Essayez le travail.<br>Examinez les preuves.">Try the work.<br>Inspect the evidence.</h1><p class="lead" data-fr="Deux sites fonctionnels, leurs sources et les tests. Une récupération guidée. Un protocole pour mesurer l’utilité avec de vraies personnes — sans inventer les résultats.">Two working websites, their source and the checks behind them. Guided recovery. A protocol to measure usefulness with real people—without inventing results.</p><div class="actions"><a class="button primary" href="#examples" data-fr="Essayer les exemples ↓">Try the examples ↓</a><a class="button" href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/study-computer-use-2026-10-14-r1" data-fr="Téléchargements de l’étude ↗">Study downloads ↗</a><a class="button" href="#reproduce" data-fr="Reproduire les tests ↓">Reproduce the checks ↓</a></div><p class="muted" data-fr="Exemples synthétiques. Aucun compte, portefeuille, achat ni appel à un modèle. Ce kit n’est pas un service autonome en production.">Synthetic study examples. No account, wallet, purchase or model call. This kit is not a production autonomous service.</p></section><div class="status-row"><span class="badge" data-fr="01 · Livrables fonctionnels">01 · Working artifacts</span><span class="badge" data-fr="02 · Sources consultables">02 · Inspectable source</span><span class="badge" data-fr="03 · Outils de reproduction">03 · Replay tools</span><span class="badge pending" data-fr="04 · Étude humaine : NON COMMENCÉE">04 · Human evidence: NOT STARTED</span></div><section id="examples"><h2 data-fr="Commencez par un résultat concret.">Start with something concrete.</h2><div class="grid"><article class="card"><span class="badge" data-fr="TÂCHE A · SYNTHÉTIQUE">TASK A · SYNTHETIC</span><h3>Atelier North</h3><p data-fr="Choisissez AI Foundations et 10 participants. L’estimation attendue est de 445,50 CAD après la remise de 10 %.">Choose AI Foundations and 10 participants. The expected estimate is CAD 445.50 after the 10% discount.</p><div class="actions"><a class="button primary" href="02_Work_Products/Task_A/after/index.html" data-fr="Ouvrir le site A">Open website A</a><a href="02_Work_Products/Task_A/OWNER_BRIEF.txt" data-fr="Voir la demande">Inspect the brief</a></div></article><article class="card"><span class="badge" data-fr="TÂCHE B · NOUVELLES EXIGENCES">TASK B · NEW REQUIREMENTS</span><h3>Studio Horizon</h3><p data-fr="Un catalogue différent : choisissez l’offre Design et 8 participants. Résultat attendu : 433,50 CAD. Les offres gratuites et complètes ont leurs propres règles.">A different catalogue: choose the Design offering and 8 participants. Expected result: CAD 433.50. Free and sold-out offers have their own rules.</p><div class="actions"><a class="button primary" href="02_Work_Products/Task_B/after/index.html" data-fr="Ouvrir le site B">Open website B</a><a href="02_Work_Products/Task_B/OWNER_BRIEF.txt" data-fr="Voir la demande">Inspect the brief</a></div></article></div><p class="muted" data-fr="Ces deux livrables ont été produits pendant l’étude. Les ouvrir ne lance pas AGI Alpha pour générer un nouveau site. Aucun atelier réel n’est vendu.">These deliverables were produced during the study. Opening them does not run AGI Alpha to generate a new website. No real workshop is being sold.</p></section><section id="recover"><h2 data-fr="Sauvegardez. Fermez. Retrouvez le travail.">Save it. Close it. Bring it back.</h2><ol class="steps"><li data-fr="Ouvrez le site A, choisissez l’offre et le nombre de places, puis calculez.">Open website A, select the offer and number of places, then calculate.</li><li data-fr="Examinez l’estimation, cochez la révision et téléchargez le résultat.">Inspect the estimate, check the review box and download the result.</li><li data-fr="Enregistrez aussi le brouillon de récupération. Gardez le fichier JSON dans un dossier que vous retrouverez.">Also save the recovery draft. Keep its JSON file somewhere you can find.</li><li data-fr="Fermez l’exemple. Rouvrez-le et utilisez le contrôle de restauration pour choisir le brouillon sauvegardé.">Close the example. Reopen it and use the restore control to select your saved draft.</li><li data-fr="Recalculez et révisez à nouveau. La révision précédente ne doit pas être héritée.">Calculate and review again. Previous approval must not carry over.</li><li data-fr="Essayez maintenant le site B. Ses prix, capacités et permissions ne viennent pas du site A.">Now try website B. Its prices, capacities and permissions do not come from website A.</li></ol><div class="notice"><strong data-fr="Le fichier de travail n’est pas une autorisation.">A saved work file is not permission.</strong><p data-fr="Le travail non sauvegardé peut être perdu. Une empreinte n’est ni une identité, ni un chiffrement. Les tests de récupération contrôlés ne prouvent pas la résistance à une panne électrique.">Unsaved work can be lost. A hash is neither identity nor encryption. Controlled recovery tests do not establish power-loss resilience.</p></div></section><section id="inspect"><h2 data-fr="Ouvrez les pièces, pas seulement le résumé.">Open the evidence, not just the summary.</h2><div class="grid"><article class="card"><h3 data-fr="Sources et exigences">Source and requirements</h3><p><a href="SOURCE_PROVENANCE.json">SOURCE_PROVENANCE.json</a> · <a href="04_Reproduce/site_template.html" data-fr="Modèle partagé original">Original shared template</a> · <a href="README.md" data-fr="Guide du kit">Kit guide</a></p><p class="muted">The original source files are fingerprinted. The repaired apps are rebuilt byte-for-byte. Existing report: <a href="01_Report/report.html">read the detailed English report</a>.</p></article><article class="card"><h3 data-fr="Comparaisons, y compris les échecs">Comparisons, including failures</h3><p><a href="02_Work_Products/Task_A/before/index.html" data-fr="A : exemple volontairement défectueux">A: defective fixture</a> · <a href="02_Work_Products/Task_B/before/index.html" data-fr="B : exemple volontairement défectueux">B: defective fixture</a> · <a href="02_Work_Products/Task_B/without-portability-fix/index.html" data-fr="B : une correction retirée">B: one fix removed</a></p><p class="muted">These are intentionally failing comparisons, not recommended versions. One export defect caused six dependent failures. Do not interpret that as six independently repaired defects.</p></article></div></section><section id="reproduce"><h2 data-fr="Des résultats que l’on peut retester.">Results you can test again.</h2><p data-fr="Pour les personnes techniques : le kit conserve le moteur de tests original et ajoute une vérification qui refuse les résultats manquants ou différents. Les tests s’exécutent dans un nouveau dossier.">For technical readers: the kit preserves the original harness and adds a checker that rejects missing or different outcomes. Tests run in a new directory.</p><pre>python verify_and_replay.py --verify-only
python verify_and_replay.py --output /absolute/path/to/new-replay</pre><p>Python 3.11–3.13 and reviewed Chromium/Playwright are required. <a href="README.md">Installation and limitations</a>. Expected mechanical results: A 31/31; B 35/35; one-fix removal 29/35; recovery 19/19; owner controls 14 versus 11. A replay tests existing code; it does not generate a new AI solution or measure human time.</p><p class="muted">Fresh CI evidence is a separate download on the study release. Historical results stay historical. This source kit is not the original 98-file Office/PDF experiment archive.</p></section><section id="people"><h2 data-fr="La prochaine preuve vient de vraies personnes.">The next evidence comes from real people.</h2><div class="notice"><span class="badge pending">NOT STARTED · 0 OBSERVED PARTICIPANTS</span><p data-fr="Aucun gain humain n’a encore été mesuré. Le protocole distingue l’utilisabilité des exemples et l’exécution réelle par AGI Alpha. Les résultats restent vides tant que les séances n’ont pas eu lieu.">No human benefit has yet been measured. The protocol separates usability of the examples from actual AGI Alpha execution. Results remain empty until sessions occur.</p><div class="actions"><a class="button" href="PILOT_PROTOCOL.html" data-fr="Lire le protocole">Read the protocol</a><a href="pilot/status.json" data-fr="Voir le statut">Inspect status</a><a href="pilot/session-template.csv" download data-fr="Modèle de mesure vierge">Blank observation template</a></div><p class="muted">Do not post personal details, workplace files, credentials or participant recordings in public issues. No compensation is promised. A public self-report is not an independently observed result.</p></div></section><section><h2 data-fr="Ce qui fonctionne aujourd’hui">What works today</h2><p>The example applications and mechanical replay are available here. The published repository's isolated Computer Use adapter has its own setup, permissions and limits. A broad hybrid code-and-browser executor and real-user outcomes are separate qualification tasks, not enabled by downloading this kit.</p><a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/agent/SUCCESSOR_COMPUTER_USE.md">Current Computer Use guide ↗</a></section></main><footer><p>Useful work. Recovered. Reused.</p><a href="https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md">Project notice</a> · <a href="LICENSE">License</a> · <a href="SHA256SUMS">Checksums</a></footer>"""
JS = """(()=>{'use strict';
const root=document.documentElement,language=document.getElementById('language'),size=document.getElementById('size');
const nodes=[...document.querySelectorAll('[data-fr]')],saved=nodes.map(n=>n.innerHTML),params=new URLSearchParams(location.search);
let fr=params.get('lang')==='fr';root.classList.toggle('large',params.get('text')==='large');
function remember(){try{const url=new URL(location.href);fr?url.searchParams.set('lang','fr'):url.searchParams.delete('lang');root.classList.contains('large')?url.searchParams.set('text','large'):url.searchParams.delete('text');history.replaceState(null,'',url)}catch(_){} }
function render(){root.lang=fr?'fr':'en';nodes.forEach((n,i)=>{n.innerHTML=fr?n.dataset.fr:saved[i]});language.textContent=fr?'English':'Français';language.lang=fr?'en':'fr';language.setAttribute('aria-label',fr?'Read in English':'Lire en français');size.textContent=fr?'Texte plus grand':'Larger text';size.setAttribute('aria-pressed',String(root.classList.contains('large')));document.querySelector('nav').setAttribute('aria-label',fr?'Préférences de lecture':'Reading preferences');document.title=fr?'Essayez le travail | Kit de preuves AGI Alpha':'Try the work | AGI Alpha Evidence & Recovery Kit'}
language.onclick=()=>{fr=!fr;render();remember()};size.onclick=()=>{root.classList.toggle('large');render();remember()};render()})();"""


def page(body: str, title: str, script: str = "") -> bytes:
    sh = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    ch = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Inspectable study artifacts, repeatable checks and a prospective human pilot."><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'sha256-{ch}\'; script-src \'sha256-{sh}\'; img-src data:; connect-src \'none\'; base-uri \'none\'; object-src \'none\'; form-action \'none\'"><title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}<script>{script}</script></body></html>'
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
    new = "async function hash(v){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(v))))].map(x=>x.toString(16).padStart(2,'0')).join('');}"
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
