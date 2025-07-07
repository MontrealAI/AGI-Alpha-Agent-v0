[See docs/DISCLAIMER_SNIPPET.md](../../../DISCLAIMER_SNIPPET.md)
This repository is a conceptual research prototype. References to "AGI" and "superintelligence" describe aspirational goals and do not indicate the presence of a real general intelligence. Use at your own risk. Nothing herein constitutes financial advice. MontrealAI and the maintainers accept no liability for losses incurred from using this software.

```mermaid
flowchart TD
    Insight["🎖️ α‑AGI Insight 👁️✨"]
    Seeds["🌱💫 α-AGI Nova-Seeds 🔐"]
    Mark["α-AGI MARK 🔮🌌✨"]
    Sovereign["🎖️ α‑AGI Sovereign 👑✨"]
    Biz["🌸 α‑AGI Business 👁️✨"]
    Market["🪐 Marketplace 👁️✨"]
    Jobs["📜 α‑AGI Jobs 👁️✨"]
    Agents["👾👾👾🌌👾👾👾 α‑AGI Agents 👁️✨"]
    Reservoir["💎 α‑AGI Value Reservoir"]
    Architect["🎖️ α‑AGI Architect 🔱✨"]
    Council["🔐 α‑AGI Council 👁️✨"]
    Nodes["🖥️ α‑AGI Nodes 👁️✨"]

    Insight --> Seeds --> Mark --> Sovereign
    Sovereign --> Biz --> Market
    Market -->|spawn| Jobs --> Agents
    Agents -- success --> Reservoir
    Jobs -- ΔΣUSD --> Reservoir
    Reservoir -. reinvest .-> Seeds
    Reservoir -. fund .-> Market
    Agents <---> Nodes
    Architect <--> Sovereign
    Architect <--> Insight
    Council --> Sovereign
```

```mermaid
flowchart LR
    SeedMint["Nova-Seed NFT\n(Merkle-proof metadata)"] --> Curve
    subgraph MARK Bonding Curve
        Curve --- BuyFlow[$AGI / USDC → SeedShare]
        Curve --- SellFlow[SeedShare → $AGI / USDC]
    end
    Curve -->|Target Met + Validators 90 %| Permit[LaunchPermit NFT]
    Permit --> SovereignDAO["👑 Sovereign DAO\n(initial treasury escrowed)"]
```


```mermaid
flowchart LR
    JobSpec{{α-Job}}
    Agent(α-AGI Agent)
    Node[(Compute Node)]
    JobSpec -- escrow \$AGIALPHA --> Agent
    Agent -- code & data --> Node
    Node -- result + attest --> Agent
    Agent -- proof --> JobSpec
```




```mermaid
flowchart TD
    subgraph Strategic Layer
        Insight["α‑AGI Insight 👁️✨"] -- KG queries / updates --> KG[(Knowledge Graph)]
        KG -- snapshot hash & context --> Seeds["🌱💫 α-AGI Nova-Seeds"]
        Architect <-- telemetry & model weights --> KG
    end
    style KG fill:#1e293b,color:#fff,stroke:#4ade80
```

