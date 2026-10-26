"""One-time presentation repair; independent of frozen study logic."""
from pathlib import Path
p=Path(__file__).with_name('demo_template.html')
s=p.read_text()

def change(old,new):
    global s
    if old not in s:
        raise ValueError(old[:100])
    s=s.replace(old,new)

change('<nav class="nav-links" aria-label="Sections">','<nav class="nav-links" aria-label="Sections" data-i18n-aria="sectionsLabel">')
change('role="group" aria-label="Comparison arm"','role="group" aria-label="Comparison arm" data-i18n-aria="comparisonArmLabel"')
change('data-arm="C" aria-pressed="false">C ·','data-arm="C" aria-pressed="false">C2 ·')
change('<label>C · USD','<label>C2 · USD')
change('<span><i style="background:#f0d29a"></i>C</span>','<span><i style="background:#f0d29a"></i>C2</span>')
change('aria-label="A construction USD 0"','aria-label="A construction USD 0" data-i18n-aria="incumbentConstructionLabel"')
change('<main id="top">','<main id="top">\n<div class="container" id="qaBanner" hidden><div class="notice blocked" style="margin-top:20px"><strong data-i18n="syntheticOnly">SYNTHETIC UI CONTROL — NOT STUDY EVIDENCE</strong></div></div>')
change('<div class="table-wrap"><table>','<aside class="notice blocked" id="primaryRecord"><div class="notice-icon">◇</div><div><strong data-i18n="primaryPreserved">The registered primary failure stays visible.</strong><p id="primaryFinding"></p><div id="primaryLinks" class="source-links"></div></div></aside>\n<div class="table-wrap"><table>')
# Static fallbacks agree with the initialized bilingual labels.
change('Complete scope accepted · B','Complete handoffs accepted · B')
change('>Scope accepted<','>Complete handoffs<')
change('Where buyers went · B market','Where buyers went · C2 market')
change('Weekly asset upkeep · USD, B and C','Weekly asset upkeep · USD, B and C2')
# Avoid accidental C22 if literal is already modified elsewhere.
s=s.replace('C22','C2')
for old,new in [
("scopeAccepted:'Scope accepted'","scopeAccepted:'Complete handoffs'"),
("scopeAccepted:'Périmètre accepté'","scopeAccepted:'Livrables complets'"),
("scopeFail:'Scope incomplete'","scopeFail:'Complete handoff not accepted'"),
("scopeUnknown:'Scope not assessed'","scopeUnknown:'Complete handoff not assessed'"),
("scopeFail:'Périmètre incomplet'","scopeFail:'Livrable complet non accepté'"),
("scopeUnknown:'Périmètre non évalué'","scopeUnknown:'Livrable complet non évalué'"),
("armC:'Conventional AST builder'","armC:'Conventional AST builder · C2'"),
("armC:'Constructeur AST classique'","armC:'Constructeur AST classique · C2'"),
("buyerAllocation:'Choix des acheteurs · marché B'","buyerAllocation:'Choix des acheteurs · marché C2'"),
('Les mêmes hypothèses d’acheteurs s’appliquent à A, B et C.','Les mêmes hypothèses d’acheteurs s’appliquent à A, B et C2.'),
('The same buyer assumptions apply to A, B and C.','The same buyer assumptions apply to A, B and C2.'),
('The complete accepted workflows are not equivalent across A, B and C.','Independently accepted complete handoffs are not established for the entire registered set across A, B and C2.'),
('Scope equivalence permits explicit conditional scenarios.','Independently accepted equivalent complete handoffs permit explicit conditional scenarios.'),
('Les processus complets acceptés ne sont pas équivalents entre A, B et C.','L’acceptation indépendante des livrables complets équivalents n’est pas établie sur tout l’ensemble enregistré pour A, B et C2.'),
('L’équivalence du périmètre permet des scénarios conditionnels explicites.','L’acceptation indépendante de livrables complets équivalents permet des scénarios conditionnels explicites.'),
('A/B/C comparison','A/B/C2 comparison'),
('comparaison A/B/C complète','comparaison A/B/C2 complète'),
('Entretien hebdomadaire · USD, B et C','Entretien hebdomadaire · USD, B et C2'),
("marketRepaid:'One tested investment repays in this scenario.'","marketRepaid:'Direct cost savings cover the tested asset bill.'"),
("marketRepaid:'Un investissement testé se rembourse dans ce scénario.'","marketRepaid:'Les économies directes couvrent la facture de l’actif testé.'"),
("marketNotRepaid:'The capability is funded but not repaid.'","marketNotRepaid:'The asset is funded; direct cost savings do not repay it.'"),
("marketNotRepaid:'La capacité est financée, mais non remboursée.'","marketNotRepaid:'L’actif est financé; ses économies directes ne le remboursent pas.'")]:
    change(old,new)
