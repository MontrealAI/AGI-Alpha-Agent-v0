# SPDX-License-Identifier: Apache-2.0
"""Render common EN/FR presentation packets from immutable confirmation records.

This post-evaluation companion does not execute a production arm or grant authority.
Its construction and execution are presentation research costs, not measured savings.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


STUDY = Path(__file__).resolve().parents[1]
ARMS = {
    "A": ("Existing strong workflow", "Méthode existante de référence"),
    "B": ("Retained AGI ALPHA capability", "Capacité AGI ALPHA conservée"),
    "C": ("Conventional builder", "Développement conventionnel"),
}
CSS = """
:root{color-scheme:light;--ink:#18213b;--muted:#58637a;--navy:#11172f;--purple:#6b39c5;
--light:#f4f1fc;--line:#e1e3ee;--red:#9f2845;--redlight:#fff2f5}
*{box-sizing:border-box}body{margin:0;background:#f8f9fd;color:var(--ink);
font:16px/1.58 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#54249f;text-underline-offset:.19em}a:hover{color:#29125e}a:focus-visible,button:focus-visible,
summary:focus-visible{outline:3px solid #cfa8ff;outline-offset:4px}button{font:inherit;cursor:pointer}
.wrap{max-width:1140px;margin:auto;padding:0 28px}.top{display:flex;align-items:center;justify-content:space-between;
gap:16px;padding-top:23px;padding-bottom:23px;flex-wrap:wrap}.brand{font-weight:800;letter-spacing:.12em;
text-decoration:none;color:var(--navy);font-size:.91rem}.brand b{color:var(--purple);font-size:1.35rem}
.controls{display:flex;gap:7px;flex-wrap:wrap}.controls button{border:1px solid var(--line);border-radius:8px;
padding:7px 12px;background:white;color:var(--ink);font-size:.82rem}.controls button[aria-pressed=true]
{background:var(--navy);color:white}.hero{color:#fff;background:radial-gradient(ellipse at 100% 0,#493072 0,
transparent 57%),var(--navy);padding:45px 0 43px;border-bottom:5px solid #a780e0}.eyebrow{color:#d0b6f5;
text-transform:uppercase;letter-spacing:.13em;font-weight:700;font-size:.75rem;margin:0 0 12px}
h1{font-size:clamp(2rem,4.3vw,3.1rem);line-height:1.12;letter-spacing:-.035em;margin:0 0 18px;font-weight:750}
.hero p{max-width:800px;margin:12px 0 0;color:#e1e3ef}.hero .badge{background:#fff1;color:#e9dfff;
border:1px solid #b197d255}.hero .badge.conflict{background:#ffecf1;color:#851b38;border:none}
main{padding-top:26px;padding-bottom:64px}.subnav{font-size:.87rem;margin:0 0 21px}.metrics{display:grid;
grid-template-columns:repeat(3,1fr);gap:16px;margin:0 0 25px}.metric{padding:21px;background:white;
border:1px solid var(--line);border-radius:12px}.metric strong{font-size:1.8rem;display:block;line-height:1.2}
.metric span{font-size:.85rem;color:var(--muted)}.panel{background:#fff;border:1px solid var(--line);
border-radius:14px;padding:26px;margin:0 0 24px;box-shadow:0 4px 16px #1a244004}h2{font-size:1.3rem;
letter-spacing:-.025em;line-height:1.3;margin:0 0 13px}h3{font-size:1rem;margin:18px 0 8px}p{margin:9px 0 14px}
.muted,.small{color:var(--muted)}.small{font-size:.83rem}.badge{display:inline-block;padding:4px 10px;
border-radius:30px;background:var(--light);font-weight:750;font-size:.74rem;letter-spacing:.035em;
color:#58328d}.badge.conflict{background:var(--redlight);color:var(--red)}.notice{border-left:4px solid #9167ce;
background:var(--light);padding:16px 18px;border-radius:0 9px 9px 0}.notice.conflict{background:var(--redlight);
border-color:var(--red)}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.88rem}
th{text-align:left;font-size:.76rem;text-transform:uppercase;letter-spacing:.045em;color:var(--muted);
border-bottom:2px solid var(--line);padding:11px 12px;vertical-align:bottom}td{border-bottom:1px solid var(--line);
padding:13px 12px;vertical-align:top}td:first-child,th:first-child{padding-left:0}tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}.arm{font-size:1.15rem;display:block}
.arm-name{font-size:.78rem;max-width:180px;display:block}.evidence-links{display:flex;gap:8px 16px;flex-wrap:wrap}
code{font: .86em/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;background:#f1f2f8;
border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}.hero code{background:#ffffff15;color:#fff}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f5fa;padding:14px;border-radius:8px;font-size:.8rem}
pre code{padding:0;background:none}.hash{word-break:break-all;font-size:.74rem}.grid{display:grid;
grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.kv{display:grid;grid-template-columns:180px minmax(0,1fr);
gap:8px 18px;font-size:.86rem}.kv dt{color:var(--muted)}.kv dd{margin:0;overflow-wrap:anywhere}
details{border-top:1px solid var(--line);padding-top:15px;margin-top:16px}summary{cursor:pointer;font-weight:650;
color:#553483}details details{border:0;padding:0;margin:5px 0}.changed{background:#f7f3ff}
.card{display:block;color:var(--ink);text-decoration:none;background:white;border:1px solid var(--line);
border-radius:12px;padding:24px;transition:border-color .15s}.card:hover{border-color:#8b63c7;color:var(--ink)}
.card h2{margin:12px 0 8px}.card .versions{font-size:.93rem;color:var(--muted);font-variant-numeric:tabular-nums}
.card .open{display:block;color:var(--purple);font-weight:650;margin-top:17px;font-size:.9rem}
footer{border-top:1px solid var(--line);padding:27px 0 38px;color:var(--muted);font-size:.8rem}
[lang=fr]{font-weight:inherit}html[data-language=en] [lang=fr],html[data-language=fr] [lang=en]{display:none}
html[data-language=both] .bilingual>span+span:before{content:" / ";color:#9c91ad}
html[data-language=both] p[lang=fr]{color:var(--muted)}html[data-language=both] .hero p[lang=fr]{color:#d5c9e8}
@media(max-width:720px){.wrap{padding-left:18px;padding-right:18px}.hero{padding:31px 0}.panel{padding:20px}
.grid{grid-template-columns:1fr}.metrics{gap:9px}.metric{padding:15px 12px}.metric strong{font-size:1.45rem}
.kv{grid-template-columns:1fr;gap:4px}.kv dd{margin-bottom:12px}th,td{padding:10px 8px}h1{overflow-wrap:anywhere}}
@media print{body{background:white;font-size:11px}.controls,.subnav{display:none}.hero{background:white;color:#18213b;
border-bottom:2px solid #6b39c5;padding:20px 0}.hero p,.hero p[lang=fr],.eyebrow{color:#4e3d62!important}
.hero code{color:#18213b;background:#eee}.panel,.metric{box-shadow:none;break-inside:avoid}.wrap{max-width:none}
.table-scroll{overflow:visible}.grid{display:block}.card{margin-bottom:12px}a{color:#492178}footer{padding:15px 0}}
"""
SCRIPT = """
(() => {
  const buttons = document.querySelectorAll('[data-set-language]');
  function setLanguage(value) {
    if (!['en', 'fr', 'both'].includes(value)) return;
    document.documentElement.dataset.language = value;
    document.documentElement.lang = value === 'fr' ? 'fr' : 'en';
    buttons.forEach(button => button.setAttribute('aria-pressed',
      String(button.dataset.setLanguage === value)));
    try { localStorage.setItem('agialpha-packet-language', value); } catch (_) {}
  }
  buttons.forEach(button => button.addEventListener('click', () => setLanguage(button.dataset.setLanguage)));
  document.querySelector('[data-print]').addEventListener('click', () => window.print());
  let language = 'both';
  try { language = localStorage.getItem('agialpha-packet-language') || language; } catch (_) {}
  setLanguage(language);
})();
"""


def esc(value: Any) -> str:
    """Escape an untrusted scalar for HTML text or a quoted attribute."""
    return html.escape(str(value), quote=True)


def bi(english: str, french: str) -> str:
    """Mark both language strings without requiring JavaScript to read them."""
    return f'<span class="bilingual"><span lang="en">{esc(english)}</span><span lang="fr">{esc(french)}</span></span>'


def paragraphs(english: str, french: str) -> str:
    """Render two language-tagged paragraphs."""
    return f'<p lang="en">{esc(english)}</p><p lang="fr">{esc(french)}</p>'


def sha(path: Path) -> str:
    """Hash exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path, expected: str | None = None) -> dict[str, Any]:
    """Read a record, rejecting an inconsistent declared identity."""
    if expected is not None and sha(path) != expected:
        raise ValueError(f"Recorded SHA-256 mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def inside_study(path: Path) -> Path:
    """Keep evidence paths within the portable study tree."""
    resolved = path.resolve()
    resolved.relative_to(STUDY)
    return resolved


def link(target: Path, output: Path, label: str) -> str:
    """Create a relative local evidence link."""
    return f'<a href="{esc(Path(os.path.relpath(target, output.parent)).as_posix())}">{label}</a>'


def document(title: str, heading: str, description: str, content: str, badge: str = "") -> str:
    """Apply the same presentation to every arm and mission."""
    return f'''<!doctype html>
<html lang="en" data-language="both"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Bilingual post-evaluation dependency decision packet with frozen evidence.">
<title>{esc(title)} · AGI ALPHA</title><style>{CSS}</style></head><body>
<header class="wrap top"><a class="brand" href="index.html">AGI ALPHA <b>∞</b></a>
<nav class="controls" aria-label="Language and print">
<button data-set-language="en" aria-pressed="false">English</button>
<button data-set-language="fr" aria-pressed="false">Français</button>
<button data-set-language="both" aria-pressed="true">EN + FR</button>
<button data-print>{bi("Print", "Imprimer")}</button></nav></header>
<section class="hero"><div class="wrap"><p class="eyebrow">THE SECOND INVESTMENT · EVIDENCE COMPANION</p>
<h1>{heading}</h1>{badge}{description}</div></section>
<main class="wrap">{content}</main>
<footer><div class="wrap">{paragraphs(
    "Common presentation produced after evaluation. No presentation saving is credited to A, B or C. "
    "This packet grants no operational authority and triggers no installation, release, payment or runtime action.",
    "Présentation commune produite après l’évaluation. Aucun gain de présentation n’est attribué à A, B ou C. "
    "Ce dossier n’accorde aucune autorité opérationnelle et ne déclenche aucune installation, publication, "
    "transaction ni action d’exécution.")}</div></footer><script>{SCRIPT}</script></body></html>'''


def load_packets(campaign_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load immutable evidence and enforce its campaign-to-certificate bindings."""
    campaign = read_json(campaign_path)
    if campaign.get("partial") or campaign.get("phase") != "fresh-confirmation":
        raise ValueError("The renderer requires a completed primary confirmation campaign")
    read_json(STUDY / "protocol/production-freeze.json", campaign["source_freeze_sha256"])
    read_json(STUDY / "protocol/confirmation-jobs.json", campaign["job_manifest_sha256"])
    baseline_path = STUDY / "inputs/development/job.json"
    baseline = read_json(baseline_path)
    baseline_lock = inside_study(baseline_path.parent / baseline["lock_path"])
    if sha(baseline_lock) != baseline["lock_sha256"]:
        raise ValueError("Baseline lock identity changed")
    baseline_versions = {row["name"]: row["version"] for row in baseline["wheels"]}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in campaign["rows"]:
        groups[row["family"]].append(row)
    packets = []
    for family, rows in groups.items():
        if re.fullmatch(r"[a-z0-9-]+", family) is None or sorted(row["arm"] for row in rows) != list(ARMS):
            raise ValueError("Expected one A/B/C result per safe mission family")
        job_path = STUDY / "inputs/confirmation" / family / "job.json"
        job = read_json(job_path, rows[0]["job_sha256"])
        source_path = job_path.with_name("source.json")
        source = read_json(source_path)
        lock_path = inside_study(job_path.parent / job["lock_path"])
        project_path = inside_study(job_path.parent / job["pyproject_path"])
        if sha(lock_path) != job["lock_sha256"] or sha(project_path) != job["pyproject_sha256"]:
            raise ValueError(f"Input bytes changed for {family}")
        inventory = sorted(job["wheels"], key=lambda row: row["name"])
        changes = [row for row in inventory if row["version"] != baseline_versions.get(row["name"])]
        if len(inventory) != 41 or len(changes) != 1 or changes[0]["name"] != family:
            raise ValueError(f"Expected exactly one substitution within the complete 41-pin lock: {family}")
        if source["version"] != changes[0]["version"] or source["baseline_version"] != baseline_versions[family]:
            raise ValueError(f"Selection provenance differs from the actual pinned proposal: {family}")
        arms = []
        for row in sorted(rows, key=lambda item: item["arm"]):
            result_path = inside_study(STUDY / row["result_path"])
            certificate_path = inside_study(STUDY / row["verification_path"])
            result = read_json(result_path, row["result_sha256"])
            cert = read_json(certificate_path, row["verification_sha256"])
            if any(record["job_sha256"] != sha(job_path) for record in (row, result, cert)):
                raise ValueError(f"Job binding changed: {family}/{row['arm']}")
            if cert["result_sha256"] != row["result_sha256"] or cert["verdict"] != row["decision"]:
                raise ValueError(f"Decision/result binding changed: {family}/{row['arm']}")
            if not row["accepted"] or not row["registered_job_binding"] or cert["status"] != "COMPLETE":
                raise ValueError("This completed-campaign presentation requires accepted, bound certificates")
            if cert["application_qualified"] or cert["authority"] or cert["financial_action"]:
                raise ValueError("Metadata presentation cannot carry operational authority")
            for file_key, hash_key in (("stdout", "stdout_sha256"), ("stderr", "stderr_sha256"),
                                       ("report", "pip_report_sha256")):
                if result["files"].get(file_key):
                    capture = inside_study(result_path.parent / result["files"][file_key])
                    if sha(capture) != cert["evidence"][hash_key]:
                        raise ValueError(f"Recorded pip evidence changed: {family}/{row['arm']}/{file_key}")
            selected = {wheel["name"]: (wheel["version"], wheel["sha256"]) for wheel in inventory}
            certified = {wheel["name"]: (wheel["version"], wheel["sha256"])
                         for wheel in cert["evidence"]["wheels"]}
            if selected != certified:
                raise ValueError("Certificate wheel inventory differs from the selected job")
            arms.append({"row": row, "result": result, "certificate": cert,
                         "result_path": result_path, "certificate_path": certificate_path})
        if len({arm["certificate"]["verdict"] for arm in arms}) != 1:
            raise ValueError(f"Arm disagreement requires an explicit presentation decision: {family}")
        packets.append({"family": family, "job": job, "source": source, "arms": arms,
                        "job_path": job_path, "source_path": source_path, "project_path": project_path,
                        "lock_path": lock_path, "baseline_path": baseline_lock, "baseline_versions": baseline_versions,
                        "inventory": inventory, "decision": arms[0]["certificate"]["verdict"]})
    if len(packets) != campaign["questions"]:
        raise ValueError("Campaign question count does not match packet count")
    return campaign, packets


def arm_table(packet: dict[str, Any], output: Path) -> str:
    """Show identical acceptance and measured timing fields for every arm."""
    body = []
    for arm in packet["arms"]:
        row, cert, result = arm["row"], arm["certificate"], arm["result"]
        files = [link(arm["certificate_path"], output, bi("Certificate", "Certificat")),
                 link(arm["result_path"], output, bi("Receipt", "Reçu"))]
        for key, labels in (("stdout", ("pip stdout", "pip stdout")),
                            ("stderr", ("pip stderr", "pip stderr")), ("report", ("pip report", "Rapport pip"))):
            if result["files"].get(key):
                target = inside_study(arm["result_path"].parent / result["files"][key])
                files.append(link(target, output, bi(*labels)))
        accepted = bi("Accepted", "Accepté") if row["accepted"] else bi("Not accepted", "Non accepté")
        body.append(f'''<tr><td><strong class="arm">{esc(row['arm'])}</strong>
<span class="arm-name">{bi(*ARMS[row['arm']])}</span></td>
<td><span class="badge {esc(cert['verdict'].lower())}">{esc(cert['verdict'])}</span><br>{accepted}
<br><span class="small">{esc(cert['status'])}</span></td>
<td class="num">{row['complete_service_wall_seconds']:.4f} s</td>
<td class="num">{row['inclusive_cpu_seconds']:.4f} s</td>
<td><div class="evidence-links">{' '.join(files)}</div></td></tr>''')
    return f'''<div class="table-scroll"><table><thead><tr>
<th>{bi("Branch", "Branche")}</th><th>{bi("Decision / acceptance", "Décision / acceptation")}</th>
<th>{bi("Complete service", "Service complet")}</th><th>{bi("Inclusive CPU", "CPU total")}</th>
<th>{bi("Recorded evidence", "Preuves enregistrées")}</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>'''


def inventory_table(packet: dict[str, Any], output: Path) -> str:
    """List every pinned package with its certificate metadata and wheel identity."""
    metadata = {row["name"]: row for row in packet["arms"][0]["certificate"]["evidence"]["wheels"]}
    wheelhouse = inside_study(packet["job_path"].parent / packet["job"]["wheelhouse_path"])
    rows = []
    for wheel in packet["inventory"]:
        name = wheel["name"]
        changed = ' class="changed"' if name == packet["family"] else ""
        row = metadata[name]
        filename = link(wheelhouse / wheel["filename"], output, esc(wheel["filename"]))
        rows.append(f'''<tr{changed}><td><strong>{esc(name)}</strong></td>
<td>{esc(packet['baseline_versions'][name])}</td><td>{esc(wheel['version'])}</td>
<td><code>{esc(row['requires_python'] or '—')}</code></td>
<td><details><summary>{bi("Wheel + hashes", "Wheel + empreintes")}</summary>
<p>{filename}</p><p class="small">Wheel SHA-256<br><code class="hash">{esc(wheel['sha256'])}</code></p>
<p class="small">METADATA SHA-256<br><code class="hash">{esc(row['metadata_sha256'])}</code></p>
</details></td></tr>''')
    return f'''<details><summary>{bi("Inspect the complete 41-package inventory", "Examiner les 41 paquets")}</summary>
<div class="table-scroll"><table><thead><tr><th>{bi("Package", "Paquet")}</th>
<th>{bi("Baseline", "Référence")}</th><th>{bi("Proposed pin", "Version proposée")}</th>
<th>Requires-Python</th><th>{bi("Byte identity", "Identité des octets")}</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></details>'''


def packet_page(packet: dict[str, Any], campaign_path: Path, output: Path) -> str:
    """Render one useful decision without changing the independent verdict."""
    family, source, cert = packet["family"], packet["source"], packet["arms"][0]["certificate"]
    conflict = packet["decision"] == "CONFLICT"
    action = (
        ("Keep the baseline pin; this proposal violates a project requirement.",
         "Conserver la version de référence : la proposition enfreint une exigence du projet.")
        if conflict else
        ("Metadata is consistent; application and runtime qualification are still required.",
         "Les métadonnées sont cohérentes ; la qualification applicative et à l’exécution reste nécessaire.")
    )
    summary = paragraphs(*action)
    heading = f"{esc(family)} <span style=\"color:#c3a3ef\">{esc(source['version'])}</span>"
    badge = f'<span class="badge {packet["decision"].lower()}">{esc(packet["decision"])}</span>'
    accepted_count = sum(arm["row"]["accepted"] for arm in packet["arms"])
    metric_labels = [("41", "Pinned packages", "Paquets à version fixe"),
                     ("1", "Proposed substitution", "Substitution proposée"),
                     (f"{accepted_count}/3", "Accepted packets", "Dossiers acceptés")]
    metrics = ''.join(f'<div class="metric"><strong>{n}</strong><span>{bi(en, fr)}</span></div>'
                      for n, en, fr in metric_labels)
    reasons = []
    for witness in cert["substantiated_witnesses"]:
        if witness["kind"] == "root_version":
            failed_edges = sum(edge["active"] and not edge["satisfied"] for edge in cert["dependency_edges"])
            reasons.append(f'''<div class="notice conflict">
<strong>{bi("Project requirement", "Exigence du projet")}</strong>
<p><code>{esc(witness['requirement'])}</code></p>
{paragraphs(f"The selected version {witness['actual']} does not satisfy this requirement. "
            f"The other 40 pins remain unchanged. The certificate reports {failed_edges} "
            "failed active transitive dependency edges.",
            f"La version retenue {witness['actual']} ne respecte pas cette exigence. "
            f"Les 40 autres versions restent inchangées. Le certificat signale {failed_edges} "
            "dépendances transitives actives insatisfaites.")}
<p>{link(packet['project_path'], output, bi("Read the original pyproject.toml", "Lire le pyproject.toml original"))}
 · {link(packet['arms'][0]['certificate_path'], output,
        bi("Read the exact witness", "Lire le constat exact"))}</p></div>''')
        else:
            reasons.append(f'<pre><code>{esc(json.dumps(witness, indent=2, ensure_ascii=False))}</code></pre>')
    if not reasons:
        active = sum(edge["active"] for edge in cert["dependency_edges"])
        reasons.append(f'''<div class="notice">{paragraphs(
            f"All 41 selected wheels, the active project roots, Python constraints, selected extras and "
            f"{active} active dependency edges are consistent in the recorded native environment. "
            "Continue with consumer installation, imports and application tests "
            "under the existing acceptance standard.",
            f"Les 41 wheels sélectionnés, les exigences du projet, les contraintes Python, les extras retenus et "
            f"les {active} dépendances actives sont cohérents dans l’environnement natif enregistré. "
            "Poursuivre avec l’installation consommateur, les imports et les tests applicatifs "
            "selon le critère d’acceptation existant.")}</div>''')
    env_rows = ''.join(f'<dt>{esc(key)}</dt><dd><code>{esc(value)}</code></dd>'
                       for key, value in packet["job"]["target_environment"].items())
    identities = [("Job", packet["job_path"]), ("Proposed lock / Verrou proposé", packet["lock_path"]),
                  ("Baseline lock / Verrou de référence", packet["baseline_path"]),
                  ("Project constraints / Contraintes du projet", packet["project_path"]),
                  ("Selection provenance / Provenance de sélection", packet["source_path"]),
                  ("Primary campaign / Campagne primaire", campaign_path),
                  ("Frozen protocol / Protocole figé", STUDY / "protocol/production-freeze.json")]
    identity_rows = ''.join(f'<dt>{link(path, output, esc(label))}</dt>'
                            f'<dd><code class="hash">{sha(path)}</code></dd>' for label, path in identities)
    certificate_rows = ''.join(
        f'<dt>{link(arm["certificate_path"], output, "Certificate / Certificat " + arm["row"]["arm"])}</dt>'
        f'<dd><code class="hash">{arm["row"]["verification_sha256"]}</code></dd>' for arm in packet["arms"])
    content = f'''<p class="subnav">
{link(output.with_name('index.html'), output, bi("← All six decisions", "← Les six décisions"))}</p>
<div class="metrics">{metrics}</div>
<section class="panel"><h2>{bi("The requested decision", "La décision demandée")}</h2>
<p>{bi("Baseline", "Référence")} <code>{esc(family)}=={esc(source['baseline_version'])}</code>
 → {bi("Proposed", "Proposition")} <code>{esc(family)}=={esc(source['version'])}</code></p>
{''.join(reasons)}
{paragraphs("The useful outcome is a complete, reviewable dependency decision for this exact 41-pin proposal. "
            "Acceptance means that the evidence packet meets the scoped metadata contract; "
            "a conflict is a valid accepted outcome.",
            "Le résultat utile est une décision complète et vérifiable sur cette proposition exacte de 41 versions. "
            "L’acceptation signifie que le dossier satisfait le contrat limité aux métadonnées ; "
            "un conflit constitue un résultat accepté valide.")}
</section><section class="panel"><h2>
{bi("Three branches, one acceptance standard", "Trois branches, un critère d’acceptation")}</h2>
{arm_table(packet, output)}
<div class="small">{paragraphs(
    "One recorded run per arm. Complete service time includes independent verification "
    "and, for B, native orchestration. CPU is measured resource use. Human and customer effort "
    "are unobserved, not zero. Earlier completion does not imply extra eventual output.",
    "Une exécution enregistrée par branche. Le temps de service complet comprend la vérification "
    "indépendante et, pour B, l’orchestration native. Le CPU mesure les ressources utilisées. "
    "L’effort humain et client est inconnu, et non nul. "
    "Finir plus tôt ne signifie pas produire davantage au total.")}</div>
</section><section class="panel"><h2>
{bi("Scope and remaining qualification", "Périmètre et qualification restante")}</h2>
{paragraphs("This decision covers the declared CPython 3.12 / Linux x86_64 environment, the chain project extra, "
            "the exact hashed lock and selected wheel metadata. It does not qualify application behavior, security, "
            "installation, runtime or release. No customer orders were created by this research question.",
            "Cette décision couvre l’environnement déclaré CPython 3.12 / Linux x86_64, l’extra chain du projet, "
            "le verrou exact identifié par empreinte et les métadonnées des wheels sélectionnés. "
            "Elle ne qualifie ni le comportement applicatif, ni la sécurité, l’installation, l’exécution "
            "ou une publication. Cette question de recherche n’a créé aucune commande client.")}
<p class="small"><code>application_qualified: false</code> · <code>authority: []</code> ·
<code>financial_action: false</code></p>
{inventory_table(packet, output)}</section>
<section class="panel"><h2>{bi("Inspect the exact evidence", "Examiner les preuves exactes")}</h2>
<details><summary>{bi("Target environment", "Environnement cible")}</summary><dl class="kv">{env_rows}</dl></details>
<details><summary>
{bi("Source and certificate SHA-256 identities", "Empreintes SHA-256 des sources et certificats")}</summary>
<dl class="kv">{identity_rows}{certificate_rows}</dl></details>
<p class="small">{link(STUDY / 'tools/render_deliveries.py', output,
                      bi("Common renderer source", "Source du rendu commun"))}</p>
</section>'''
    return document(f"{family} {source['version']} · {packet['decision']}", heading, summary, content, badge)


def index_page(packets: list[dict[str, Any]], campaign_path: Path, output: Path) -> str:
    """Render the reusable bilingual catalogue."""
    cards = []
    for packet in packets:
        source = packet["source"]
        decision = packet["decision"]
        action = (("Retain the baseline; project requirement violated.",
                   "Conserver la référence ; exigence du projet enfreinte.")
                  if decision == "CONFLICT" else
                  ("Metadata consistent; runtime qualification remains.",
                   "Métadonnées cohérentes ; qualification à l’exécution requise."))
        cards.append(f'''<a class="card" href="{esc(packet['family'])}.html">
<span class="badge {decision.lower()}">{decision}</span><h2>{esc(packet['family'])}</h2>
<p class="versions">{esc(source['baseline_version'])} → {esc(source['version'])}</p>
{paragraphs(*action)}<span class="open">{bi("Open decision packet →", "Ouvrir le dossier →")}</span></a>''')
    consistent = sum(packet["decision"] == "CONSISTENT" for packet in packets)
    conflicts = sum(packet["decision"] == "CONFLICT" for packet in packets)
    summary = paragraphs(
        "Six complete dependency decisions, with the same independent acceptance standard for A, B and C.",
        "Six décisions complètes sur les dépendances, avec le même critère d’acceptation indépendant pour A, B et C.")
    content = f'''<div class="metrics"><div class="metric"><strong>{len(packets)}</strong>
<span>{bi("Fresh research questions", "Questions de recherche nouvelles")}</span></div>
<div class="metric"><strong>{consistent}</strong>
<span>{bi("Metadata-consistent proposals", "Propositions aux métadonnées cohérentes")}</span></div>
<div class="metric"><strong>{conflicts}</strong>
<span>{bi("Substantiated conflicts", "Conflits établis")}</span></div></div>
<section class="panel"><h2>
{bi("Read the decision, inspect the evidence", "Lire la décision, examiner les preuves")}</h2>
{paragraphs("Each proposal changes one package in the 41-pin native lock. "
            "All three branches produced an accepted evidence "
            "packet for all six questions. These are six research inputs evaluated three ways, not 18 customer orders. "
            "The four metadata-consistent proposals still require consumer and runtime qualification.",
            "Chaque proposition modifie un paquet du verrou natif de 41 versions. "
            "Les trois branches ont produit un dossier accepté pour chacune des six questions. "
            "Il s’agit de six entrées de recherche évaluées selon trois méthodes, et non de 18 commandes clients. "
            "Les quatre propositions cohérentes exigent encore une qualification consommateur et à l’exécution.")}
<p>{link(campaign_path, output, bi("Primary campaign record", "Enregistrement de la campagne primaire"))} ·
{link(STUDY / 'protocol/production-freeze.json', output, bi("Frozen protocol", "Protocole figé"))}</p></section>
<div class="grid">{''.join(cards)}</div>
<section class="panel" style="margin-top:24px"><h2>{bi("How to use these packets", "Utilisation de ces dossiers")}</h2>
{paragraphs("For a conflict, keep the baseline while reviewing the exact project constraint. "
            "For a consistent result, use the exact hashes and environment to plan the next consumer acceptance check. "
            "The linked certificates, logs and "
            "full package inventories support independent review. This shared renderer was added after confirmation; "
            "its presentation work is not part of the frozen capability or a measured productivity gain.",
            "En cas de conflit, conserver la référence pendant l’examen de la contrainte exacte du projet. "
            "Pour un résultat cohérent, utiliser les empreintes et l’environnement exacts pour préparer la prochaine "
            "vérification d’acceptation consommateur. Les certificats, journaux et inventaires complets "
            "permettent un examen indépendant. Ce rendu commun a été ajouté après confirmation ; "
            "sa présentation ne fait pas partie de la capacité figée ni d’un gain de productivité mesuré.")}
</section>'''
    return document("Six dependency decisions",
                    bi("Dependency decision packets", "Dossiers de décision sur les dépendances"),
                    summary, content)


class LinkCollector(HTMLParser):
    """Collect only the local resource references emitted by this renderer."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.references.append(value)


def validate_links(paths: list[Path]) -> dict[str, Any]:
    """Ensure every generated link resolves in the actual portable tree."""
    checked = 0
    for path in paths:
        collector = LinkCollector()
        collector.feed(path.read_text(encoding="utf-8"))
        for value in collector.references:
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
                raise ValueError(f"Nonportable or external link in {path}: {value}")
            target = inside_study(path.parent / unquote(parsed.path))
            if not target.is_file():
                raise ValueError(f"Missing linked artifact: {path} -> {value}")
            checked += 1
    return {"all_local_links_resolve": True, "checked_link_occurrences": checked,
            "external_requests_required": False, "html_files": len(paths)}


def main() -> None:
    """Render and validate the companion without altering frozen inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=STUDY / "results/confirmation-01/campaign.json")
    parser.add_argument("--out", type=Path, default=STUDY / "deliverables/packets")
    args = parser.parse_args()
    started, cpu = time.perf_counter(), time.process_time()
    output_dir = inside_study(args.out)
    output_dir.relative_to(STUDY / "deliverables")
    campaign_path = inside_study(args.campaign)
    campaign, packets = load_packets(campaign_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for packet in packets:
        path = output_dir / f"{packet['family']}.html"
        path.write_text(packet_page(packet, campaign_path, path), encoding="utf-8")
        paths.append(path)
    index = output_dir / "index.html"
    index.write_text(index_page(packets, campaign_path, index), encoding="utf-8")
    paths.append(index)
    validation = validate_links(paths)
    manifest = {"schema": "agi-alpha-post-evaluation-presentation/v1", "presentation_only": True,
                "included_in_frozen_confirmation": False, "credited_productivity_saving": False,
                "customer_orders": campaign["new_customer_orders"], "renderer_sha256": sha(Path(__file__)),
                "campaign_sha256": sha(campaign_path), "validation": validation,
                "outputs": {path.name: sha(path) for path in paths},
                "elapsed_wall_seconds": time.perf_counter() - started,
                "process_cpu_seconds": time.process_time() - cpu,
                "model_billing_usd": None, "human_attention_minutes": None}
    (output_dir / "presentation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packets": len(packets), "index": str(index.relative_to(STUDY)), **validation}))


if __name__ == "__main__":
    main()
