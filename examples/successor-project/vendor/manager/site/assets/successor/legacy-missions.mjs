import { fail, keys, text, LIMITS, parseStrict, publicOnly, escapeHTML, canonical } from './safe.mjs';

export const ENGINE = 'successor-local/1';
export const EXAMPLE_DATA = 'id,category,value\na1,Solar,12.50\na2,Wind,8.25\na3,Solar,3.75\na2,Wind,8.25\na4,Hydro,6.10';
export const EXAMPLE_SITE = { title: 'A brighter neighbourhood', intro: 'A public guide to sharing ideas, learning together and making our neighbourhood more welcoming.', sections: [{ heading: 'Our idea', body: 'Small practical projects can make a visible difference. Start with one useful improvement.' }, { heading: 'How to take part', body: 'Choose a project, agree on a clear result and share what you learn.' }, { heading: 'What comes next', body: 'Review the results together and choose the next improvement.' }] };

export function csvRows(raw) {
  text(raw, LIMITS.input); const rows = []; let row = [], cell = '', quoted = false, closed = false;
  for (let i = 0; i <= raw.length; i++) {
    const c = raw[i];
    if (quoted) { if (c === '"' && raw[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') { quoted = false; closed = true; } else { fail(c !== undefined, 'CSV_QUOTE'); cell += c; } continue; }
    if (c === '"') { fail(!cell && !closed, 'CSV_QUOTE'); quoted = true; continue; }
    if (c === ',' || c === '\n' || c === '\r' || c === undefined) {
      row.push(cell); cell = ''; closed = false;
      if (c !== ',') { if (!(row.length === 1 && row[0] === '' && c === undefined)) rows.push(row); row = []; if (c === '\r' && raw[i + 1] === '\n') i++; }
      fail(rows.length <= LIMITS.rows + 1 && row.length <= 3, 'DATA_LIMIT');
    } else { fail(!closed, 'CSV_QUOTE'); cell += c; }
  }
  return rows;
}
export function decimal(value) {
  fail(typeof value === 'string' && /^-?(?:0|[1-9]\d{0,11})(?:\.\d{1,6})?$/.test(value), 'DATA_DECIMAL');
  const negative = value.startsWith('-'), [whole, fraction = ''] = value.replace(/^-/, '').split('.');
  return (BigInt(whole) * 1000000n + BigInt(fraction.padEnd(6, '0'))) * (negative ? -1n : 1n);
}
export function decimalText(value) {
  const sign = value < 0n ? '-' : '', absolute = value < 0n ? -value : value;
  const fraction = (absolute % 1000000n).toString().padStart(6, '0').replace(/0+$/, '');
  return sign + (absolute / 1000000n) + (fraction ? '.' + fraction : '');
}
export function dataRows(raw) {
  publicOnly(raw); text(raw, LIMITS.input);
  let rows;
  if (raw.trimStart().startsWith('[')) rows = parseStrict(raw, LIMITS.input);
  else { const all = csvRows(raw); fail(canonical(all[0]) === canonical(['id', 'category', 'value']), 'CSV_HEADER'); rows = all.slice(1).map(cells => { fail(cells.length === 3, 'CSV_COLUMNS'); return { id: cells[0], category: cells[1], value: cells[2] }; }); }
  fail(Array.isArray(rows) && rows.length > 0 && rows.length <= LIMITS.rows, 'DATA_LIMIT');
  for (const row of rows) { keys(row, ['id', 'category', 'value'], 'DATA_FIELDS'); text(row.id, 80); text(row.category, 80); decimal(row.value); }
  return rows;
}
export function validateMission(mission) {
  keys(mission, ['schema', 'principal', 'forbidden', 'recovery', 'kind', 'name', 'purpose', 'rights', 'input', 'language', 'outputs', 'success', 'tools', 'limits'], 'MISSION_FIELDS');
  fail(['analyst', 'website', 'custom'].includes(mission.kind), 'MISSION_KIND');
  text(mission.name, 100, true); text(mission.purpose, 1500); text(mission.rights, 1000); text(mission.input, LIMITS.input);
  fail(['en', 'fr'].includes(mission.language), 'LANGUAGE');
  for (const field of ['outputs', 'success', 'tools']) text(mission[field], 2000);
  fail(mission.schema === 'successor-mission/v1' && mission.principal === 'local-user-unverified', 'MISSION_IDENTITY');
  text(mission.forbidden, 2000); text(mission.recovery, 2000);
  keys(mission.limits, ['network', 'spendUSDC', 'maxRows', 'maxSeconds'], 'MISSION_LIMITS');
  fail(mission.limits.network === false && mission.limits.spendUSDC === '0' && mission.limits.maxRows === LIMITS.rows && mission.limits.maxSeconds === 10, 'AUTHORITY_NONE');
  publicOnly(canonical(mission));
  if (mission.kind === 'analyst') dataRows(mission.input);
  if (mission.kind === 'website') siteContent(mission.input);
  return mission;
}
export function defaultMission(kind = 'analyst', language = 'en') {
  const fr = language === 'fr';
  return { schema: 'successor-mission/v1', principal: 'local-user-unverified', forbidden: fr ? 'Données privées ou personnelles, scripts non vérifiés, transactions et fausses autorisations.' : 'Private/personal data, unreviewed code, transactions and unsupported authority claims.', recovery: fr ? 'Conserver les fichiers originaux; revenir à une version choisie; ne pas réactiver les permissions.' : 'Keep original files; roll back to a previously chosen version; never restore permissions.', kind, language, name: '', purpose: fr ? (kind === 'website' ? 'Créer un site clair pour mon projet public.' : kind === 'custom' ? 'Décrire le résultat utile que je souhaite.' : 'Résumer mes données publiques avec des totaux vérifiables.') : (kind === 'website' ? 'Create a clear website for my public project.' : kind === 'custom' ? 'Describe the useful result I want.' : 'Summarize public data with checkable totals.'), rights: fr ? 'Exemple synthétique fourni sous licence MIT.' : 'Supplied synthetic example, MIT licensed.', input: kind === 'analyst' ? EXAMPLE_DATA : kind === 'website' ? JSON.stringify(fr ? { title: 'Un quartier plus accueillant', intro: 'Un guide public pour partager des idées, apprendre ensemble et améliorer notre quartier.', sections: [{ heading: 'Notre idée', body: 'De petits projets pratiques peuvent changer les choses. Commencez par une amélioration utile.' }, { heading: 'Comment participer', body: 'Choisissez un projet, convenez d’un résultat précis et partagez ce que vous apprenez.' }, { heading: 'La suite', body: 'Examinez les résultats ensemble et choisissez la prochaine amélioration.' }] } : EXAMPLE_SITE, null, 2) : (fr ? 'Sources publiques et non personnelles à préciser.' : 'Describe public, nonpersonal sources.'), outputs: kind === 'website' ? 'index.html; editable source' : kind === 'analyst' ? 'report.html; result.json; method.json' : 'Describe required files', success: kind === 'website' ? 'Readable content, semantic headings, keyboard navigation, no network' : kind === 'analyst' ? 'Exact category totals; identify repeated IDs; preserve source records' : 'Describe measurable checks', tools: kind === 'custom' ? 'Unspecified; execution unavailable' : 'Reviewed local deterministic engine; no model/provider', limits: { network: false, spendUSDC: '0', maxRows: LIMITS.rows, maxSeconds: 10 } };
}
export function siteContent(raw) {
  publicOnly(raw); const content = parseStrict(raw, LIMITS.input); keys(content, ['title', 'intro', 'sections'], 'SITE_FIELDS'); text(content.title, 120); text(content.intro, 1500);
  fail(Array.isArray(content.sections) && content.sections.length > 0 && content.sections.length <= 12, 'SITE_SECTIONS');
  for (const section of content.sections) { keys(section, ['heading', 'body'], 'SITE_SECTION'); text(section.heading, 120); text(section.body, 3000); }
  return content;
}
export const STYLE = 'html{font:112.5%/1.65 system-ui,sans-serif;color:#231d36;background:#faf8ff}body{margin:0}main,header,footer,nav{max-width:64rem;margin:auto;padding:1.5rem}h1,h2{line-height:1.2;overflow-wrap:anywhere}h1{font-size:clamp(2rem,6vw,4rem)}a{color:#562aa8}a:focus-visible{outline:3px solid #251042;outline-offset:4px}nav{display:flex;flex-wrap:wrap;gap:1rem}nav a,.skip{padding:.7rem}section{margin:2rem 0}p,td,th{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:.6rem;border-bottom:1px solid #a89eb6}.skip{position:absolute;left:-9999px}.skip:focus{position:static}@media print{nav,.skip{display:none}html{font-size:12pt;background:white}}';
function htmlDocument(title, body, lang) { return '<!doctype html>\n<html lang="' + lang + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'"><title>' + escapeHTML(title) + '</title><style>' + STYLE + '</style></head><body>' + body + '</body></html>\n'; }
export function executeMission(mission, variant = 'baseline') {
  validateMission(mission); fail(mission.kind !== 'custom', 'RUNTIME_UNAVAILABLE'); fail(['baseline', 'improved'].includes(variant), 'VARIANT');
  const fr = mission.language === 'fr', files = [], gaps = [];
  if (mission.kind === 'analyst') {
    const rows = dataRows(mission.input), seen = new Map(), groups = new Map(); let duplicates = 0;
    for (const row of rows) {
      if (seen.has(row.id)) { duplicates++; if (variant === 'improved') { fail(seen.get(row.id) === canonical(row), 'DUPLICATE_CONFLICT'); continue; } }
      seen.set(row.id, canonical(row)); const value = decimal(row.value), group = groups.get(row.category) || { count: 0, total: 0n, min: value, max: value };
      group.count++; group.total += value; if (value < group.min) group.min = value; if (value > group.max) group.max = value; groups.set(row.category, group);
    }
    const result = { schema: 'successor-analysis/v1', policy: variant === 'improved' ? 'identical-id-once' : 'every-row', inputRows: rows.length, repeatedIds: duplicates, includedRows: [...groups.values()].reduce((n, g) => n + g.count, 0), groups: [...groups.keys()].sort().map(category => { const g = groups.get(category); return { category, count: g.count, total: decimalText(g.total), min: decimalText(g.min), max: decimalText(g.max) }; }) };
    if (duplicates && variant === 'baseline') gaps.push('repeated-ids');
    const title = mission.name || (fr ? 'Rapport de données publiques' : 'Public data report');
    const body = '<header><h1>' + escapeHTML(title) + '</h1><p>' + escapeHTML(mission.purpose) + '</p></header><main><p>' + (fr ? 'Politique de calcul : ' : 'Calculation policy: ') + escapeHTML(result.policy) + '. ' + result.inputRows + (fr ? ' lignes sources; ' : ' input rows; ') + result.includedRows + (fr ? ' lignes retenues.' : ' included rows.') + '</p><table><caption>' + (fr ? 'Totaux exacts par catégorie' : 'Exact category totals') + '</caption><thead><tr>' + (fr ? ['Catégorie', 'Nombre', 'Total', 'Minimum', 'Maximum'] : ['Category', 'Count', 'Total', 'Minimum', 'Maximum']).map(x => '<th scope="col">' + x + '</th>').join('') + '</tr></thead><tbody>' + result.groups.map(g => '<tr>' + [g.category, g.count, g.total, g.min, g.max].map(x => '<td>' + escapeHTML(x) + '</td>').join('') + '</tr>').join('') + '</tbody></table><p>' + (fr ? 'Source et droits : ' : 'Source and rights: ') + escapeHTML(mission.rights) + '</p></main>';
    files.push({ name: 'report.html', mediaType: 'text/html', content: htmlDocument(title, body, mission.language) }, { name: 'result.json', mediaType: 'application/json', content: JSON.stringify(result, null, 2) + '\n' });
  } else {
    const content = siteContent(mission.input), nav = variant === 'improved' ? '<nav aria-label="' + (fr ? 'Sections' : 'Sections') + '">' + content.sections.map((s, i) => '<a href="#section-' + i + '">' + escapeHTML(s.heading) + '</a>').join('') + '</nav>' : '';
    const body = '<a class="skip" href="#main">' + (fr ? 'Aller au contenu' : 'Skip to content') + '</a><header><h1>' + escapeHTML(content.title) + '</h1><p>' + escapeHTML(content.intro) + '</p></header>' + nav + '<main id="main">' + content.sections.map((s, i) => '<section id="section-' + i + '"><h2>' + escapeHTML(s.heading) + '</h2><p>' + escapeHTML(s.body) + '</p></section>').join('') + '</main><footer><p>' + escapeHTML(mission.rights) + '</p></footer>';
    files.push({ name: 'index.html', mediaType: 'text/html', content: htmlDocument(content.title, body, mission.language) });
    if (variant === 'baseline' && content.sections.length > 1) gaps.push('section-navigation');
  }
  files.push({ name: 'method.json', mediaType: 'application/json', content: JSON.stringify({ engine: ENGINE, kind: mission.kind, variant, numericPrecision: 'exact integer millionths', network: false, model: null }, null, 2) + '\n' });
  for (const f of files) fail(new TextEncoder().encode(f.content).length <= LIMITS.output, 'OUTPUT_SIZE');
  return { files, gaps };
}