```mermaid
flowchart TD
    %% ───────────  CORE VALUE‑CREATION SPINE  ───────────
    Insight["👁️ α‑AGI Insight"]
    Seeds["🌱 Nova‑Seeds"]
    MARK["🔮 MARK"]
    Sovereign["👑 α‑AGI Sovereign"]
    Market["🛒 α‑AGI Marketplace"]
    Exec["⚙️ Jobs & Agents"]
    Vault["💎 Infinite Value Reservoir"]

    Insight --> Seeds
    Seeds  --> MARK
    MARK   --> Sovereign
    Sovereign --> Market
    Market --> Exec
    Exec   --> Vault

    %% ───────────  FEEDBACK VORTICES  ───────────
    Vault  -. "reinvests capital" .-> Market
    Vault  -. "funds exploration" .-> Seeds

    Architect["🛠️ Architect"]
    Architect -. "model tuning" .-> Insight
    Architect -. "policy hot‑swap" .-> Sovereign

    %% ───────────  GOVERNANCE & COMPUTE  ───────────
    Council["⚖️ Validator Council"]
    Council -. "audits" .-> Vault
    Council -. "governs" .-> Sovereign

    Nodes["🖥️ Compute Nodes"]
    Exec  -. "compute spend" .-> Nodes

    %% ───────────  STYLING  ───────────
    classDef core   fill:#0f172a,color:#ffffff,stroke-width:0px
    classDef accent fill:#4f46e5,color:#ffffff,stroke-width:0px
    classDef gold   fill:#fbbf24,color:#000000,font-weight:bold,stroke-width:0px

    class Insight,Seeds,MARK,Sovereign,Market,Exec core
    class Vault gold
    class Architect,Council,Nodes accent
```




```mermaid
flowchart TD
    %% ── STRATEGIC LAYER ──────────────────────────────────────────────
    subgraph "🌌 Strategic Foresight Loop"
        Insight["👁️✨ α‑AGI Insight"] -- "semantic / causal queries" --> KG[(🔗💎 Decision‑Relevant\nKnowledge Graph)]
        DefIngest["📡 Ingestion Bots"] -- "real‑time edges\n+ provenance" --> KG
        KG -- "snapshot CID 📜\n+ trust score" --> Seeds["🌱💫 α‑AGI Nova‑Seeds"]
        Validator["🛡️ Validator Agents"] -- "path‑proof audits" --- KG
        Architect["⚙️🧠 α‑AGI Architect"] <-. "telemetry ∆, model weights" .-> KG
    end

    %% ── VISUAL STYLES ────────────────────────────────────────────────
    classDef dark   fill:#0f172a,color:#ffffff,stroke-width:0px;
    classDef neon   fill:#1e293b,color:#ffffff,stroke:#4ade80,stroke-width:2px;
    classDef seed   fill:#166534,color:#ffffff,stroke-width:0px;
    classDef blue   fill:#0e7490,color:#ffffff,stroke-width:0px;
    classDef violet fill:#7c3aed,color:#ffffff,stroke-width:0px;
    classDef amber  fill:#b45309,color:#ffffff,stroke-width:0px;

    class Insight dark
    class KG neon
    class Seeds seed
    class DefIngest blue
    class Validator violet
    class Architect amber
```

```mermaid
flowchart TD
    %% ── STRATEGIC LAYER ──────────────────────────────────────────────
    subgraph "🌌 Strategic Foresight Loop"
        Insight["👁️✨ α‑AGI Insight"] -- "semantic / causal queries" --> KG[(🔗💎 Decision‑Relevant\nKnowledge Graph)]
        DefIngest["📡 Ingestion Bots"] -- "real‑time edges\n+ provenance" --> KG
        KG -- "snapshot CID 📜\n+ trust score" --> Seeds["🌱💫 α‑AGI Nova‑Seeds"]
        Validator["🛡️ Validator Agents"] -- "path‑proof audits" --- KG
        Architect["⚙️🧠 α‑AGI Architect"] <-. "telemetry ∆, model weights" .-> KG
    end

    %% ── VISUAL STYLES ────────────────────────────────────────────────
    classDef dark   fill:#0f172a,color:#ffffff,stroke-width:0px;
    classDef neon   fill:#1e293b,color:#ffffff,stroke:#4ade80,stroke-width:2px;
    classDef seed   fill:#166534,color:#ffffff,stroke-width:0px;
    classDef blue   fill:#0e7490,color:#ffffff,stroke-width:0px;
    classDef violet fill:#7c3aed,color:#ffffff,stroke-width:0px;
    classDef amber  fill:#b45309,color:#ffffff,stroke-width:0px;

    class Insight dark
    class KG neon
    class Seeds seed
    class DefIngest blue
    class Validator violet
    class Architect amber
```

