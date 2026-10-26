/* SPDX-License-Identifier: Apache-2.0 */
'use strict';
// Execute the actual saved inline script. This is not a layout engine or browser.
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const path = require('node:path');
const assert = require('node:assert/strict');
const fixture = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const clean = value => JSON.parse(JSON.stringify(value));
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const checks = [];
const money = (cents, language) => cents === null ? (language === 'fr' ? 'Inconnu' : 'Unknown')
  : new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-US', {
    style: 'currency', currency: 'USD', currencyDisplay: language === 'fr' ? 'symbol' : 'narrowSymbol',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(cents / 100);

function environment({decompress = true, oldScript = null} = {}) {
  const downloads = [], urls = new Map();
  class Element {
    constructor(tag, attrs = {}) {
      this.tagName = tag.toUpperCase(); this.attrs = {...attrs}; this.children = [];
      this.dataset = Object.fromEntries(Object.entries(attrs).filter(([k]) => k.startsWith('data-'))
        .map(([k, v]) => [k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase()), v]));
      this.listeners = {}; this._value = attrs.value ?? ''; this.hidden = 'hidden' in attrs;
      this.className = attrs.class || ''; this.id = attrs.id || '';
      this.href = attrs.href || ''; this.download = attrs.download || '';
      this.disabled = 'disabled' in attrs;
      this.classList = {toggle: (name, force) => {
        const values = new Set(this.className.split(/\s+/).filter(Boolean));
        if (force ?? !values.has(name)) values.add(name); else values.delete(name);
        this.className = [...values].join(' ');
      }};
    }
    get options() { return this.children.filter(c => c instanceof Element && c.tagName === 'OPTION'); }
    get value() { return this._value; }
    set value(value) {
      const text = String(value);
      this._value = this.tagName === 'SELECT' && !this.options.some(option => option.value === text) ? '' : text;
    }
    get textContent() {
      return this._html !== undefined ? this._html.replace(/<[^>]*>/g, '')
        : this.children.map(c => typeof c === 'string' ? c : c.textContent).join('');
    }
    set textContent(value) { delete this._html; this.children = [String(value)]; }
    get innerHTML() { return this._html ?? this.textContent; }
    set innerHTML(value) { this._html = String(value); this.children = []; }
    replaceChildren(...nodes) {
      delete this._html; this.children = nodes; for (const node of nodes) node.parent = this;
      if (this.tagName === 'SELECT') this._value = this.options[0]?.value ?? '';
    }
    appendChild(node) { this.children.push(node); node.parent = this; return node; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); }
    setAttribute(name, value) { this.attrs[name] = String(value); }
    addEventListener(name, callback) { (this.listeners[name] ??= []).push(callback); }
    async emit(name) {
      const event = {target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }};
      await Promise.all((this.listeners[name] || []).map(fn => fn(event)));
    }
    async click() {
      if (this.tagName === 'A') downloads.push({name: this.download, blob: urls.get(this.href)});
      await this.emit('click');
    }
    scrollIntoView() {}
  }
  const nodes = fixture.nodes.map(node => new Element(node.tag, node.attrs));
  fixture.nodes.forEach((node, i) => {
    nodes[i].children = node.children.map(child => typeof child === 'number' ? nodes[child] : child);
    nodes[i].parent = node.parent === null ? null : nodes[node.parent];
    if (nodes[i].tagName === 'SELECT') {
      const options = nodes[i].options;
      nodes[i]._value = (options.find(option => 'selected' in option.attrs) ?? options[0])?.value ?? '';
    }
  });
  const byId = new Map(nodes.filter(n => n.id).map(n => [n.id, n]));
  const walk = node => [node, ...node.children.flatMap(c => typeof c === 'string' ? [] : walk(c))];
  const document = {
    getElementById: id => byId.get(id),
    documentElement: nodes.find(n => n.tagName === 'HTML'), body: nodes.find(n => n.tagName === 'BODY'),
    createElement: tag => new Element(tag),
    querySelectorAll: selector => {
      const match = selector.match(/^\[([^\]]+)\]$/); assert.ok(match, `Supported selector: ${selector}`);
      return walk(nodes[0]).filter(n => match[1] in n.attrs);
    },
  };
  const context = {
    document, window: {}, console, Blob, Response, Uint8Array, TextDecoder, atob,
    crypto: crypto.webcrypto,
    URL: {createObjectURL: blob => { const url = `blob:test-${urls.size}`; urls.set(url, blob); return url; },
      revokeObjectURL: () => {}},
    setTimeout: () => 0,
  };
  if (decompress) context.DecompressionStream = DecompressionStream;
  const source = oldScript ?? byId.get('demo-script').textContent;
  vm.runInNewContext(source, context, {filename: 'actual-demo-inline.js', timeout: 10000});
  return {context, document, $, api: context.window.AGIAlphaDemo, downloads,
    async select(id, value) { $(id).value = value; await $(id).emit('change'); },
    async input(id, value) { $(id).value = value; await $(id).emit('input'); }};
  function $(id) { const value = byId.get(id); assert.ok(value, `Element ${id}`); return value; }
}

