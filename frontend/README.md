# FlowStorm Frontend

> Visual Pipeline Editor + Real-Time Dashboard for Stream Processing

[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-5.1-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  App.tsx (Root + Hash Router)                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  Header.tsx (Status + Demo Controls)         │   │
│  ├──────┬───────────────────────────────────────┤   │
│  │ Side │  Active View                          │   │
│  │ bar  │  ┌─ PipelineEditor (React Flow)       │   │
│  │      │  ├─ Dashboard (4 panels)              │   │
│  │  7   │  ├─ ChaosPanel                        │   │
│  │ views│  ├─ LineagePanel                       │   │
│  │      │  ├─ VersionHistory + VisualDiff        │   │
│  │      │  ├─ DLQPanel                           │   │
│  │      │  └─ ABTestPanel                        │   │
│  └──────┴───────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │                          │
    ┌────┴────┐              ┌──────┴──────┐
    │ Zustand │              │ useWebSocket│
    │ Stores  │              │    Hook     │
    │ (3)     │              └──────┬──────┘
    └────┬────┘                     │
         │                     WebSocket
    ┌────┴────┐              /api/ws/pipeline/:id
    │ api.ts  │
    │ (REST)  │
    └────┬────┘
         │
    HTTP /api/*
```

## Directory Structure

```
src/
├── App.tsx                         # Root component + hash-based view routing
├── main.tsx                        # React entry point
├── index.css                       # Global styles + animations
├── components/
│   ├── pipeline/                   # Visual DAG Editor
│   │   ├── PipelineEditor.tsx      # React Flow canvas + deploy controls
│   │   ├── CustomNodes.tsx         # FlowStormNode with health + metrics
│   │   ├── CustomEdges.tsx         # Animated edges with throughput labels
│   │   ├── NodePalette.tsx         # 14 draggable operator types
│   │   └── NodeConfigPanel.tsx     # Dynamic node configuration form
│   ├── dashboard/                  # Monitoring Dashboard
│   │   ├── Dashboard.tsx           # 2x2 grid layout
│   │   ├── MetricsPanel.tsx        # Line chart: throughput over time
│   │   ├── HealthPanel.tsx         # Per-worker health scores
│   │   ├── HealingLog.tsx          # Self-healing event timeline
│   │   └── OptimizationLog.tsx     # DAG optimization history
│   ├── chaos/
│   │   └── ChaosPanel.tsx          # Intensity slider + event feed
│   ├── lineage/
│   │   └── LineagePanel.tsx        # Event trace visualization
│   ├── git/
│   │   ├── VersionHistory.tsx      # Version timeline + rollback
│   │   └── VisualDiff.tsx          # Node/edge diff viewer
│   ├── dlq/
│   │   └── DLQPanel.tsx            # Failed events + fix suggestions
│   ├── ab/
│   │   └── ABTestPanel.tsx         # Side-by-side metrics comparison
│   └── common/
│       ├── Header.tsx              # Pipeline status + demo controls
│       └── Sidebar.tsx             # 7-view navigation
├── store/                          # Zustand State Stores
│   ├── pipelineStore.ts            # Pipeline nodes, edges, versions
│   ├── metricsStore.ts             # Live metrics, health, healing/opt logs
│   └── chaosStore.ts               # Chaos active state + event log
├── hooks/
│   └── useWebSocket.ts             # WS connection + event dispatching
├── services/
│   ├── api.ts                      # 30+ REST API methods (axios)
│   └── websocket.ts                # WebSocket client
├── types/
│   ├── pipeline.ts                 # Pipeline, Node, Edge, OperatorType
│   ├── metrics.ts                  # WorkerMetrics, Health, Events
│   └── websocket.ts                # WS message types
└── data/
    └── demoPipeline.ts             # Default IoT pipeline (7 nodes)
```

## Components

### Pipeline Editor (`components/pipeline/`)

| Component | Purpose |
|-----------|---------|
| **PipelineEditor** | React Flow canvas with drag-and-drop. Loads default demo pipeline on mount. Updates edge labels with live throughput from metrics store. Deploy/stop controls. |
| **CustomNodes** | Renders each node with type badge (source/operator/sink), operator label, live EPS + latency metrics, health indicator glow, and input/output handles. Color-coded by node type. |
| **CustomEdges** | Bezier edges with animated dashed stroke when pipeline is active. Shows events/second label. Animation speed varies with throughput. |
| **NodePalette** | 3 groups (Sources: 3, Operators: 5, Sinks: 4) with draggable items. Each shows icon and color. |
| **NodeConfigPanel** | Dynamic form that adapts to operator type. Text/number/select inputs for all OperatorConfig fields. |

### Dashboard (`components/dashboard/`)

| Component | Purpose |
|-----------|---------|
| **Dashboard** | 2x2 responsive grid containing all 4 panels |
| **MetricsPanel** | Recharts line chart showing throughput history. Displays total EPS, total events, worker count. |
| **HealthPanel** | Per-worker health cards with score (0-100), color status, CPU/memory/latency breakdown. Computes average cluster health. |
| **HealingLog** | Chronological feed of healing events (restart, migrate, scale-out, failover) with icons, timing, and details. |
| **OptimizationLog** | Feed of optimization events (pushdown, fusion, parallel, buffer) with estimated gains and worker changes. |

### Other Views

| Component | Purpose |
|-----------|---------|
| **ChaosPanel** | Intensity selector (low/med/high), duration slider, start/stop button, 6 scenario descriptions, live event feed with severity badges |
| **LineagePanel** | Event ID search input → vertical timeline showing event journey through each pipeline stage with processing times |
| **VersionHistory** | Timeline of versions with trigger badges (USER/AUTO_OPTIMIZE/AUTO_HEAL/ROLLBACK), diff viewer, rollback confirmation |
| **VisualDiff** | Stats summary + color-coded changes: green (added), red (removed), yellow (modified), old→new config values |
| **DLQPanel** | Summary stats, failure groups with suggestions, individual failed event details |
| **ABTestPanel** | Test creation form, active tests list, metric comparison bars with green winner highlight |

## State Management (Zustand)

### pipelineStore
```typescript
{
  pipeline: Pipeline | null,       // Current pipeline definition
  versions: PipelineVersion[],     // Version history
  selectedNodeId: string | null,   // Selected node for config panel
  isDirty: boolean                 // Unsaved changes flag
}
```

### metricsStore
```typescript
{
  metrics: PipelineMetrics | null,            // Latest metrics snapshot
  workerHealth: Record<string, WorkerHealth>, // Per-worker health
  healingLog: HealingEvent[],                 // Healing history
  optimizationLog: OptimizationEvent[],       // Optimization history
  throughputHistory: {time, eps}[]            // Chart data
}
```

### chaosStore
```typescript
{
  active: boolean,         // Chaos mode on/off
  intensity: string,       // low | medium | high
  events: ChaosEvent[]     // Chaos event log
}
```

## WebSocket Events

The `useWebSocket` hook connects to `WS /api/ws/pipeline/:id` and dispatches events to stores:

| Event | Store Action |
|-------|-------------|
| `pipeline.metrics` | `metricsStore.setMetrics()` + derive `workerHealth` (CPU 30%, Mem 30%, Throughput 20%, Latency 20%) |
| `worker.recovered` | `metricsStore.addHealingEvent()` |
| `worker.scaled` | `metricsStore.addHealingEvent()` |
| `optimizer.applied` | `metricsStore.addOptimizationEvent()` |
| `chaos.event` | `chaosStore.addEvent()` |
| `chaos.started` | `chaosStore.setActive(true)` |
| `chaos.stopped` | `chaosStore.setActive(false)` |

## Custom Theme

FlowStorm uses a dark theme via Tailwind config:

| Token | Color | Usage |
|-------|-------|-------|
| `flowstorm-bg` | `#0f1117` | Page background |
| `flowstorm-surface` | `#1a1d27` | Card/panel background |
| `flowstorm-border` | `#2a2d3a` | Borders |
| `flowstorm-primary` | `#6366f1` | Primary actions (indigo) |
| `flowstorm-secondary` | `#8b5cf6` | Secondary elements (purple) |
| `flowstorm-success` | `#22c55e` | Healthy status (green) |
| `flowstorm-warning` | `#f59e0b` | Degraded status (amber) |
| `flowstorm-danger` | `#ef4444` | Critical status (red) |

## Development

```bash
npm install          # Install dependencies
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Production build
npm test             # Run Vitest test suite
npm run lint         # ESLint check
```

## API Client

All backend communication goes through `services/api.ts`:

```typescript
// Pipeline lifecycle
api.createPipeline(data)     // POST /api/pipelines
api.deletePipeline(id)       // DELETE /api/pipelines/:id

// Real-time features
api.startChaos(id, intensity, duration)
api.getHealth(id)
api.getDLQ(id, count)
api.getVersions(id)
api.getLineage(pipelineId, eventId)

// Demo mode
api.startDemo()              // POST /api/demo/start
api.stopDemo()               // POST /api/demo/stop
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | 18.2 | UI framework |
| `reactflow` | 11.10 | Visual DAG editor with drag-and-drop |
| `zustand` | 4.5 | Lightweight state management |
| `recharts` | 2.12 | Throughput and metrics charts |
| `framer-motion` | 11.0 | Animations and transitions |
| `tailwindcss` | 3.4 | Utility-first CSS styling |
| `vite` | 5.1 | Build tool + HMR dev server |
| `vitest` | 4.0 | Test framework |
