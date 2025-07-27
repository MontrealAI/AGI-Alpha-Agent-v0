"""Compatibility wrapper for the ``openai_agents`` import path."""
from agents import *  # noqa: F401,F403
from agents import __all__ as _agents_all
from agents import __version__

# Older SDKs expose ``OpenAIAgent``. Map it to ``Agent`` when missing.
if 'OpenAIAgent' not in globals() and 'Agent' in globals():
    OpenAIAgent = globals()['Agent']  # type: ignore

__all__ = list(_agents_all)
if 'OpenAIAgent' in globals() and 'OpenAIAgent' not in __all__:
    __all__.append('OpenAIAgent')
