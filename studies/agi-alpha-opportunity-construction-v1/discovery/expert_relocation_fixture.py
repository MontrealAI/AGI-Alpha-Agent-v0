"""Synthetic participation and cash-flow falsifier; no real offers or legal conclusion."""
import itertools
import json

def evaluate(consents=255, days=120, sponsor_cap=250000, bridge=2000000,
             approved=True, titles_ready=True, guarantee=2000000):
    households = consents.bit_count()
    principal = 8 * 250000
    option_cost = 8 * 2000
    gap_support = 8 * (265000 + 5000 - 250000)
    success_fee = 20000
    interest = principal * .08 * days / 365
    sponsor_need = gap_support + option_cost + success_fee + interest
    reasons = []
    if households != 8: reasons.append('withdrawal_or_missing_consent')
    if not approved: reasons.append('no_approved_reimbursement')
    if not titles_ready: reasons.append('replacement_and_old_title_not_jointly_ready')
    if bridge < principal: reasons.append('insufficient_bridge')
    if guarantee < principal: reasons.append('unfunded_nonreimbursement_risk')
    if sponsor_cap < sponsor_need: reasons.append('unfunded_gap_fees_or_interest')
    close = not reasons
    return dict(close=close, reasons=reasons, principal=principal,
                sponsor_need=round(sponsor_need, 2), sponsor_abort_loss=option_cost,
                household_preclose_money_at_risk=0,
                household_unfunded_replacement_gap=0 if close else None)

if __name__ == '__main__':
    checked = 0
    closed = 0
    for args in itertools.product(range(256), (120, 365), (200000, 250000, 400000),
                                  (500000, 2000000), (False, True),
                                  (False, True), (0, 2000000)):
        result = evaluate(*args)
        checked += 1
        closed += int(result['close'])
        if result['close']:
            assert args[0] == 255 and args[4] and args[5]
            assert args[3] >= result['principal'] and args[6] >= result['principal']
            assert args[2] >= result['sponsor_need']
            assert result['household_unfunded_replacement_gap'] == 0
    print(json.dumps(dict(synthetic_only=True, combinations_checked=checked,
                         feasible_combinations=closed, base=evaluate(),
                         low_sponsor_budget=evaluate(sponsor_cap=200000),
                         delayed=evaluate(days=365),
                         withdrawal=evaluate(consents=254),
                         no_guarantee=evaluate(guarantee=0)), indent=2))
