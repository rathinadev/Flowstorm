# FlowStorm - Complete Technical Reference
## All States, Triggers, and Detection Factors

---

# 🔴 SELF-HEALING SYSTEM

## Health Score Calculation (Weighted)

| Factor | Weight | Threshold | Description |
|--------|--------|-----------|------------|
| CPU | 30% | >80% = critical | Average CPU utilization |
| Memory | 30% | >80% = critical | Average memory usage |
| Throughput | 20% | <50% drop = critical | Events per second |
| Latency | 20% | >500ms = critical | Average processing latency |

**Formula:** `health_score = (100 - cpu) * 0.30 + (100 - mem) * 0.30 + throughput_weight * 0.20 + latency_weight * 0.20`

---

## Anomaly Types Detected

| Anomaly | Detection Method | Indicator |
|---------|-----------------|---------------|
| **Throughput Drop** | Current EPS < 50% of moving average | Events/sec falls dramatically |
| **Error Spike** | Error count > threshold in window | Errors increase suddenly |
| **Memory Leak** | Memory increases for N consecutive readings | Memory keeps growing |
| **Latency Spike** | Latency > 500ms for N readings | Processing gets slow |
| **Worker Death** | No heartbeat for 3 intervals | Worker stops responding |
| **Consumer Lag** | Kafka/Redis lag > threshold | Backlog building |

---

## Healing Actions (4 Types)

| Action | When Triggered | Recovery Method |
|--------|---------------|----------------|
| **Restart** | Worker unhealthy but exists | Stop, clear state, restart process |
| **Migrate** | Node health degraded | Move operator to healthier node |
| **Scale Out** | CPU > 80% sustained | Add parallel worker instances |
| **Failover** | Worker died completely | Restart on new node + replay from checkpoint |

---

## Healing Triggers

| Trigger Type | Source | Timing |
|-------------|--------|--------|
| **Auto Timer** | Main loop tick | Every ~10 seconds |
| **Chaos-Triggered** | After chaos event | 2-5 seconds after chaos |
| **Manual** | API call | On-demand |

---

# 🟡 AUTO-OPTIMIZATION SYSTEM

## Optimization Types (5 Types)

| Optimization | What It Does | Gain | Trigger Condition |
|--------------|--------------|------|------------------|
| **Predicate Pushdown** | Move filters earlier in pipeline | 25-40% throughput | Filter selectivity >70% |
| **Operator Fusion** | Merge consecutive map/filter ops | 40-60% less overhead | Adjacent map ops found |
| **Auto-Parallelization** | Split hot operator to N workers | Near-linear speedup | CPU > 85% sustained |
| **Buffer Insertion** | Add async buffer between ops | Reduces backpressure | Latency spikes detected |
| **Window Optimization** | Switch time-window to count-window | Lower memory | Data pattern changes |

---

## Optimization Triggers

| Trigger Type | Source | Timing |
|-------------|--------|--------|
| **Timer** | Main loop tick | Every ~20 seconds |
| **CPU-Based** | High CPU detected | CPU > 85% for 10s |
| **Manual** | API call | On-demand |

---

# 🔵 CHAOS ENGINEERING

## Chaos Scenarios (6 Types)

| Scenario | Severity | What It Does | Detection |
|---------|----------|-------------|----------|
| **Kill Worker** | High | Terminates random worker process | Worker death → failover |
| **CPU Stress** | Medium | Spikes container CPU to 100% | High CPU → heal |
| **Network Delay** | Medium | Adds 100-500ms latency between ops | Latency spike |
| **Memory Pressure** | High | Forces memory exhaustion | OOM trigger |
| **Event Corruption** | Low | Injects malformed events | DLQ entry |
| **Network Partition** | Critical | Isolates worker from cluster | Worker appears dead |

---

## Chaos Severity Levels

| Level | Behavior |
|-------|----------|
| **Low** | Single scenario, short duration |
| **Medium** | Single scenario, medium duration |
| **High** | Multiple scenarios, long duration |

---

# 🟠 DLQ FAILURE TYPES

## Failure Classification (6 Types)

| Failure Type | Error Example | Suggestion |
|-------------|--------------|-----------|
| **missing_field** | `KeyError: 'temperature'` | Add default value, add schema validation |
| **type_mismatch** | `TypeError: expected float, got str` | Add type coercion |
| **null_value** | `NullPointerError: 'sensor_id' is null` | Add null check, filter nulls |
| **operator_error** | `Division by zero in avg()` | Add guard for empty windows |
| **schema_violation** | `unexpected field 'temp_celsius'` | Update schema, add mapping |
| **timeout** | `Redis write timed out` | Increase timeout, check load |

---