```mermaid
flowchart TD
    %% ────────────── STRATEGIC LAYER ──────────────
    subgraph "🌌 Strategic Foresight Loop"
        Insight["👁️✨ α‑AGI Insight"] -- "semantic / causal queries" --> KG[(🔗💎 Decision‑Relevant\nKnowledge Graph)]
        IngestBot["📡 Data Ingestion Bots"] -- "real‑time edges\n+ provenance" --> KG
        KG -- "snapshot hash\n+ context" --> Seeds["🌱💫 α‑AGI Nova-Seeds"]
        Validator["🛡️ Validator Agents"] -- "audit\nKG sub-graph" --> KG
        Architect["⚙️🧠 α‑AGI Architect"] <-. "telemetry / model updates" .-> KG
    end

    %% ────────────── VISUAL STYLES ──────────────
    classDef dark   fill:#0f172a,color:#ffffff,stroke-width:0px
    classDef neon   fill:#1e293b,color:#ffffff,stroke:#4ade80,stroke-width:2px
    classDef seed   fill:#166534,color:#ffffff,stroke-width:0px
    classDef blue   fill:#0e7490,color:#ffffff,stroke-width:0px
    classDef violet fill:#7c3aed,color:#ffffff,stroke-width:0px
    classDef amber  fill:#d97706,color:#ffffff,stroke-width:0px

    class Insight dark
    class KG neon
    class IngestBot blue
    class Seeds seed
    class Validator violet
    class Architect amber
```







```mermaid
%% α-AGI Insight • Parts 11-35 • High-Level System Graph
%% Palette — C-A:red; C-B:orange; C-C:gold; C-D:yellowgreen; C-E:cyan; 
%% C-F:cornflowerblue; C-G:violet; C-H:mediumpurple; C-I:magenta

flowchart TD
  %% ❖  Darwinian Search (C-A)
  subgraph C-A[Darwinian Search 💡]
    style C-A fill:#ffdddd,stroke:#ff5544,stroke-width:2px
    P11["11 Darwin-Archive\nEngine"]
    P12["12 Evolution\nRun Simulator"]
    P13["13 Recursive\nEvaluator Evolution"]
    P11 --> P12 --> P13
  end
  
  %% ❖  Semantic / Temporal Topology (C-B)
  subgraph C-B[Semantic-Temporal Topology 🌐]
    style C-B fill:#ffebcc,stroke:#ff9944,stroke-width:2px
    P14["14 Self-Gen\nTaxonomies"]
    P15["15 Horizon-Adaptive\nMutation"]
    P16["16 Semantic Terrain\n+ Auto-Curriculum"]
  end
  
  %% ❖  Reflexive Evaluation (C-C)
  subgraph C-C[Reflexive Evaluation 🔍]
    style C-C fill:#fff8d6,stroke:#d4a017,stroke-width:2px
    P17["17 Memory-Aug Oracles"]
    P18["18 Meta-Generative\nReplay"]
    P19["19 Discourse Arena\n(MARDA)"]
  end
  
  %% ❖  Memetic Strategy (C-D)
  subgraph C-D[Memetic Strategy 🧬]
    style C-D fill:#d8f6d6,stroke:#66bb66,stroke-width:2px
    P20["20 Meta-Memetic\nEmergence"]
    P21["21 Frontier Entropy\nOptimiser"]
  end
  
  %% ❖  Crypto / Privacy (C-E)
  subgraph C-E[Zero-Knowledge Trust 🔐]
    style C-E fill:#d6ffff,stroke:#00bcbc,stroke-width:2px
    P22["22 ZK Proofs\nof Insight"]
  end
  
  %% ❖  Meta-Infrastructure (C-F)
  subgraph C-F[Meta-Infrastructure 🔧]
    style C-F fill:#d6e8ff,stroke:#5b8def,stroke-width:2px
    P23["23 Infrastructure\nSelf-Mod"]
  end
  
  %% ❖  Foresight → Action Fusion (C-G)
  subgraph C-G[Foresight→Action 🎯]
    style C-G fill:#eed6ff,stroke:#aa55ff,stroke-width:2px
    P24["24 Insight×Sovereign\nFusion"]
    P25["25 Economic Memory\nCrystals"]
    P26["26 Latent Loop\nHarvesting"]
  end
  
  %% ❖  Ontological & Institutional (C-H)
  subgraph C-H[Ontological & Institutional 🏛️]
    style C-H fill:#e5d6ff,stroke:#8666ff,stroke-width:2px
    P27["27 Ontological\nFusion Engine"]
    P28["28 Autopoietic\nAgencies"]
    P29["29 Adaptive\nAGI Firms"]
    P30["30 Onto-Economic\nGravity Wells"]
  end
  
  %% ❖  Civilization-Scale (C-I)
  subgraph C-I[Civilization-Scale 🌏]
    style C-I fill:#ffd6ff,stroke:#ff44cc,stroke-width:2px
    P31["31 AGI-First\nCivilization Sim"]
    P32["32 Treaty Genesis"]
    P33["33 Treaty Cascades"]
    P34["34 Autonomic\nForesight Mesh"]
    P35["35 Self-Reflective\nTreaty Loops"]
  end
  
  %% ⤷  Cross-Cluster Edges (simplified)
  P13 --> P17
  P16 --> P17
  P17 --> P18 --> P20
  P21 --> P24
  P22 -. privacy .- P24
  P24 --> P25 --> P26 --> P27
  P27 --> P28 --> P29 --> P30 --> P31
  P31 --> P32 --> P33 --> P34 --> P35
  P35 -.feedback.- P17
```


