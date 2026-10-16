// Deliberately does not import the producer, its CSV parser or arithmetic.
import { parseStrict, fail, canonical, escapeHTML } from './safe.mjs';

// Approved, closed presentation snapshot. The checker does not import producer CSS.
const APPROVED_STYLE = 'html{font:112.5%/1.65 system-ui,sans-serif;color:#231d36;background:#faf8ff}body{margin:0}main,header,footer,nav{max-width:64rem;margin:auto;padding:1.5rem}h1,h2{line-height:1.2;overflow-wrap:anywhere}h1{font-size:clamp(2rem,6vw,4rem)}a{color:#562aa8}a:focus-visible{outline:3px solid #251042;outline-offset:4px}nav{display:flex;flex-wrap:wrap;gap:1rem}nav a,.skip{padding:.7rem}section{margin:2rem 0}p,td,th{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}.table-scroll{max-width:100%;overflow-x:auto;border:1px solid #a89eb6;border-radius:.5rem}.table-scroll:focus-visible{outline:3px solid #562aa8}.table-scroll table{min-width:32rem}.table-scroll th,.table-scroll td:not(:first-child){white-space:nowrap;overflow-wrap:normal;font-variant-numeric:tabular-nums}.table-scroll td:first-child{min-width:8rem;max-width:20rem}.report-scope{border-left:4px solid #562aa8;padding-left:1rem}th,td{text-align:left;padding:.6rem;border-bottom:1px solid #a89eb6}.skip{position:absolute;left:-9999px}.skip:focus{position:static}@media print{.table-scroll{overflow:visible;border:0}.table-scroll table{min-width:0}nav,.skip{display:none}html{font-size:12pt;background:white}}';
const APPROVED_CSP = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'">`;
function referenceRows(raw) {
  if (raw.trimStart().startsWith('[')) return parseStrict(raw);
  const rows = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').match(/(?:[^"\n]|"(?:[^"]|"")*")*(?:\n|$)/g).filter(Boolean).map(line => {
    const result = [], pattern = /(?:^|,)("(?:[^"]|"")*"|[^,\n]*)/g;
    for (const match of line.replace(/\n$/, '').matchAll(pattern)) result.push(match[1].startsWith('"') ? match[1].slice(1, -1).replace(/""/g, '"') : match[1]);
    return result;
  });
  fail(rows.shift()?.join(',') === 'id,category,value', 'CHECKER_HEADER');
  return rows.map(([id, category, value]) => ({ id, category, value }));
}
const units = value => { const digits = value.replace('-', '').split('.'); return BigInt(digits[0] + (digits[1] || '').padEnd(6, '0')) * (value[0] === '-' ? -1n : 1n); };
function formatted(number) {
  const negative = number < 0n, digits = (negative ? -number : number).toString().padStart(7, '0');
  return (negative ? '-' : '') + (digits.slice(0, -6) + '.' + digits.slice(-6)).replace(/0+$/, '').replace(/\.$/, '');
}
export function referenceAnalysis(raw, unique) {
  const original = referenceRows(raw), byId = new Map();
  for (const row of original) {
    if (unique && byId.has(row.id)) fail(canonical(byId.get(row.id)) === canonical(row), 'DUPLICATE_CONFLICT');
    byId.set(row.id, row);
  }
  const included = unique ? [...byId.values()] : original;
  const groups = [...new Set(included.map(r => r.category))].sort().map(category => {
    const values = included.filter(r => r.category === category).map(r => units(r.value)).sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
    return { category, count: values.length, total: formatted(values.reduce((sum, v) => sum + v, 0n)), min: formatted(values[0]), max: formatted(values.at(-1)) };
  });
  return { schema: 'successor-analysis/v1', policy: unique ? 'identical-id-once' : 'every-row', inputRows: original.length, repeatedIds: original.length - byId.size, includedRows: included.length, groups };
}

