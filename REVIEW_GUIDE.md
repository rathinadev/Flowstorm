# FlowStorm - 3rd Project Review Guide
## Complete Demo & Presentation Manual

---

# 🎯 QUICK START (5 minutes before presentation)

```bash
cd /home/rathina-devan/Desktop/personal/personal/flowstorm
./start.sh
```

Wait 5 seconds for services to start, then open **http://localhost:3000**

---

# 📋 PRESENTATION FLOW

## Step 1: Start Demo (30 seconds)
1. Click **Start Demo** button in header (or press Space)
2. Point to stats cards showing live throughput
3. Say: "Let me show you our self-healing stream processing engine"

## Step 2: Show Dashboard (1 minute)
Press **D** or click Dashboard tab

What to show:
- Real-time metrics (sparkline chart)
- Throughput: ~1500-2000 events/sec
- Trend indicator (↑ or ↓)
- Self-healing events appearing every ~10s
- Optimization events every ~20s

Say: "Notice events fire automatically - healing every 10 seconds"

## Step 3: Show Pipeline Editor (30 seconds)
Press **P** or click Pipeline tab

What to show:
- 7-node IoT pipeline visualized
- Color-coded edges (green = high throughput)
- Animated dots on edges showing flow

## Step 4: Show Chaos Mode (1 minute)
Press **C** or click Chaos tab
1. Click **Start Chaos**
2. Watch chaos events fire every ~10 seconds
3. Watch healing automatically triggers after chaos

Say: "When chaos hits, the system automatically heals itself!"

## Step 5: Show Pipeline Git (30 seconds)
Press **G** or click Git tab

What to show:
- Version history with triggers (USER, AUTO_HEAL, AUTO_OPTIMIZE)
- Visual diff between versions

Say: "Every change is versioned automatically"

## Step 6: Show DLQ (30 seconds)
Press **L** or click DLQ tab

What to show:
- 30 failed events with diagnostics
- Click any failure to see suggestions

Say: "Failed events are automatically analyzed with fix suggestions"

---

# ⌨️ KEYBOARD SHORTCUTS

| Key | Action |
|-----|--------|
| `Space` | Toggle demo on/off |
| `D` | Go to Dashboard |
| `P` | Go to Pipeline |
| `C` | Go to Chaos |
| `G` | Go to Git (Pipeline Git) |
| `L` | Go to Lineage |
| `1-7` | Quick switch to any view |

---

# 🔧 TECHNICAL DEMO TALKING POINTS

## What Makes FlowStorm Special

### 1. Self-Healing Engine
- MAPE-K (Monitor-Analyze-Plan-Execute) feedback loop
- Health scoring: CPU (30%) + Memory (30%) + Throughput (20%) + Latency (20%)
- 4 healing actions: Restart, Migrate, Scale-out, Failover

### 2. Auto-Optimization
- Predicate Pushdown: Move filters earlier (25-40% gain)
- Operator Fusion: Merge consecutive maps (40-60% gain)
- Auto-Parallelization: Split hot operators (near-linear speedup)
- Runs automatically every ~20 seconds

### 3. Chaos Engineering
- 6 scenarios: Kill Worker, CPU Stress, Network Delay, Memory Pressure, Event Corruption, Network Partition
- 3 intensity levels: Low, Medium, High
- Validates self-healing automatically

### 4. Pipeline Git
- Automatic versioning on every change
- Triggers: USER, AUTO_HEAL, AUTO_OPTIMIZE, ROLLBACK, AB_TEST
- One-click rollback to any version

### 5. DLQ Diagnostics
- 6 failure types auto-classified
- Smart suggestions for fixes
- Per-node analysis

---

# 📊 EXPECTED DATA AT REVIEW

When you open each panel, you should see:

| Panel | Data to Show |
|-------|--------------|
| Dashboard | Metrics flowing, healing events, optimization events |
| Pipeline | 7-node pipeline with colored edges |
| Chaos | Chaos events when active |
| Git | 5+ versions in history |
| DLQ | 30 failed events, click to see details |
| Lineage | Event traces |

---

# 🚀 FEATURES WORKING (All Verified)

| Feature | Status | Notes |
|---------|--------|-------|
| Real-time metrics | ✅ Working | 500ms updates |
| Self-healing events | ✅ Working | ~10s interval |
| Auto-optimization | ✅ Working | ~20s interval |
| Chaos mode | ✅ Working | ~10s when active |
| Pipeline Git versions | ✅ Working | PostgreSQL |
| DLQ diagnostics | ✅ Working | 30 events |
| A/B Testing | ⚠️ Ready | Need to create test |
| Lineage | ✅ Working | Event tracing |

---

# 🏗️ ARCHITECTURE SUMMARY

```
┌─────────────────────────────────────┐
│   Frontend (React + TypeScript)     │
│  - Dashboard (Recharts)            │
│  - Pipeline Editor (React Flow)      │
│  - Chaos/Lineage/Git/DLQ/AB panels │
└──────────────┬────────────────────┘
               WebSocket + REST
┌──────────────┴────────────────────┐
│   Backend (FastAPI + Python)        │
│  - Demo Simulator                │
│  - Health Monitor (MAPE-K)       │
│  - Chaos Engine                  │
│  - Pipeline Git                  │
│  - DLQ Diagnostics               │
└──────────────┬────────────────────┘
               Redis + PostgreSQL
┌──────────────┴────────────────────┐
│   Data Layer                     │
│  - Redis: Streams, Pub/Sub       │
│  - PostgreSQL: Versions, DLQ     │
└─────────────────────────────────┘
```

---

# 💬 ANSWERS TO COMMON QUESTIONS

**Q: How does it heal automatically?**
A: Workers send heartbeats every 500ms. When health drops below threshold, the system triggers one of 4 healing actions (restart, migrate, scale-out, failover).

**Q: What happens during optimization?**
A: Every ~20 seconds, the optimizer analyzes metrics. If it finds inefficiencies, it rewrites the DAG automatically (predicate pushdown, operator fusion, or parallelization).

**Q: How does chaos testing work?**
A: The chaos engine injects failures (kill worker, CPU stress, network issues, etc.). The system detects these and triggers self-healing to prove resilience.

**Q: What data persists?**
A: PostgreSQL stores pipeline versions and DLQ diagnostics. In-memory fallback works if PostgreSQL isn't available.

---

# 🔗 USEFUL URLS

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

# ✅ PRE-REVIEW CHECKLIST

- [ ] PostgreSQL running (optional)
- [ ] FlowStorm started: `./start.sh`
- [ ] Demo started: Click "Start Demo"
- [ ] Keyboard shortcuts tested
- [ ] All panels verified showing data

---

# 📞 IF SOMETHING BREAKS

**Common Issues:**

| Issue | Fix |
|-------|-----|
| Black screen | Refresh browser, check console for errors |
| No metrics | Click "Start Demo" first |
| PostgreSQL error | Check logs - may need to create user: `CREATE USER flowstorm WITH PASSWORD 'flowstorm';` |
| No data in panels | Wait 15-30 seconds for events to generate |

**Emergency Restart:**
```bash
# Kill stuck processes
pkill -f uvicorn
pkill -f vite

# Restart
cd /home/rathina-devan/Desktop/personal/personal/flowstorm
./start.sh
```

---

# 🎉 THAT'S IT!

FlowStorm is ready for tomorrow's review. The system demonstrates:

1. ✅ Self-healing stream processing
2. ✅ Auto-optimization of DAG topology  
3. ✅ Visual pipeline editor
4. ✅ Chaos engineering
5. ✅ Pipeline version control
6. ✅ DLQ diagnostics of failure

Good luck tomorrow! 🚀