```mermaid
%% 🎖️ α‑AGI Insight 👁️✨ — Beyond Human Foresight — Official Demo
%% Comprehensive architecture & workflow diagram (ZERO‑DATA)

flowchart TD
  %% === Core Orchestration Layer ===
  subgraph Core["Core Services"]
    Orchestrator["Macro‑Sentinel<br/>Orchestrator"]
    MessageBus["Secure A2A<br/>pub/sub bus"]
  end

  Orchestrator -- "registry / heartbeat" --> MessageBus
  MessageBus -- "routing / TLS" --> Orchestrator

  %% === Agents Swarm ===
  subgraph AgentsPool["Specialised α‑AGI Agents"]
    PlanningAgent["Planning Agent<br/>(OpenAI SDK)"]
    ResearchAgent["Research Agent<br/>(Google ADK)"]
    StrategyAgent["Strategy Agent"]
    MarketAgent["Market‑Analysis Agent"]
    CodeGenAgent["Code‑Gen Agent"]
    SafetyAgent["Safety‑Guardian Agent"]
    MemoryAgent["Memory / Knowledge<br/>Store Agent"]
  end

  MessageBus <--> PlanningAgent
  MessageBus <--> ResearchAgent
  MessageBus <--> StrategyAgent
  MessageBus <--> MarketAgent
  MessageBus <--> CodeGenAgent
  MessageBus <--> MemoryAgent
  SafetyAgent -- "policy guard" --- MessageBus

  %% === Simulation & Analytics Engines ===
  subgraph Simulation["Zero‑Data Simulation Engines"]
    MATS["Meta‑Agentic Tree Search<br/>(NSGA‑II, Eq. 3)"]
    Forecast["Thermodynamic Forecast<br/>(Eq. 1 trigger)"]
    InnovationPool["Elite Innovation Pool"]
    SectorDB["Sector State DB"]
  end

  PlanningAgent -- "spawn search" --> MATS
  ResearchAgent -- "spawn search" --> MATS
  MATS --> InnovationPool
  InnovationPool --> Forecast
  StrategyAgent --> Forecast
  Forecast --> SectorDB

  %% === User Interfaces ===
  subgraph Interfaces["User‑Facing Interfaces"]
    WebUI["Web UI<br/>(Streamlit / React)"]
    CLI["CLI (Click)"]
  end

  SectorDB --> WebUI
  SectorDB --> CLI
  Users["👤 End Users"] <--> WebUI
  Users <--> CLI

  %% === Storage & Audit ===
  subgraph Storage["Immutable Logs & Artifacts"]
    Ledger["Append‑only Ledger<br/>(SQLite + Merkle→Blockchain)"]
    ContainerRegistry["Container Registry"]
  end

  MessageBus -- "hash‑chain events" --> Ledger
  Orchestrator -- "push images" --> ContainerRegistry

  %% === Deployment & Ops ===
  subgraph DevOps["Packaging & Deployment"]
    DockerCompose["Docker‑Compose"]
    HelmChart["Helm (K8s)"]
    Terraform["Terraform<br/>(GCP / AWS)"]
  end

  ContainerRegistry --> DockerCompose
  ContainerRegistry --> HelmChart
  ContainerRegistry --> Terraform

  %% === Offline / Air‑gapped Mode ===
  subgraph OfflineMode["Resource‑Adaptive Runtime"]
    LocalLLM["Local LLM Runtime<br/>(Llama‑3 / GPT‑Neo)"]
  end
  LocalLLM -. "inference" .-> PlanningAgent
  LocalLLM -. "inference" .-> StrategyAgent
  LocalLLM -. "code eval" .-> CodeGenAgent

  %% Styling
  classDef core fill:#e0f7ff,stroke:#0288d1,stroke-width:1px;
  classDef agents fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
  classDef sim fill:#fff3e0,stroke:#f57c00,stroke-width:1px;
  classDef iface fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px;
  classDef storage fill:#ede7f6,stroke:#512da8,stroke-width:1px;
  classDef devops fill:#eceff1,stroke:#455a64,stroke-width:1px;
  classDef offline fill:#ffebee,stroke:#c62828,stroke-width:1px;

  class Core,Orchestrator,MessageBus core;
  class AgentsPool,PlanningAgent,ResearchAgent,StrategyAgent,MarketAgent,CodeGenAgent,SafetyAgent,MemoryAgent agents;
  class Simulation,MATS,Forecast,InnovationPool,SectorDB sim;
  class Interfaces,WebUI,CLI iface;
  class Storage,Ledger,ContainerRegistry storage;
  class DevOps,DockerCompose,HelmChart,Terraform devops;
  class OfflineMode,LocalLLM offline;
```


