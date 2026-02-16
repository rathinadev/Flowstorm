# FlowStorm Backend

> Self-Healing Stream Processing Engine + Control Plane

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?logo=redis&logoColor=white)](https://redis.io)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Application (src/main.py)                      │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │  REST API     │  │  WebSocket    │  │  Lifespan    │ │
│  │  (25 routes)  │  │  Manager      │  │  (init/shut) │ │
│  └──────┬───────┘  └───────┬───────┘  └──────────────┘ │
└─────────┼──────────────────┼────────────────────────────┘
          │                  │
     ┌────┴──────────────────┴────┐
     │     Module Layer           │
     ├────────────────────────────┤
     │  engine/   → Runtime, DAG Compiler, Scheduler      │
     │  health/   → Monitor, Detector, Healer, Predictor  │
     │  optimizer/ → Analyzer, Rewriter, Rules, Migrator  │
     │  chaos/    → Engine, Scenarios                     │
     │  workers/  → Base, Sources, Operators, Sinks       │
     │  pipeline_git/ → Versioner, Differ, Store          │
     │  dlq/      → Diagnostics                           │
     │  ab_testing/ → Manager                             │
     │  checkpoint/ → Manager, Store                      │
     │  demo/     → Simulator                             │
     └────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │   Infrastructure      │
          ├───────────────────────┤
          │  Redis 7.0            │
          │  ├─ Streams (events)  │
          │  ├─ Pub/Sub (beats)   │
          │  └─ Keys (state)      │
          │  PostgreSQL 15        │
          │  └─ Versions          │
          │  Docker               │
          │  └─ Workers           │
          └───────────────────────┘
```

## Directory Structure

```
src/
├── main.py                  # FastAPI app + lifespan (init RuntimeManager, HealthMonitor, Versioner)
├── api/
│   ├── routes.py            # 25 REST endpoints + 1 WebSocket + demo mode bypass
│   ├── websocket.py         # ConnectionManager, PipelineEventForwarder, MetricsPusher
│   └── schemas.py           # Pydantic request/response models
├── engine/
│   ├── runtime.py           # RuntimeManager (all pipelines) + PipelineRuntime (single pipeline)
│   ├── compiler.py          # PipelineCompiler → CompiledPipeline (validates, assigns streams)
│   ├── dag.py               # DAG class (topo sort, validate, mutate, snapshot, clone)
│   └── scheduler.py         # Scheduler → PlacementDecision + ResourceLimits
├── workers/
│   ├── base.py              # BaseWorker ABC (connect, run loop, heartbeat, checkpoint, DLQ)
│   ├── sources.py           # MQTTSource, SimulatorSource
│   ├── operators.py         # Filter, Map, Window, Aggregate, Join
│   ├── sinks.py             # Console, Redis, Alert, Webhook
│   └── runner.py            # Docker container entry point
├── health/
│   ├── monitor.py           # HealthMonitor (heartbeat listener, health scoring, healing trigger)
│   ├── detector.py          # AnomalyDetector (5 anomaly types)
│   ├── healer.py            # SelfHealer (4 healing actions + cooldown)
│   └── predictor.py         # PredictiveScaler (throughput forecast)
├── optimizer/
│   ├── analyzer.py          # PatternAnalyzer (runtime metrics → optimization candidates)
│   ├── rewriter.py          # DAGRewriter (5 optimization types → live DAG mutation)
│   ├── rules.py             # 5 OptimizationRules (pushdown, fusion, parallel, buffer, window)
│   └── migrator.py          # LiveMigrator (zero-downtime state transfer)
├── chaos/
│   ├── engine.py            # ChaosEngine (orchestrate, pick scenario, intensity filter)
│   └── scenarios.py         # 6 scenarios: Kill, Latency, Corrupt, Memory, Flood, Partition
├── pipeline_git/
│   ├── versioner.py         # PipelineVersioner (save on USER/AUTO_OPTIMIZE/AUTO_HEAL/ROLLBACK)
│   ├── differ.py            # PipelineDiffer → PipelineDiff (node/edge diffs)
│   └── store.py             # PipelineVersionStore (PostgreSQL + in-memory fallback)
├── dlq/
│   └── diagnostics.py       # DLQDiagnostics (classify 6 failure types, suggest fixes)
├── ab_testing/
│   └── manager.py           # ABTestManager (create, record metrics, determine winner)
├── checkpoint/
│   ├── manager.py           # CheckpointManager (save/get/replay)
│   └── store.py             # Redis checkpoint persistence
├── demo/
│   └── simulator.py         # DemoSimulator (metrics, healing, optimization, chaos, DLQ, versions, lineage)
└── models/
    ├── pipeline.py           # Pipeline, PipelineNode, PipelineEdge, OperatorType (14), PipelineStatus
    ├── events.py             # StreamEvent, Heartbeat, Checkpoint, HealingEvent, OptimizationEvent
    └── worker.py             # Worker, WorkerMetrics, WorkerHealth, WorkerConfig, WorkerStatus
```

## API Endpoints (25 + 1 WebSocket)

### Pipeline CRUD
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/pipelines` | Create and deploy pipeline |
| `GET` | `/api/pipelines` | List all active pipelines |
| `GET` | `/api/pipelines/:id` | Get pipeline status |
| `DELETE` | `/api/pipelines/:id` | Stop and remove pipeline |

### Chaos Engineering
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/pipelines/:id/chaos` | Start chaos mode |
| `DELETE` | `/api/pipelines/:id/chaos` | Stop chaos mode |
| `GET` | `/api/pipelines/:id/chaos/history` | Chaos event log |

### Version Control
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/:id/versions` | Version history |
| `GET` | `/api/pipelines/:id/versions/:from/diff/:to` | Visual diff |
| `POST` | `/api/pipelines/:id/rollback` | Rollback to version |

### Health & Healing
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/:id/health` | Worker health scores |
| `GET` | `/api/pipelines/:id/healing-log` | Self-healing log |

### Dead Letter Queue
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/:id/dlq` | Failed events with diagnostics |
| `GET` | `/api/pipelines/:id/dlq/stats` | Aggregated failure stats |

### Data Lineage
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/:id/lineage/:eventId` | Event trace |

### A/B Testing
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/ab-tests` | Create A/B test |
| `GET` | `/api/ab-tests` | List tests |
| `GET` | `/api/ab-tests/:id` | Get test results |
| `DELETE` | `/api/ab-tests/:id` | Stop test |

### Predictions
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/:id/prediction` | Scaling recommendation |

### Demo
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/demo/start` | Start demo simulator |
| `POST` | `/api/demo/stop` | Stop demo simulator |
| `GET` | `/api/demo/status` | Demo status |
| `POST` | `/api/demo/chaos` | Toggle demo chaos |

### WebSocket
| Protocol | Path | Description |
|----------|------|-------------|
| `WS` | `/api/ws/pipeline/:id` | Real-time event stream |

## Key Algorithms

### Health Scoring
```
health_score = (
    cpu_score * 0.30 +
    memory_score * 0.30 +
    throughput_score * 0.20 +
    latency_score * 0.20
)

Status:
  HEALTHY  → score > 70
  DEGRADED → 30 < score ≤ 70
  CRITICAL → score ≤ 30
```

### Self-Healing Decision Tree
```
Anomaly Type          → Healing Action
─────────────────────────────────────
Throughput Drop       → Scale Out (add parallel worker)
Error Spike           → Restart Worker
Memory Leak           → Migrate to new container
Latency Spike         → Insert Buffer operator
Consumer Lag          → Scale Out + Increase parallelism
Worker Death          → Failover + Checkpoint Replay
```

### Optimization Rules
```
Runtime Pattern       → DAG Rewrite
─────────────────────────────────────
Filter selectivity <0.3 late in DAG → Predicate Pushdown
Adjacent map+filter operators       → Operator Fusion
Single operator CPU >80%            → Auto-Parallelization
Backpressure detected               → Buffer Insertion
Sliding window high memory          → Window Optimization
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server (demo mode — no infra needed)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Full mode with infrastructure
docker-compose up -d redis postgres mosquitto
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `POSTGRES_URL` | `postgresql://localhost:5432/flowstorm` | PostgreSQL (optional) |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | Docker socket |
| `LOG_LEVEL` | `INFO` | Logging level |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.109.2 | REST API + WebSocket |
| `uvicorn[standard]` | 0.27.1 | ASGI server |
| `websockets` | 12.0 | WebSocket protocol |
| `redis` | 5.0.1 | Redis client (async) |
| `docker` | 7.0.0 | Docker SDK |
| `paho-mqtt` | 1.6.1 | MQTT client |
| `httpx` | 0.26.0 | Async HTTP |
| `pydantic` | 2.6.1 | Data validation |
| `asyncpg` | 0.29.0 | PostgreSQL async |
| `psutil` | 5.9.8 | System metrics |
| `python-dotenv` | 1.0.1 | Env config |

## Testing

```bash
pytest tests/ -v
```
