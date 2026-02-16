# FlowStorm - System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React + React Flow)"]
        PE[Pipeline Editor]
        DB[Dashboard]
        CM[Chaos Mode UI]
        LV[Lineage Viewer]
        PG[Pipeline Git UI]
    end

    subgraph ControlPlane["Control Plane (FastAPI)"]
        API[REST + WebSocket API]
        DC[DAG Compiler]
        HM[Health Monitor]
        OPT[DAG Optimizer]
        PGit[Pipeline Git Engine]
        CKP[Checkpoint Manager]
        PS[Predictive Scaler]
        CE[Chaos Engine]
    end

    subgraph DataPlane["Data Plane (Docker Containers)"]
        W1[Worker 1<br/>Filter]
        W2[Worker 2<br/>Window]
        W3[Worker 3<br/>Aggregate]
        W4[Worker 4<br/>Sink]
    end

    subgraph Transport["Message Transport"]
        RS[(Redis Streams)]
    end

    subgraph Sources["Data Sources"]
        MQTT[MQTT Broker<br/>Mosquitto]
        SIM[IoT Simulator<br/>Python]
        HW[ESP32<br/>Optional]
    end

    subgraph Storage["Storage Layer"]
        RED[(Redis<br/>Ephemeral State/Metrics)]
        PG_DB[(PostgreSQL<br/>Pipeline Versions/Checkpoints)]
    end

    Frontend <-->|WebSocket| API
    API --> DC
    API --> HM
    API --> OPT
    API --> PGit
    API --> CKP
    API --> PS
    API --> CE

    DC -->|Docker SDK| DataPlane
    HM -->|Heartbeat| DataPlane
    OPT -->|Rewrite DAG| DC

    W1 <--> RS
    W2 <--> RS
    W3 <--> RS
    W4 <--> RS

    Sources -->|MQTT| W1
    SIM -->|MQTT| MQTT
    HW -->|MQTT| MQTT

    W4 --> RED
    CKP --> PG_DB
    PGit --> PG_DB
    HM --> RED
```

---

## Component Deep Dive

### 1. DAG Compiler

```mermaid
flowchart LR
    A[Pipeline JSON<br/>from UI] --> B[Validate<br/>Schema]
    B --> C[Build<br/>Logical DAG]
    C --> D[Optimize<br/>Placement]
    D --> E[Generate<br/>Worker Configs]
    E --> F[Deploy<br/>Containers]
    F --> G[Wire<br/>Redis Streams]
    G --> H[Start<br/>Processing]
```

**Responsibilities:**
- Receives pipeline definition from frontend (JSON graph of nodes + edges)
- Validates operator compatibility (source can't connect to source, etc.)
- Builds a logical DAG (directed acyclic graph) of operators
- Determines optimal placement of operators on available workers
- Generates per-worker configuration (what operator to run, input/output streams)
- Deploys Docker containers via Docker SDK
- Creates Redis Stream topics for inter-operator communication
- Signals workers to begin processing

### 2. Health Monitor

```mermaid
sequenceDiagram
    participant W as Worker
    participant HM as Health Monitor
    participant DE as Decision Engine
    participant EP as Execution Planner
    participant UI as Frontend

    loop Every 500ms
        W->>HM: Heartbeat + Metrics<br/>(CPU, Memory, Throughput, Latency)
    end

    HM->>HM: Calculate Health Score (0-100)

    alt Health Score < 30
        HM->>DE: Worker Unhealthy
        DE->>EP: Migrate Operators Away
        EP->>EP: Generate New Placement Plan
        EP->>UI: Push Update via WebSocket
    end

    alt No Heartbeat for 2s
        HM->>DE: Worker Dead
        DE->>EP: Failover + Replay from Checkpoint
        EP->>UI: Push Recovery Animation
    end

    alt Throughput Drop > 50%
        HM->>DE: Bottleneck Detected
        DE->>EP: Scale Out Operator
        EP->>UI: Push Split Animation
    end
