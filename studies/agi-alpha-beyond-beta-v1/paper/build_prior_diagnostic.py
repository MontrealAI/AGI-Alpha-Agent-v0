# SPDX-License-Identifier: Apache-2.0
"""Render the one separately frozen exploratory belief diagnostic."""
import json
from build import ROOT, money, number, pct, table, write


def main():
    path = ROOT / 'results/paid_work_prior_diagnostic'
    s = json.loads((path / 'summary.json').read_text())
    manifest = json.loads((path / 'run_manifest.json').read_text())
    assert manifest['completed_at_utc'] and manifest['worlds'] == 100
    assert s['seed'] == 951557 and manifest['no_further_tuning']
    arms = s['arms']; pairs = s['paired']
    ext = arms['posterior_coherent_network']
    full = pairs['posterior_network_vs_beta_net_profit']
    repair = pairs['posterior_vs_frozen_network_net_profit']
    body = r'\subsection{One exploratory recipient-belief diagnostic}'
    body += '\nAfter the frozen zero-use result was diagnosed, one new protocol was frozen before a single fresh run: 100 matched world IDs, seed 951557, and three arms (300 complete histories). It uses the previously declared compound condition, with static Beta, 48 recipients, greater contract recurrence and paid additional capacity. This is a post-confirmation exploratory belief sensitivity, not replacement confirmation or evidence of a real market.'
    body += '\n\n' + r'The treatment preserves the actual task, capability, failure, cost, cash, demand and resource generators. It retains four prior-equivalent cases but centers the prior on declared construction assumptions: $q_0=\pi q_{\rm good}+(1-\pi)0.65$ and $\hat q=(4q_0+s)/(4+n)$. For a paid-job capsule, $\pi$ is declared reconstruction correctness times retention-generalization success; for separate research it is declared build success. No latent source truth or future outcome is available to the controller. This prior is an unmeasured decision assumption, not a capability bonus. The extension also honors the quality-effect multiplier in reuse valuation; it equals one here and cannot cause this treatment difference.'
    rows=[]
    for key,label in [('frozen_beta','Frozen Beta'),('frozen_network','Frozen network'),('posterior_coherent_network','Declared-prior network')]:
        a=arms[key]
        inc=0 if key=='frozen_beta' else pairs[('frozen_network' if key=='frozen_network' else 'posterior_network')+'_vs_beta_net_profit']['mean']
        rows.append([label,money(inc,2),pct(a['probability_retention_admission']),pct(a['probability_useful_recipient_use']),number(a['retention_useful_fresh_projects']['mean'],2)])
    body += '\n'+r'\begin{table}[htbp]\centering\small'+table(['Arm','Profit $-$ Beta','Admission','Useful reuse','Useful pairs'],rows)+r'\caption{Fresh exploratory diagnostic. Frequencies use all 100 worlds. Useful pairs are capsule--project pairs, not necessarily distinct projects. Beta mean complete profit is '+money(arms['frozen_beta']['net_profit']['mean'])+r' in this deliberately strong compound condition. All inputs, full ledgers and negative outcomes are retained.}\end{table}'
    body += '\nThe declared-prior policy produces useful reuse in '+pct(ext['probability_useful_recipient_use'])+' of worlds, with '+number(ext['retention_uses']['mean'],2)+' attempted and '+number(ext['retention_useful_fresh_projects']['mean'],2)+' useful capsule--project uses per world. Admission occurs in '+pct(ext['probability_retention_admission'])+' of worlds. Relative to the frozen network it improves mean profit by '+money(repair['mean'],2)+' (median '+money(repair['median'])+'; 5th--95th percentile '+money(repair['p05'])+' to '+money(repair['p95'],2)+'; minimum '+money(repair['min'],2)+'). The revised belief opens a previously blocked reuse path; it does not guarantee a worthwhile retention policy.'
    body += '\n\n'+r'\textbf{Beta remains the best tested policy.} '+'The declared-prior network loses '+money(abs(full['mean']),2)+' on average relative to Beta (Monte Carlo standard error '+money(pairs['posterior_network_vs_beta_profit_mean_mc_standard_error'],2)+'; median '+money(full['median'],2)+'; 5th--95th percentile '+money(full['p05'],2)+' to '+money(full['p95'],2)+'). It underperforms Beta in every one of the 100 worlds. Quality-adjusted differences are identical. The paired change in distinct useful accepted projects is zero. Mean extra B spending is '+money(ext['ledger_B_retention_total']['mean'],2)+', including rejected candidates and upkeep. Useful transfer is therefore demonstrated within this simulation, but total retention-policy repayment and operating-funded profitable feedback remain unsupported. Both network arms also undertake one optional C campaign in one world; its cost remains in total policy profit (mean USD47.68 across all worlds). These contrasts therefore measure whole-policy effects, not the isolated repayment of each capsule.'
    body += '\n\nThis single diagnostic separates a software decision bottleneck from economic success: correcting the belief mismatch can enable useful reuse without making the complete enhancement worthwhile. No further policy or parameter tuning followed. The primary Beta result is unchanged, and no volume, graph size, reuse count or profitable source job is relabeled as recursive improvement. The separately frozen files, four directed extension tests and independent 300-history cash/provenance audit accompany the result.'
    write('exploratory_coherence.tex',body)
    print(json.dumps({'worlds':100,'seed':951557,'use_frequency':ext['probability_useful_recipient_use'],'increment_vs_beta':full['mean'],'increment_vs_frozen_network':repair['mean']}))


if __name__ == '__main__':
    main()
