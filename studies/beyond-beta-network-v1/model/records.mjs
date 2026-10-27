// SPDX-License-Identifier: Apache-2.0
// Remove repeated debugging traces only; every cash bill, resource total and test observation remains.
export function compactPlan(p){if(!p)return p;const {roleUsage,...out}=p;
 if(out.diagnostics){const {candidateHistory,...d}=out.diagnostics;out.diagnostics=d;}if(out.probeCases)delete out.probeCases;return out;}
export function compactRun(run){const h=run.histories;
 for(const j of h.jobs)j.plan=compactPlan(j.plan);for(const a of h.auxiliary)a.plan=compactPlan(a.plan);
 for(const d of h.decisions){delete d.alphaBound;d.construction=compactPlan(d.construction);}
 for(const a of h.campaigns){a.construction=compactPlan(a.construction);a.review.review=compactPlan(a.review.review);}
 for(const a of h.revalidations)a.review.review=compactPlan(a.review.review);return run;}
