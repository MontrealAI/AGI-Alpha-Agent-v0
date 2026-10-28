#!/usr/bin/env python3
"""Build a claim index from frozen executed results; never change experiment files."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def main():
    technical = read('research/claims_technical.json')
    claims = list(technical['claims'])
    base = read('results/business_confirmation.json')['summaries']['base']
    derived = read('results/derived_economics.json')
    audit = read('audit/accounting_confirmation.json')

    def add(identifier, claim, status, paths, values=None, limits=None):
        claims.append({'id': identifier, 'claim': claim, 'status': status,
                       'values': values or {}, 'evidence': [{'path': p} for p in paths],
                       'limits': limits or []})

    add('ECON-01', 'The frozen standalone policy loses complete-project money in all 1,024 base histories.',
        'model_conditional', ['results/business_confirmation.json', 'protocol/commercial_policy.json',
        'protocol/commercial_freeze.json'],
        {k: base[k]['mean'] for k in ['net_revenue', 'expenses', 'operating_contribution', 'full_profit', 'accepted']},
        ['No observed demand or willingness to pay; participants and monetary entries are simulated.',
         'Policy was frozen after 15 development price-arrangement combinations; no-launch dominates the tested launch policies.'])
    add('ECON-02', 'Nine additional conditional scenarios also lose in every history; they are not a probability-weighted forecast.',
        'model_conditional', ['results/business_confirmation.json', 'results/business_confirmation.csv'],
        {'scenarios': 10, 'histories_per_scenario': 1024},
        ['Scenario probabilities are unspecified. Model-generated buyer choices are not independent customer evidence.'])
    add('ECON-03', 'Revenue, customer cash, full-project profit and capital requirement are distinct.',
        'model_conditional', ['results/business_confirmation.json', 'results/derived_economics.json',
        'audit/accounting_confirmation.json'],
        {'net_customer_cash_usd': base['net_revenue']['mean'] - derived['cost_categories_mean']['bad_debt'],
         'capital_mean_usd': base['required_capital']['mean'], 'capital_p95_usd': base['required_capital']['p95'],
         'ratio_of_mean_profit_to_mean_cost': derived['ratio_of_mean_profit_to_mean_cost'],
         'cash_shortfall_probability_under_base_model': base['cash_shortfall_probability']},
        ['Refundable deposits are restricted. Initial capital is a modeled policy, not an actual contribution.',
         'Zero sampled base shortfalls does not establish real-world financing sufficiency.'])
    add('ECON-04', 'An independent parser reconstructed the full histories and decisions without importing the simulator.',
        'executed_supported', ['audit/accounting_reconstruct.py', 'audit/accounting_confirmation.json',
        'results/business_confirmation_journals.jsonl.gz', 'audit/accounting_controls.json'],
        {'histories': audit['histories_audited'], 'journal_entries': audit['journal_entries_audited'],
         'errors': len(audit['errors']), 'warnings': len(audit['warnings']), 'passed': audit['passed']},
        ['Arithmetic and policy reconstruction validate model execution, not demand assumptions or real sales.',
         'Seven terminal stress insolvencies remain explicit creditor claims.'])
    add('ECON-05', 'Constant-mix break-even requirements exceed observed modeled demand and reserved capacity.',
        'derived_diagnostic', ['results/derived_economics.json', 'src/analyze_results.py',
        'results/business_development.json'],
        {k: derived[k] for k in ['break_even_accepted_at_constant_mix', 'required_accepted_price_at_unchanged_demand',
         'max_orders_from_reserved_capacity_180days', 'direct_cost_reduction_needed_for_break_even']},
        ['Holding customer mix fixed is a diagnostic, not a demand forecast.',
         'Eight support-reserve hours per order are an aggregate proxy, not a calendar SLA.'])
    add('ECON-06', 'Human exceptions and buyer benefit are explicit modeled quantities, not measured human performance.',
        'model_conditional', ['results/business_confirmation.json', 'results/derived_economics.json',
        'protocol/business_assumptions.json'],
        {'variable_service_hours_per_accepted': derived['variable_human_hours_per_accepted'],
         'interventions_per_accepted': base['human_interventions_per_accepted'],
         'buyer_benefit_ex_ante_usd': base['buyer_benefit_conditional_on_participation'],
         'buyer_benefit_realized_model_usd': derived['mean_realized_modeled_buyer_gain']},
        ['No customer time study or measured cost per human intervention was performed.'])
    add('ECON-07', 'The stylized strategic game favors no entry when exit is permitted.',
        'model_conditional', ['src/strategic_analysis.py', 'results/strategic_game.json',
        'audit/strategic_reconstruct.py', 'audit/strategic_confirmation.json'],
        {'independently_checked_payoff_cells': 324},
        ['Synthetic buyer distribution, finite prices, entrant fixed cost and incumbent advantage are assumptions.',
         'This separate game does not convert the lifecycle bargaining heuristic into a market equilibrium.'])
    add('DECISION-01', 'Stop the tested standalone offering; no replacement earned flagship status in the bounded campaign.',
        'evidence_based_decision', ['results/business_confirmation.json', 'results/kernel_ablation.json',
        'research/return_to_search.json', 'research/return_to_search_manifest.json'],
        {'commercial_action': 'STOP', 'replacement_flagship': None},
        ['A rejected modeled offering does not prove every related business impossible.',
         'The experience-foundry opening is an unbuilt hypothesis with physical-transfer and buyer-evidence gates.'])
    add('FRONTIER-01', 'Exact named releases were checked against primary sources and separated from actual execution access.',
        'primary_source_desk_research', ['research/frontier.json', 'research/technical_sources.json',
        'research/return_to_search.json', 'research/bibliography.json'], limits=[
        'Provider performance remains reported evidence. Terra was not separately benchmarked; internal mathematical model unavailable.',
        'No reopened-search world model, robotics system, material assay or multi-owner experiment was executed.'])
    add('ECOSYSTEM-01', 'Prior source editions and native FusionPlan modules were inspected at a pinned repository revision.',
        'executed_and_source_supported', ['research/ecosystem.json', 'research/source_editions/source_manifest.json',
        'results/native_alpha/fusion_plan.json', 'results/native_alpha/verification.json'], limits=[
        'Local work-plan compilation is not deployed MARK coordination, on-chain execution or a funded bounty.',
        'Canonical release/Pages qualification remains with the existing repository owner.'])
    add('SCALE-01', 'No defensible billion-plus economic thesis was earned.',
        'evidence_based_limit', ['research/scaling_thesis.json', 'results/derived_economics.json'],
        {'hurdle_metric': 'annual net incremental productive value in constant 2026 USD',
         'hurdle_usd': 1000000000, 'horizon_year': 2031},
        ['10,000 deployments times USD100,000 benefit is an unverified hurdle decomposition.',
         'Industry revenue, enterprise revenue, profit, productive value and valuation are not interchangeable.'])

    files = sorted({e['path'] for c in claims for e in c['evidence']})
    missing = [f for f in files if not (ROOT/f).is_file()]
    if missing:
        raise SystemExit('Missing evidence paths: '+', '.join(missing))
    hashes = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    output = {'schema': 'possibility_engine.claim_map.v1', 'edition': '2026-10-28',
              'decision': 'STOP standalone offering; NO FLAGSHIP EARNED',
              'claims': claims, 'evidence_sha256': hashes}
    (ROOT/'research/claims.json').write_text(json.dumps(output, indent=2)+'\n')
    print(f'{len(claims)} claims; {len(hashes)} evidence files, all present')


if __name__ == '__main__':
    main()
