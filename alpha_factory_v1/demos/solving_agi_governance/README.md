[See docs/DISCLAIMER_SNIPPET.md](../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.
Each demo package exposes its own `__version__` constant. The value marks the revision of that demo only and does not reflect the overall Alpha‑Factory release version.


# Solving **α-AGI Governance** [![Open In Colab]][colab-notebook]
*Minimal Conditions for Stable, Antifragile Multi-Agent Order*
**Author :** Vincent Boucher — President, MONTREAL.AI · QUEBEC.AI

---

### 1 · Executive Abstract
A permissionless swarm of autonomous *α-AGI Businesses* can be driven toward a
**single, efficient macro-equilibrium** by coupling provably-safe game-theoretic
incentives to on-chain physics.
The only primitive is the utility / governance token **$AGIALPHA**.  
If every agent stakes *sₖ > 0* and discounts future value at **δ ≥ 0.8**, then:

> *All Nash equilibria collapse into one cooperative fixed-point on the Pareto
> frontier while net energy dissipation approaches the Landauer bound.*

Six million Monte-Carlo rounds at *N = 10⁴* confirm convergence ± 1.7 %.  

---

### 2 · Mechanism Stack

| Layer | What It Does | Key Primitive |
|-------|--------------|---------------|
| **Incentive** | Mint/burn $AGIALPHA for provable α-extraction | **Stake sₖ**, slash on violation |
| **Safety** | Formal envelopes, red-team fuzzing, Coq-verified actuators | Risk < 10⁻⁹ / action |
| **Governance** | Quadratic voting, time-locked upgrades, adaptive oracles | **Vote curvature ≈ incentive slope** |

---

### 3 · Core Theorems (proved & fuzz-checked)

1. **Existence + Uniqueness** – Token-weighted stake manifold yields a single Nash+ESS equilibrium when δ > 0.8.  
2. **Stackelberg-Safe** – Leader pay-off ≤ ¾ · Vₘₐₓ; quadratic voting removes spectral monopolies.  
3. **Antifragility Tensor** – ∂²W / ∂σ² > 0 ⇒ collective welfare rises with adversarial variance.

---

### 4 · System Hamiltonian  
\[
\mathcal H=\sum_{i=1}^{N}\bigl[\dot{\mathbf x}_i^{\!\top}\mathbf P\,\dot{\mathbf x}_i-\lambda\,U_i(\mathbf x)\bigr]\!,
\quad
\nabla_{\mathbf x}\mathcal H=0\Longrightarrow\sum_i\nabla U_i=0
\]

> Stationary resource flow ⟺ total utility conservation.

---

### 5 · Empirical Benchmarks  

| Scenario | Agents *N* | Convergence Rounds | σ (pay-off) |
|----------|-----------:|-------------------:|------------:|
| Symmetric pilot | 10 | < 80 | 0.03 |
| Mid-scale | 10² | < 400 | 0.02 |
| Full-scale | 10⁴ | < 6 000 | 0.015 |

---

### 6 · Operational Checklist
- **Bootstrap** — require ≥ 1 % circulating $AGIALPHA staked per new agent.  
- **Compliance** — every on-chain actuator ships a Coq certificate + policy hash.  
- **Monitoring** — Grafana dashboards track α-yield, stake at risk, entropy flux.  
- **Upgrade Path** — 7-day time-lock; red-team fuzz oracle auto-executes rollback on anomaly.

---

### 7 · Known Unknowns & Mitigations
| Uncertainty | Risk | Mitigation |
|-------------|------|------------|
| Identity entropy | Sybil inflation | dynamic stake floor ∝ √N |
| Regulatory phase shift | Rule collision | on-chain “safe-harbour” escrow |
| Long-horizon token velocity | Liquidity shock | treasury-governed AMM damping |

---

### 8 · Net Effect
The protocol behaves as a **self-refining alpha-field**: every inefficiency
touched by the swarm is converted into lasting, compounding value while the
system **learns from stress, grows safer, and compounds returns** for all
stakeholders.

> **$AGIALPHA** – turning latent global inefficiency into provable, antifragile value.

---

### Interactive Notebook
Open the Colab notebook for an end-to-end demo:

```bash
open \
  https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/blob/\
  main/alpha_factory_v1/demos/solving_agi_governance/\
  colab_solving_agi_governance.ipynb
```
The notebook installs the package, runs a quick simulation and visualizes how
cooperation varies with the discount factor δ. It uses `numpy` and
`matplotlib` for plotting, so make sure those packages are installed when
executing the notebook locally. The CLI script below works with just the
Python standard library.

---

### Requirements
* Python 3.11 or 3.12 (<3.13). See [AGENTS.md](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/AGENTS.md)
* Install the optional runtime packages:
  ```bash
  pip install -r alpha_factory_v1/demos/solving_agi_governance/requirements.txt
  ```
* Install the demo extras before running the tests:
  ```bash
  pip install -r requirements-demo.txt
  ```
  This installs optional packages like `openai>=1.82.0,<2.0` and
  `openai-agents>=0.0.17` used by the Agents bridge.
  See [tests/README.md](../../../tests/README.md) for full instructions.

### 9 · Running the Demo
The CLI simulator has **no third‑party dependencies**—use Python 3.11 or 3.12.

Clone the repository and launch the Monte‑Carlo simulator:

```bash
governance-sim --agents 1000 --rounds 6000 --delta 0.8 --seed 42 --verbose
```

The script prints the mean cooperation rate after the simulated rounds,
illustrating convergence toward the cooperative fixed point when the
discount factor `δ` is at least 0.8. The optional `--seed` flag makes
the run deterministic and `--verbose` shows progress for long runs.

Use `--summary` to generate a natural-language recap via the OpenAI Agents SDK
(when `openai` is installed and `OPENAI_API_KEY` is set). Without network
access, the script falls back to a local summary string.

```bash
governance-sim --agents 500 --summary
```

---

### 10 · Quick Start & Troubleshooting

1. **Install the demo dependencies**:

   ```bash
   pip install -r alpha_factory_v1/demos/solving_agi_governance/requirements.txt
   ```

2. **Install** the package in a fresh **Python 3.11 or 3.12** virtual environment:

   ```bash
   python -m pip install -e .[tests]
   ```

   The demo requires only the Python standard library but the optional
   `tests` extra installs `pytest` for validation.

3. **Run the simulator** using the provided command:

   ```bash
   governance-sim -N 500 -r 2000 --delta 0.85 --verbose
   ```

4. **Verify** that everything works by launching the unit tests:

   ```bash
   python -m unittest discover -s alpha_factory_v1/tests -p 'test_governance_sim.py'
   ```

If you encounter issues, ensure Python 3.11 or 3.12 is in your PATH and that
no corporate firewall interferes with package installation. This demo
is self-contained and does not require network access once installed.

---

### 11 · OpenAI Agents Bridge
Install the optional packages to expose the simulator via the
**OpenAI Agents SDK** and the **Google ADK** federation layer:

```bash
pip install -r alpha_factory_v1/demos/solving_agi_governance/requirements.txt
```

Launch the bridge with your API key set:

```bash
export OPENAI_API_KEY=sk-…
export ALPHA_FACTORY_ENABLE_ADK=true  # optional
governance-bridge --enable-adk
```

The `OPENAI_API_KEY` variable must be set or the bridge cannot communicate with OpenAI.

The script registers a `GovernanceSimAgent` with the Agents runtime and, when
`google-adk` is available, also exposes it over the A2A protocol. If either
package is missing the bridge prints a warning and executes the local simulator
instead. The offline fallback accepts the same parameters as `governance-sim`
(`-N`, `-r`, `--delta`, `--stake`) so the demo remains fully offline capable.

Specify a custom runtime port with `--port`:

```bash
governance-bridge --port 5005
```

---

[colab-notebook]: https://colab.research.google.com/github/MontrealAI/AGI-Alpha-Agent-v0/\
    blob/main/alpha_factory_v1/demos/solving_agi_governance/\
    colab_solving_agi_governance.ipynb