function closedMarkup(html, mission) {
  const permitted = new Set(['<html lang="'+mission.language+'">','<head>','<title>','<style>','<body>','<header>','<footer>','<main>','<main id="main">','<p>','<h1>','<h2>','<table>','<thead>','<tbody>','<tr>','<td>','<th scope="col">','<caption id="report-caption">','<p class="report-scope">','<p id="table-help">','<div class="table-scroll" role="region" aria-labelledby="report-caption" aria-describedby="table-help" tabindex="0">','<meta charset="utf-8">','<meta name="viewport" content="width=device-width,initial-scale=1">']);
  const parents = {html:[null],head:['html'],body:['html'],meta:['head'],title:['head'],style:['head'],header:['body'],footer:['body'],main:['body'],nav:['body'],a:['body','nav'],section:['main'],h1:['header'],h2:['section'],p:['header','main','section','footer'],div:['main'],table:['div'],caption:['table'],thead:['table'],tbody:['table'],tr:['thead','tbody'],th:['tr'],td:['tr']};
  const stack=[], counts=new Map(), headChildren=[], metadata=new Set();
  const tokens=html.match(/<[^>]*>|[^<]+/g)||[];
  if(tokens.join('')!==html || tokens[0]!=='<!doctype html>')return false;
  for(const token of tokens.slice(1)) {
    if(!token.startsWith('<')) {if(!/^[\t\n\f\r ]*$/.test(token) && !['title','style','h1','h2','p','a','caption','th','td'].includes(stack.at(-1)))return false;continue;}
    const closing=token.match(/^<\/([a-z][a-z0-9]*)>$/);
    if(closing){if(stack.pop()!==closing[1])return false;continue;}
    const opening=token.match(/^<([a-z][a-z0-9]*)([^>]*)>$/);
    if(!opening)return false;
    const tag=opening[1], parent=stack.at(-1)||null;
    const allowed=permitted.has(token) || (tag==='meta' && token===APPROVED_CSP) || (mission.kind==='website' && (token==='<nav aria-label="Sections">' || token==='<a class="skip" href="#main">' || /^<(?:a href="#section-\d+"|section id="section-\d+")>$/.test(token)));
    if(!allowed || !parents[tag]?.includes(parent))return false;
    if(tag==='body' && counts.get('head')!==1)return false;
    if(tag==='meta'){if(metadata.has(token))return false;metadata.add(token);}
    counts.set(tag,(counts.get(tag)||0)+1);
    if(parent==='head')headChildren.push(tag);
    if(tag!=='meta')stack.push(tag);
  }
  return stack.length===0 && ['html','head','body','main','header','title','style'].every(tag=>counts.get(tag)===1) && ['nav','footer'].every(tag=>(counts.get(tag)||0)<=1) && canonical(headChildren)===canonical(['meta','meta','meta','title','style']);
}