# 🎖️ α‑AGI Insight 👁️✨ — Beyond Human Foresight — Official Demo  
### Production‑Grade System – Mermaid Specification
> **Note:** Copy‑paste the following Mermaid blocks into your README.md (or any Mermaid‑enabled renderer) to obtain interactive architecture, repository, and DevOps diagrams.

---

## 1. End‑to‑End System Architecture
```mermaid
%% α‑AGI Insight – High‑Level Architecture
graph TD
    %% ===== User Interfaces =====
    subgraph UI[User Interfaces]
        CLI["CLI (Click)"]
        WebUI["Web UI (Streamlit / React+FastAPI)"]
    end

    %% ===== Orchestrator & Bus =====
    subgraph ORCH[Macro‑Sentinel Orchestrator]
        Orchestrator["Orchestrator<br/>(Agent Registry • Heartbeats • Scheduling)"]
        A2ABus[["Secure A2A Message Bus<br/>(gRPC pub/sub, TLS)"]]
        Ledger["Audit Ledger<br/>(SQLite + Merkle Roots)"]
    end

    %% ===== Core Engine =====
    subgraph CORE[Zero‑Data Simulation Engine]
        MATS["MATS Engine<br/>(NSGA‑II Evolutionary Search)"]
        Forecast["Disruption Forecaster<br/>(Thermodynamic Trigger)"]
        Memory["Shared Memory Store"]
    end

    %% ===== Agents =====
    subgraph AGENTS[α‑AGI Agents]
        Planning["Planning Agent"]
        Research["Research Agent"]
        Strategy["Strategy Agent"]
        Market["Market Analysis Agent"]
        CodeGen["CodeGen Agent"]
        Safety["Safety Guardian Agent"]
    end

    %% ===== Tool Layer =====
    subgraph TOOLS[Tooling & Plugins]
        MCP["Model Context Protocol Adapter"]
        Plugins["Safe Plugins<br/>(Data • Viz • Persistence)"]
    end

    %% ===== Data / Chain =====
    Blockchain["Public Blockchain<br/>(Solana Testnet)"]

    %% --- Data Flow ---
    CLI-->|REST / gRPC|Orchestrator
    WebUI-->|REST / WebSocket|Orchestrator

    Orchestrator-->|pub/sub|A2ABus
    A2ABus-->|broadcast|Planning
    A2ABus-->|broadcast|Research
    A2ABus-->|broadcast|Strategy
    A2ABus-->|broadcast|Market
    A2ABus-->|broadcast|CodeGen
    A2ABus-->|monitor|Safety

    Safety-->|policy actions|Orchestrator

    %% Agents tool calls
    Planning-->|call|MCP
    Research-->|call|MCP
    Strategy-->|call|MCP
    CodeGen-->|call|MCP
    MCP-->|executes|Plugins

    %% Core Engine links
    Orchestrator-->|invoke|MATS
    MATS-->|elite pool|Forecast
    Forecast-->|writes|Memory
    Agents-->|query/update|Memory

    Orchestrator-->|log hashes|Ledger
    Ledger-->|checkpoint|Blockchain

    %% Result channels
    Forecast-->|stream results|WebUI
    Forecast-->|print summary|CLI
```

