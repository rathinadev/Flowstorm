# FlowStorm - Product Specification

## One-Liner
A self-healing, self-optimizing real-time stream processing engine with a live visual pipeline editor that adapts to failures and data pattern changes without human intervention.

---

## Core Product Pillars

### Pillar 1: Visual Pipeline Builder (The Face)
- Drag-and-drop node editor for building stream processing pipelines
- Node types: Sources (MQTT, HTTP, Simulator), Operators (Filter, Map, Window, Join, Aggregate), Sinks (Database, Alert, Webhook)
- Live data flow visualization - event counts, throughput, latency shown on edges in real-time
- Nodes glow green/yellow/red based on health status
- Click any node to see live events passing through it
- Built with React Flow library

### Pillar 2: Self-Healing Engine (The Brain)
- **Node Death Recovery**: Auto-detects dead worker in <2s via heartbeats, reassigns work to surviving nodes, replays lost events from checkpoint
- **Data Spike Handling**: Auto-splits hot operators across more workers, shows scaling animation on visual pipeline
- **Backpressure Management**: Detects slow downstream sinks, auto-inserts buffers, rate-limits only affected branches
- **Memory Protection**: Detects approaching OOM, spills to disk, alerts, migrates operator to healthier node
- Health Monitor Agent sends heartbeats every 500ms, tracks CPU/memory/throughput/latency per operator
- Decision Engine uses rule-based + heuristic optimizer for autonomous healing decisions
- Execution Planner generates new DAG placement plans with live migration (no downtime)

### Pillar 3: Self-Optimizing DAG (The Muscle)
- **Predicate Pushdown**: Moves filters closer to source to reduce data volume early
- **Operator Fusion**: Merges consecutive map operations into a single operation
- **Auto-Parallelization**: Detects CPU-heavy operators and splits them across workers
- **Window Optimization**: Switches windowing strategy based on data patterns (time-window vs count-window)
- Engine observes data patterns (selectivity ratios, throughput, compute cost) and restructures the DAG automatically
- Before/after visualization of optimizations on the pipeline view

### Pillar 4: Live Observability Dashboard
- Cluster health percentage
- Events/sec throughput
- Average latency
- Active workers count
- Self-healing action log with timestamps
- DAG optimization history with gain metrics
- Custom-built in React (not Grafana - more impressive)

---

## Additional Features

### Feature 5: Chaos Mode (Built-In Chaos Monkey)
- "Unleash Chaos" button on the dashboard
- Randomly: kills workers, injects network latency, corrupts events, simulates memory pressure, floods sources with 50x data
- System self-heals from all chaos while user watches
- Configurable chaos intensity levels

### Feature 6: Pipeline Git (Version Control for Pipelines)
- Every change (manual or auto-optimization) is versioned like git commits
- Visual diff between any two versions (nodes added/removed/moved highlighted)
- One-click rollback to any previous version
- Fork a pipeline version to A/B test two approaches on live data
- Tagged as [USER] or [AUTO] to distinguish manual vs automatic changes

### Feature 7: Predictive Scaling
- Learns traffic patterns over time
- Pre-scales workers BEFORE predicted spikes
- Shows prediction graph: predicted load vs actual load vs scaling decisions
- Even simple moving average + pattern matching demonstrates the concept

### Feature 8: Live Data Lineage (X-Ray Vision)
- Click any output event to see its entire journey through the pipeline
- Shows: origin source, raw data, each transformation applied, window grouping, alert rule evaluation, delivery status
- Visual path highlighting on the DAG - the route lights up like a circuit
- Provides proof chain for any alert or output

### Feature 9: A/B Testing Pipelines
- Split live traffic between two pipeline versions
- Side-by-side comparison: latency, cost, accuracy
- Traffic split percentage configurable
- One-click promote winner to 100%

### Feature 10: Smart Dead Letter Queue
- Failed events auto-diagnosed for root cause
- Grouped by failure type
- Suggests fixes: add default value, skip, alert sensor team, auto-correct timestamps
- Shows failure timeline and source identification

---

## Tech Stack

### Backend (Python)
- **Framework**: FastAPI + asyncio
- **Message Transport**: Redis Streams
- **Worker Orchestration**: Docker + Docker SDK for Python
- **Persistent Storage**: PostgreSQL 16 (pipeline versions, checkpoints)
- **Ephemeral State**: Redis (streams, pub/sub, live metrics, heartbeats)
- **MQTT**: paho-mqtt + Mosquitto broker (Docker)
- **Key Packages**: fastapi, uvicorn, websockets, redis, docker, paho-mqtt, httpx, asyncpg

### Frontend (React)
- **DAG Editor**: React Flow (react-flow-renderer)
- **Animations**: Framer Motion
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Real-time**: WebSocket (native browser API)
- **State Management**: Zustand (lightweight)
- **Key Packages**: react, reactflow, framer-motion, tailwindcss, recharts, zustand

### Infrastructure
- Docker Desktop (worker containers, Redis, PostgreSQL, Mosquitto)
- Python 3.11+
- Node.js 18+

---

## Architecture Layers

1. **Frontend Layer** (React): Visual pipeline editor, dashboard, chaos panel, lineage viewer, version history
2. **Control Plane** (FastAPI): DAG compiler, health monitor, optimizer, pipeline git, checkpoint manager
3. **Data Plane** (Docker Containers): Worker containers running pipeline operators, communicating via Redis Streams
4. **Data Sources**: MQTT broker, Python IoT simulator, optional ESP32 hardware
5. **Storage**: PostgreSQL (pipeline versions, checkpoints) + Redis (streams, live metrics, heartbeats)

---

## Demo Script (5-7 Minutes)

1. Open visual editor, drag-drop a pipeline: MQTT Source -> Filter -> 60s Average -> Alert + Store
2. Hit Deploy, watch pipeline go live with real-time data flow on edges
3. Show dashboard: 10,000 events/sec, all green
4. Kill a worker (docker kill), watch visual pipeline flash red, heal in 2s, show "Zero events lost"
5. Flood with 10x data, watch engine auto-split bottleneck operator into 3 parallel nodes with animation
6. Show DAG optimization: engine moved Filter before Join autonomously, 20x cost reduction, before/after view
7. Click "Unleash Chaos" - random failures cascade and self-heal
8. Show pipeline version history, visual diff, one-click rollback
9. Click an output event, show full data lineage trace lighting up the DAG

---

## Team
- Solo developer + Claude AI assistant
- Separate git repositories for backend and frontend

---

## Project Status
- [ ] Project setup and documentation
- [ ] Core DAG execution engine
- [ ] Worker container management
- [ ] Redis Streams message transport
- [ ] Health monitoring + heartbeat system
- [ ] Self-healing logic (failover, migration, recovery)
- [ ] DAG optimizer (predicate pushdown, fusion, auto-parallel)
- [ ] FastAPI control plane + WebSocket
- [ ] React Flow visual pipeline editor
- [ ] Live dashboard with metrics
- [ ] Chaos mode
- [ ] Pipeline Git (versioning)
- [ ] Predictive scaling
- [ ] Data lineage
- [ ] A/B pipeline testing
- [ ] Smart dead letter queue
- [ ] IoT simulator
- [ ] Docker Compose for full stack
- [ ] Testing + polish
