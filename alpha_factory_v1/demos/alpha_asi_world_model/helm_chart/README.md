[See docs/DISCLAIMER_SNIPPET.md](../../../../docs/DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# α-ASI World-Model 🛰️ — Helm Chart 📦
*Alpha-Factory v1 👁️✨ • Multi-Agent AGENTIC α-AGI*

presence of a real general intelligence. Use at your own risk.

| Chart version | App version | License |
|---------------|------------|---------|
| 0.1.0         | 1.0.0      | MIT     |

> **Purpose** — Deploy the **α-ASI World-Model demo** (POET × MuZero, orchestrated
> by ≥5 cooperative Alpha-Factory agents) to any Kubernetes 1.26+ cluster in
> **one command** while retaining full production-grade knobs for security,
> scaling and cross-industry customisation.

---

## ✨ What gets deployed?

| Kubernetes Object | Description | Why it matters to “Alpha Factory → Alpha Opportunities → Value” |
|-------------------|-------------|-----------------------------------------------------------------|
| **`Deployment/asi-orchestrator`** | Runs the `alpha_asi_world_model_demo.py` process. | Central brain that *generates environments* & *trains agents* → raw discovery of 🌟 alpha signals. |
| **`Service/asi-ui`** *(ClusterIP or LoadBalancer)* | Exposes REST + WebSocket API (`/agents`, `/command`, `/ws`). | Lets non-technical users *watch*, *steer* and *harvest* value in real time. |
| **`ConfigMap/asi-config`** | Injects runtime config (`ALPHA_ASI_*`, ultra-safe defaults). | Rapid cross-industry retargeting without images rebuilds. |
| **`Secret/asi-api-keys`** | (Optional) `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. | Seamless toggle between *offline-only* and *LLM-augmented* operation. |
| **`PodDisruptionBudget/asi-core`** | Prevents accidental 0-replica situations. | Maintains continuous alpha extraction 📈 under node-drain chaos. |
| **`HorizontalPodAutoscaler/asi-orchestrator`** | *(disabled by default)* | Proof-point that the demo is *cloud-native & antifragile*: auto-scale on CPU/GPU load spikes. |

### Agent roles baked into the container 👥 

| Agent topic (class) | Helm relevance | Cross-industry usefulness |
|---------------------|----------------|---------------------------|
| `planning_agent` | Reads `GOAL_*` envs from **values.yaml** → seeds high-level objectives. | Aligns curricula to any sector (finance, health, aero…). |
| `research_agent` | Can be wired to an external vector-DB via secret refs. | Streams domain knowledge to learner → faster alpha capture. |
| `strategy_agent` | Emits “pivot” messages if KPI rules in **values.yaml** trigger. | Auto-switch between opportunity classes (e.g. cost-saving vs. revenue). |
| `market_agent` | Optional Kafka side-car example in `extras/`. | Feeds live market ticks; learner treats them as novel envs. |
| `safety_agent` | Always ON, no config needed. | Halts pods on NaNs / runaway rewards → regulatory guard-rail. |

*(Stubbed when missing, so the chart stays green even on minimal clusters.)*

---

## 🚀 Quick start

```bash
# 1 — Add the repo (if you publish it) or use local path
helm install alpha-asi-demo ./helm_chart   --create-namespace --namespace alpha-factory

# 2 — Port-forward the UI if you’re on a private cluster
kubectl -n alpha-factory port-forward svc/asi-ui 7860:80

# 3 — Open the dashboard
xdg-open http://localhost:7860      # or just paste in browser
```

> 🛡️ **No cloud keys?** That’s fine—LLM helpers stay stubbed and the app runs
> fully offline.

---

## 🔧 Key values (`values.yaml`)

| Path | Default | Meaning |
|------|---------|---------|
| `image.repository` | `alpha_asi_world_model` | Override if you push to ECR/GCR/ACR etc. |
| `image.tag` | `latest` | Pin to a digest for prod. |
| `service.type` | `ClusterIP` | Switch to `LoadBalancer` or `Ingress` for public clouds. |
| `resources.requests.cpu` | `250m` | Tweak for on-prem GPU nodes (see docs). |
| `env.ALPHA_ASI_MAX_STEPS` | `100000` | Faster demo? Set to `20000`. |
| `enableADK` | `false` | Set to `true` to expose the Google ADK gateway. |
| `secretKeys.openai` | *(unset)* | Will be mounted to `OPENAI_API_KEY`. |

```yaml
# — example mini-override —
env:
  GOAL_PRIMARY: "optimise_supply_chain_CO2"
  ALPHA_ASI_MAX_STEPS: "75000"
secretKeys:
  openai: "OPENAI_API_KEY"        # key name in Kubernetes secret
```

Create the secret:

```bash
kubectl -n alpha-factory create secret generic asi-api-keys   --from-literal=OPENAI_API_KEY="sk-••••"
```

---

## 🔒 Security notes & best practices

| Issue | Chart mitigation |
|-------|------------------|
| **Outbound traffic control** | `securityContext.capabilities.drop: ALL` + no default egress; user must opt-in via `networkPolicy.enabled`. |
| **LLM prompt-injection** | `safety_agent` filters outgoing tool invocations; helm value `env.LLM_REDTEAM=1` enables extra adversarial replay tests. |
| **Resource runaway** | Default limits (`cpu=1`, `memory=1Gi`) + **HPA** guard. |
| **Data compliance** | Enable `persistence.enabled` to back models with PVCs located in compliant storage zones. |

---

## 🛠️ Extending the chart

* **Multiple learners** — set `replicaCount` > 1 and `env.LEARNER_ID=$(POD_NAME)`; the orchestrator auto-detects peers via the service DNS.
* **Pluggable env-generators** — mount a ConfigMap with your Python module under
  `/app/plugins/`, append `PYTHONPATH` in `extraEnv`.
* **Side-car vector DB** — uncomment the stub in `templates/vector db.yaml` for instant hybrid-search memory.

---

## 📝 Change log

| Version | Date (UTC) | Notes |
|---------|------------|-------|
| **0.1.0** | 2025-04-25 | First GA release 🎉 – matches repository tag `v1.0.0`. |

---

## ❤️ Credits

Built with  
**Alpha-Factory v1 👁️✨** • OpenAI Agents SDK • Google ADK • Agent2Agent • MCP •
Helm ❤️.  

> *“Outlearn. Outthink. Outdesign. Outstrategize. Outexecute.”*  

Enjoy deploying super-intelligence responsibly 🚀
