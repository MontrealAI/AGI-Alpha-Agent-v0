[Project notice](../DISCLAIMER_SNIPPET.md)

# Experience Lab — operating guide

**Release 1.16.0.** [Open the lab](../era_of_experience/index.html) or start it locally:

```bash
python -m alpha_factory_v1.demos.era_of_experience --serve
```

Visit http://127.0.0.1:7860/era_of_experience/. The supported lab needs Python 3.11–3.13 and the
packaged assets; it does not call providers or require an SDK, GPU or Docker service.
The installed console command is `experience-lab`.

Start with **Build routing**, inspect the action and outcome trace, and change one setting.
Select **Run experiment** to refresh results. Try **The reward trap** next: a profitable-looking
proxy must fail the independently measured safety gate. The active policy remains the baseline.

Native execution and portable replay:

```bash
python -m alpha_factory_v1.demos.era_of_experience --case build-routing --output experience-runs
python -m alpha_factory_v1.demos.era_of_experience --verify experience-runs/<run-sha256>/run.json
```

Replace `<run-sha256>` with the directory printed by the first command. Each directory contains
`scenario.json`, `run.json`, `policy-proposal.json`, `jobs.json`, `review.md` and `SHA256SUMS`.
Importing a run recomputes every episode, policy and gate; changing a result and updating its hash
cannot pass verification. Browser and native bundles use identical bytes.

The learner is an epsilon-greedy contextual bandit. Only selected-action outcomes enter bounded
per-context/action memory. Two separate frozen-policy suites test held-out performance and original
environment retention using paired random draws. Gates require sufficient reward gain, low incident
rate, adequate success, acceptable cost, retained observation coverage and limited retention loss.
One synthetic seed is a demonstration, not a generalization guarantee. Reusing evaluation to tune
settings needs a fresh independent test afterward.

The exported $AGIALPHA job requests independent reproduction and a review decision; it is not
submitted or funded. Use the [Ascension guide](ASCENSION_PROTOCOL.md) for validator identity,
Sovereign execution, marketplace settlement and the 1% payout burn. Passing local gates does not
authorize deployment, mint a Nova-Seed, authenticate a validator or certify compliance.

The [complete demo guide](../demos/era_of_experience.md) explains the
schemas, exact arithmetic, bounds, seed streams, troubleshooting and preserved integrations.
The [research archive](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/alpha_factory_v1/demos/era_of_experience/RESEARCH_ARCHIVE.md) retains
all original diagrams and narrative. The former Docker/SDK path remains explicit `--legacy`
research functionality; its live collector and MCTS claims are not the supported lab's behavior.
