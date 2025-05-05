from importlib import import_module
import asyncio

AGENT_NAMES = ["finance"]      # add more Alpha-Factory agents here

def make_forward_fn(agent_name: str):
    agent_cls = import_module(f"backend.agents.{agent_name}_agent").Agent
    async def forward(task_json: dict) -> str:
        agent = agent_cls()
        return await agent.run_cycle(task_json)
    return forward
