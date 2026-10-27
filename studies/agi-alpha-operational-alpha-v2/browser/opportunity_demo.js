/* SPDX-License-Identifier: Apache-2.0 */
const O = D.opportunity;
let selectedMission = 'equilibrium';
let scienceArm = 'U';
Object.assign(EN, {
  edition: 'RESEARCH NOTEBOOK · ADDITIVE EDITION 2.1.0',
  heroKicker: 'Useful opportunity. Constructed instrument. Fresh qualification.',
  heroSummary: 'Follow a selected scientific-model reuse opportunity from documented source evidence to an executable qualification instrument, fresh recipient transfer and the exact economics of a conditional arrangement.'
});
Object.assign(FR, {
  edition: 'CARNET DE RECHERCHE · ÉDITION ADDITIVE 2.1.0',
  heroKicker: 'Occasion utile. Instrument construit. Nouvelle qualification.',
  heroSummary: 'Suivez une occasion choisie de réutilisation scientifique : preuves documentaires, instrument exécutable de qualification, transfert à un nouveau destinataire et économie exacte d’un arrangement conditionnel.'
});
const write = (id, value) => { document.getElementById(id).textContent = value; };
const missionById = id => O.packet?.missions?.find(m => m.id === id);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const missing = () => t('Unavailable', 'Indisponible');
const sourceRows = [
  ['S1', ['New mechanism-discrimination experiment', 'Nouvelle expérience de discrimination des mécanismes'], ['Known fitting question already answered; new observations and laboratory commitment absent.', 'Question d’ajustement déjà résolue; nouvelles observations et engagement de laboratoire absents.'], 'science'],
  ['S2', ['Laboratory protocol relocation', 'Transfert de protocole de laboratoire'], ['Close prior art; no physical oracle for the claimed assay transfer.', 'Travaux antérieurs proches; absence de référence physique pour valider le transfert d’essai.'], 'science'],
  ['ENG1', ['Geospatial decision qualification', 'Qualification de décision géospatiale'], ['Twelve actual metadata fixtures retained; strong GIS alternatives; paid gap unestablished.', 'Douze cas réels de métadonnées conservés; fortes alternatives SIG; besoin payant non établi.'], 'engineering'],
  ['ENG2', ['Protected PLC qualification', 'Qualification d’automates protégés'], ['Existing service precedent; no authorized executable vendor oracle.', 'Précédent de service existant; aucune référence exécutable autorisée du fournisseur.'], 'engineering'],
  ['M1', ['Shared dependency-repair qualification', 'Qualification partagée de correctifs de dépendances'], ['Strong existing security tools and funding; a distinct underserved gap not isolated.', 'Outils de sécurité et financements existants solides; besoin distinct mal desservi non isolé.'], 'market'],
  ['M2', ['Custom measurement qualification', 'Qualification de mesures spécialisées'], ['Missing laboratory evidence and overlap with earlier qualification infrastructure.', 'Preuves de laboratoire manquantes et chevauchement avec l’infrastructure antérieure.'], 'market']
];
const scienceMethods = {
  H: [
    ['Matched human scientific service', 'Prestation scientifique humaine comparable'],
    ['Same purpose, source review, acceptance, turnaround and customer effort. No matched S3 quote or human trial was collected. Use explicit hours/rates or buyer-value hypotheses until evidence exists; the arrangement’s arbitrary $300 is not a market price.', 'Même objectif, examen des sources, acceptation, délai et effort client. Aucun devis S3 comparable ni essai humain n’a été recueilli. Employer des heures et taux explicites ou des hypothèses de valeur client en attendant des preuves; les 300 $ arbitraires de l’arrangement ne sont pas un prix de marché.']
  ],
  U: [
    ['Ordinary use with a complete scientific brief and tools', 'Usage ordinaire avec cahier des charges scientifique complet et outils'],
    ['The same inherited hosted frontier model receives all source files, four purposes, packages and reasonable correction freedom. Conventional algebra and self-built helpers are allowed. This is one competent proxy, not a representative ordinary-user sample.', 'Le même modèle de pointe hérité reçoit tous les fichiers sources, quatre objectifs, les bibliothèques et une liberté raisonnable de correction. Algèbre conventionnelle et outils construits sont permis. Il s’agit d’un cas compétent, non d’un échantillon représentatif d’utilisateurs ordinaires.']
  ],
  E: [
    ['U plus the established, frozen expert workflow', 'U plus la méthode experte établie et figée'],
    ['Map the contract to explicit invariants, inspect evidence, execute checks and preserve limits. This generic contract workflow existed before S3; it is not a newly optimized scientific prompt or a model upgrade.', 'Associer le contrat à des invariants explicites, examiner les preuves, exécuter les vérifications et préserver les limites. Cette méthode générique précédait S3; ce n’est ni une nouvelle invite scientifique optimisée ni une mise à niveau du modèle.']
  ],
  E_plus: [
    ['E plus scientific-model-reuse 1.0.0', 'E plus scientific-model-reuse 1.0.0'],
    ['The fresh recipient receives the frozen executable capsule through the existing research relay. It uses inventory, stationary, dimension_bound, clock_witness and qualify unchanged. Generic code is transferred; scientific validity and execution authority must be earned for each mission.', 'Le nouveau destinataire reçoit la capsule exécutable figée via le relais de recherche existant. Il utilise inventory, stationary, dimension_bound, clock_witness et qualify sans modification. Le code générique est transmis; validité scientifique et autorité d’exécution restent à établir pour chaque mission.']
  ]
};
function renderDiscovery() {
  const body = document.querySelector('#discovery-table tbody');
  body.replaceChildren();
  for (const [id, name, reason, path] of sourceRows) {
    const tr = document.createElement('tr');
    const a = document.createElement('td'); a.textContent = id + ' · ' + name[lang === 'fr' ? 1 : 0];
    const b = document.createElement('td'); b.textContent = reason[lang === 'fr' ? 1 : 0];
    const c = document.createElement('td'); const link = document.createElement('a');
    link.href = '../opportunity/discovery/' + path + '/dossier.md'; link.textContent = t('Dossier', 'Dossier'); c.append(link);
    tr.append(a, b, c); body.append(tr);
  }
}
function addMissionRows(rows) {
  const host = document.getElementById('mission-evidence'); host.replaceChildren();
  for (const [label, value] of rows) {
    const row = document.createElement('div'); row.className = 'mission-evidence-row';
    const l = document.createElement('span'); l.textContent = label;
    const r = document.createElement('strong'); r.textContent = value;
    row.append(l, r); host.append(row);
  }
}
function renderMission() {
  const m = missionById(selectedMission);
  document.querySelectorAll('[data-mission]').forEach(button => {
    const active = button.dataset.mission === selectedMission;
    button.setAttribute('aria-selected', String(active)); button.tabIndex = active ? 0 : -1;
  });
  document.getElementById('mission-panel').setAttribute('aria-labelledby', 'mission-' + selectedMission);
  if (!m) { write('mission-title', missing()); return; }
  const idx = lang === 'fr' ? 1 : 0;
  const content = {
    equilibrium: {
      kind: ['Executed calculation · supplied fit', 'Calcul exécuté · ajustement fourni'],
      title: ['Preserve a valid stationary prediction', 'Préserver une prédiction stationnaire valide'],
      text: ['For the pinned H4 parameter point, calculate the stationary distribution and mean acetylation. The original measurements are treated as equilibrium observations. This answer remains conditional on that source model and fit.', 'Pour le point paramétrique H4 figé, calculer la distribution stationnaire et l’acétylation moyenne. Les mesures originales sont traitées comme observations d’équilibre. Cette réponse reste conditionnelle au modèle et à l’ajustement fournis.'],
      equation: 'Qp = 0,   Σpᵢ = 1',
      decision: ['Conditional model prediction supported', 'Prédiction conditionnelle du modèle soutenue'],
      obligation: ['No claim of new biology or complete parameter identifiability follows.', 'Aucune nouvelle biologie ou identifiabilité complète des paramètres n’en découle.'],
      label: ['Mean acetylation · supplied parameter point', 'Acétylation moyenne · paramètres fournis'],
      measure: fmt(m.mean_acetylation, 6),
      rows: [[t('Stationary states', 'États stationnaires'), Object.keys(m.stationary || {}).length], [t('Selected kinetic parameters', 'Paramètres cinétiques retenus'), m.dimension_check?.selected_kinetic_parameters], [t('Independent equilibrium coordinates, at most', 'Coordonnées d’équilibre indépendantes, au plus'), m.dimension_check?.independent_equilibrium_mean_coordinates_at_most]],
      boundary: ['The 33-parameter superset has a necessary dimension shortfall; that does not invalidate the selected eight-parameter fit.', 'L’ensemble étendu à 33 paramètres présente un déficit dimensionnel nécessaire; cela n’invalide pas l’ajustement retenu à huit paramètres.']
    },
    unsupported_clock: {
      kind: ['Executed witness · hypothetical clocks', 'Témoin exécuté · horloges hypothétiques'],
      title: ['Same equilibrium, different finite-time answer', 'Même équilibre, réponse temporelle différente'],
      text: ['Multiply all rates by a positive clock conversion. The stationary probabilities remain unchanged, yet the response at the requested time changes. Equilibrium evidence alone cannot choose the physical clock.', 'Multiplier tous les taux par une conversion d’horloge positive. Les probabilités stationnaires restent inchangées, mais la réponse au temps demandé change. Les preuves d’équilibre seules ne choisissent pas l’horloge physique.'],
      equation: 'Qp = 0 ⇒ (cQ)p = 0;   exp(cQt)x₀ = x(ct)',
      decision: ['Independent physical-clock calibration required', 'Calibration indépendante de l’horloge physique requise'],
      obligation: ['The original da_b = 1 normalization remains intact. Two alternative physical embeddings demonstrate the missing evidence.', 'La normalisation originale da_b = 1 reste intacte. Deux interprétations physiques alternatives démontrent la preuve manquante.'],
      label: ['Absolute x₀ac contrast at requested time 1.25', 'Contraste absolu x₀ac au temps demandé 1,25'],
      measure: m.state_at_request_time ? fmt(Math.abs(m.state_at_request_time[0].x_0ac - m.state_at_request_time[1].x_0ac), 6) : missing(),
      rows: (m.clock_scales || []).map((c, i) => [t('Clock conversion ', 'Conversion d’horloge ') + fmt(c, 1), fmt(m.state_at_request_time[i].x_0ac, 6)]).concat([[t('Maximum equilibrium difference', 'Écart maximal à l’équilibre'), m.equilibrium_max_abs_difference?.toExponential(2)]]),
      boundary: ['These clock conversions are hypothetical. The witness exposes an unsupported new physical-time interpretation, not an error in the published normalized model.', 'Ces conversions d’horloge sont hypothétiques. Le témoin révèle une interprétation temporelle physique nouvelle non étayée, non une erreur du modèle normalisé publié.']
    },
    calibrated_clock: {
      kind: ['Assumed calibration · conditional calculation', 'Calibration supposée · calcul conditionnel'],
      title: ['A concrete interval under a declared assumption', 'Un intervalle concret sous une hypothèse déclarée'],
      text: ['Supply a hypothetical scale between 0.4 and 1.6 normalized clock units per minute. The instrument converts the model relaxation time into a conditional physical interval. No experiment established this calibration.', 'Fournir une échelle hypothétique de 0,4 à 1,6 unités d’horloge normalisée par minute. L’instrument convertit le temps de relaxation du modèle en intervalle physique conditionnel. Aucune expérience n’a établi cette calibration.'],
      equation: 'τphysical = τmodel / c',
      decision: ['Conditional on HYPOTHETICAL-CLOCK-01', 'Conditionnel à HYPOTHETICAL-CLOCK-01'],
      obligation: ['Validate the calibration independently before using this as an empirically supported physical-time answer.', 'Valider la calibration indépendamment avant d’utiliser ce résultat comme réponse temporelle physique étayée empiriquement.'],
      label: ['Conditional relaxation interval · minutes', 'Intervalle conditionnel de relaxation · minutes'],
      measure: m.tau_physical_interval ? fmt(m.tau_physical_interval[0], 4) + ' – ' + fmt(m.tau_physical_interval[1], 4) : missing(),
      rows: [[t('Normalized relaxation time', 'Temps de relaxation normalisé'), fmt(m.tau_model, 6)], [t('Calibration observed?', 'Calibration observée ?'), t('No', 'Non')], [t('Evidence kind', 'Nature de la preuve'), t('Assumed', 'Supposée')]],
      boundary: ['This is a source-bound propagation of an assumption. It is not measured biological calibration or certified interval arithmetic.', 'Il s’agit d’une propagation d’hypothèse liée aux sources, sans calibration biologique mesurée ni arithmétique d’intervalles certifiée.']
    },
    new_mission: {
      kind: ['Fresh source · inheritance boundary', 'Nouvelle source · limite de transmission'],
      title: ['Boehm’s timed observations require fresh qualification', 'Les observations temporelles Boehm exigent une nouvelle qualification'],
      text: ['The source family, observation map and evidence identity change. Finite fixed times break the premise of the inherited equilibrium witness. The earlier H4 verdict cannot authorize this new purpose.', 'La famille de sources, la carte d’observation et l’identité des preuves changent. Les temps finis fixés rompent la prémisse du témoin d’équilibre hérité. Le verdict H4 antérieur ne peut autoriser ce nouvel usage.'],
      equation: t('new source + new request ⇒ new qualification', 'nouvelle source + nouvelle demande ⇒ nouvelle qualification'),
      decision: ['Withdraw inherited equilibrium qualification', 'Retirer la qualification d’équilibre héritée'],
      obligation: ['Use a solver and scientific analysis qualified for this finite-time model and the new requested prediction.', 'Employer un solveur et une analyse scientifique qualifiés pour ce modèle temporel et la nouvelle prédiction demandée.'],
      label: ['Actual finite-time measurement rows', 'Lignes réelles de mesures temporelles'],
      measure: String(m.measurement_rows ?? '—'),
      rows: [[t('Distinct observation times', 'Temps d’observation distincts'), m.observation_times?.length], [t('Observables', 'Observables'), m.observable_count], [t('Inherited witness applicable?', 'Témoin hérité applicable ?'), t('No', 'Non')]],
      boundary: ['Contrasts in the supplied simulations are reference predictions, not new observations. Timed data alone do not prove full identifiability or physical validity.', 'Les contrastes des simulations fournies sont des prédictions de référence, non de nouvelles observations. Les données temporelles seules ne prouvent ni identifiabilité complète ni validité physique.']
    }
  }[selectedMission];
  write('mission-kind', content.kind[idx]);
  document.getElementById('mission-kind').classList.toggle('assumed', selectedMission === 'calibrated_clock');
  write('mission-title', content.title[idx]); write('mission-text', content.text[idx]);
  write('mission-equation', content.equation); write('mission-decision', content.decision[idx]);
  write('mission-obligation', content.obligation[idx]); write('mission-measure-label', content.label[idx]);
  write('mission-measure', content.measure); addMissionRows(content.rows); write('mission-boundary', content.boundary[idx]);
  write('mission-json', JSON.stringify(m, null, 2));
}
function renderScience() {
  const text = scienceMethods[scienceArm], i = lang === 'fr' ? 1 : 0;
  write('science-method-title', text[0][i]); write('science-method-copy', text[1][i]);
  document.querySelectorAll('[data-science-arm]').forEach(b => {
    const active = b.dataset.scienceArm === scienceArm;
    b.setAttribute('aria-selected', String(active)); b.tabIndex = active ? 0 : -1;
  });
  document.getElementById('science-method').setAttribute('aria-labelledby', 'science-' + scienceArm);
  const host = document.getElementById('science-results'); host.replaceChildren();
  const c = O.confirmation;
  for (const arm of ['U', 'E', 'E_plus']) {
    const r = c?.arms?.[arm], card = document.createElement('article'); card.className = 'card';
    const a = document.createElement('div'); a.className = 'arm'; a.textContent = labelArm(arm);
    const count = document.createElement('div'); count.className = 'metric'; count.textContent = r ? r.passed_missions + ' / ' + r.total_missions : '—';
    const desc = document.createElement('p'); desc.textContent = t('mission requirements accepted under both request variants', 'exigences de mission acceptées sous les deux variantes');
    const timing = document.createElement('p'); timing.className = 'figure-label'; timing.textContent = r ? fmt(r.elapsed_seconds, 1) + t(' s · ', ' s · ') + r.operations + t(' logged operations', ' opérations consignées') : missing();
    card.append(a, count, desc, timing); host.append(card);
  }
  write('science-alpha', c ? fmt(c.operational_alpha_acceptance_percentage_points, 0) + ' pp' : '—');
  write('science-learned', c ? fmt(c.additional_learned_alpha_acceptance_percentage_points, 0) + ' pp' : '—');
  write('science-conventional', c ? c.conventional.passed + ' / ' + c.conventional.total : '—');
  const recipient = c?.recipient;
  write('science-receipt', recipient?.actual_received_bytes_equal ? t('Frozen capsule bytes are recovered unchanged, then executed by a separate recipient. No live ENS authentication occurred.', 'Les octets figés de la capsule sont récupérés sans changement, puis exécutés par un destinataire distinct. Aucune authentification ENS réelle n’a eu lieu.') : missing());
  write('capsule-hash', recipient?.actual_capsule_sha256 || missing());
  write('science-native', O.integration ? O.integration.passed + ' / ' + O.integration.total + t(' local controls pass', ' contrôles locaux réussis') : missing());
}
function renderCash() {
  const mode = document.getElementById('cash-mode').value;
  const delay = Number(document.getElementById('cash-delay').value);
  const record = O.timing?.cases?.find(c => c.mode === mode && c.payment_release_delay_days === delay);
  if (!record) { write('cash-required', missing()); return; }
  const r = record.result;
  write('cash-contribution', money(r.contribution_cents / 100));
  write('cash-required', money(r.required_opening_cash_cents / 100));
  write('cash-opening', money(r.opening_cash_cents / 100));
  write('cash-funding', r.opening_cash_cents >= r.required_opening_cash_cents ? t('This arbitrary opening balance funds every recorded prefix. Successful contribution remains $200.', 'Ce solde initial arbitraire finance chaque étape consignée. La contribution réussie reste de 200 $.') : t('The arbitrary $500 opening balance is insufficient: positive final contribution does not fund the earlier cash shortfall.', 'Le solde initial arbitraire de 500 $ est insuffisant : une contribution finale positive ne finance pas le déficit de trésorerie antérieur.'));
  drawCash(r);
  const s = O.selection_result?.selection;
  if (s) {
    const ex = s.expected_contribution_cents;
    write('arrangement-selected', t('P2 + P3 · coordinated commitments · refundable escrow · ', 'P2 + P3 · engagements coordonnés · séquestre remboursable · ') + money(s.plan.price_cents / 100) + t(' per mission.', ' par mission.'));
    write('arrangement-values', t('Weighted expected contribution ', 'Contribution attendue pondérée ') + money(ex.numerator / ex.denominator / 100) + t('; required opening cash ', '; trésorerie initiale requise ') + money(s.required_opening_cash_cents / 100) + t('. Actual business qualification remains unestablished.', '. Qualification commerciale réelle non établie.'));
  }
  const stress = O.stress || [], losses = stress.filter(x => x.result.contribution_cents < 0).length;
  write('stress-heading', losses + ' / ' + stress.length + t(' combinations lose money', ' combinaisons perdent de l’argent'));
  const grid = document.getElementById('stress-grid'); grid.replaceChildren();
  grid.setAttribute('aria-label', losses + t(' losses in ', ' pertes parmi ') + stress.length + t(' synthetic combinations; no cash cap exceeded.', ' combinaisons synthétiques; aucun dépassement du plafond de trésorerie.'));
  stress.forEach((r, i) => { const block = document.createElement('span'); const loss = r.result.contribution_cents < 0; block.className = loss ? 'loss' : ''; block.textContent = i + 1; block.title = t('Case ', 'Cas ') + (i + 1) + ': ' + money(r.result.contribution_cents / 100); grid.append(block); });
}
function drawCash(result) {
  const svg = document.getElementById('cash-chart'); svg.replaceChildren();
  const NS = 'http://www.w3.org/2000/svg';
  const add = (name, attrs = {}, content = '') => { const el = document.createElementNS(NS, name); Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v)); el.textContent = content; svg.append(el); return el; };
  add('title', {id: 'cash-chart-title'}, t('Available cash after each event', 'Trésorerie disponible après chaque événement'));
  add('desc', {id: 'cash-chart-desc'}, t('Exact recorded cash prefixes, less refundable liabilities and reserves, at the declared hypothetical opening capital.', 'Étapes exactes de trésorerie consignées, déduction faite du passif remboursable et des réserves, au capital initial hypothétique déclaré.'));
  const points = result.events.map(e => e.available_with_declared_opening_cents / 100);
  const compact = window.matchMedia('(max-width: 600px)').matches;
  const W = compact ? 420 : 900, H = 250, L = compact ? 52 : 64, R = 24, T = 24, B = 45;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const lo = Math.min(0, ...points) - 40, hi = Math.max(0, ...points) + 40;
  const x = i => L + i / Math.max(1, points.length - 1) * (W - L - R);
  const y = value => H - B - (value - lo) / (hi - lo) * (H - T - B);
  add('line', {class: 'axis', x1: L, y1: T, x2: L, y2: H - B});
  add('line', {class: 'axis', x1: L, y1: H - B, x2: W - R, y2: H - B});
  add('line', {class: 'zero', x1: L, y1: y(0), x2: W - R, y2: y(0)});
  let d = '';
  points.forEach((v, i) => { d += (i ? ' H ' + x(i) + ' V ' : 'M ' + x(i) + ' ') + y(v); });
  add('path', {class: 'line', d});
  for (const value of [lo, 0, hi]) add('text', {x: L - 8, y: y(value) + 3, 'text-anchor': 'end'}, fmt(value, 0));
  for (const i of [0, Math.floor((points.length - 1) / 2), points.length - 1]) add('text', {x: x(i), y: H - B + 20, 'text-anchor': 'middle'}, i + 1);
  add('text', {x: W / 2, y: H - 6, 'text-anchor': 'middle'}, t('Recorded cash-event sequence', 'Séquence des événements de trésorerie consignés'));
  const minIndex = points.indexOf(Math.min(...points));
  add('circle', {cx: x(minIndex), cy: y(points[minIndex]), r: 4, fill: points[minIndex] < 0 ? '#a13e3e' : '#ac7730'});
}
function renderHold() {
  const pair = O.value?.value_minus_original_same_fresh_worlds?.['reference/shared_retention'];
  const expert = O.value?.value_selected?.groups?.['reference/expert_E'];
  if (!pair || !expert) { write('hold-increment', missing()); return; }
  write('hold-increment', '+' + money(pair.mean_increment_usd));
  const ci = pair.conditional_monte_carlo_95_interval_usd;
  write('hold-result', t('HOLD and established E: ', 'HOLD et E établi : ') + money(expert.mean_profit_usd) + t(' mean modeled profit. Conditional Monte Carlo 95% interval for the avoided-loss increment: [', ' de profit modélisé moyen. Intervalle Monte-Carlo conditionnel à 95 % de la perte évitée : [') + money(ci[0]) + '; ' + money(ci[1]) + '].');
}
function renderOpportunity() {
  document.querySelectorAll('[data-en]').forEach(el => { el.textContent = el.dataset[lang]; });
  renderDiscovery(); renderMission(); renderScience(); renderCash(); renderHold();
}
function installTabs(attribute, order, get, set, render, prefix) {
  document.querySelectorAll('[' + attribute + ']').forEach(b => {
    b.addEventListener('click', () => { set(b.getAttribute(attribute)); render(); });
    b.addEventListener('keydown', e => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
      e.preventDefault(); const current = order.indexOf(get());
      const next = e.key === 'Home' ? 0 : e.key === 'End' ? order.length - 1 : (current + (e.key === 'ArrowRight' ? 1 : -1) + order.length) % order.length;
      set(order[next]); render(); document.getElementById(prefix + order[next]).focus();
    });
  });
}
installTabs('data-mission', ['equilibrium', 'unsupported_clock', 'calibrated_clock', 'new_mission'], () => selectedMission, value => { selectedMission = value; }, renderMission, 'mission-');
installTabs('data-science-arm', ['H', 'U', 'E', 'E_plus'], () => scienceArm, value => { scienceArm = value; }, renderScience, 'science-');
document.getElementById('cash-mode').addEventListener('change', renderCash);
document.getElementById('cash-delay').addEventListener('change', renderCash);

window.addEventListener('resize', renderCash);
