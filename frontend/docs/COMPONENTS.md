# FlowStorm Frontend Component Reference

This document covers all 19 components in the FlowStorm frontend, organized by directory. For each component: purpose, props, state dependencies, and key behaviors.

---

## Table of Contents

1. [Root Component](#root-component)
2. [Pipeline Components](#pipeline-components-componentspipeline)
3. [Dashboard Components](#dashboard-components-componentsdashboard)
4. [Chaos Components](#chaos-components-componentschaos)
5. [Lineage Components](#lineage-components-componentslineage)
6. [Git Components](#git-components-componentsgit)
7. [DLQ Components](#dlq-components-componentsdlq)
8. [A/B Testing Components](#ab-testing-components-componentsab)
9. [Common Components](#common-components-componentscommon)

---

## Root Component

### App (`src/App.tsx`)

**Purpose**: Application root. Manages pipeline lifecycle state, view routing, demo mode, and WebSocket connection initialization.

**Props**: None (root component).

**Local State**:

| State | Type | Default | Description |
|-------|------|---------|-------------|
| `activeView` | `View` | From URL hash or `"pipeline"` | Currently displayed view |
| `pipelineId` | `string \| null` | `null` | Active pipeline identifier |
| `pipelineName` | `string` | `"Untitled Pipeline"` | Editable pipeline name |
| `pipelineStatus` | `string` | `"draft"` | Pipeline lifecycle status |
| `demoRunning` | `boolean` | `false` | Whether demo mode is active |

**Store Dependencies**: None directly (stores are consumed by child components).

**Hook Dependencies**: `useWebSocket(pipelineId)` -- connects/disconnects WebSocket when `pipelineId` changes.

**Key Behaviors**:

- Hash-based routing: reads `window.location.hash` on load, writes it when `activeView` changes
- Validates hash against `VALID_VIEWS` array; invalid hashes default to `"pipeline"`
- `handleStartDemo()`: calls `api.startDemo()`, sets pipeline ID, name, and status to `"running"`
- `handleStopDemo()`: calls `api.stopDemo()`, clears pipeline ID, sets status to `"stopped"`
- `handleDeploy(nodes, edges)`: calls `api.createPipeline(...)`, transitions status through `"deploying"` to `"running"` or `"failed"`
- `handleStop()`: calls `api.deletePipeline(pipelineId)`, clears pipeline ID
- Renders `Header` + `Sidebar` + one active view via `renderView()` switch

---

## Pipeline Components (`components/pipeline/`)

### PipelineEditor (`src/components/pipeline/PipelineEditor.tsx`)

**Purpose**: Main visual DAG editor. Wraps React Flow canvas with a node palette, deploy controls, and a configuration panel.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `onDeploy` | `(nodes, edges) => void` | Callback to deploy the current pipeline graph |
| `onStop` | `() => void` | Callback to stop the running pipeline |
| `pipelineId` | `string \| null` | Currently active pipeline ID |
| `pipelineStatus` | `string` | Current pipeline lifecycle status |

**Local State**:

| State | Type | Description |
|-------|------|-------------|
| `nodes` | `Node[]` | React Flow node array (initialized with demo pipeline) |
| `edges` | `Edge[]` | React Flow edge array (initialized with demo edges) |
| `selectedNode` | `Node \| null` | Currently clicked node for config panel |
| `reactFlowInstance` | `ReactFlowInstance \| null` | Flow instance for coordinate projection |

**Store Dependencies**:
- `pipelineStore.selectNode` -- syncs selection to global store
- `metricsStore.metrics` -- reads live worker metrics to update edge throughput labels

**Key Behaviors**:

- Loads default 7-node IoT demo pipeline (`getDemoNodes()`, `getDemoEdges()`) on mount so the editor is never empty
- **Live edge updates**: `useEffect` watching `metrics` builds a `node_id -> eps` map from worker metrics, then updates each edge's `data.events_per_second` only when the value actually changes
- **Drag-and-drop**: `onDrop` reads `operator_type` from `dataTransfer`, projects mouse coordinates to canvas coordinates via `reactFlowInstance.project()`, and creates a new node
- **Node ID generation**: Uses a module-level counter `nodeIdCounter` producing IDs like `n-1`, `n-2`, etc.
- **Deploy**: Transforms React Flow nodes/edges to API format (flat objects with `position_x`/`position_y`) and calls `onDeploy`
- **Config changes**: `handleConfigChange(nodeId, config)` immutably updates a node's `data.config`
- **Canvas features**: 16px snap grid, background grid, zoom controls, color-coded MiniMap
- **Deploy button states**: disabled when no nodes or already running/deploying; shows spinner during deploying
- Injects `@keyframes flowDash` CSS for animated edges

### CustomNodes / FlowStormNode (`src/components/pipeline/CustomNodes.tsx`)

**Purpose**: Custom React Flow node renderer. Displays node metadata, live metrics, and health status with visual indicators.

**Props** (via React Flow `NodeProps<FlowStormNodeData>`):

| Data Field | Type | Description |
|------------|------|-------------|
| `label` | `string` | Display name |
| `operatorType` | `OperatorType` | One of 12 operator types |
| `nodeType` | `NodeType` | `"source"`, `"operator"`, or `"sink"` |
| `nodeId` | `string` | Node identifier for metrics lookup |
| `config` | `Record<string, unknown>` | Operator configuration |

**Store Dependencies**:
- `metricsStore.metrics` -- finds worker metrics matching this node's ID
- `metricsStore.workerHealth` -- reads pre-computed health score for the worker

**Key Behaviors**:

- **Memoized**: Wrapped in `React.memo` to prevent unnecessary re-renders
- **Health derivation**: Uses `workerHealth` from store if available; falls back to computing from raw metrics
- **Visual indicators**: Border color reflects health status (green/amber/red) when metrics are present, otherwise uses node type color. Pulsing health dot in top-right corner and box-shadow glow when active.
- **Conditional handles**: Source nodes have no input handle; sink nodes have no output handle
- **Metrics display**: Shows EPS and latency only when worker metrics exist
- Exported as `nodeTypes = { flowstorm: CustomNode }` for React Flow registration

### CustomEdges / FlowStormEdge (`src/components/pipeline/CustomEdges.tsx`)

**Purpose**: Custom React Flow edge renderer. Renders bezier paths with animated flow indicators and throughput labels.

**Props** (via React Flow `EdgeProps`):

| Prop | Type | Description |
|------|------|-------------|
| `sourceX/Y`, `targetX/Y` | `number` | Edge endpoint coordinates |
| `sourcePosition`, `targetPosition` | `Position` | Handle positions |
| `data` | `object` | Contains `events_per_second` |

**Key Behaviors**:

- **Memoized**: Wrapped in `React.memo`
- **Dual-path rendering**: A static background path (`#2a2d3a`, 3px) plus an animated overlay path (`#6366f1`, 2px) that only renders when `eps > 0`
- **Adaptive animation speed**: `animationDuration = Math.max(0.5, 5 / Math.log2(eps + 1))` -- higher throughput means faster animation
- **Throughput label**: `foreignObject` element at the edge midpoint showing `"{eps}/s"` in a small bordered pill
- Exported as `edgeTypes = { flowstorm: CustomEdge }` for React Flow registration

### NodePalette (`src/components/pipeline/NodePalette.tsx`)

**Purpose**: Side panel listing all available operator types organized in three groups for drag-and-drop onto the canvas.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `onDragStart` | `(operatorType: OperatorType) => void` | Callback when drag begins |

**Key Behaviors**:

- Renders 3 groups: Sources (2 items: MQTT Source, Simulator), Operators (5 items: Filter, Map, Window, Aggregate, Join), Sinks (4 items: Console, Redis, Alert, Webhook)
- Each item is a `draggable` div that sets `operator_type` in `dataTransfer` on drag start
- Items show a color-coded icon badge (color matches node type: blue/purple/green) and the operator label
- Fixed width of `w-56` (224px) on the left side of the editor
- Hover state highlights border with primary color

### NodeConfigPanel (`src/components/pipeline/NodeConfigPanel.tsx`)

**Purpose**: Right-side panel showing a dynamic configuration form when a node is selected. Form fields adapt to the operator type.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `node` | `Node` | The selected React Flow node |
| `onConfigChange` | `(nodeId: string, config: Record<string, unknown>) => void` | Callback on config update |
| `onClose` | `() => void` | Close/deselect callback |

**Local State**:
- `config: Record<string, unknown>` -- local copy of node config, synced on node change via `useEffect`

**Key Behaviors**:

- **Dynamic field rendering**: Uses `OPERATOR_FIELDS` map (keyed by operator type) to determine which fields to show. Supports `text`, `number`, and `select` field types.
- **Operator-specific fields**: Each of the 12 operator types has its own field set defined in `OPERATOR_FIELDS`. Sources configure connection details (topics, ports), operators configure processing logic (conditions, expressions, windows, aggregations), and sinks configure output targets (URLs, key prefixes). `console_sink` requires no configuration.
- **Auto-save**: Changes are propagated immediately via `onConfigChange` on every keystroke
- **Type coercion**: Number fields are parsed to `Number` before saving
- **Node info display**: Shows node label, type badge with color, operator type, and node ID
- Fixed width of `w-72` (288px) on the right side of the editor

---

## Dashboard Components (`components/dashboard/`)

### Dashboard (`src/components/dashboard/Dashboard.tsx`)

**Purpose**: Container component that arranges the four monitoring panels in a 2x2 responsive grid.

**Props**: None.

**Key Behaviors**:

- Renders a `grid grid-cols-2 gap-4` layout
- Contains: MetricsPanel (top-left), HealthPanel (top-right), HealingLog (bottom-left), OptimizationLog (bottom-right)
- Full height with vertical scroll overflow
- No local state or store dependencies (pure layout component)

### MetricsPanel (`src/components/dashboard/MetricsPanel.tsx`)

**Purpose**: Displays pipeline throughput metrics with a Recharts line chart and key statistics.

**Props**: None.

**Store Dependencies**:
- `metricsStore.metrics` -- current metrics snapshot
- `metricsStore.throughputHistory` -- array of `{ time, eps }` for the chart

**Key Behaviors**:

- **Key stats grid**: Three cards showing Events/sec, Total Events, and Worker count
- **Line chart**: Recharts `LineChart` with `ResponsiveContainer`, plotting `eps` over `time`
- Chart shows last 60 data points (controlled by store's throughput history cap)
- Uses indigo stroke (`#6366f1`) for the line, dark-themed tooltip
- Displays `0` for all values when no metrics are available

### HealthPanel (`src/components/dashboard/HealthPanel.tsx`)

**Purpose**: Shows per-worker health scores with an overall cluster health bar.

**Props**: None.

**Store Dependencies**:
- `metricsStore.metrics` -- reads `metrics.workers` to list all active workers
- `metricsStore.workerHealth` -- reads pre-computed health scores per worker

**Key Behaviors**:

- **Overall health bar**: Computes average of all worker health scores, displays as a colored progress bar
- **Worker list**: Scrollable list (max-height 192px) of worker cards showing:
  - Health status dot (colored by score threshold)
  - Node ID
  - Events/sec and latency
  - Health score percentage
  - CPU percentage
- Uses `getHealthStatus()` and `HEALTH_COLORS` from `types/metrics.ts` for consistent color coding
- Shows "No active workers" placeholder when empty

### HealingLog (`src/components/dashboard/HealingLog.tsx`)

**Purpose**: Chronological feed of self-healing events with action icons, status badges, and metadata.

**Props**: None.

**Store Dependencies**:
- `metricsStore.healingLog` -- array of `HealingEvent` objects (newest first, capped at 100)

**Key Behaviors**:

- **Action icons and colors**: Four types: `restart_worker` (R, amber), `migrate_worker` (M, blue), `scale_out` (S, purple), `checkpoint_replay` (C, green)
- **Event cards**: Each shows action name, success/failure badge (green "OK" or red "FAIL"), details text, target node, trigger reason, duration in ms, and events replayed count
- **Timestamps**: Formatted via `toLocaleTimeString()`
- **Empty state**: Descriptive message explaining that the engine will auto-heal when anomalies are detected
- Active indicator dot in the header (pulsing green)
- Scrollable container capped at `max-h-56` (224px)

### OptimizationLog (`src/components/dashboard/OptimizationLog.tsx`)

**Purpose**: Feed of DAG optimization events with type icons, descriptions, and performance impact.

**Props**: None.

**Store Dependencies**:
- `metricsStore.optimizationLog` -- array of `OptimizationEvent` objects (newest first, capped at 50)

**Key Behaviors**:

- **Optimization type icons and colors**: Four optimization types:
  - `predicate_pushdown` -> "PP" (purple)
  - `operator_fusion` -> "OF" (blue)
  - `auto_parallel` -> "AP" (amber)
  - `buffer_insertion` -> "BI" (green)
- **Event cards**: Each shows optimization type name, description, estimated gain (green text), workers added (primary color), workers removed (danger color), and duration
- **Counter badge**: Header shows total count of applied optimizations
- **Empty state**: Explains that the engine will auto-optimize based on live metrics
- Scrollable container capped at `max-h-56` (224px)

---

## Chaos Components (`components/chaos/`)

### ChaosPanel (`src/components/chaos/ChaosPanel.tsx`)

**Purpose**: Full chaos engineering interface with intensity configuration, start/stop controls, scenario descriptions, and a live event feed.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID (required for chaos operations) |

**Local State**:

| State | Type | Default | Description |
|-------|------|---------|-------------|
| `selectedIntensity` | `string` | From store's `intensity` | Selected chaos level |
| `duration` | `number` | `60` | Chaos duration in seconds |
| `loading` | `boolean` | `false` | API call in progress |
| `error` | `string \| null` | `null` | Last error message |

**Store Dependencies**:
- `chaosStore.active` -- whether chaos is currently running
- `chaosStore.intensity` -- current intensity level
- `chaosStore.events` -- chaos event log
- `chaosStore.setActive` -- toggle chaos state

**Key Behaviors**:

- **Gated on pipelineId**: Shows "Deploy a pipeline first" message when no pipeline is active
- **Intensity selector**: Three buttons (Low/Medium/High) with descriptions, disabled during active chaos
- **Duration slider**: Range input from 15s to 300s in 15s steps
- **Start/Stop**: Calls `api.startChaos()` or `api.stopChaos()` and updates local/store state
- **Scenario descriptions**: 6 static scenarios displayed (Kill Worker, Inject Latency, Corrupt Events, Memory Pressure, Flood Source, Network Partition)
- **Event feed**: Scrollable list (max-height 256px) of chaos events with severity badges:
  - `high` -> red badge
  - `medium` -> yellow badge
  - `low` -> blue badge
- **Active indicator**: Red pulsing "CHAOS ACTIVE" badge in the header when active

---

## Lineage Components (`components/lineage/`)

### LineagePanel (`src/components/lineage/LineagePanel.tsx`)

**Purpose**: Event lineage tracing interface. Search for an event ID and visualize its journey through every pipeline stage.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID |

**Local State**:

| State | Type | Description |
|-------|------|-------------|
| `eventId` | `string` | Search input value |
| `lineage` | `LineageResult \| null` | Trace result with array of lineage entries |
| `loading` | `boolean` | API call in progress |
| `error` | `string \| null` | Last error message |

**Local Types**:
- `LineageEntry`: `{ node_id, operator_type, timestamp, input_event_id?, output_event_id?, processing_time_ms? }`
- `LineageResult`: `{ event_id, pipeline_id, lineage: LineageEntry[] }`

**Key Behaviors**:

- **Search**: Text input with Enter key support and a "Trace" button; calls `api.getLineage(pipelineId, eventId)`
- **Vertical timeline visualization**: Each lineage entry renders as a numbered circle (blue=source, purple=operator, green=sink) connected by a vertical line, with node ID, operator type badge, processing time, and timestamp
- **Instructions panel**: Shows when no trace has been performed, explaining how lineage works with a color legend
- **Gated on pipelineId**: Shows placeholder when no pipeline is active

---

## Git Components (`components/git/`)

### VersionHistory (`src/components/git/VersionHistory.tsx`)

**Purpose**: Pipeline version timeline with diff viewing and rollback capabilities.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID |

**Local State**:

| State | Type | Description |
|-------|------|-------------|
| `loading` | `boolean` | Version list loading |
| `diffLoading` | `boolean` | Diff computation loading |
| `error` | `string \| null` | Last error message |
| `selectedDiff` | `PipelineDiff \| null` | Currently displayed diff |
| `compareFrom` | `number \| null` | Source version for diff |
| `compareTo` | `number \| null` | Target version for diff |
| `rollbackTarget` | `number \| null` | Version ID for rollback confirmation |
| `rollbackLoading` | `boolean` | Rollback in progress |

**Store Dependencies**:
- `pipelineStore.versions` -- version list
- `pipelineStore.setVersions` -- update version list

**Key Behaviors**:

- **Auto-load**: Fetches versions via `api.getVersions()` when `pipelineId` changes
- **Two-panel layout**: Left panel (w-72) shows version timeline; right panel shows diff
- **Version timeline**: Vertical timeline with colored dots per trigger type: USER (blue), AUTO_OPTIMIZE (purple), AUTO_HEAL (green), ROLLBACK (red)
- **Version cards**: Show trigger badge, timestamp, description, node/edge counts, and Diff/Rollback action buttons
- **Diff**: Calls `api.diffVersions(pipelineId, from, to)` and passes result to `VisualDiff`
- **Rollback**: Shows confirmation modal with version number. Calls `api.rollback(pipelineId, versionId)`, then reloads versions. Warns that current state will be saved before rolling back.
- **Refresh button**: Manual reload of version list

### VisualDiff (`src/components/git/VisualDiff.tsx`)

**Purpose**: Renders a visual diff between two pipeline versions, showing node and edge changes with color coding.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `diff` | `PipelineDiff` | Diff data with node_diffs and edge_diffs |
| `versionFrom` | `number` | Source version number |
| `versionTo` | `number` | Target version number |

**Key Behaviors**:

- **Stats header**: Shows counts of added/removed/modified nodes and added/removed edges with color coding
- **Summary text**: Displays the diff summary string
- **Change type color coding**:
  - Added: green background/text
  - Removed: red background/text
  - Modified: yellow background/text
  - Moved: blue background/text
  - Unchanged: muted (filtered out of display)
- **Node changes section**: For each changed node, shows change type badge, node label, node ID, config changes (old value with strikethrough -> new value), and position change indicator
- **Edge changes section**: For each changed edge, shows change type badge and `source -> target` IDs
- **Filters**: Only displays nodes/edges where `change_type !== "unchanged"`
- **Empty state**: "No changes between these versions" when both lists are empty

---

## DLQ Components (`components/dlq/`)

### DLQPanel (`src/components/dlq/DLQPanel.tsx`)

**Purpose**: Dead letter queue viewer with summary statistics, failure group analysis with fix suggestions, and individual failed event details.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID |

**Local State**:

| State | Type | Description |
|-------|------|-------------|
| `stats` | `DLQStats \| null` | Summary statistics and failure groups |
| `entries` | `DLQEntry[]` | Individual failed events |
| `loading` | `boolean` | Data loading state |
| `selectedGroup` | `string \| null` | Currently filtered failure type |

**Local Types**:
- `DLQStats`: `{ total_failed, groups: [{ failure_type, count, affected_nodes, suggestions }], by_node }`
- `DLQEntry`: `{ event_id, node_id, error_message, failure_type, suggestions, timestamp }`

**Key Behaviors**:

- **Auto-load**: Fetches both stats (`api.getDLQStats()`) and entries (`api.getDLQ(id, 50)`) in parallel when `pipelineId` changes
- **Summary stats**: Three cards showing Total Failed (red), Failure Types count, and Affected Nodes count
- **Failure groups**: Clickable cards that act as toggleable filters. Each shows failure type badge (color-coded: orange for `missing_field`, yellow for `type_mismatch`, blue for `null_value`, red for `schema_violation`/`operator_error`, purple for `timeout`), event count, affected nodes, and fix suggestions
- **Filtering**: Clicking a group filters the entry list to that type; clicking again clears
- **Individual entries**: Shows up to 20 entries with event ID, timestamp, error message, and node ID
- **Refresh button**: Manual reload of data
- **Zero-failure state**: Clean "No failed events" display when `total_failed === 0`

---

## A/B Testing Components (`components/ab/`)

### ABTestPanel (`src/components/ab/ABTestPanel.tsx`)

**Purpose**: A/B pipeline testing interface for creating tests, viewing active tests, and comparing performance metrics between two pipeline versions.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID (used as Version A) |

**Local State**:

| State | Type | Description |
|-------|------|-------------|
| `tests` | `ABTest[]` | List of active tests |
| `selectedResult` | `ABTestResult \| null` | Currently viewed test result |
| `creating` | `boolean` | Whether create form is visible |
| `pipelineIdB` | `string` | Version B pipeline ID input |
| `splitPercent` | `number` | Traffic split percentage (10-90) |
| `testName` | `string` | Optional test name |

**Local Types**:
- `ABTest`: `{ test_id, name, pipeline_a, pipeline_b, split_percent_a, samples_a, samples_b }`
- `ABTestResult`: `{ test_id, name, version_a: { metrics... }, version_b: { metrics... }, winner, summary, duration_seconds }`

**Key Behaviors**:

- **Auto-load**: Fetches test list via `api.listABTests()` on mount
- **Create form**: Toggle-able form with Version A (read-only, current pipeline), Version B text input, optional test name, and traffic split slider (10-90% in 10% steps). Calls `api.createABTest()`.
- **Active tests list**: Each test card shows name/ID, pipeline IDs with split percentages, sample counts, and Results/Stop action buttons
- **Results view**: Calls `api.getABTest(testId)` to fetch comparative results
- **Stop test**: Calls `api.stopABTest(testId)`, shows final results, reloads test list
- **MetricBar sub-component**: Side-by-side horizontal bars comparing A vs B across throughput (e/s), latency (ms), CPU (%), and errors. Uses `lowerIsBetter` flag per metric. Winning bar is green; loser uses type color (blue=A, purple=B).
- **Winner badge**: Displayed in the results header when a winner is determined

---

## Common Components (`components/common/`)

### Header (`src/components/common/Header.tsx`)

**Purpose**: Top navigation bar showing the FlowStorm logo, editable pipeline name, status badge, live metrics indicators, chaos indicator, demo controls, and connection status.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `pipelineId` | `string \| null` | Active pipeline ID |
| `pipelineName` | `string` | Current pipeline name |
| `pipelineStatus` | `string` | Pipeline lifecycle status |
| `onNameChange` | `(name: string) => void` | Pipeline rename callback |
| `onStartDemo` | `() => void` (optional) | Start demo callback |
| `onStopDemo` | `() => void` (optional) | Stop demo callback |
| `demoRunning` | `boolean` (optional) | Whether demo mode is active |

**Local State**:
- `editing: boolean` -- whether the pipeline name input is in edit mode

**Store Dependencies**:
- `metricsStore.metrics` -- reads `total_events_per_second` and `active_workers` for status indicators
- `chaosStore.active` -- shows red "CHAOS" badge when active

**Key Behaviors**:

- **Logo**: Gradient indigo-to-purple badge with "FS" text and "FlowStorm" label
- **Editable name**: Clicking the name switches to an input field; pressing Enter or blurring saves
- **Status badge**: Color-coded (draft/stopped=gray, deploying=yellow, running=green, paused=blue, failed=red) with animated pulse dot for `deploying` and `running`
- **Live indicators** (shown when metrics exist): Events/sec with green pulsing dot, and worker count
- **Chaos indicator**: Red pulsing "CHAOS" badge when `chaosStore.active` is true
- **Demo button**: Toggles between "Start Demo" (indigo) and "Stop Demo" (red)
- **Connection dot**: Green when `pipelineId` exists ("Connected"), gray otherwise ("No Pipeline")
- Fixed height of `h-12` (48px)

### Sidebar (`src/components/common/Sidebar.tsx`)

**Purpose**: Vertical navigation rail with icon buttons for 7 application views.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `activeView` | `View` | Currently active view |
| `onViewChange` | `(view: View) => void` | View change callback |

**Exports**: `type View = "pipeline" | "dashboard" | "chaos" | "lineage" | "git" | "dlq" | "ab"`

**Key Behaviors**:

- **7 navigation items**: Pipeline (P), Dashboard (D), Chaos (C), Lineage (L), Git (G), DLQ (Q), A/B (AB) -- each with icon, short label, and hover tooltip showing a description
- **Active state**: Active view button gets indigo background and primary text color
- **Hover tooltip**: Positioned to the right of the button, appears on hover
- Fixed width of `w-14` (56px) with 40x40px icon buttons; compact two-line layout (icon + label)

---

## Component-Store Dependency Matrix

| Component | pipelineStore | metricsStore | chaosStore |
|-----------|:---:|:---:|:---:|
| App | - | - | - |
| PipelineEditor | selectNode | metrics | - |
| CustomNodes | - | metrics, workerHealth | - |
| CustomEdges | - | - | - |
| NodePalette | - | - | - |
| NodeConfigPanel | - | - | - |
| Dashboard | - | - | - |
| MetricsPanel | - | metrics, throughputHistory | - |
| HealthPanel | - | metrics, workerHealth | - |
| HealingLog | - | healingLog | - |
| OptimizationLog | - | optimizationLog | - |
| ChaosPanel | - | - | active, intensity, events |
| LineagePanel | - | - | - |
| VersionHistory | versions, setVersions | - | - |
| VisualDiff | - | - | - |
| DLQPanel | - | - | - |
| ABTestPanel | - | - | - |
| Header | - | metrics | active |
| Sidebar | - | - | - |

---

## Component-API Dependency Matrix

Components that make direct REST API calls:

| Component | API Methods Used |
|-----------|-----------------|
| App | `api.startDemo()`, `api.stopDemo()`, `api.createPipeline()`, `api.deletePipeline()` |
| ChaosPanel | `api.startChaos()`, `api.stopChaos()` |
| LineagePanel | `api.getLineage()` |
| VersionHistory | `api.getVersions()`, `api.diffVersions()`, `api.rollback()` |
| DLQPanel | `api.getDLQStats()`, `api.getDLQ()` |
| ABTestPanel | `api.listABTests()`, `api.createABTest()`, `api.getABTest()`, `api.stopABTest()` |
