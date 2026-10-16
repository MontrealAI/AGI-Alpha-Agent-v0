// Deliberately does not import the producer, its CSV parser or arithmetic.
import { parseStrict, fail, canonical, escapeHTML } from './safe.mjs';

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
export function checkArtifacts(mission, variant, files) {
  const checks = [], check = (id, passed) => checks.push({ id, passed: Boolean(passed) });
  try {
    const expected = mission.kind === 'analyst' ? ['method.json', 'report.html', 'result.json'] : ['index.html', 'method.json'];
    check('exact-files', canonical(files.map(f => f.name).sort()) === canonical(expected));
    const html = files.find(f => f.name.endsWith('.html'))?.content || '';
    const tags = (html.match(/<[^>]*>/g) || []).join('');
    check('no-active-content', !/<(?:script|iframe|object|embed|form|base|link|img|audio|video)\b|\son[a-z]+\s*=|(?:href|src)\s*=\s*["'](?:https?:|data:|javascript:|\/\/)/i.test(tags) && !/@import|url\s*\(/i.test(html.match(/<style>([\s\S]*?)<\/style>/)?.[1] || ''));
    check('document-structure', /^<!doctype html>/i.test(html) && (html.match(/<h1\b/g) || []).length === 1 && html.includes('<html lang="' + mission.language + '">') && html.includes('name="viewport"') && html.includes('<main'));
    check('network-policy', html.includes("default-src 'none'") && html.includes("form-action 'none'"));
    const method = parseStrict(files.find(f => f.name === 'method.json')?.content || 'null');
    check('method-binding', method?.kind === mission.kind && method?.variant === variant && method?.network === false && method?.model === null);
    if (mission.kind === 'analyst') {
      const received = parseStrict(files.find(f => f.name === 'result.json')?.content || 'null');
      const expectedResult = referenceAnalysis(mission.input, variant === 'improved');
      check('exact-totals', canonical(received) === canonical(expectedResult));
      check('report-values', expectedResult.groups.every(g => Object.values(g).every(v => html.includes('<td>' + escapeHTML(v) + '</td>'))));
      check('table-headers', (html.match(/<th scope="col">/g) || []).length === 5 && html.includes('<caption>'));
    } else {
      const content = parseStrict(mission.input);
      check('source-content', [content.title, content.intro, ...content.sections.flatMap(s => [s.heading, s.body])].every(t => html.includes(escapeHTML(t))));
      check('heading-hierarchy', (html.match(/<h2>/g) || []).length === content.sections.length);
      check('skip-link', html.includes('href="#main"') && html.includes('id="main"'));
      check('section-navigation', variant === 'baseline' || content.sections.every((_, i) => html.includes('href="#section-' + i + '"') && html.includes('id="section-' + i + '"')));
    }
  } catch { check('readable-output', false); }
  return { implementation: 'successor-checker/1', evidence: 'local-measurement', independentController: false, accessibilityCertification: false, passed: checks.length > 0 && checks.every(c => c.passed), checks };
}
