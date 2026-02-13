"""Demo Simulator - generates realistic pipeline metrics for live demos.

Pushes simulated metrics, healing events, optimization events, and chaos
events through the WebSocket so the frontend dashboard comes alive without
needing a real deployed pipeline.

Usage: POST /api/demo/start with a pipeline spec, GET /api/demo/stop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from datetime import datetime
from typing import Any

from src.api.websocket import ConnectionManager

logger = logging.getLogger(__name__)

# Demo pipeline definition for quick start
DEMO_PIPELINE = {
    "name": "IoT Temperature Monitor",
    "nodes": [
        {"id": "src-mqtt", "label": "MQTT Source", "operator_type": "mqtt_source", "node_type": "source"},
        {"id": "flt-temp", "label": "Temp > 30C", "operator_type": "filter", "node_type": "operator"},
        {"id": "map-enrich", "label": "Enrich Location", "operator_type": "map", "node_type": "operator"},
        {"id": "win-5m", "label": "5min Window", "operator_type": "window", "node_type": "operator"},
        {"id": "agg-avg", "label": "Avg Temperature", "operator_type": "aggregate", "node_type": "operator"},
        {"id": "sink-redis", "label": "Redis Sink", "operator_type": "redis_sink", "node_type": "sink"},
        {"id": "sink-alert", "label": "Alert Sink", "operator_type": "alert_sink", "node_type": "sink"},
    ],
    "edges": [
        {"source": "src-mqtt", "target": "flt-temp"},
        {"source": "flt-temp", "target": "map-enrich"},
        {"source": "map-enrich", "target": "win-5m"},
        {"source": "win-5m", "target": "agg-avg"},
        {"source": "agg-avg", "target": "sink-redis"},
        {"source": "agg-avg", "target": "sink-alert"},
    ],
}

# Healing scenarios to simulate
HEALING_SCENARIOS = [
    {
        "action": "failover",
        "trigger": "Worker stopped sending heartbeats",
        "details": "Respawned worker with fresh state, replayed {n} events",
    },
    {
        "action": "restart",
        "trigger": "Memory usage exceeded 85%",
        "details": "Restarted worker to reclaim memory (was at {mem}%)",
    },
    {
        "action": "scale_out",
        "trigger": "Throughput bottleneck detected (CPU at {cpu}%)",
        "details": "Scaled from {old} to {new} instances",
    },
    {
        "action": "migrate",
        "trigger": "Memory leak detected (growing {rate}MB/min)",
        "details": "Migrated operator to fresh container",
    },
]

OPTIMIZATION_SCENARIOS = [
    {
        "type": "predicate_pushdown",
        "description": "Pushed filter 'Temp > 30C' before window aggregation",
        "gain": "~10x cost reduction (selectivity 0.10)",
    },
    {
        "type": "auto_parallel",
        "description": "Parallelized 'Enrich Location' operator to 3 instances",
        "gain": "~3x throughput increase",
    },
    {
        "type": "operator_fusion",
        "description": "Fused consecutive map operators into single pass",
        "gain": "~2x throughput, 50% less memory",
    },
    {
        "type": "window_optimization",
        "description": "Switched from sliding to tumbling window (5min)",
        "gain": "~40% memory reduction",
    },
    {
        "type": "buffer_insertion",
        "description": "Inserted async buffer between source and filter",
        "gain": "Eliminated backpressure, ~30% throughput gain",
    },
]

CHAOS_SCENARIOS = [
    {"scenario": "kill_worker", "severity": "high", "desc": "Killed worker {w} (operator: {op})"},
    {"scenario": "cpu_stress", "severity": "medium", "desc": "Injected CPU stress on {w} for 10s"},
    {"scenario": "network_delay", "severity": "medium", "desc": "Added 200ms network latency to {w}"},
    {"scenario": "memory_pressure", "severity": "high", "desc": "Injected memory pressure on {w}"},
    {"scenario": "partition", "severity": "critical", "desc": "Network partition: isolated {w} from Redis"},
]


class DemoSimulator:
    """Generates realistic simulated pipeline data and pushes via WebSocket."""

    def __init__(self, ws_manager: ConnectionManager):
        self.ws_manager = ws_manager
        self.pipeline_id = "demo-pipeline-001"
        self.nodes = DEMO_PIPELINE["nodes"]
        self.edges = DEMO_PIPELINE["edges"]
        self._running = False
        self._task: asyncio.Task | None = None
        self._tick = 0
        self._start_time = 0.0

        # Per-node state for realistic variance
        self._node_state: dict[str, dict[str, float]] = {}
        self._chaos_active = False
        self._degraded_node: str | None = None
        self._degraded_until = 0

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> dict[str, Any]:
        """Start the demo simulation. Returns the demo pipeline spec."""
        if self._running:
            return self._get_pipeline_info()

        self._running = True
        self._tick = 0
        self._start_time = time.time()

        # Initialize per-node state
        for node in self.nodes:
            nid = node["id"]
            self._node_state[nid] = {
                "base_eps": random.uniform(800, 1500),
                "base_cpu": random.uniform(20, 45),
                "base_mem": random.uniform(30, 50),
                "base_latency": random.uniform(5, 30),
                "phase": random.uniform(0, 6.28),
                "events_total": 0,
            }

        self._task = asyncio.create_task(self._run())
        logger.info("Demo simulator started")

        # Broadcast deployment event
        await self.ws_manager.broadcast(self.pipeline_id, {
            "type": "pipeline.deployed",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "pipeline_id": self.pipeline_id,
                "workers": len(self.nodes),
                "status": "running",
            },
        })

        return self._get_pipeline_info()

    async def stop(self) -> None:
        """Stop the demo simulation."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.ws_manager.broadcast(self.pipeline_id, {
            "type": "pipeline.stopped",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"pipeline_id": self.pipeline_id},
        })

        logger.info("Demo simulator stopped")

    def _get_pipeline_info(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": DEMO_PIPELINE["name"],
            "status": "running" if self._running else "stopped",
            "nodes": self.nodes,
            "edges": self.edges,
            "workers": len(self.nodes),
        }

    # ---- Main Loop ----

    async def _run(self) -> None:
        try:
            while self._running:
                await self._push_metrics()
                self._tick += 1

                # Healing event every ~15 seconds
                if self._tick > 0 and self._tick % 30 == 0:
                    await self._push_healing_event()

                # Optimization event every ~40 seconds
                if self._tick > 20 and self._tick % 80 == 40:
                    await self._push_optimization_event()

                # Chaos event every ~25 seconds (if chaos active)
                if self._chaos_active and self._tick % 50 == 25:
                    await self._push_chaos_event()

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    # ---- Metrics Generation ----

    async def _push_metrics(self) -> None:
        """Generate and broadcast realistic per-worker metrics."""
        workers: dict[str, Any] = {}
        total_eps = 0.0
        total_events = 0

        for node in self.nodes:
            nid = node["id"]
            state = self._node_state[nid]
            worker_id = f"w-{nid}-demo"

            # Realistic oscillation with noise
            t = self._tick * 0.05
            phase = state["phase"]

            eps = state["base_eps"] + 200 * math.sin(t + phase) + random.gauss(0, 30)
            cpu = state["base_cpu"] + 10 * math.sin(t * 0.7 + phase) + random.gauss(0, 3)
            mem = state["base_mem"] + 5 * math.sin(t * 0.3 + phase) + random.gauss(0, 2)
            latency = state["base_latency"] + 8 * math.sin(t * 0.4 + phase) + random.gauss(0, 2)

            # If this node is degraded (from healing scenario)
            if self._degraded_node == nid and self._tick < self._degraded_until:
                cpu = min(95, cpu + 40)
                latency = latency * 3
                eps = eps * 0.3

            eps = max(0, eps)
            cpu = max(0, min(100, cpu))
            mem = max(0, min(100, mem))
            latency = max(0.1, latency)

            state["events_total"] += int(eps * 0.5)  # 500ms interval

            errors = random.randint(0, 1) if random.random() < 0.05 else 0

            workers[worker_id] = {
                "worker_id": worker_id,
                "node_id": nid,
                "cpu_percent": round(cpu, 1),
                "memory_percent": round(mem, 1),
                "events_per_second": round(eps, 1),
                "events_processed": state["events_total"],
                "avg_latency_ms": round(latency, 1),
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat(),
            }

            total_eps += eps
            total_events += state["events_total"]

        message = {
            "type": "pipeline.metrics",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "workers": workers,
                "total_events_per_second": round(total_eps, 1),
                "total_events_processed": total_events,
                "active_workers": len(workers),
            },
        }

        await self.ws_manager.broadcast(self.pipeline_id, message)

    # ---- Healing Events ----

    async def _push_healing_event(self) -> None:
        """Simulate a self-healing event."""
        target_node = random.choice(self.nodes)
        scenario = random.choice(HEALING_SCENARIOS)

        # Make the target node degraded temporarily
        self._degraded_node = target_node["id"]
        self._degraded_until = self._tick + 10  # 5 seconds degraded

        worker_id = f"w-{target_node['id']}-demo"
        new_worker_id = f"w-{target_node['id']}-{random.randint(1000, 9999)}"

        details = scenario["details"].format(
            n=random.randint(50, 500),
            mem=random.randint(80, 95),
            cpu=random.randint(85, 98),
            old=1,
            new=random.choice([2, 3]),
            rate=round(random.uniform(2, 8), 1),
        )

        duration = round(random.uniform(200, 1500), 1)

        # Push worker.recovered event
        await self.ws_manager.broadcast(self.pipeline_id, {
            "type": "worker.recovered",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "old_worker_id": worker_id,
                "new_worker_id": new_worker_id,
                "node_id": target_node["id"],
                "events_replayed": random.randint(50, 500),
                "duration_ms": duration,
            },
        })

        logger.info(f"Demo: Simulated healing on {target_node['label']} ({scenario['action']})")

    # ---- Optimization Events ----

    async def _push_optimization_event(self) -> None:
        """Simulate a DAG optimization being applied."""
        scenario = random.choice(OPTIMIZATION_SCENARIOS)

        await self.ws_manager.broadcast(self.pipeline_id, {
            "type": "optimizer.applied",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "optimization_type": scenario["type"],
                "description": scenario["description"],
                "estimated_gain": scenario["gain"],
                "workers_added": random.choice([0, 1, 2]),
                "workers_removed": 0,
                "duration_ms": round(random.uniform(50, 300), 1),
            },
        })

        logger.info(f"Demo: Simulated optimization - {scenario['type']}")

    # ---- Chaos Events ----

    async def _push_chaos_event(self) -> None:
        """Simulate a chaos event."""
        target_node = random.choice(self.nodes)
        scenario = random.choice(CHAOS_SCENARIOS)
        worker_id = f"w-{target_node['id']}-demo"

        desc = scenario["desc"].format(w=worker_id, op=target_node["operator_type"])

        await self.ws_manager.broadcast(self.pipeline_id, {
            "type": "chaos.event",
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "scenario": scenario["scenario"],
                "target": worker_id,
                "description": desc,
                "severity": scenario["severity"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        })

        # Degrade the target node
        self._degraded_node = target_node["id"]
        self._degraded_until = self._tick + 16  # 8 seconds degraded

        # After a delay, push the healing response
        async def _delayed_heal():
            await asyncio.sleep(random.uniform(2, 5))
            if self._running:
                await self._push_healing_event()

        asyncio.create_task(_delayed_heal())

    def set_chaos_active(self, active: bool) -> None:
        """Toggle chaos mode."""
        self._chaos_active = active
