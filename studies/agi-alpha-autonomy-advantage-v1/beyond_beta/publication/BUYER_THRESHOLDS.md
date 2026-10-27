# Buyer-choice thresholds in the frozen BeyondBeta model

**Classification: post-freeze mechanical explanation, written 27 October 2026.** This note derives algebra from the frozen source. It does not inspect partial results, execute economic worlds, change calibration, select another policy or establish empirical demand. The numerical illustration below evaluates explicit equations with stated round-number inputs; it is not a sampled world or a campaign result.

Source bindings:

- [Frozen protocol](sandbox:/workspace/scratch/28e17bbc80e2/beyond_beta/protocol.json), SHA-256 `ac755ad9b148c33fed91bfb247fc4b09abd2199d839e2741fec4fce38e357664`.
- [Frozen economic engine](sandbox:/workspace/scratch/28e17bbc80e2/beyond_beta/src/economy.py), SHA-256 `bcbbb66b87cd8c5d9e458c289fe435bdf99fadd48ef98adaa6b04f218dc36633`; relevant functions are `quoted_precision`, `utilities`, `opportunity` and `choose_price`.

## 1. What the buyer compares

Let:

| Symbol | Meaning in the frozen model |
|---|---|
| \(V\) | Assumed project value before delay; drawn independently of the human-cost reference. |
| \(P_A,P_H\) | The network's offered price and the cost-derived hypothetical human-service price. |
| \(t_A,t_H\) | Quoted delivery delays in model calendar days. \(t_H=20\) is fixed. |
| \(q_A\) | Public network precision estimate, conditional on technical acceptance. |
| \(q_H\) | Fixed human-service quality weight, \(0.985\). |
| \(d\) | Fixed delivery probability weight used in network utility, \(0.85\). |
| \(\tau\) | This buyer's trust discount for the network; distinct from technical precision. |
| \(E\) | Customer intake effort valued in dollars; the same \(E\) is charged in both current-service utilities. |
| \(S\) | Additional switching burden for first network use; zero after a technically accepted network delivery. |
| \(\delta\) | Weekly value decay, \(0.015\). |
| \(R\) | Remaining buyer budget in the current model budget year. |
| \(D\) | This opportunity's deadline in days. |

Define discounted value fractions and the effective network weight:

\[
D_A=e^{-\delta t_A/7},\qquad D_H=e^{-\delta t_H/7},\qquad w_A=\tau d q_A.
\]

Before eligibility restrictions, the exact utility equations are

\[
U_A=w_A(VD_A-P_A)-E-S,
\]

\[
U_H=q_H(VD_H-P_H)-E.
\]

The offered price appears inside each service's success-weighted term. These are the model's decision weights, not measured probabilities of a contemporary frontier model or a professional service. In particular, \(\tau\), \(d\) and \(q_A\) have separate meanings; their product is not a new quality benchmark.

The additional outside options are decline, with utility zero, and a reduced-form postponement option:

\[
U_W=\max\{0,\gamma q_H(Ve^{-\delta T_W}-P_H)-E-C_W\},
\]

where \(\gamma=0.60\), \(T_W=8\) weeks and \(C_W=200\) USD are explicit assumptions. Postponement does not create an explicit deferred-job queue in this engine. It is a current outside-option value; subsequent weekly opportunities are generated separately.

The human reference is computed from assumed task hours, a loaded occupational wage proxy, matched non-AI proof-container resources and an explicit 20% business allowance:

\[
P_H=1.20\,[h_p f L+C_H(f)].
\]

Here \(h_p\) is 64, 180 or 488 hours according to the declared profile, \(f\) is the job-type multiplier, and \(L\) is the frozen loaded wage proxy. This is neither a consulting quotation nor observed willingness to pay. The 20-day delivery time is not derived from this labor calculation.

## 2. Eligibility comes before a price threshold

The network can be chosen only if its public precision estimate satisfies the buyer's threshold, its price fits the remaining budget, its quoted delivery fits the deadline, the company is open, a public maximum capacity reservation exists, and the corresponding maximum cash requirement can be funded:

\[
q_A\geq q_{\min},\quad P_A\leq R,\quad t_A\leq D,
\]

together with the provider's cash and capacity conditions. A cheap but ineligible offer receives utility \(-\infty\).

