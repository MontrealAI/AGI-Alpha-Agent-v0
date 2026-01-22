[See docs/DISCLAIMER_SNIPPET.md](../../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

```mermaid
%% ───────────────────────────  PANE A  ───────────────────────────
%% Royalty Radar 👁️✨ – Meta-Agentic Inner Loop
flowchart LR
  subgraph meta["RoyaltyRadar.alpha.agi.eth  (meta-agent)"]
    ORCH["Coordinator Ω"]:::meta
    ORCH -->|spawn| DM["DataMinerAgent<br/>(DSP adapters)"]:::agent
    ORCH -->|spawn| CL["ClaimAgent<br/>(Bayes + LLM)"]:::agent
    ORCH -->|score + evolve| DM
    ORCH -->|score + evolve| CL
  end

  DM  -- public counts --> STORE["Lineage & Audit"]:::store
  CL  -- gap + letter + tx-hash --> STORE
  CL  -- € payout (on-chain) --> WALLET["Artist Wallet"]:::val

%% ───────────────────────────  PANE B  ───────────────────────────
%% How the Business plugs into the α-AGI Marketplace
  subgraph market["α-AGI Marketplace 🎪"]
    CLIENT["Artist / Label"]:::user
    CLIENT -- post&nbsp;job + stake $AGIALPHA --> ESCROW["Escrow ▶"]:::val
    ESCROW --> MATCH["Match Engine"]:::proc
    MATCH  --> BIZ["RoyaltyRadar.alpha.agi.eth"]:::meta
    BIZ    -- proofs&nbsp;✔ --> VALID["Validator Swarm"]:::store
    VALID  -- release ▶ --> ESCROW
    ESCROW -- 💎 $AGIALPHA --> BIZ
  end

%% Styling
classDef meta   fill:#6425ff,color:#ffffff,stroke-width:0;
classDef agent  fill:#0f9d58,color:#ffffff,stroke-width:0;
classDef store  fill:#2b2b40,color:#ffffff,stroke-width:0;
classDef val    fill:#1e88e5,color:#ffffff,stroke-width:0;
classDef proc   fill:#ff6d00,color:#ffffff,stroke-width:0;
classDef user   fill:#fbbc05,color:#000000,stroke-width:0;
```

```mermaid
flowchart TD
  %% α-AGI Marketplace
  subgraph marketplace["α-AGI Marketplace  🎪"]
    client["Artist / Label  🟡"]
    escrow["Escrow  🔵"]
    match["Match Engine  🟧"]
    rr[RoyaltyRadar.alpha.agi.eth  🟣]
    vs["Validator Swarm  ⬛"]
    client -- "post job + stake $AGIALPHA" --> escrow
    escrow --> match
    match --> rr
    rr -- "proofs ✔" --> vs
    vs -- "✓ $AGIALPHA" --> escrow
    escrow -- "release ▶" --> client
  end

  %% RoyaltyRadar internal
  subgraph rr_box["RoyaltyRadar.alpha.agi.eth  (meta-agent)"]
    orch["Coordinator Ω  🟪"]
    dm["DataMinerAgent  🟩"]
    cl["ClaimAgent  🟩"]
    orch -->|spawn| dm & cl
    orch -->|score + evolve| dm & cl
    dm -->|public counts| lin["Lineage & Audit  ⬛"]
    cl -->|gap + letter + tx-hash| lin
    cl -- "€ payout on-chain" --> wallet["Artist Wallet  🔵"]
  end

  classDef default stroke-width:0,color:#fff
  class client,escrow,match,rr,vs,orch,dm,cl,lin,wallet default
```

```mermaid
flowchart LR
    subgraph "α-AGI Business  (<name>.alpha.agi.eth)"
        META["Meta-Programmer Ω"]:::meta
        subgraph "Agent Swarm"
            FIN["finance.agent"]:::agent
            BIO["biotech.agent"]:::agent
            SUP["supply.agent"]:::agent
        end
        META -- spawns/retires --> FIN & BIO & SUP
        FIN -- proofs --> VAL
        BIO -- proofs --> VAL
        SUP -- proofs --> VAL
    end
    JOBS["α-Job Queue  🎯"] --> FIN & BIO & SUP
    VAL["Validator Swarm ⬛"] --> ESC["Escrow 🔵"]
    ESC -- payout ($AGIALPHA) --> TREAS["Treasury 💎"]

    classDef meta fill:#6425ff,color:#fff,stroke-width:0
    classDef agent fill:#0f9d58,color:#fff,stroke-width:0
    classDef default stroke-width:0,color:#fff
```
