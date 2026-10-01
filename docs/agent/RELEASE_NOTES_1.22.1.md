[Project notice](../DISCLAIMER_SNIPPET.md)

# 1.22.1 — Sovereign session cleanup

Locking the local Sovereign console now clears imported drafts, unsaved review notes, hidden result
text and displayed metrics. It restores the public balanced example and focuses the access-code field.
Saved mandates remain in the signed journal and can be reopened after unlocking. Download a draft
before locking if you want to keep it.

Pending unlocks can be canceled with **Lock this tab**. Delayed unlock responses, clipboard responses
and file reads cannot change the next session. Mandate downloads require an unlocked, idle console.
Actual Chromium regressions cover private form cleanup, retained mandates, a rejected old unlock
arriving after a successful new unlock, and a file read completing after locking and re-unlocking.

This patch changes browser session behavior; it does not change journal or signed-packet formats.
The original source, media, presentations and flowcharts remain preserved. Existing sample packet
signatures and their public fixture identities are unchanged.

The supported profile remains private, single-operator planning. Locking clears this page's working
state; it is not token rotation, worker cancellation or guaranteed erasure from browser process memory.
Local review remains distinct from independent validators, ENS identity and on-chain settlement.

Use the [Sovereign guide](../demos/sovereign_agentic_agialpha_agent_v0.md) for the complete workflow,
or [start here](START_HERE.md) for installation and operator procedures. Keep a verified private backup
and install the matching release in a fresh environment before restoring existing state.
