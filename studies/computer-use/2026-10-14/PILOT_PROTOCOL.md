[Project notice](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md)

# Real-user pilot: measure before claiming

Protocol v1 • 14 October 2026 • NOT STARTED • Zero participants observed

This is a prospective protocol, not a report of human results. The published engineering study used a simulated owner. Neither a successful script nor a public comment establishes an observed human outcome. Freeze the exact protocol, build and task-pack commits before the first participant; record later amendments without rewriting earlier versions.

## Two separate questions

**Pilot U — usability of the released examples and recovery.** Can a likely nontechnical user obtain a correct estimate, save it, recover a draft and complete a different task with less repeated setup? This tests the examples, not autonomous software generation by AGI Alpha.

**Pilot E — usefulness of AGI Alpha doing the work.** Can the released repository, a genuinely connected executor and real model produce an accepted artifact and help on a fresh task? Do not start E until a maintainer has pinned and qualified that actual runtime end to end. Record model identifier, provider, tools, permissions, limits, actual usage and total costs. The existing isolated-browser adapter is not silently widened into a shell or desktop executor.

Pilot U cannot be relabeled as evidence for E. Neither pilot, alone, establishes general autonomy or benchmark leadership.

## Before recruitment

Name a facilitator, an artifact reviewer who did not produce the evaluated work, and a private data custodian. Resolve consent, secure collection, retention, withdrawal and access before asking anyone to submit observations. Do not solicit names, email addresses, credentials, workplace files or recordings in a public GitHub issue. Public comments are for nonsensitive questions only. No payment or compensation is promised by this protocol.

Use synthetic or properly licensed nonpersonal tasks. Obtain permission separately for recording and for any quotation or identifiable publication. A participant may stop without explanation. Do not record their other tabs or applications. Maintain the consent/contact mapping separately from measurements; public results contain aggregates, not the mapping. Proposed retention is 90 days after analysis, subject to the custodian's approved policy and participant agreement. This checklist is not legal advice or a declaration of regulatory compliance.

Check real HTTPS, the downloaded kit, supported browsers, zoom, keyboard operation, screen-reader interaction where relevant, recovery refusals and every task's expected answer. An administrative file-access restriction must be reported, not bypassed. Test-only --no-sandbox browser flags do not qualify production isolation.

## Participants and allocation

Use twelve adults from the intended nontechnical audience for a formative pilot. This is a practical pilot size, not a statistical power calculation or a representative sample. Record recruitment channel, relevant experience, accessibility needs and exclusions privately. Report eligible, started, completed, withdrew and excluded counts with reasons; do not turn twelve invited people into twelve completed observations.

Give every participant the same neutral orientation and a separate practice task. Before collection, allocate participants evenly across four sequences: A/no-profile then B/profile; B/profile then A/no-profile; A/profile then B/no-profile; B/no-profile then A/profile. Generate the allocation before sessions and preserve it privately. Task order, practice and carryover cannot be erased; retain per-sequence results and describe the limitation.

Use the same finished application and equivalent evidence/review duties in both U conditions. No-profile users must not be artificially deprived of normal browser affordances. Record the cost of creating the reusable profile separately, including its first-use cost. Do not count a stored approval as a saved preference. For E, match model, tool access, budget, task specification and acceptance rubric; retained knowledge is the treatment, not extra tools or a stronger model.

## Neutral session guide

Explain that the product is being tested, not the participant. Read the same task instructions without identifying buttons or giving expected answers. Ask the participant to obtain and retain an estimate for the assigned synthetic workshop request. Then ask them to close the example, reopen it, restore the saved draft and review a new result. Finally assign the matched follow-on task. Do not use a production customer system or manufacture an external transaction to test recovery.

Observe without coaching. Record each request for help and exactly what help was given. Mark a task assisted once assistance occurs. Stop at 20 active minutes per task or at an unsafe action; record incomplete outcomes rather than discarding them. Think-aloud commentary is optional and must be applied consistently or analyzed separately because it can affect time.

Keep an unseen reviewer rubric outside the participant material. The reviewer checks exact amounts, discount/rounding, capacity, language, saved artifact, successful recovery, fresh review and absence of prohibited effects. Record pass, fail or not assessed for each item. A model's completion statement or a checked UI box is not customer acceptance.

## Measurements

Use monotonic timestamps and explicit pause/resume marks. Measure active participant time, wall-clock time, system wait, interruptions, assistance, corrections, review time, mistaken approvals, recovery attempts, accepted artifacts and whether the participant can explain what was saved. Do not replace these measurements with automated event duration. Record separately any manual transcription and observer uncertainty.

For E also record provider request/usage receipts, inference cost, execution cost, storage, reviewer labor and failed attempts. Unknown costs stay null, not zero. Keep actual commercial payment and willingness-to-pay questions separate from simulated task usefulness.

The blank `pilot/session-template.csv` is an observation schema, not test data. Keep completed records private until a privacy and quality review permits a de-identified export. Never populate this template with synthetic people to obtain a sample size.

## Analysis plan

Report paired differences in active effort only for matched accepted-quality tasks, alongside all incomplete/assisted cases. Also report the full attempted-task denominator so a fast failure cannot look like productivity. Publish medians, individual paired anonymous differences when safe, range/interquartile range, and uncertainty appropriate to the small sample. Do not claim a causal population effect from twelve formative sessions. Show task/order strata and retain null or negative transfer.

Report profile creation cost and the number of later tasks needed to recover that cost under observed, not invented, savings. Evaluate false approvals separately from task success. Do not improve the result by removing review or authority checks.

Suggested progression criteria: at least 11 of 12 participants completing the core journey unaided, no critical incorrect approvals, and at least 20% median matched-task active-effort reduction at equal or better accepted quality. These are proposed decision thresholds, not achieved results, universal standards or a guarantee. Failure to meet them is a result to publish and investigate.

## Publication gate

`pilot/status.json` remains NOT_STARTED, participantsObserved = 0, results = null until actual sessions occur. After collection, publish a dated report with the protocol/build/task/model identifiers, denominators, measurement definitions, help and failure records, cost accounting, reviewer role/conflicts, privacy review and limitations. Do not edit the historical simulated results into human results. Self-reported community feedback remains a separate category.

Publish a customer case only after genuine artifact acceptance and explicit permission. State whether the work was paid, subsidized or a demonstration. No revenue, saved labor or customer testimonial exists merely because this protocol is public.

## Method references

The protocol adapts the GOV.UK Service Manual's guidance on moderated usability testing: recruit likely users, use realistic neutral tasks, obtain informed consent, observe actual behavior and record assistance consistently. It does not imply GOV.UK endorsement.

https://www.gov.uk/service-manual/user-research/using-moderated-usability-testing