async function run(name, action) {
  try { const details = await action(); checks.push({name, passed: true, details: details ?? null}); }
  catch (error) { checks.push({name, passed: false, error: error.stack}); }
}

(async () => {
  const app = environment();
  await run('All 80 saved cells match frozen summaries and work in both languages', async () => {
    const expected = new Map(fixture.expectedGroups.map(group => [group.groupId, group]));
    assert.equal(app.api.data.groups.length, 80);
    assert.equal(new Set(app.api.data.groups.map(g => g.id)).size, 80);
    let selections = 0;
    for (const language of ['en', 'fr']) {
      app.api.setLanguage(language);
      for (const group of app.api.data.groups) {
        const raw = expected.get(group.id); assert.ok(raw);
        assert.deepEqual(clean(group.difference), raw.causal.B_minus_A_projectInclusiveProfitCents);
        assert.deepEqual(clean(group.counts), raw.arms.B.counts);
        assert.deepEqual(clean(group.BMinusC), raw.causal.B_minus_C_projectInclusiveProfitCents);
        assert.equal(group.n, raw.completedSeeds);
        app.$('market-cost').value = group.cost; app.$('market-policy').value = group.policy;
        app.$('market-condition').value = group.condition; await app.$('market-cost').emit('change');
        assert.equal(app.api.selectedGroup().id, raw.groupId);
        assert.equal(app.$('market-mean').textContent, money(raw.causal.B_minus_A_projectInclusiveProfitCents.mean, language));
        assert.equal(app.$('market-funded').textContent, `${raw.arms.B.counts.secondInvestmentPaidFromGeneratedResources} / 24`);
        assert.equal(app.$('market-gates').textContent, `${raw.arms.B.counts.conditionalFinancialGatePasses} / 24`);
        assert.ok(app.$('condition-note').textContent.length > 20);
        if (group.cost === 'actual-unknown') {
          assert.equal(app.$('market-mean').textContent, language === 'fr' ? 'Inconnu' : 'Unknown');
          assert.equal(app.$('market-condition').options.filter(o => !o.disabled).length, 1);
          assert.ok(!app.$('market-chart').innerHTML.includes('<svg'));
          assert.equal(group.difference.n, 0); assert.equal(group.difference.missing, 24);
        } else {
          assert.equal(app.$('market-condition').options.filter(o => !o.disabled).length, 13);
          assert.ok(app.$('market-chart').innerHTML.includes('<svg'));
        }
        selections++;
      }
    }
    return {savedCells: 80, actualControlSelections: selections, languages: ['en', 'fr']};
  });
  await run('Eight ledger selectors preserve full original cash and cost histories', async () => {
    for (const expected of fixture.expectedRepresentatives) {
      app.$('ledger-cost').value = expected.cost_profile; app.$('ledger-policy').value = expected.policy;
      await app.$('ledger-policy').emit('change');
      const actual = app.api.selectedLedger();
      for (const [key, value] of Object.entries(expected)) assert.deepEqual(clean(actual[key]), value, key);
      assert.equal(app.$('ledger-uses').textContent, String(expected.B_second.actualAssetInvocationsInModel));
      assert.equal(app.$('ledger-delta').textContent, money(expected.causal.B_minus_A_projectInclusiveProfitCents, 'fr'));
      if (expected.cost_profile === 'actual-unknown') {
        assert.equal(app.$('ledger-oneoff').textContent, 'Inconnu');
        assert.equal(app.$('ledger-maintenance').textContent, 'Inconnu');
        assert.equal(app.$('ledger-delta').textContent, 'Inconnu');
      }
    }
    return {representatives: 8, cashBillsInvoicesBalances: 'A and B byte-derived data equal frozen histories'};
  });
  await run('Affordable low replay uses the second capability 15 times, loses $27.47, and is never qualified', async () => {
    app.api.setLanguage('en'); app.$('ledger-cost').value = 'low';
    app.$('ledger-policy').value = 'completed-research-replay'; await app.$('ledger-policy').emit('change');
    const r = app.api.selectedLedger(), s = r.B_second;
    assert.equal(s.actualAssetInvocationsInModel, 15); assert.equal(r.B.enterpriseAccepted, 34);
    assert.equal(s.declaredCompletePrototypeOneoffCostCents, 2597);
    assert.equal(s.maintenanceAccruedCents, 150); assert.equal(s.completeRealizedSecondCostsCents, 2747);
    assert.equal(r.causal.B_minus_A_projectInclusiveProfitCents, -2747);
    assert.equal(s.financiallyAdmitted, false); assert.equal(r.qualification.B.conditionalModeledFinancialGatePassed, false);
    assert.equal(app.$('ledger-uses').textContent, '15'); assert.equal(app.$('ledger-delta').textContent, '-$27.47');
    assert.ok(app.$('ledger-status').textContent.includes('15 modeled uses'));
    assert.ok(app.$('ledger-status').textContent.includes('no evidenced delivery saving'));
    app.$('ledger-cost').value = 'reference'; await app.$('ledger-cost').emit('change');
    assert.equal(app.api.selectedLedger().B_second.actualAssetInvocationsInModel, 0);
    assert.equal(app.$('ledger-uses').textContent, '0');
    assert.ok(app.$('ledger-status').textContent.includes('$82.74'));
    return {uses: 15, eventualAccepted: 34, paidOneoffCents: 2597, upkeepCents: 150, incrementalProfitCents: -2747};
  });
  await run('Language controls preserve choices, translate all dynamic option labels, and localize unknowns', async () => {
    app.$('market-cost').value = 'high'; app.$('market-policy').value = 'adaptive';
    app.$('market-condition').value = 'price-1600c'; await app.$('market-cost').emit('change');
    const selections = ['ledger-cost', 'ledger-policy', 'market-condition', 'market-cost', 'market-policy'];
    const previous = selections.map(id => app.$(id).value);
    const english = Object.fromEntries(['ledger-cost', 'ledger-policy', 'market-condition', 'artifact-select']
      .map(id => [id, app.$(id).options.map(o => o.textContent)]));
    const languageButtons = app.document.querySelectorAll('[data-lang]');
    await languageButtons.find(button => button.dataset.lang === 'fr').click();
    assert.equal(app.document.documentElement.lang, 'fr');
    assert.equal(app.document.documentElement.dataset.language, 'fr');
    assert.deepEqual(selections.map(id => app.$(id).value), previous);
    for (const [id, values] of Object.entries(english)) {
      const french = app.$(id).options.map(o => o.textContent);
      assert.equal(french.length, values.length);
      values.forEach((value, i) => {
        if (id === 'artifact-select' && value === french[i]) {
          // A literal source filename is a language-independent identifier.
          assert.equal(value, app.$(id).options[i].value, 'Untranslated prose is not allowed');
        } else assert.notEqual(value, french[i], `${id} option ${i}`);
      });
    }
    assert.ok(app.$('condition-note').textContent.startsWith('Prix fixe'));
    assert.ok(app.$('market-parity').textContent.includes('précision du cent'));
    assert.ok(app.$('market-chart').innerHTML.includes('Médiane'));
    assert.equal(languageButtons.find(button => button.dataset.lang === 'fr').attrs['aria-pressed'], 'true');
    assert.equal(languageButtons.find(button => button.dataset.lang === 'en').attrs['aria-pressed'], 'false');
    return {selectorChoicesPreserved: 5, allDynamicOptionsTranslated: true};
  });
  await run('Calculator rejects blank, invalid and fractional counts; explicit zero and reset are meaningful', async () => {
    app.api.setLanguage('en'); await app.$('calc-reset').click();
    assert.equal(app.$('calc-net').textContent, '-$110.10');
    assert.ok(app.$('calc-threshold').textContent.includes('$7.34'));
    assert.ok(app.$('calc-interpretation').textContent.includes('no finite number of uses'));
    for (const id of ['calc-cost', 'calc-uses', 'calc-wage', 'calc-upkeep', 'calc-minutes']) {
      await app.$('calc-reset').click(); await app.input(id, '');
      assert.equal(app.$('calc-net').textContent, 'Check inputs', `${id} blank must not mean zero`);
    }
    for (const [id, value] of [['calc-cost', '-1'], ['calc-uses', '1.5'], ['calc-uses', '1001'],
      ['calc-wage', '1001'], ['calc-minutes', '2.1'], ['calc-upkeep', 'Infinity']]) {
      await app.$('calc-reset').click(); await app.input(id, value);
      assert.equal(app.$('calc-net').textContent, 'Check inputs');
    }
    await app.$('calc-reset').click(); await app.input('calc-uses', '0');
    assert.ok(app.$('calc-threshold').textContent.includes('zero uses'));
    assert.equal(app.$('calc-net').textContent, '-$110.10');
    const frozen = JSON.stringify(app.api.data);
    for (const [id, value] of [['calc-cost', '1'], ['calc-uses', '15'], ['calc-wage', '65.38'],
      ['calc-upkeep', '0'], ['calc-minutes', '2']]) await app.input(id, value);
    assert.equal(app.$('calc-net').textContent, '$31.69');
    assert.ok(app.$('calc-interpretation').textContent.includes('does not validate savings, demand, available funds'));
    assert.equal(JSON.stringify(app.api.data), frozen, 'Exploration must not change any saved result');
    app.api.setLanguage('fr'); await app.input('calc-cost', '');
    assert.equal(app.$('calc-net').textContent, 'Vérifier les entrées');
    await app.$('calc-reset').click();
    assert.equal(app.$('calc-minutes').value, '0'); assert.equal(app.$('calc-uses').value, '15');
    assert.ok(app.$('calc-interpretation').textContent.includes('aucun nombre fini'));
    return {blankInputs: 5, invalidBoundaryInputs: 6, positiveScenarioStillExploratory: true, frozenDataUnchanged: true};
  });
  await run('Actual ledger, cash CSV and selected-group download buttons preserve selected data', async () => {
    app.$('ledger-cost').value = 'low'; app.$('ledger-policy').value = 'completed-research-replay';
    await app.$('ledger-cost').emit('change');
    await app.$('download-ledger').click();
    const ledgerDownload = app.downloads.at(-1); const ledger = JSON.parse(await ledgerDownload.blob.text());
    assert.deepEqual(ledger.ledger, clean(app.api.selectedLedger()));
    assert.equal(ledger.sourcePublicationDataSHA256, app.api.data.publicationDataSHA256);
    assert.equal(ledger.selection.cost, 'low'); assert.equal(ledger.selection.policy, 'completed-research-replay');
    assert.ok(ledger.basis.includes('actual customer receipts zero'));
    await app.$('download-cash').click();
    const cashDownload = app.downloads.at(-1), csv = await cashDownload.blob.text();
    assert.ok(cashDownload.name.endsWith('.csv'));
    const rows = csv.trimEnd().split('\r\n');
    assert.equal(rows.length, app.api.selectedLedger().A_cash.length + app.api.selectedLedger().B_cash.length + 1);
    assert.ok(rows[0].includes('amount_cents')); assert.ok(rows[1].startsWith('"A",'));
    assert.ok(rows.at(-1).startsWith('"B",')); assert.ok(rows.at(-1).includes('"93480"'));
    await app.$('download-group').click();
    const group = JSON.parse(await app.downloads.at(-1).blob.text());
    assert.deepEqual(group.group, clean(app.api.selectedGroup()));
    assert.ok(group.basis.includes('not market probabilities'));
    return {ledgerJson: ledgerDownload.name, cashCsv: cashDownload.name, csvRows: rows.length};
  });
  await run('Every embedded payload decodes byte-identically to its archived source file', async () => {
    assert.equal(Object.keys(app.api.files).length, Object.keys(fixture.expectedFileSources).length);
    let bytes = 0;
    for (const [name, expected] of Object.entries(fixture.expectedFileSources)) {
      const actual = app.api.files[name]; assert.equal(actual.sha256, expected.sha256);
      assert.equal(actual.bytes, expected.bytes);
      const native = Buffer.from(await app.api.decodeFile(name));
      const independent = zlib.gunzipSync(Buffer.from(actual.data, 'base64'));
      assert.equal(digest(native), expected.sha256); assert.equal(native.length, expected.bytes);
      assert.ok(native.equals(independent)); assert.ok(native.equals(fs.readFileSync(path.join(fixture.root, name))));
      assert.ok(actual.label.en); assert.ok(actual.label.fr); bytes += native.length;
    }
    const selected = 'publication/publication-data.json'; app.$('artifact-select').value = selected;
    await app.$('download-selected').click();
    assert.equal(digest(Buffer.from(await app.downloads.at(-1).blob.arrayBuffer())), fixture.expectedFileSources[selected].sha256);
    await app.$('inspect-selected').click(); assert.equal(app.$('inspector').hidden, false);
    assert.equal(digest(Buffer.from(app.$('inspector-content').textContent)), fixture.expectedFileSources[selected].sha256);
    assert.ok(app.$('download-status').textContent.startsWith('Fichier intégré téléchargé'));
    if (app.api.files['publication/paper.pdf']) {
      const button = app.document.querySelectorAll('[data-file-download]')
        .find(element => element.dataset.fileDownload === 'publication/paper.pdf');
      assert.ok(button, 'Embedded PDF has a real download button');
      const previousDownloads = app.downloads.length; await button.click();
      const deadline = Date.now() + 2000;
      while (app.downloads.length === previousDownloads && Date.now() < deadline) {
        await new Promise(resolve => setImmediate(resolve));
      }
      assert.equal(app.downloads.length, previousDownloads + 1, 'Asynchronous PDF button completes one download');
      const pdf = app.downloads.at(-1);
      assert.equal(pdf.name, 'AGI_ALPHA_Second_Investment_Paper.pdf');
      assert.equal(pdf.blob.type, 'application/pdf');
      assert.equal(digest(Buffer.from(await pdf.blob.arrayBuffer())), fixture.expectedFileSources['publication/paper.pdf'].sha256);
    }
    return {artifacts: Object.keys(fixture.expectedFileSources).length, uncompressedBytes: bytes,
      selectedDownloadAndInspectorChecked: selected};
  });
  await run('Missing browser decompression offers exact gzip and corruption refuses output', async () => {
    const fallback = environment({decompress: false}); fallback.api.setLanguage('fr');
    const selected = 'protocol/asset-B.json'; fallback.$('artifact-select').value = selected;
    await fallback.$('download-selected').click();
    const output = fallback.downloads.at(-1); assert.ok(output.name.endsWith('.gz'));
    assert.ok(Buffer.from(await output.blob.arrayBuffer()).equals(Buffer.from(fallback.api.files[selected].data, 'base64')));
    assert.ok(fallback.$('download-status').textContent.includes('décompressez'));
    const corrupt = environment(); corrupt.api.files[selected].sha256 = '0'.repeat(64);
    corrupt.$('artifact-select').value = selected; await corrupt.$('download-selected').click();
    assert.equal(corrupt.downloads.length, 0);
    assert.ok(corrupt.$('download-status').textContent.includes('validation failed'));
    return {noDecompressionFallback: 'exact .gz', badHash: 'download refused'};
  });
  await run('Original blank-to-zero defect has preserved execution evidence and repaired validation', async () => {
    const originalPath = path.join(fixture.root, 'review/demo-inline-source.js');
    const prior = JSON.parse(fs.readFileSync(path.join(fixture.root, 'review/demo-functional-before-pdf.json'), 'utf8'));
    const evidence = prior.javascript.checks.find(check => check.name.startsWith('Original blank-to-zero defect'));
    assert.equal(evidence.passed, true);
    assert.equal(evidence.details.originalScriptSHA256, digest(fs.readFileSync(originalPath)));
    assert.equal(evidence.details.originalBlankCostDisplay, '-$6.25');
    return {...evidence.details, preservedExecution: 'review/demo-functional-before-pdf.json',
      rerun: false, reason: 'Initial script expects original uncompressed app-data shape; final encoding deduplicates A.'};
  });
  const passed = checks.every(check => check.passed);
  process.stdout.write(JSON.stringify({passed, minimalDOM: true, browserLayoutVerified: false,
    htmlSHA256: fixture.htmlSHA256, checks}) + '\n');
  process.exitCode = passed ? 0 : 1;
})().catch(error => { process.stdout.write(JSON.stringify({passed: false, fatal: error.stack}) + '\n'); process.exitCode = 1; });