The human alternative is available only when \(P_H\leq R\) and \(t_H\leq D\). **The implementation applies the buyer's explicit precision threshold to the network; it does not apply the same hard threshold to the human alternative.** Human quality instead remains the fixed \(q_H\) utility weight. This is a limitation of the stipulated buyer-choice model and should not be described as empirically established equivalence of customer screening rules.

Let the strongest currently available outside option be

\[
U_* = \max\{0,U_W,U_H\text{ if eligible}\}.
\]

The source orders options as decline, postpone, human, network and chooses the first maximum. Consequently, the network must **strictly** beat \(U_*\); it loses exact ties. For \(w_A>0\), the complete one-opportunity adoption condition is

\[
\boxed{P_A < VD_A-\frac{E+S+U_*}{w_A}},
\]

in addition to all eligibility conditions. The right-hand side is an analytical utility ceiling, not the price selected by the engine. If it is nonpositive, no nonnegative network price wins. If \(w_A=0\), nonnegative effort and switching costs make the network unable to beat decline.

## 3. Price, trust, effort and latency thresholds

### Relative to the human service

When the human offer is eligible, the network must satisfy

\[
\boxed{
P_A < VD_A-\frac{q_H}{w_A}(VD_H-P_H)-\frac{S}{w_A}.
}
\]

Common intake effort \(E\) cancels from this pairwise comparison. It still matters when either service is compared with decline or when the postponement term is clamped at zero. The model therefore does not support the statement that reducing the same intake burden on both services necessarily shifts preference toward the network.

Equivalently, the human fee must exceed

\[
P_H>VD_H-\frac{w_A}{q_H}(VD_A-P_A)+\frac{S}{q_H}
\]

for the network to beat the human offer at a fixed network price. Beating this one alternative is insufficient if postponement is better or an eligibility gate fails.

### Relative to decline and postponement

Beating decline requires

\[
P_A<VD_A-\frac{E+S}{w_A}.
\]

When the unclamped postponement value is positive, beating it requires

\[
P_A<VD_A-\frac{\gamma q_H}{w_A}(Ve^{-\delta T_W}-P_H)
+\frac{C_W-S}{w_A}.
\]

The effective price ceiling is the smallest applicable bound, with the budget condition also enforced. In particular, neither the human replacement cost nor project value automatically becomes the network's collectible price.

### Minimum trust or precision

If \(VD_A-P_A>0\), the trust required to beat all outside options is

\[
\boxed{\tau>\frac{E+S+U_*}{d q_A(VD_A-P_A)}}.
\]

The analogous utility threshold for precision is

\[
q_A>\frac{E+S+U_*}{\tau d(VD_A-P_A)},
\]

combined with the independent hard gate \(q_A\geq q_{\min}\). A required trust or precision above one is infeasible. If discounted value minus price is nonpositive, increasing trust cannot make the network beat a nonnegative outside option.

The model initializes \(q_A=0.985\), uses a prior weight of six, and updates precision from public technical-acceptance feedback. Initial trust is 0.55, 0.70 or 0.82 by profile. Those exact values and the update rules are assumptions; this note does not reinterpret them as empirical adoption probabilities.

### Maximum switching burden and delivery time

The largest admissible switching burden satisfies

\[
S<w_A(VD_A-P_A)-E-U_*.
\]

For positive \(\delta\), the utility-implied network latency ceiling is

\[
\boxed{
t_A<\frac{7}{\delta}
\log\!\left(\frac{V}{P_A+(E+S+U_*)/w_A}\right).
}
\]

The quoted delay must also meet \(t_A\leq D\). A nonpositive logarithm leaves no feasible nonnegative delay. A provider's low marginal computation cost cannot override these buyer-side constraints or the provider's cash and resource limits.

## 4. Why a higher-value project need not favor the cheaper producer

The network-minus-human utility difference is

\[
U_A-U_H=(w_AD_A-q_HD_H)V+q_HP_H-w_AP_A-S.
\]

If \(w_AD_A<q_HD_H\), the stipulated buyer assigns the human service a larger value-weighted outcome probability. In that case, the network beats the human service only below the crossover

\[
V<\frac{q_HP_H-w_AP_A-S}{q_HD_H-w_AD_A},
\]

provided the numerator is positive. The other adoption conditions still apply. If the numerator is nonpositive, no positive project value makes the network beat the human offer in this case. If the sign of the coefficient reverses, the inequality reverses; equality of the coefficients leaves a pure price/switching comparison.

