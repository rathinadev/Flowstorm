<div align="center">

# FlowStorm

### Self-Healing, Self-Optimizing Real-Time Stream Processing Engine

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**A distributed stream processing platform that automatically heals failures, optimizes pipeline topology at runtime, and provides a visual drag-and-drop interface for building real-time data pipelines.**

[Architecture](#architecture) &bull; [Features](#features) &bull; [Quick Start](#quick-start) &bull; [Documentation](#-documentation) &bull; [Tech Stack](#tech-stack)

---

```
       ┌─ You build the pipeline visually
       │
       ▼
   ┌──────────┐    ┌──────────────┐    ┌──────────────┐
   │  Design  │───▶│ FlowStorm    │───▶│  Something   │
   │  (UI)    │    │  Runs It     │    │  Breaks?     │
   └──────────┘    └──────────────┘    └───────┬──────┘
                          ▲                    │
                          │     FlowStorm      │
                          │     Heals It       │
                          │                    ▼
                   ┌──────┴───────┐    ┌──────────────┐
                   │  Inefficient?│◀───│  Recovered!  │
                   │  Optimizes!  │    │              │
                   └──────────────┘    └──────────────┘
```

</div>

---

## The Problem

Modern stream processing platforms like Apache Flink, Kafka Streams, and Spark Streaming are powerful but share critical limitations:

| Problem | Impact |
|---------|--------|
| **Manual Configuration** | Requires deep systems expertise, YAML configs, custom deployment scripts |
| **Manual Failure Recovery** | 15-30 minutes of downtime per incident — operators SSH in, diagnose, restart |
| **Static Pipeline Topology** | Once deployed, DAGs never adapt — 30-50% wasted compute from unoptimized operators |
| **Fragmented Monitoring** | 5-7 separate tools for deployment, metrics, logs, alerts, and debugging |

## The Solution

FlowStorm is a **zero-intervention stream processing engine** that:

- **Self-Heals** — Detects worker failures in <500ms and recovers via checkpoint replay with exactly-once semantics
- **Self-Optimizes** — Analyzes runtime patterns and rewrites DAG topology (predicate pushdown, operator fusion, auto-parallelization) without stopping data flow
- **Visualizes Everything** — Single-pane interface combining pipeline design, live metrics, chaos testing, version control, DLQ diagnostics, and data lineage

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  VISUAL INTERFACE — React 18 + TypeScript + React Flow + Recharts       │
│  Pipeline Editor │ Dashboard │ Chaos │ DLQ │ Git │ Lineage │ A/B       │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ WebSocket (500ms push) + REST API
┌──────────────────────────────┴───────────────────────────────────────────┐
│  API & ORCHESTRATION — FastAPI + Uvicorn + Pydantic                     │
│  REST Server │ WebSocket Manager │ Event Forwarder │ Demo Simulator     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Deploy / Compile / Schedule
┌──────────────────────────────┴───────────────────────────────────────────┐
│  RUNTIME ENGINE — Docker SDK + AsyncIO + Redis Streams                  │
│  DAG Compiler → Scheduler → [Sources → Operators → Sinks]              │
│  Checkpoint Manager │ Pipeline Git Versioner                            │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Heartbeats / Healing / Rewrites
┌──────────────────────────────┴───────────────────────────────────────────┐
│  INTELLIGENCE — MAPE-K Self-Healing + Auto-Optimization + Chaos         │
│  Health Monitor → Anomaly Detector → Self-Healer                        │
│  Pattern Analyzer → DAG Rewriter │ Chaos Engine │ Predictive Scaler     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Redis Streams + Pub/Sub + PostgreSQL
┌──────────────────────────────┴───────────────────────────────────────────┐
│  DATA BACKBONE — Redis 7.0 + PostgreSQL 15                              │
│  Streams (Events) │ Pub/Sub (Heartbeats) │ Checkpoints │ DLQ │ PG      │
└──────────────────────────────────────────────────────────────────────────┘
```

> For detailed architecture with Mermaid diagrams, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

---

## Features

### Self-Healing Engine

The health monitoring system implements a **MAPE-K (Monitor-Analyze-Plan-Execute)** feedback loop:

```
Worker Heartbeats (1s) → Health Monitor → Anomaly Detector → Self-Healer → Recovery
       ▲                                                          │
       └──────────── Checkpoint Replay (exactly-once) ◀───────────┘
```

- **Weighted Health Scoring**: CPU (30%) + Memory (30%) + Throughput (20%) + Latency (20%)
- **5 Anomaly Types**: Throughput drops, error spikes, memory leaks, latency spikes, consumer lag
- **4 Healing Actions**: Restart worker, migrate operator, scale-out, failover with checkpoint replay
- **Cooldown Mechanism**: Prevents healing loops from cascading false positives
- **Sub-second Recovery**: Checkpoint-based replay achieves exactly-once semantics
- **Event Frequency**: Self-healing events fire every ~10 seconds automatically, plus 2-5 seconds after chaos events
- **3-Stage Sequence**: Worker degraded → health alert → recovered (full recovery sequence visible in UI)

### Auto-Optimization

The optimizer continuously watches runtime metrics and rewrites the DAG topology:

| Optimization | What It Does | Typical Gain |
|-------------|-------------|-------------|
| **Predicate Pushdown** | Moves high-selectivity filters earlier in the pipeline | 25-40% throughput |
| **Operator Fusion** | Merges adjacent map/filter operators to eliminate serialization | 40-60% less overhead |
| **Auto-Parallelization** | Splits bottleneck operators into N parallel instances | Near-linear speedup |
| **Buffer Insertion** | Adds async buffers between operators to prevent backpressure | Reduces latency spikes |
| **Window Optimization** | Switches window strategies based on data patterns | Lower memory usage |

Every optimization creates a versioned snapshot in Pipeline Git for instant rollback.

- **Event Frequency**: Optimization events fire every ~20 seconds automatically
- **Trigger-based**: Also fires when high CPU (>85%) is detected (auto-parallelization)

### Visual Pipeline Editor

A React Flow-based drag-and-drop interface with **14 operator types**:

| Sources (3) | Operators (5) | Sinks (4) |
|-------------|---------------|-----------|
| MQTT Source | Filter | Console Sink |
| HTTP Source | Map | Redis Sink |
| Simulator | Window | Alert Sink |
| | Join | Webhook Sink |
| | Aggregate | |

**Live overlays** show events/second on edges and health scores on nodes during execution.

### Visual Features

FlowStorm includes enhanced visualizations for real-time monitoring:

| Feature | Description |
|---------|-------------|
| **Sparkline Chart** | Mini throughput trend in dashboard header |
| **Gradient Area Chart** | Smooth area chart with gradient fill |
| **Trend Indicator** | ↑/↓/→ showing % change in throughput |
| **Edge Throughput Colors** | Color-coded edges (green >1000, blue >500, yellow >100, orange >0) |
| **Animated Flowing Dots** | Small dots animating on high-throughput edges |
| **Status Badges** | Pulsing green/yellow/red worker badges |
| **Progress Bars** | CPU and Memory usage bars per worker |
| **Live Indicator** | Pulsing green dot showing active connection |

### Chaos Engineering

Inject controlled failures to validate self-healing:

| Scenario | Severity | What It Does |
|----------|----------|-------------|
| **Kill Worker** | High | Terminates a random worker process |
| **CPU Stress** | Medium | Spikes CPU usage on containers |
| **Network Delay** | Medium | Injects latency between operators |
| **Memory Pressure** | High | Forces memory exhaustion |
| **Event Corruption** | Low | Injects malformed events |
| **Network Partition** | Critical | Isolates workers from the cluster |

Three intensity levels (low, medium, high) with configurable duration and automatic chaos-healing validation.

### Pipeline Git (Version Control)

Every pipeline topology change creates an immutable version:

- **5 Version Triggers**: `USER`, `AUTO_OPTIMIZE`, `AUTO_HEAL`, `ROLLBACK`, `AB_TEST`
- **Visual Diff**: Side-by-side comparison showing added/removed/modified nodes and edges
- **One-Click Rollback**: Instantly revert to any previous version
- **Full History**: Complete audit trail of every change with timestamps and metadata

### Dead Letter Queue Diagnostics

Failed events are captured with intelligent diagnostics:

- **6 Failure Types**: `schema_violation`, `type_mismatch`, `missing_field`, `null_value`, `operator_error`, `timeout`
- **Auto-Classification**: Each failed event is analyzed and categorized
- **Fix Suggestions**: Targeted suggestions for resolving each failure type
- **Grouped Analysis**: Failures aggregated by type and source node

### A/B Testing

Compare pipeline versions side-by-side:

- Configurable traffic splitting (e.g., 50/50, 70/30)
- Per-variant metrics: throughput, latency, errors, CPU, memory
- Automatic winner determination
- Visual comparison dashboard

### Predictive Scaling

Forecasts throughput trends and recommends scaling actions before bottlenecks occur:

- Time-series forecasting with exponential smoothing
- Confidence intervals on predictions
- Scale-up/scale-down recommendations via API

### Data Lineage

Trace any event's journey through the entire pipeline:

- Per-operator transformation tracking
- Processing time at each stage
- Full provenance chain from source to sink

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis 7.0+ *(optional — demo mode works without it)*
- Docker *(optional — demo mode works without it)*
- PostgreSQL 15 *(optional — auto-falls back to in-memory storage)*

### One-Command Start

```bash
chmod +x start.sh && ./start.sh
```

This will:
1. Create a Python virtual environment
2. Install backend + frontend dependencies **in parallel**
3. Start the FastAPI backend on `http://localhost:8000`
4. Start the React frontend on `http://localhost:3000`

### Manual Start

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Demo Mode (No Infrastructure Required)

FlowStorm includes a built-in demo simulator that generates realistic metrics without Redis, Docker, or PostgreSQL:

1. Open `http://localhost:3000`
2. A default **IoT Temperature Monitor** pipeline is pre-loaded with 7 nodes
3. Click **Start Demo** in the header
4. Watch all panels come alive:
   - Real-time metrics flowing through the pipeline (500ms updates)
   - Self-healing events every ~10 seconds + chaos-triggered
   - Auto-optimization events every ~20 seconds
   - Chaos events every ~10 seconds (when chaos mode active)
   - DLQ entries with diagnostic data
   - Version history with diffs
   - Data lineage traces

### Keyboard Shortcuts

FlowStorm supports keyboard shortcuts for quick demo control:

| Key | Action |
|-----|--------|
| `Space` | Toggle demo on/off |
| `C` | Switch to Chaos view |
| `D` | Switch to Dashboard view |
| `P` | Switch to Pipeline view |
| `R` | Reset/restart demo |
| `1-7` | Quick switch to any view |

---

## Project Structure

```
flowstorm/
├── backend/                       # Python/FastAPI backend
│   ├── src/
│   │   ├── main.py                # Application entry point
│   │   ├── api/                   # REST + WebSocket (25 endpoints)
│   │   ├── engine/                # DAG compiler, runtime, scheduler
│   │   ├── workers/               # 14 operator implementations
│   │   ├── health/                # MAPE-K self-healing system
│   │   ├── optimizer/             # Pattern analyzer + DAG rewriter
│   │   ├── chaos/                 # 6 chaos scenarios
│   │   ├── pipeline_git/          # Version control + diff + store
│   │   ├── dlq/                   # Failure diagnostics
│   │   ├── ab_testing/            # A/B test manager
│   │   ├── checkpoint/            # State snapshots
│   │   ├── demo/                  # Demo simulator
│   │   └── models/                # Pydantic data models
│   ├── config/                    # Settings + env config
│   ├── tests/                     # pytest suite
│   └── requirements.txt
├── frontend/                      # React/TypeScript frontend
│   ├── src/
│   │   ├── components/            # 19 React components
│   │   │   ├── pipeline/          # Visual DAG editor (React Flow)
│   │   │   ├── dashboard/         # Real-time monitoring (Recharts)
│   │   │   ├── chaos/             # Chaos engineering controls
│   │   │   ├── dlq/               # DLQ diagnostics browser
│   │   │   ├── git/               # Version history + visual diff
│   │   │   ├── lineage/           # Data lineage tracer
│   │   │   ├── ab/                # A/B test comparator
│   │   │   └── common/            # Header + Sidebar
│   │   ├── store/                 # 3 Zustand stores
│   │   ├── hooks/                 # WebSocket hook
│   │   ├── services/              # API client (30+ methods)
│   │   └── types/                 # TypeScript definitions
│   └── package.json
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # Architecture + Mermaid diagrams
│   ├── API_REFERENCE.md           # Full API documentation
│   └── MODULES.md                 # Module deep-dive
├── start.sh                       # One-command startup
├── LICENSE                        # MIT License
└── README.md                      # This file
```

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core runtime |
| FastAPI | 0.109 | REST API + WebSocket server |
| Uvicorn | 0.27 | ASGI server |
| Redis | 7.0 | Event transport (Streams), heartbeats (Pub/Sub), checkpoints |
| Docker SDK | 7.0 | Worker container orchestration |
| Pydantic | 2.6 | Data validation + serialization |
| AsyncPG | 0.29 | Async PostgreSQL driver |
| Paho MQTT | 1.6 | IoT source connector |
| HTTPX | 0.26 | Async HTTP client |
| psutil | 5.9 | System metrics collection |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18.2 | UI framework |
| TypeScript | 5.3 | Type safety |
| Vite | 5.1 | Build tool + dev server |
| React Flow | 11.10 | Visual DAG editor |
| Zustand | 4.5 | State management |
| Recharts | 2.12 | Metrics visualization |
| Framer Motion | 11.0 | Animations |
| Tailwind CSS | 3.4 | Styling |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| Redis Streams | Event backbone between operators |
| Redis Pub/Sub | Real-time heartbeat delivery |
| PostgreSQL 15 | Pipeline version persistence |
| Docker | Worker containerization |

---

## API Overview

FlowStorm exposes **25 REST endpoints** and **1 WebSocket endpoint**:

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Pipeline** | `POST/GET/DELETE /api/pipelines` | Create, list, delete pipelines |
| **Chaos** | `POST/DELETE /api/pipelines/:id/chaos` | Start/stop chaos engineering |
| **Versions** | `GET /api/pipelines/:id/versions` | Version history + diff + rollback |
| **DLQ** | `GET /api/pipelines/:id/dlq` | Dead letter queue + stats |
| **Health** | `GET /api/pipelines/:id/health` | Worker health + healing log |
| **Lineage** | `GET /api/pipelines/:id/lineage/:eventId` | Event lineage trace |
| **A/B Tests** | `POST/GET/DELETE /api/ab-tests` | A/B test lifecycle |
| **Predictions** | `GET /api/pipelines/:id/prediction` | Scaling recommendations |
| **Demo** | `POST /api/demo/start\|stop` | Demo simulator control |
| **WebSocket** | `WS /api/ws/pipeline/:id` | Real-time event stream |

> Complete API documentation: **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)**