---

## 4. Legend
- **Solid arrows**: primary data/control flow  
- **Dashed arrows**: monitoring / logging / audit paths  
- **Rounded rectangles**: active services or agents  
- **Parallelograms**: data stores or ledgers  
- **Cylinders**: external persistent storage / blockchain

# α‑AGI Insight — Architectural Overview (Mermaid diagrams)

```mermaid
%% Diagram 1: High‑level system architecture
flowchart TD
    subgraph User_Interfaces
        CLI["Command‑Line Interface (Click)"]
        WebUI["Web UI (Streamlit / React+FastAPI)"]
    end

    subgraph Core_Services
        Orchestrator["Macro‑Sentinel Orchestrator"]
        Bus["Secure A2A Message Bus\n(gRPC + TLS)"]
        Ledger["Append‑Only Audit Ledger\n(SQLite + Merkle ➜ Blockchain)"]
    end

    subgraph Agents_Cluster
        Planning[PlanningAgent]
        Research[ResearchAgent]
        Strategy[StrategyAgent]
        Market[MarketAnalysisAgent]
        CodeGen[CodeGenAgent]
        Safety[SafetyGuardianAgent]
        Memory[MemoryAgent / KV Store]
    end

    subgraph Simulation_Engine
        MATS["Zero‑Data Meta‑Agentic Tree Search\n(NSGA‑II)"]
        Forecast["Thermodynamic Disruption Forecaster"]
    end

    subgraph External_Services
        OpenAISDK["OpenAI Agents SDK"]
        GoogleADK["Google ADK"]
        MCP["Anthropic MCP"]
        LocalLLM["Local LLM\n(Fallback, Llama‑3)"]
    end

    CLI -- REST/CLI --> Orchestrator
    WebUI -- WebSocket/REST --> Orchestrator
    Orchestrator -- pub/sub --> Bus
    Bus <-- heartbeat --> Agents_Cluster
    Orchestrator -- audit --> Ledger

    Agents_Cluster -->|tool calls| Simulation_Engine
    MATS --> Forecast
    Forecast --> Orchestrator

    CodeGen -- sandbox_exec --> Orchestrator
    Safety -. monitors .- Agents_Cluster
    Memory -. query .- Agents_Cluster

    Orchestrator -->|API| OpenAISDK
    Orchestrator --> GoogleADK
    Orchestrator --> MCP
    Orchestrator --> LocalLLM
```