```

**Health Score Calculation:**
```
health_score = (
    cpu_score * 0.3 +       # 100 if CPU < 50%, linear decrease
    memory_score * 0.3 +     # 100 if mem < 60%, linear decrease
    throughput_score * 0.2 + # 100 if at expected rate, decrease if dropping
    latency_score * 0.2      # 100 if < target, decrease if increasing
)
```

### 3. DAG Optimizer

```mermaid
flowchart TD
    A[Observe Data Patterns<br/>Every 30 seconds] --> B{Analyze<br/>Opportunities}

    B --> C[Predicate Pushdown]
    B --> D[Operator Fusion]
    B --> E[Auto-Parallelization]
    B --> F[Window Optimization]

    C --> G{Filter selectivity<br/>ratio < 0.3?}
    G -->|Yes| H[Move filter<br/>closer to source]

    D --> I{Consecutive<br/>map operators?}
    I -->|Yes| J[Merge into<br/>single operator]

    E --> K{Operator CPU<br/>> 80%?}
    K -->|Yes| L[Split across<br/>N workers]

    F --> M{Data pattern<br/>changed?}
    M -->|Yes| N[Switch window<br/>strategy]

    H --> O[Generate New DAG]
    J --> O
    L --> O
    N --> O

    O --> P[Live Migrate<br/>No Downtime]
    P --> Q[Version in<br/>Pipeline Git]
    Q --> R[Push Visual Update<br/>to Frontend]
```

**Optimization Rules:**
| Rule | Trigger | Action | Expected Gain |
|------|---------|--------|---------------|
| Predicate Pushdown | Filter selectivity < 30% (drops 70%+ data) | Move filter before join/aggregate | Up to 10-20x |
| Operator Fusion | Two consecutive stateless transforms | Merge into one operator | 2x (eliminate serialization) |
| Auto-Parallel | Operator CPU > 80% sustained | Split into N parallel instances | Nx throughput |
| Window Switch | Bursty data pattern detected | Switch time-window to count-window | Better accuracy |

### 4. Self-Healing Decision Engine

```mermaid
stateDiagram-v2
    [*] --> Healthy: All workers running
    Healthy --> Degraded: Health score drops
    Healthy --> NodeDead: No heartbeat 2s
    Healthy --> Overloaded: Throughput spike

    Degraded --> Migrating: Migrate operators
    NodeDead --> Recovering: Failover + replay
    Overloaded --> Scaling: Add workers

    Migrating --> Healthy: Migration complete
    Recovering --> Healthy: Recovery complete
    Scaling --> Healthy: Scale-out complete

    Degraded --> NodeDead: Worker dies
    Overloaded --> NodeDead: OOM kill
```

### 5. Pipeline Git (Version Control)

```mermaid
gitGraph
    commit id: "v1: Pipeline created"
    commit id: "v2: Added Window operator"
    commit id: "v3: Added Alert sink"
    branch auto-optimize
    commit id: "v4: [AUTO] Pushed Filter before Join"
    commit id: "v5: [AUTO] Scaled Aggregate x3"
    checkout main
    merge auto-optimize id: "v6: Accept optimizations"
    branch ab-test
    commit id: "v7: [AB] Test new filter strategy"
    checkout main
    commit id: "v8: [AUTO] Healed from Worker-2 death"
```

**Stored per version:**
- Full DAG definition (nodes, edges, operator configs)
- Trigger: USER | AUTO_OPTIMIZE | AUTO_HEAL | AB_TEST
- Timestamp
- Description of change
- Performance metrics at time of change
- Diff from previous version

### 6. Chaos Engine

```mermaid
flowchart LR
    A[Chaos Mode<br/>Activated] --> B{Random<br/>Selection}

    B -->|20%| C[Kill Random<br/>Worker]
    B -->|20%| D[Inject 500ms<br/>Latency]
    B -->|20%| E[Corrupt Random<br/>Events]
    B -->|20%| F[Simulate<br/>Memory Pressure]
    B -->|20%| G[Flood Source<br/>50x Data]

    C --> H[Self-Heal:<br/>Failover]
    D --> I[Self-Heal:<br/>Detect + Buffer]
    E --> J[Self-Heal:<br/>Dead Letter + Diagnose]
    F --> K[Self-Heal:<br/>Spill + Migrate]
    G --> L[Self-Heal:<br/>Scale Out]

    H --> M[Log Action<br/>to Dashboard]
    I --> M
    J --> M
    K --> M
    L --> M