---

## WebSocket Events

Real-time events pushed to the frontend:

| Event Type | Description | Frequency |
|-----------|-------------|-----------|
| `pipeline.metrics` | Per-worker CPU, memory, throughput, latency | Every 500ms |
| `pipeline.deployed` | Pipeline successfully deployed | Once |
| `worker.recovered` | Worker recovered via self-healing | On event |
| `worker.scaled` | Worker auto-scaled | On event |
| `optimizer.applied` | DAG optimization applied | On event |
| `chaos.event` | Chaos failure injected | During chaos |
| `chaos.started/stopped` | Chaos mode toggled | On toggle |
| `pipeline_git.version` | New version created | On change |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `POSTGRES_URL` | `postgresql://localhost:5432/flowstorm` | PostgreSQL URL *(optional)* |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | Docker socket |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Research Foundation

FlowStorm's architecture is informed by peer-reviewed research in stream processing, distributed systems, and chaos engineering:

| # | Paper | Relevance |
|---|-------|-----------|
| 1 | Zhang et al., *"Hardware-Conscious Stream Processing: A Survey"* (2020) | Runtime optimization foundation |
| 2 | Nikolic et al., *"Self-healing Dilemmas in Distributed Systems"* (2021) | Hybrid healing strategy (MAPE-K) |
| 3 | Owotogbe et al., *"Chaos Engineering: A Multi-Vocal Literature Review"* (2025) | Chaos validation framework |
| 4 | Heinrich et al., *"COSTREAM: Learned Cost Models for Operator Placement"* (ICDE 2024) | DAG optimization techniques |
| 5 | Siachamis et al., *"CheckMate: Evaluating Checkpointing Protocols"* (2024) | Fault tolerance design |
| 6 | Psarakis, *"Transactional Stateful Functions on Streaming Dataflows"* (2025) | Elastic auto-scaling |
| 7 | Han et al., *"PROV-IO+: Cross-Platform Provenance Framework"* (2023) | Data lineage tracking |

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built as a Final Year Project (CS22811) at Sri Venkateswara College of Engineering**

*Designed and developed by Rathinadevan E M*

</div>
