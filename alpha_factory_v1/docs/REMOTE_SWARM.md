[See docs/DISCLAIMER_SNIPPET.md](../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Remote Swarm Quick‑start

## 1. Build & push image
docker build -t ghcr.io/montrealai/alpha-factory:v2remote .
docker push ghcr.io/montrealai/alpha-factory:v2remote
cosign verify ghcr.io/montrealai/alpha-factory:v2remote

## 2. Helm install on any cluster
helm upgrade --install af-remote ./helm/alpha-factory-remote \
  --set image.repository=ghcr.io/montrealai/alpha-factory \
  --set image.tag=v2remote \
  --set env.OPENAI_API_KEY=$OPENAI_API_KEY

Pods expose :8000 for A2A RPC.

## 3. Tell Planner about remote hosts
export ALPHA_REMOTE_HOSTS="10.0.1.23:8000,10.0.2.17:8000"
# PlannerAgent will round‑robin send_task() to these hosts.

