# Condition U task assignment messages

The following messages are transcribed verbatim from the available conversation context. They are the parent agent's task assignments for rounds A and B, excluding system and developer instructions.

## Round A

```text
You are completing a bounded research audit job, condition U. Working directory /workspace/scratch/dc74b0c283d5/workflow_trials/U. Please audit all 12 tasks in packet_a.json using catalog.json, PROTOCOL.md and SCOPE.md. Deliver reports_a.json as JSON array of the 12 required report objects in task order. You may use Python, other tools, your own scripts and verification as useful. Apply the complete supplied contract and keep outputs correct; a negative source screen can be a correct report. Do not assert actual ecology or customers. Time cap is 480 seconds from this instruction; aim to finish sooner. Record UTC start/end, elapsed seconds, tool calls you made, retries/corrections and limitations in receipt_a.json. Missing provider/token billing must remain unknown. Restrict reads/writes for the experiment to your own directory and standard installed libraries; do not inspect other arms, study code, reference oracle, protected answers or existing results. No outside search is required: the supplied source-screen facts and definitions govern this finite task. You can retain any self-created script for a subsequent fresh job. Do not contact anyone, buy anything or save intermediate files externally. Final response: brief completion path and elapsed only; do not ask questions.
```

## Round B

```text
Fresh second job B is now in your same directory as packet_b.json. Its habitat, provenance and host-purpose differ; recheck meaning. No score or correction feedback from A is supplied. Preserve reports_a.json/receipt_a.json unchanged. Apply the same contract, tools, condition U and 480-second cap from this instruction. You may reuse your own A scripts and working knowledge. Write reports_b.json array of 12 report objects in B task order and receipt_b.json with UTC times, elapsed, calls/retries/corrections and unknown billing. Read only own directory/installed libraries, no external answers/results. Final brief paths and elapsed.
```