```mermaid
%% Diagram 2: Repository layout
graph TD
    A0[alpha_agi_insight_v1/] --- A1[README.md]
    A0 --- A2[requirements.txt]
    A0 --- SRC[src/]
    A0 --- TEST[tests/]
    A0 --- INFRA[infrastructure/]
    A0 --- DOCS[docs/]

    subgraph src/
        Orc[orchestrator.py]
        subgraph agents/
            BA[base_agent.py]
            PA[planning_agent.py]
            RA[research_agent.py]
            SA[strategy_agent.py]
            MA[market_agent.py]
            CG[codegen_agent.py]
            SG[safety_agent.py]
            MEM[memory_agent.py]
        end
        subgraph simulation/
            MATS_SIM[mats.py]
            FC[forecast.py]
            SEC[sector.py]
        end
        subgraph interface/
            CLI_FILE[cli.py]
            WEB[web_app.py]
            API[api_server.py]
            CLIENT[web_client/]
        end
        subgraph utils/
            MSG[messaging.py]
            CFG[config.py]
            LOG[logging.py]
        end
    end

    subgraph tests/
        TM[test_mats.py]
        TF[test_forecast.py]
        TA[test_agents.py]
        TCL[test_cli.py]
    end

    subgraph infrastructure/
        DF[Dockerfile]
        DC[docker-compose.yml]
        HELM[helm-chart/]
        TF_FOLDER[terraform/]
    end

    subgraph docs/
        DES[DESIGN.md]
        API_DOC[API.md]
        CHG[CHANGELOG.md]
    end
```

%% 🎖️ α‑AGI Insight 👁️✨ — Beyond Human Foresight — Official Demo (ZERO‑DATA)
%% Production‑grade Mermaid specification for README.md

### System Architecture

```mermaid
flowchart TD
  %% ---------- Interface Layer ----------
  subgraph Interfaces
    CLI["CLI<br/><i>click/argparse</i>"]
    WEB["Web UI<br/><i>Streamlit / FastAPI + React</i>"]
  end

  %% ---------- Core Services ----------
  subgraph Core["Core Services"]
    ORCH["Macro‑Sentinel<br/>Orchestrator"]
    BUS["Secure A2A Bus<br/><i>gRPC Pub/Sub</i>"]
    LEDGER["Audit Ledger<br/><i>SQLite + Merkle</i>"]
    MATS["MATS Engine<br/><i>NSGA‑II Evo‑Search</i>"]
    FORECAST["Thermo‑Forecast<br/><i>Free‑Energy Model</i>"]
  end

  %% ---------- Agents ----------
  subgraph Agents
    PLAN["Planning Agent"]
    RESEARCH["Research Agent"]
    STRAT["Strategy Agent"]
    MARKET["Market Analysis Agent"]
    CODE["CodeGen Agent"]
    SAFE["Safety Guardian"]
    MEMORY["Memory Store"]
  end

  %% ---------- Providers & Runtime ----------
  subgraph Providers
    OPENAI["OpenAI Agents SDK"]
    ADK["Google ADK"]
    MCP["Anthropic MCP"]
  end
  SANDBOX["Isolated Runtime<br/><i>Docker / Firejail</i>"]
  CHAIN["Public Blockchain<br/><i>Checkpoint (Solana testnet)</i>"]

  %% ---------- Edges ----------
  CLI -->|commands| ORCH
  WEB -->|REST / WS| ORCH

  ORCH <--> BUS
  BUS <-->|A2A envelopes| PLAN
  BUS <-->|A2A envelopes| RESEARCH
  BUS <-->|A2A envelopes| STRAT
  BUS <-->|A2A envelopes| MARKET
  BUS <-->|A2A envelopes| CODE
  BUS <-->|A2A envelopes| SAFE
  BUS <-->|A2A envelopes| MEMORY

  SAFE -. monitors .-> BUS

  PLAN & RESEARCH & STRAT & MARKET & CODE -->|invoke| MATS
  PLAN & RESEARCH & STRAT & MARKET & CODE -->|invoke| FORECAST
  MATS --> FORECAST

  CODE --> SANDBOX

  ORCH -. writes .-> LEDGER
  LEDGER --> CHAIN

  ORCH <--> OPENAI
  ORCH <--> ADK
  ORCH <--> MCP

  MEMORY --- Agents

  %% ---------- Styling ----------
  classDef iface fill:#d3f9d8,stroke:#34a853,stroke-width:1px;
  classDef core fill:#e5e5ff,stroke:#6b6bff,stroke-width:1px;
  classDef agents fill:#fef9e7,stroke:#f39c12,stroke-width:1px;
  classDef provider fill:#f5e0ff,stroke:#8e44ad,stroke-width:1px;
  class Interfaces iface
  class Core core
  class Agents agents
  class Providers provider
```