# 🟢 PIPELINE GIT

## Version Triggers (5 Types)

| Trigger | Source | Description |
|---------|--------|-------------|
| **USER** | Manual edit | User modified pipeline |
| **AUTO_HEAL** | Healing action | System healed a failure |
| **AUTO_OPTIMIZE** | Optimization | System optimized DAG |
| **ROLLBACK** | Manual | User rolled back |
| **AB_TEST** | A/B test | Test variant created |

---

# 🔵 WORKER STATES

## Worker Lifecycle States

| State | Description | Color in UI |
|-------|-------------|-------------|
| **Starting** | Container starting up | Yellow |
| **Running** | Processing normally | Green |
| **Degraded** | Health < 70% | Yellow |
| **Critical** | Health < 30% | Red |
| **Restarting** | Being restarted | Yellow |
| **Dead** | No heartbeat | Gray |

---

# 📊 METRICS COLLECTED

## Per-Worker Metrics

| Metric | Update Frequency | Description |
|--------|------------------|-------------|
| CPU | Every 500ms | CPU usage % |
| Memory | Every 500ms | Memory usage % |
| Events/sec | Every 500ms | Throughput |
| Events Processed | Every 500ms | Total count |
| Latency | Every 500ms | Avg processing time |
| Errors | Every 500ms | Error count |

---

# ⚙️ PIPELINE OPERATORS

## Source Operators (3)

| Operator | Description | Config |
|----------|-------------|--------|
| **MQTT Source** | Subscribe to MQTT topic | broker, topic, QoS |
| **HTTP Source** | Poll HTTP endpoint | url, interval |
| **Simulator** | Generate test data | sensor_count, interval |

## Processing Operators (5)

| Operator | Description | Config |
|----------|-------------|--------|
| **Filter** | Filter events by condition | field, condition, value |
| **Map** | Transform event fields | expression, output_field |
| **Window** | Time/count window aggregation | window_type, size |
| **Join** | Join two streams | stream, key, window |
| **Aggregate** | Aggregate with function | function, group_by |

## Sink Operators (4)

| Operator | Description | Config |
|----------|-------------|--------|
| **Console** | Print to console | - |
| **Redis** | Write to Redis | host, key |
| **Alert** | Send alert notification | channel, template |
| **Webhook** | POST to URL | url, payload |

---

# 🎯 EDGE THROUGHPUT LEVELS

| Throughput | Range | Color | Label |
|-----------|-------|-------|-------|
| **High** | >1000 e/s | Green | `>1k/s` |
| **Good** | 500-1000 e/s | Blue | `500-1k/s` |
| **Moderate** | 100-500 e/s | Yellow | `100-500/s` |
| **Low** | 1-100 e/s | Orange | `<100/s` |
| **None** | 0 e/s | Gray | `0/s` |

---

# ⏱️ TIMING REFERENCE

| Event | Frequency | Source |
|-------|-----------|--------|
| Metrics Update | 500ms | WebSocket |
| Health Check | 500ms | Heartbeat |
| Healing Event | ~10s | Timer + trigger |
| Optimization | ~20s | Timer + trigger |
| Chaos Event | ~10s | When active |

---

# 📋 KEYBOARD SHORTCUTS

| Key | Action |
|-----|--------|
| `Space` | Toggle demo |
| `D` | Dashboard |
| `P` | Pipeline Editor |
| `C` | Chaos |
| `G` | Pipeline Git |
| `L` | Lineage |
| `1-7` | Any view |

---

# 🏗️ ARCHITECTURE LAYERS

```
┌─────────────────────────────────────────┐
│  PRESENTATION LAYER                    │
│  React + TypeScript + React Flow       │
└──────────────┬──────────────────────┘
               WebSocket + REST
┌──────────────┴──────────────────────┐
│  CONTROL PLANE                     │
│  FastAPI + Python                 │
│  - DAG Compiler                   │
│  - Health Monitor (MAPE-K)        │
│  - Optimizer                     │
│  - Chaos Engine                  │
└──────────────┬──────────────────────┘
               Docker SDK
┌──────────────┴──────────────────────┐
│  DATA PLANE                        │
│  Workers (Containers)             │
│  Sources → Operators → Sinks     │
└──────────────┬──────────────────────┘
               Redis + PostgreSQL
┌──────────────┴──────────────────────┐
│  STORAGE                          │
│  Redis: Streams, Pub/Sub          │
│  PostgreSQL: Versions, Checkpoints│
└─────────────────────────────────────────┘
```

---

# ✅ THIS IS EVERYTHING YOU NEED TO KNOW!

Print or save this reference to study before the presentation.
All the states, triggers, timing, and possibilities are documented above.

**You're ready!** 🚀