```

### 7. Predictive Scaler

```mermaid
flowchart TD
    A[Collect Historical<br/>Throughput Data] --> B[Pattern Detection<br/>Moving Average + Seasonality]
    B --> C[Predict Next<br/>15-Minute Load]
    C --> D{Predicted Load ><br/>Current Capacity * 0.8?}
    D -->|Yes| E[Pre-Scale Workers<br/>Before Spike]
    D -->|No| F{Predicted Load <<br/>Current Capacity * 0.3?}
    F -->|Yes| G[Scale Down<br/>Save Resources]
    F -->|No| H[No Action]

    E --> I[Log Prediction<br/>+ Decision]
    G --> I
    H --> I
    I --> J[Show on Dashboard:<br/>Predicted vs Actual]
```

---

## Data Flow

```mermaid
flowchart LR
    subgraph Sources
        S1[Sensor 1]
        S2[Sensor 2]
        S3[Sensor N]
    end

    subgraph MQTT
        MB[Mosquitto<br/>Broker]
    end

    subgraph RedisStreams["Redis Streams"]
        RS1[stream:source:raw]
        RS2[stream:filter:out]
        RS3[stream:window:out]
        RS4[stream:agg:out]
    end

    subgraph Workers["Docker Workers"]
        W1[Source<br/>Ingester]
        W2[Filter<br/>Operator]
        W3[Window<br/>Operator]
        W4[Aggregate<br/>Operator]
        W5[Alert<br/>Sink]
        W6[Store<br/>Sink]
    end

    S1 & S2 & S3 -->|MQTT| MB
    MB --> W1
    W1 -->|Write| RS1
    RS1 -->|Read| W2
    W2 -->|Write| RS2
    RS2 -->|Read| W3
    W3 -->|Write| RS3
    RS3 -->|Read| W4
    W4 -->|Write| RS4
    RS4 -->|Read| W5
    RS4 -->|Read| W6
```

---

## Worker Container Internals

```mermaid
flowchart TD
    subgraph DockerContainer["Worker Container"]
        A[Heartbeat Thread<br/>Every 500ms] -->|Report| B[Health Metrics]
        C[Input Consumer<br/>Redis Stream Read] --> D[Operator Logic<br/>Filter/Map/Window/etc]
        D --> E[Output Producer<br/>Redis Stream Write]
        D --> F[Checkpoint<br/>Every N events]
        F --> G[(PostgreSQL<br/>Checkpoint Store)]
    end

    H[Health Monitor] <-->|Heartbeat| A
    I[(Redis Streams<br/>Input)] --> C
    E --> J[(Redis Streams<br/>Output)]
```

---

## WebSocket Communication Protocol

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant BE as Backend (FastAPI)

    FE->>BE: ws://connect
    BE-->>FE: Connected

    loop Every 500ms
        BE-->>FE: pipeline.metrics {throughput, latency, health}
    end

    FE->>BE: pipeline.deploy {nodes, edges}
    BE-->>FE: pipeline.deployed {id, status}

    BE-->>FE: health.alert {worker_id, issue, action_taken}
    BE-->>FE: optimizer.applied {optimization_type, before, after, gain}
    BE-->>FE: worker.died {worker_id}
    BE-->>FE: worker.recovered {worker_id, events_replayed}
    BE-->>FE: worker.scaled {operator, old_count, new_count}

    FE->>BE: chaos.start {intensity: "medium"}
    BE-->>FE: chaos.event {type, target, timestamp}
    BE-->>FE: chaos.healed {action, duration_ms}

    FE->>BE: pipeline_git.history {}
    BE-->>FE: pipeline_git.versions [{id, trigger, desc, timestamp}]
    FE->>BE: pipeline_git.rollback {version_id}
    BE-->>FE: pipeline_git.rolled_back {new_dag}

    FE->>BE: lineage.trace {event_id}
    BE-->>FE: lineage.result {path: [{node, transform, data}]}
```

---

## Directory Structure

