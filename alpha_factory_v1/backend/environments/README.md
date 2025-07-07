[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

# Backend Environments

Compact demo environments used by Alpha‑Factory v1.  Each implements a minimal gym‑like API with `reset()`, `step()` and `legal_actions()`.

## GridWorldEnv
A lightweight 9×9 maze.  The agent starts at `S` and aims for `G`.

```
from backend.environments.alpha_labyrinth import GridWorldEnv
env = GridWorldEnv()
state = env.reset()
state, reward, done = env.step("UP")
```

## MarketEnv
Stochastic price simulator with a one‑asset inventory.  Supports `BUY`, `SELL` and `HOLD` actions.

```
from backend.environments.market_sim import MarketEnv
market = MarketEnv()
price = market.reset()
price, reward, done = market.step("BUY")
```