export function checkArtifacts(mission, variant, files) {
  const checks = [], check = (id, passed) => checks.push({ id, passed: Boolean(passed) });
  try {
    const expected = mission.kind === 'analyst' ? ['method.json', 'report.html', 'result.json'] : ['index.html', 'method.json'];
    check('exact-files', canonical(files.map(f => f.name).sort()) === canonical(expected));
    const html = files.find(f => f.name.endsWith('.html'))?.content || '';
    const tags = (html.match(/<[^>]*>/g) || []).join('');
    check('no-active-content', !/<(?:script|iframe|object|embed|form|base|link|img|audio|video)\b|\son[a-z]+\s*=|(?:href|src)\s*=\s*["'](?:https?:|data:|javascript:|\/\/)/i.test(tags) && !/@import|url\s*\(/i.test(html.match(/<style>([\s\S]*?)<\/style>/)?.[1] || ''));
    check('document-structure', /^<!doctype html>/i.test(html) && (html.match(/<h1\b/g) || []).length === 1 && html.includes('<html lang="' + mission.language + '">') && html.includes('name="viewport"') && html.includes('<main'));
    check('approved-presentation', (html.match(/<style>/g)||[]).length === 1 && html.match(/<style>([\s\S]*?)<\/style>/)?.[1] === APPROVED_STYLE && !/\s(?:style|aria-hidden)\s*=|\s(?:hidden|inert)(?:\s|>|=)/i.test(tags) && !html.includes('<'+'!--') && !/<template\b|<details\b/i.test(html));
    check('presentation-attributes', !/<(?:body|header|main|footer|p|h1|h2)\s[^>]*>/g.test(tags.replace(/<main id="main">|<p class="report-scope">|<p id="table-help">/g,'')) && !/<\/?(?:svg|template|canvas|marquee|dialog|details)\b/i.test(tags));
    check('closed-markup', closedMarkup(html, mission));
    check('network-policy', html.includes(APPROVED_CSP));
    const method = parseStrict(files.find(f => f.name === 'method.json')?.content || 'null');
    check('method-binding', canonical(method) === canonical({engine:'successor-local/2',kind:mission.kind,variant,numericPrecision:'exact integer millionths',network:false,model:null}));
    if (mission.kind === 'analyst') {
      const received = parseStrict(files.find(f => f.name === 'result.json')?.content || 'null');
      const expectedResult = referenceAnalysis(mission.input, variant === 'improved');
      check('exact-totals', canonical(received) === canonical(expectedResult));
      const tables = [...html.matchAll(/<table>([\s\S]*?)<\/table>/g)];
      const table = tables.length === 1 ? tables[0][1] : '';
      const headers = mission.language === 'fr' ? ['Catégorie','Nombre','Total','Minimum','Maximum'] : ['Category','Count','Total','Minimum','Maximum'];
      const head = '<thead><tr>' + headers.map(h => '<th scope="col">' + h + '</th>').join('') + '</tr></thead>';
      const caption = '<caption id="report-caption">' + (mission.language === 'fr' ? 'Totaux exacts par catégorie' : 'Exact category totals') + '</caption>';
      const rows = [...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].slice(1).map(row => [...row[1].matchAll(/<td>([^<]*)<\/td>/g)].map(cell=>cell[1]));
      const expectedRows = expectedResult.groups.map(g => [g.category,g.count,g.total,g.min,g.max].map(escapeHTML));
      const body = '<tbody>' + expectedRows.map(row=>'<tr>' + row.map(cell=>'<td>'+cell+'</td>').join('') + '</tr>').join('') + '</tbody>';
      check('report-values', canonical(rows) === canonical(expectedRows) && table === caption + head + body && (html.match(/<td>/g)||[]).length === expectedRows.length*5);
      check('table-headers', table.startsWith(caption + head));
      check('report-scope', html.includes('<p class="report-scope">') && html.includes(mission.language === 'fr' ? 'Acceptation métier et revue indépendante : non évaluées.' : 'Business acceptance and independent review: not evaluated.'));
    } else {
      const content = parseStrict(mission.input);
      check('source-content', html.includes('<h1>'+escapeHTML(content.title)+'</h1><p>'+escapeHTML(content.intro)+'</p>') && content.sections.every((section,i)=>html.includes('<section id="section-'+i+'"><h2>'+escapeHTML(section.heading)+'</h2><p>'+escapeHTML(section.body)+'</p></section>')));
      check('heading-hierarchy', (html.match(/<h2>/g) || []).length === content.sections.length);
      check('skip-link', html.includes('<a class="skip" href="#main">'+(mission.language==='fr'?'Aller au contenu':'Skip to content')+'</a>') && (html.match(/class="skip"/g)||[]).length===1 && html.includes('id="main"'));
      check('section-navigation', variant === 'baseline' || content.sections.every((_, i) => html.includes('href="#section-' + i + '"') && html.includes('id="section-' + i + '"')));
    }
  } catch { check('readable-output', false); }
  return { implementation: 'successor-checker/2', evidence: 'local-measurement', independentController: false, accessibilityCertification: false, assurance: {integrity:'separate-capsule-check',deterministicMethod:'local-check',businessCriteria:'not-evaluated',internalReview:'local-check',independentReview:'not-evaluated',rendering:'not-evaluated'}, passed: checks.length > 0 && checks.every(c => c.passed), checks };
}
