// Shared data boundary. No imported code, object revivers or network fetches.
export const LIMITS = Object.freeze({ capsule: 4_000_000, input: 120_000, rows: 1000, candidates: 12, events: 100, historySegments: 10, output: 300_000 });
export function fail(ok, code, detail = '') {
  if (!ok) { const error = new Error(detail || code); error.code = code; throw error; }
}
export function keys(value, expected, code = 'FIELDS') {
  fail(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...expected].sort().join('|'), code);
}
export function text(value, max = 2000, empty = false) {
  fail(typeof value === 'string' && (empty || value.trim().length > 0) && value.length <= max && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u202a-\u202e\u2066-\u2069]/u.test(value) && !/[\uD800-\uDFFF]/u.test(value.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '')), 'TEXT');
  return value;
}
export const canonical = value => value === null || typeof value !== 'object' ? JSON.stringify(value) : Array.isArray(value) ? '[' + value.map(canonical).join(',') + ']' : '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
export async function sha256(value) {
  fail(globalThis.crypto?.subtle, 'CRYPTO_UNAVAILABLE');
  const data = new TextEncoder().encode(typeof value === 'string' ? value : canonical(value));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('');
}
export const isHash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

// JSON.parse accepts duplicate names. Signed/committed records must not.
export function parseStrict(raw, maximum = LIMITS.capsule) {
  fail(typeof raw === 'string' && new TextEncoder().encode(raw).length <= maximum, 'INPUT_SIZE');
  let at = 0, nodes = 0;
  const space = () => { while (/[\x20\t\r\n]/.test(raw[at] || '\0')) at++; };
  const string = () => {
    const start = at++;
    while (at < raw.length) {
      if (raw[at] === '\\') { at += 2; continue; }
      if (raw[at++] === '"') { let value; try { value = JSON.parse(raw.slice(start, at)); } catch { fail(false, 'JSON'); } text(value, maximum, true); return value; }
    }
    fail(false, 'JSON');
  };
  const read = depth => {
    fail(depth <= 24 && ++nodes <= 50000, 'INPUT_DEPTH'); space();
    if (raw[at] === '"') return string();
    if (raw[at] === '{') {
      at++; space(); const out = {}, seen = new Set();
      if (raw[at] === '}') { at++; return out; }
      for (;;) {
        space(); fail(raw[at] === '"', 'JSON'); const name = string();
        fail(!['__proto__', 'constructor', 'prototype'].includes(name), 'UNSAFE_KEY');
        fail(!seen.has(name), 'DUPLICATE_KEY'); seen.add(name); space(); fail(raw[at++] === ':', 'JSON'); out[name] = read(depth + 1); space();
        const end = raw[at++]; if (end === '}') return out; fail(end === ',', 'JSON');
      }
    }
    if (raw[at] === '[') {
      at++; space(); const out = []; if (raw[at] === ']') { at++; return out; }
      for (;;) { fail(out.length < 6000, 'INPUT_COUNT'); out.push(read(depth + 1)); space(); const end = raw[at++]; if (end === ']') return out; fail(end === ',', 'JSON'); }
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(raw.slice(at));
    fail(token, 'JSON'); at += token[0].length; const value = JSON.parse(token[0]); fail(typeof value !== 'number' || Number.isFinite(value), 'NUMBER'); return value;
  };
  const result = read(0); space(); fail(at === raw.length, 'JSON'); return result;
}

export function publicOnly(raw) {
  text(raw, LIMITS.capsule, true);
  fail(!/(?:-----BEGIN [A-Z ]*PRIVATE KEY|\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{16,}|\b(?:password|passwd|api[_-]?key|private[_-]?key|seed[_ -]?phrase|access[_-]?token)\s*[=:]\s*\S{6,}|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)/i.test(raw), 'PRIVATE_INPUT');
  fail(!/https?:\/\/[^\s"<>]*(?:[?&#](?:token|key|sig|signature|secret|password|x-amz-[^=]*|x-goog-[^=]*)=|(?:localhost|127\.0\.0\.1|169\.254\.169\.254))|https?:\/\/[^\s/]+:[^\s@]+@/i.test(raw), 'PRIVATE_INPUT');
  return raw;
}
export function safePath(name) {
  fail(typeof name === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,159}$/.test(name) && name.split('/').every(p => p && !p.startsWith('.')), 'PATH'); return name;
}
export function clone(value) { return parseStrict(canonical(value)); }
