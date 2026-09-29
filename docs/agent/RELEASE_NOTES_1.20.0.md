[See docs/DISCLAIMER_SNIPPET.md](../DISCLAIMER_SNIPPET.md)

# 1.20.0 — Evidence & Planning Lab

The `muzeromctsllmagent_v0` demo now runs an actual evidence-to-planning experiment.
The previous installer generated placeholder retrieval, ignored language-model
output and assigned random MCTS scores without expanding a search tree. It also
wrote generated files into the caller's directory.

The maintained path retrieves source-linked MiniChoice task facts, optionally
requests structured advice from a local Ollama model, validates actions and exact
source quotations, trains the shared MuZero neural model, and compares proposals
with actual search and simulator transitions. Reports preserve source hashes,
configuration, versions, training losses, four measured baselines, search visits,
candidate action traces and portable neural weights. Model failures are explicit;
no synthetic fallback is passed off as inference.

The local dashboard provides progress, cancellation, evidence, comparisons and a
copyable JSON record. The finite CLI refuses output overwrites. The launcher uses
a dedicated environment and the shared hash-locked Linux CPU dependencies. No
credentials, model downloads, external execution or wallet access are required.

The original installer and research are retained in an inert archive with a
source-commit and hash manifest. Original imagery and presentations remain.
Embedded RPC credentials were redacted from retained copies; credentials in old
Git history are not thereby rotated. The historical browser balance check is
explicitly identified as unsuitable for authentication or authorization.

Behavioral tests cover retrieval, exact quotations, malformed and oversized
responses, provider errors, real learning, counterfactual outcomes and output
preservation. The mandatory MuZero release matrix includes the integration on
Python 3.11–3.13, and browser acceptance runs real training with external requests
blocked. The optional provider contract is tested with HTTP fixtures; this is
not a quality certification of arbitrary local language models.

This remains an educational two-step simulation. It does not implement the
broader autonomous-enterprise, token-settlement or validator-network vision,
and does not claim AGI or production financial readiness.

[Setup and use the lab](../demos/muzeromctsllmagent_v0.md).

Use [Start here](START_HERE.md) for the main agent installation and supported
operator workflow.