### Backend
```
backend/
├── src/
│   ├── engine/          # Core DAG execution engine
│   │   ├── dag.py       # DAG data structure and operations
│   │   ├── compiler.py  # Pipeline JSON -> Executable DAG
│   │   ├── scheduler.py # Operator placement on workers
│   │   └── runtime.py   # DAG execution coordinator
│   ├── api/             # FastAPI routes + WebSocket
│   │   ├── routes.py    # REST endpoints
│   │   ├── websocket.py # WebSocket handler
│   │   └── schemas.py   # Pydantic models
│   ├── workers/         # Worker container logic
│   │   ├── base.py      # Base worker class
│   │   ├── operators.py # Filter, Map, Window, Join, Aggregate
│   │   ├── sources.py   # MQTT source, HTTP source
│   │   ├── sinks.py     # DB sink, Alert sink, Webhook sink
│   │   └── runner.py    # Worker entry point (runs in container)
│   ├── health/          # Health monitoring + self-healing
│   │   ├── monitor.py   # Heartbeat collector + health scoring
│   │   ├── detector.py  # Anomaly/failure detection
│   │   ├── healer.py    # Self-healing actions
│   │   └── predictor.py # Predictive scaling
│   ├── optimizer/       # DAG optimization engine
│   │   ├── analyzer.py  # Data pattern analysis
│   │   ├── rules.py     # Optimization rules
│   │   ├── rewriter.py  # DAG transformation
│   │   └── migrator.py  # Live migration without downtime
│   ├── pipeline_git/    # Version control for pipelines
│   │   ├── versioner.py # Version management
│   │   ├── differ.py    # Visual diff generation
│   │   └── store.py     # PostgreSQL version storage (asyncpg)
│   ├── checkpoint/      # State checkpointing
│   │   ├── manager.py   # Checkpoint coordination
│   │   └── store.py     # PostgreSQL checkpoint store (asyncpg)
│   ├── chaos/           # Chaos engineering module
│   │   ├── engine.py    # Chaos scenario orchestrator
│   │   └── scenarios.py # Individual chaos scenarios
│   ├── models/          # Shared data models
│   │   ├── pipeline.py  # Pipeline, Node, Edge models
│   │   ├── worker.py    # Worker state models
│   │   └── events.py    # Event/message models
│   └── main.py          # FastAPI app entry point
├── tests/
├── config/
│   └── settings.py      # Configuration management
├── scripts/
│   ├── simulator.py     # IoT data simulator
│   └── seed_data.py     # Demo data seeder
├── Dockerfile           # Worker container image
├── docker-compose.yml   # Full stack compose
├── requirements.txt
└── README.md
```

### Frontend
```
frontend/
├── src/
│   ├── components/
│   │   ├── pipeline/    # React Flow pipeline editor
│   │   │   ├── PipelineEditor.tsx
│   │   │   ├── CustomNodes.tsx
│   │   │   ├── CustomEdges.tsx
│   │   │   └── NodePalette.tsx
│   │   ├── dashboard/   # Observability dashboard
│   │   │   ├── Dashboard.tsx
│   │   │   ├── MetricsPanel.tsx
│   │   │   ├── HealthPanel.tsx
│   │   │   ├── HealingLog.tsx
│   │   │   └── OptimizationLog.tsx
│   │   ├── chaos/       # Chaos mode UI
│   │   │   ├── ChaosPanel.tsx
│   │   │   └── ChaosControls.tsx
│   │   ├── lineage/     # Data lineage viewer
│   │   │   ├── LineagePanel.tsx
│   │   │   └── EventTrace.tsx
│   │   ├── git/         # Pipeline version control UI
│   │   │   ├── VersionHistory.tsx
│   │   │   ├── VisualDiff.tsx
│   │   │   └── RollbackModal.tsx
│   │   └── common/      # Shared UI components
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── StatusBadge.tsx
│   ├── hooks/           # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── usePipeline.ts
│   │   └── useMetrics.ts
│   ├── services/        # API + WebSocket clients
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── store/           # Zustand state management
│   │   ├── pipelineStore.ts
│   │   ├── metricsStore.ts
│   │   └── chaosStore.ts
│   ├── utils/           # Utility functions
│   ├── types/           # TypeScript type definitions
│   │   ├── pipeline.ts
│   │   ├── metrics.ts
│   │   └── websocket.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
├── tests/
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── package.json
└── README.md
```
