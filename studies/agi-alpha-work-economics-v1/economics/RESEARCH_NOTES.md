# Economics source audit for The Economics of Autonomous Work

Research date: 25 October 2026. These are intermediate research notes for the parent publication team, not a claim that an empirical human comparison has been performed.

## Decision

Label the proposed **USD 40 trillion per year of computer-mediated labor expenditure an illustrative scenario**, worldwide, on a 2025 current-dollar accounting basis. No inspected primary source establishes this exact quantity. The commercial argument should begin with accepted job economics, not this market number.

Primary sources do establish a large economy and labor share. The World Bank World page currently displays **2025 GDP of USD 118.35 trillion**. ILO's 19 March 2026 review reports a **2025 global labor-income share of 52.6%**. Multiplying these displayed values yields USD 62.2521 trillion, and USD 40 trillion is 64.2549% of that mechanical envelope. This multiplication is an **arithmetic scale check**, not an official estimate of current-dollar employer expenditure: we have not harmonized the two sources' country coverage, aggregation weights, price bases, vintages or revisions. In particular, PPP values must never be relabeled nominal dollars.

The ILO national-accounts concept includes employee compensation and imputed labor income of self-employed workers. Compensation includes wages, in-kind remuneration and employer social-insurance contributions, but excludes employer payroll taxes. It is neither total employer overhead nor pure payroll. The 2026 methods document explains that 2024--2025 labor shares require modeled estimates because underlying UNSD national accounts currently stop at 2023. An estimate is not an observed cash ledger.

## Sources verified through both search systems / authoritative opens

| BibTeX key | Exact fact used | URL | Retrieval refs |
|---|---|---|---|
| worldbank2025gdp | World GDP current USD, 2025, 118.35 trillion; display precision only | https://data.worldbank.org/country/world | turn2view3, turn10search0 |
| ilo2026sdgreview | World labor-income share, 2025, 52.6%; publication 19 March 2026 | https://ilostat.ilo.org/blog/the-world-of-work-and-the-2030-agenda-a-ten-year-review/ | turn2view0, turn10search1 |
| ilo2026labourmetadata | Defines compensation plus self-employment labor income; aggregation from country numerators/denominators; excludes employer payroll tax | https://unstats.un.org/sdgs/metadata/files/Metadata-10-04-01.pdf | turn3view2 |
| ilo2026modelmethods | Modeled estimates for 2024--2025; global/regional income distributions in PPP terms | https://webapps.ilo.org/ilostat-files/Documents/TEM.pdf | turn3view0, turn4view1, turn4view2 |
| bls2025ecec | Dec 2025 hourly total compensation: office/admin 35.96; professional/related 72.19; management/business/financial 86.61 USD | https://www.bls.gov/news.release/archives/ecec_03202026.htm | turn7view0; primary PDF independently found as turn10search2 |
| eurostat2022digital | Nearly 30% of employed EU people 15--74 use digital devices all/most working time in 2022; excludes phone calls | https://ec.europa.eu/eurostat/en/web/products-eurostat-news/w/ddn-20230627-1 | turn12view1, turn10search3 |
| jrc2025digital | AIM-WORK 2024--25: over 90% of EU workers use digital devices; a third report work-related AI use | https://publications.jrc.ec.europa.eu/repository/handle/JRC143072 | turn12view0 |
| oecd2019icttasks | ICT task intensity is frequency-based and distinguished from workers' skills; not a wage-weighted worldwide time share | https://www.oecd.org/en/publications/measuring-the-digital-transformation_9789264311992-en/full-report/component-51.html | turn5view3 |

No long verbatim excerpts are reproduced. Root must open or search+find these sources before using these reference IDs in its own final response. Bibliography contains exact primary URLs.

## Why device-use counts cannot establish the USD 40T thesis

Eurostat's intensive-use measure and JRC's any-use measure answer different questions in different periods. They should not be combined into a trend or substituted for a global share of compensation attributable to digital tasks. Neither says that a device-using employee's whole role is executable through software. They also do not establish the share of work performed without AI. The employer's no-AI comparator is a study definition, not a claim that every actual employer uses no AI.

A defensible bottom-up expenditure estimate is:

L_digital = sum over countries and occupations of (paid hours × loaded compensation/hour × fraction of those hours spent on eligible digital-interface tasks).

Weights must track compensation, not just headcounts; computer tasks may overlap with interpersonal and physical work, so a mutually exclusive allocation or explicit overlap adjustment is necessary. Compatible years, exchange rates, occupation coverage, self-employment accounting and task-time surveys are required. Worldwide task-time and compensation linkage was not completed here. Therefore the tested portfolio cannot supply a global eligibility share.