Thus the frozen utility assumptions do not guarantee that automation wins every expensive or valuable job. A sufficiently large reliability/credibility discount can outweigh a substantial cost advantage. Whether actual buyers apply such weights is unknown.

## 5. The fixed 20-day human-service assumption

Human delivery is fixed at **20 model calendar days** across all three work-hour profiles and job types. It is not measured professional turnaround, is not inferred from the 64/180/488-hour work breakdown, and does not explicitly model staffing, parallel work, queueing or expedited human service. Network delivery, in contrast, depends on its public maximum reservation schedule. These differences must remain visible when interpreting a service advantage.

This assumption affects choice in two distinct ways:

1. **Discounted value.** A faster human service raises \(U_H\) while it remains eligible. Holding all other quantities fixed, the human-relative network price ceiling changes with human delay as

   \[
   \frac{\partial P_A^{\max,H}}{\partial t_H}
   =\frac{q_H}{w_A}\frac{\delta}{7}V e^{-\delta t_H/7}>0.
   \]

   Faster human service therefore lowers the network's admissible price; slower service raises it.

2. **A discontinuous deadline gate.** Whenever \(D<20\), the frozen human offer is unavailable, irrespective of its price. Under the assumed uniform deadline interval of 10–60 days, this gate alone excludes the human option on one fifth of draws. That is a property of the assumed deadline distribution, not an observed market share or an estimate of network adoption. A human delay of ten days or less would remove this particular exclusion; all other buyer and provider gates would remain.

The following table illustrates only the first effect. It fixes \(t_A=14\) days, \(P_H=20{,}000\) USD, \(S=1{,}000\) USD, \(\tau=0.70\), \(d=0.85\), and \(q_A=q_H=0.985\). These round-number prices and values are explicit illustrative inputs, not selected policies, observed quotes or campaign outcomes. The effective network weight is \(w_A=0.586075\). Each entry is the **strict upper network price to beat the human offer alone**, assuming both are eligible.

| Assumed human delay | Ceiling when \(V=25{,}000\) USD | Ceiling when \(V=50{,}000\) USD |
|---|---:|---:|
| 20 days, frozen assumption | 15,914.19 USD | −78.80 USD |
| 10 days, analytical sensitivity | 15,042.29 USD | −1,822.59 USD |
| 5 days, analytical sensitivity | 14,599.29 USD | −2,708.60 USD |
| 1 day, analytical sensitivity | 14,241.45 USD | −3,424.28 USD |

A negative ceiling means no nonnegative network price beats that eligible human offer under these particular utility inputs. It does not mean the campaign's entire market is unviable. For the 25,000-USD illustration, reducing human delay from 20 to five days lowers the ceiling by 1,314.90 USD. A better network trust/quality weight, a different human fee, a lower switching burden, or a different value can change the result; each is a separate assumption.

## 6. What this analysis can and cannot support

These equations are exact conditional choice boundaries for the frozen model. They support transparent statements about which stipulated combinations of price, delay, quality, trust and effort permit adoption. They do not establish real demand, actual willingness to pay, a profit margin, an equilibrium market price or a commercially optimal policy.

The engine's adaptive price rule does **not** receive these private buyer utilities. It uses its own previous quote/conversion history, the declared discrete price grid, public precision and public maximum delivery cost. An analytical ceiling derived with a specified \(V\) is an explanatory calculation available to the researcher, not a new information advantage silently granted to the provider.

Changing human delay analytically while holding one offer's state fixed is valid. Claiming an alternative whole-enterprise profit, investment path or optimized price policy from that calculation is not. Different choices would change later budgets, trust, conversion observations, cash, queues, learning opportunities and asset decisions. Such a dynamic sensitivity would require a separately registered campaign; none is run or asserted here.

The safe commercial interpretation is therefore conditional: a network offer can win where its complete price, credible expected outcome, switching burden and delivery timing jointly beat the available human and waiting options, while cash and capacity permit delivery. The frozen 20-day human delay, the asymmetric hard quality gate, the assumed trust weights and the reduced-form waiting option limit how broadly that statement can be generalized. Profitable accepted delivery and worthwhile additional Alpha remain separate tests in the registered financial and paired-policy records.