### Repository Layout

```mermaid
graph TD
  ROOT["alpha_agi_insight_v1/"]
  subgraph Root
    ROOT_README["README.md"]
    REQ["requirements.txt"]
    SRC["src/"]
    TEST["tests/"]
    INFRA["infrastructure/"]
    DOCS["docs/"]
  end

  %% src subtree
  subgraph Source["src/"]
    ORCH_PY["orchestrator.py"]
    UTILS["utils/"]
    AGENTS_DIR["agents/"]
    SIM["simulation/"]
    IFACE["interface/"]
  end
  SRC -->|contains| Source

  %% utils subtree
  UTILS_CFG["config.py"]
  UTILS_MSG["messaging.py"]
  UTILS_LOG["logging.py"]
  UTILS --> UTILS_CFG & UTILS_MSG & UTILS_LOG

  %% agents subtree
  AG_BASE["base_agent.py"]
  AG_PLAN["planning_agent.py"]
  AG_RES["research_agent.py"]
  AG_STRAT["strategy_agent.py"]
  AG_MARK["market_agent.py"]
  AG_CODE["codegen_agent.py"]
  AG_SAFE["safety_agent.py"]
  AG_MEM["memory_agent.py"]
  AGENTS_DIR --> AG_BASE & AG_PLAN & AG_RES & AG_STRAT & AG_MARK & AG_CODE & AG_SAFE & AG_MEM

  %% simulation subtree
  SIM_MATS["mats.py"]
  SIM_FC["forecast.py"]
  SIM_SEC["sector.py"]
  SIM --> SIM_MATS & SIM_FC & SIM_SEC

  %% interface subtree
  IF_CLI["cli.py"]
  IF_WEB["web_app.py"]
  IF_API["api_server.py"]
  IF_REACT["web_client/"]
  IFACE --> IF_CLI & IF_WEB & IF_API & IF_REACT

  %% tests subtree
  TEST_MATS["test_mats.py"]
  TEST_FC["test_forecast.py"]
  TEST_AG["test_agents.py"]
  TEST_CLI["test_cli.py"]
  TEST --> TEST_MATS & TEST_FC & TEST_AG & TEST_CLI

  %% infrastructure subtree
  INF_DOCK["Dockerfile"]
  INF_COMPOSE["docker-compose.yml"]
  INF_HELM["helm-chart/"]
  INF_TF["terraform/"]
  INFRA --> INF_DOCK & INF_COMPOSE & INF_HELM & INF_TF

  %% docs subtree
  DOC_DESIGN["DESIGN.md"]
  DOC_API["API.md"]
  DOC_CHANGE["CHANGELOG.md"]
  DOCS --> DOC_DESIGN & DOC_API & DOC_CHANGE
```

> **Download** this file to embed the diagrams directly in your README.