## Scenario cascade: definitions and no double counting

The runnable `compute_scenarios.py` reads `market_scenarios.json` and writes `scenario_results.json`. Every market input is visibly an assumption. The common USD 60T labor envelope is a round hypothetical calibration, not a published statistic.

For a scenario with digital task expenditure D, eligibility e and adoption a:

B = D × e × a

B is comparable baseline labor expenditure for adopted jobs. It is **not provider revenue**. Let h be retained employer attention/integration cost as a fraction of B, p the service price fraction, k the provider operating-cost fraction, and m one provider's service-market share:

- Potential customer economic savings = B × (1 - h - p).
- Total industry service fees = B × p.
- One provider's revenue = B × p × m.
- That provider's gross contribution before fixed costs = B × (p - k) × m.

The identity B = retained customer costs + provider fees + potential customer savings is tested in the script. Provider costs are inside provider fees, not added again to customer costs. Gross contribution excludes fixed R&D, sales, corporate overhead, capital expenditure and financing, and is not profit. Economic savings become cash savings only if payroll, hiring, contractor spend or another real expense changes; redeployed staff time is freed capacity.

| Assumption/result | Conservative | Central | Ambitious |
|---|---:|---:|---:|
| Common illustrative total labor envelope | $60T | $60T | $60T |
| Digital task compensation share | 20% | 40% | 66.67% |
| Digital task labor expenditure D | $12T | $24T | $40T |
| Hypothetical technically eligible share e | 5% | 20% | 50% |
| Adoption share a | 5% | 20% | 40% |
| Adopted baseline expenditure B | $30B | $960B | $8T |
| Retained employer cost share h | 50% | 30% | 10% |
| Provider service price share p | 20% | 20% | 20% |
| Potential customer economic savings | $9B | $480B | $5.6T |
| All-provider revenue | $6B | $192B | $1.6T |
| Arbitrary individual-provider share m | 1% | 1% | 1% |
| Individual-provider revenue | $60M | $1.92B | $16B |

**These are conditional arithmetic scenarios, not confidence bounds, forecasts, market-share targets or extrapolations supported by the experiment.** Technical eligibility, adoption, price and retained cost require independent future evidence. The point is to separate the economic quantities cleanly. Do not headline the speculative provider numbers as a business result.

## Documented human-cost valuation without inventing a worker

BLS December 2025 private-industry averages (Table 4):

| Category | Wages/hour | Benefits/hour | Total compensation/hour |
|---|---:|---:|---:|
| Office and administrative support | $24.79 | $11.17 | $35.96 |
| Professional and related | $50.10 | $22.09 | $72.19 |
| Management, business and financial | $58.51 | $28.09 | $86.61 |

Small published rounding differences can occur in component sums. The total is authoritative; do not apply another generic benefits multiplier. These U.S. averages are valuation assumptions, not observed compensation for recruited people and not global wages. Prefer participants' documented local employer costs when available. Role-specific industry averages and geography will materially change economics.

Where human work has not been observed, a **break-even threshold** is more honest than a fabricated speedup:

Human-minute threshold = 60 × fully allocated system cost / documented hourly human cost.

At the office/admin assumption, hypothetical system costs $5/$10 break even at 8.34/16.69 minutes; at the professional assumption, 4.16/8.31 minutes. These are thresholds, not claimed worker completion times. Actual human review, management and attributable overhead must be included consistently. If system cost is itself unknown, label it a scenario rather than using zero.

## Reporting advice for the paper

Use separate fields for measured execution time, unmetered authoring/model use, hypothetical valuation and observed participant data. Any unknown full-cost component makes fully allocated cost unknown rather than zero. A good deterministic artifact and measured local timings can be reported even if complete monetary cost or the human baseline is absent. Report the empirical human comparison NOT RUN until observed participant records exist.

The five adoption measures should use accepted outputs as denominator. Aggregate all attempted-job costs, including rejection, rescue and abandonment; divide by accepted deliverables. Show marginal and allocated cost separately. Do not treat retained-tool reuse as proof that all whole-product advantage is caused by learning, and do not treat reduced CPU as earned revenue.

## Retrieval limitations retained

A sandboxed direct Python request for public ILO/World Bank bulk files returned `Operation not permitted`; no network escalation was requested. Search-service opens of the ILO bulk contents URL and World Bank JSON endpoint failed. Therefore no claim of a completed country-by-country aggregation or raw API export is made. The quoted numerical facts come from authoritative public pages, with stable archived BLS data and explicit retrieval dates.