change("en:{\n", "en:{\nsectionsLabel:'Sections',comparisonArmLabel:'Comparison arm',incumbentConstructionLabel:'A construction USD 0',syntheticOnly:'SYNTHETIC UI CONTROL — NOT STUDY EVIDENCE',primaryPreserved:'The registered primary failure stays visible.',primaryBoundary:'The original primary failure is preserved. C2 is a separately registered follow-up; fresh follow-up results and exploratory scenarios do not replace the primary conclusion.',dispatchUnproved:'Dispatch unproved',conditionalBinding:'Conditional binding check',incrementalProfit:'Profit change vs A',paybackBoundary:'Direct avoided costs are one repayment diagnostic. Incremental enterprise profit, foregone service and cash timing remain separate. No complete commercial Flywheel or second justified investment is established.',\n")
change("fr:{\n", "fr:{\nsectionsLabel:'Sections',comparisonArmLabel:'Bras de comparaison',incumbentConstructionLabel:'Construction A : 0 USD',syntheticOnly:'CONTRÔLE SYNTHÉTIQUE DE L’INTERFACE — AUCUNE PREUVE D’ÉTUDE',primaryPreserved:'L’échec primaire enregistré reste visible.',primaryBoundary:'L’échec primaire d’origine est conservé. C2 fait l’objet d’un suivi enregistré séparément; les résultats inédits et les scénarios exploratoires ne remplacent pas la conclusion primaire.',dispatchUnproved:'Appel cible non prouvé',conditionalBinding:'Contrôle de liaison conditionnel',incrementalProfit:'Variation du profit vs A',paybackBoundary:'Les coûts directs évités constituent un indicateur de remboursement. Le profit incrémental, les livraisons perdues et les délais de trésorerie restent distincts. Aucun Flywheel commercial complet ni second investissement justifié n’est établi.',\n")
change("const t=key=>", "const armLabel=arm=>arm==='C'?'C2':arm;\nconst t=key=>")
change("a.download=name;a.click();", "a.download=String(name).replace(/[\\/\\\\\\u0000-\\u001f\\u007f]/g,'_');a.click();")
change("...callRows(a).filter(r=>r.status==='UNRESOLVED')", "...callRows(a).filter(r=>r.status==='UNRESOLVED'||r.mappingVerified===false)")
change("r.status==='BINDING_CONFLICT'?'fail':r.status==='BINDING_PRESERVED'?'measured':'unknown'", "r.mappingVerified===false?'assumed':r.status==='BINDING_CONFLICT'?'fail':r.status==='BINDING_PRESERVED'?'measured':'unknown'")
change("item.append(top);if(r.beforeAccepts", "item.append(top);if(r.mappingVerified===false)item.append(tag(t('dispatchUnproved'),'unknown'),el('p','',t('conditionalBinding')));if(r.beforeAccepts")
change("el('span','arm-badge arm-'+arm,arm)", "el('span','arm-badge arm-'+arm,armLabel(arm))")
change("$('marketOutcomeText').textContent=t('noPrimaryReplacement')+' '+t('marketNextLimit');", "$('marketOutcomeText').textContent=t('paybackBoundary')+' '+t('noPrimaryReplacement')+' '+t('marketNextLimit');")
change("[[t('acceptedJobs'),s.enterpriseAccepted]", "[[t('incrementalProfit'),arm==='A'?'—':money(s.profitCents-currentPair.arms.A.summary.profitCents)],[t('acceptedJobs'),s.enterpriseAccepted]")
change("supplied.costs?.[arm]?.completeRecurringCostCents!==undefined", "Number.isSafeInteger(supplied.costs?.[arm]?.completeRecurringCostCents)&&supplied.costs[arm].completeRecurringCostCents>=0")
change("supplied.costs?.[arm]?.completeConstructionCostCents!==undefined", "Number.isSafeInteger(supplied.costs?.[arm]?.completeConstructionCostCents)&&supplied.costs[arm].completeConstructionCostCents>=0")
change("function renderEvidence(){clear($('sourceRegister'));", "function renderEvidence(){$('qaBanner').hidden=DATA.qaSynthetic!==true;$('primaryFinding').textContent=local(DATA.primaryConfirmation?.finding)||t('primaryBoundary');clear($('primaryLinks'));for(const l of DATA.primaryConfirmation?.sourceLinks||[])$('primaryLinks').append(safeLink(local(l.label)||l.url,l.url));clear($('sourceRegister'));")
change("document.querySelectorAll('[data-i18n]').forEach(n=>n.textContent=t(n.dataset.i18n));", "document.querySelectorAll('[data-i18n]').forEach(n=>n.textContent=t(n.dataset.i18n));document.querySelectorAll('[data-i18n-aria]').forEach(n=>n.setAttribute('aria-label',t(n.dataset.i18nAria)));")
# Labels in compact cards may wrap without forcing the viewport wider.
change('.arm-badge{display:inline-flex;width:27px;', '.arm-badge{display:inline-flex;flex-shrink:0;width:30px;')
change('.market-card dt{color:var(--soft)}', '.market-card dt{color:var(--soft);overflow-wrap:anywhere}')
p.write_text(s)
print('Template presentation and unknown-null safeguards updated.')
