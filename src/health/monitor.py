"""Health Monitor - the brain of FlowStorm's self-healing system.

Subscribes to worker heartbeats via Redis pub/sub.
Computes health scores for each worker.
Detects failures and triggers healing actions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as aioredis

from src.models.events import Heartbeat, HealingAction, HealingEvent
from src.models.worker import WorkerHealth, WorkerMetrics, WorkerStatus

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Monitors worker health and triggers self-healing.

    Health score (0-100) is computed from:
    - CPU usage (30% weight)
    - Memory usage (30% weight)
    - Throughput stability (20% weight)
    - Latency (20% weight)

    Thresholds:
    - score >= 70: HEALTHY (green)
    - 30 <= score < 70: DEGRADED (yellow)
    - score < 30: CRITICAL (red) -> trigger healing
    - No heartbeat for 2s: DEAD -> trigger failover
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        runtime_manager: Any = None,
        heartbeat_timeout_ms: int = 2000,
        check_interval_ms: int = 1000,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.runtime_manager = runtime_manager
        self.heartbeat_timeout = timedelta(milliseconds=heartbeat_timeout_ms)
        self.check_interval = check_interval_ms / 1000.0

        self.redis: aioredis.Redis | None = None

        # worker_id -> last heartbeat data
        self._heartbeats: dict[str, Heartbeat] = {}
        self._last_heartbeat_time: dict[str, datetime] = {}

        # Throughput history for stability analysis
        # worker_id -> list of (timestamp, events_per_second)
        self._throughput_history: dict[str, list[tuple[datetime, float]]] = {}

        # Healing events log
        self.healing_log: list[HealingEvent] = []

        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start the health monitoring system."""
        self.redis = aioredis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True,
        )
        self._running = True

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._heartbeat_listener()))
        self._tasks.append(asyncio.create_task(self._health_check_loop()))

        logger.info("Health monitor started")

    async def stop(self) -> None:
        """Stop the health monitoring system."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self.redis:
            await self.redis.close()
        logger.info("Health monitor stopped")

    # ---- Heartbeat Processing ----

    async def _heartbeat_listener(self) -> None:
        """Subscribe to all heartbeat channels and process them."""
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("flowstorm:heartbeat:*")

        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "pmessage":
                    try:
                        heartbeat = Heartbeat(**json.loads(message["data"]))
                        await self._process_heartbeat(heartbeat)
                    except Exception as e:
                        logger.error(f"Heartbeat processing error: {e}")
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.punsubscribe("flowstorm:heartbeat:*")
            await pubsub.close()

    async def _process_heartbeat(self, heartbeat: Heartbeat) -> None:
        """Process a single heartbeat from a worker."""
        worker_id = heartbeat.worker_id
        now = datetime.utcnow()

        self._heartbeats[worker_id] = heartbeat
        self._last_heartbeat_time[worker_id] = now

        # Track throughput history
        if worker_id not in self._throughput_history:
            self._throughput_history[worker_id] = []
        self._throughput_history[worker_id].append(
            (now, heartbeat.events_per_second)
        )
        # Keep only last 5 minutes
        cutoff = now - timedelta(minutes=5)
        self._throughput_history[worker_id] = [
            (ts, eps) for ts, eps in self._throughput_history[worker_id]
            if ts >= cutoff
        ]

        # Store latest metrics in Redis for dashboard consumption
        metrics_key = f"flowstorm:metrics:{heartbeat.pipeline_id}"
        await self.redis.hset(metrics_key, worker_id, json.dumps({
            "worker_id": worker_id,
            "node_id": heartbeat.node_id,
            "cpu_percent": heartbeat.cpu_percent,
            "memory_percent": heartbeat.memory_percent,
            "events_per_second": heartbeat.events_per_second,
            "events_processed": heartbeat.events_processed,
            "avg_latency_ms": heartbeat.avg_latency_ms,
            "errors": heartbeat.errors,
            "timestamp": now.isoformat(),
        }))

        # Update worker state in the runtime
        if self.runtime_manager:
            for runtime in self.runtime_manager.runtimes.values():
                worker = runtime.workers.get(worker_id)
                if worker:
                    worker.last_heartbeat_at = now
                    worker.metrics = WorkerMetrics(
                        cpu_percent=heartbeat.cpu_percent,
                        memory_percent=heartbeat.memory_percent,
                        events_processed=heartbeat.events_processed,
                        events_per_second=heartbeat.events_per_second,
                        avg_latency_ms=heartbeat.avg_latency_ms,
                        errors=heartbeat.errors,
                    )
                    worker.health = self._compute_health(worker_id)

                    if worker.health.is_critical and worker.status == WorkerStatus.RUNNING:
                        worker.status = WorkerStatus.DEGRADED

    # ---- Health Score Computation ----

    def _compute_health(self, worker_id: str) -> WorkerHealth:
        """Compute health score for a worker based on its metrics."""
        heartbeat = self._heartbeats.get(worker_id)
        if not heartbeat:
            return WorkerHealth(score=0, status=WorkerStatus.DEAD, issues=["No heartbeat data"])

        issues: list[str] = []

        # CPU score: 100 at 0%, linear decrease, 0 at 100%
        cpu_score = max(0, 100 - heartbeat.cpu_percent)
        if heartbeat.cpu_percent > 80:
            issues.append(f"High CPU: {heartbeat.cpu_percent:.0f}%")

        # Memory score: 100 at 0%, drops faster after 60%
        if heartbeat.memory_percent < 60:
            memory_score = 100.0
        else:
            memory_score = max(0, 100 - (heartbeat.memory_percent - 60) * 2.5)
        if heartbeat.memory_percent > 75:
            issues.append(f"High memory: {heartbeat.memory_percent:.0f}%")

        # Throughput score: based on stability (no sudden drops)
        throughput_score = self._compute_throughput_score(worker_id)
        if throughput_score < 50:
            issues.append("Throughput dropping")

        # Latency score: 100 if < 50ms, drops to 0 at 500ms
        if heartbeat.avg_latency_ms < 50:
            latency_score = 100.0
        elif heartbeat.avg_latency_ms < 500:
            latency_score = 100 - ((heartbeat.avg_latency_ms - 50) / 450) * 100
        else:
            latency_score = 0.0
        if heartbeat.avg_latency_ms > 200:
            issues.append(f"High latency: {heartbeat.avg_latency_ms:.0f}ms")

        # Weighted overall score
        score = (
            cpu_score * 0.3
            + memory_score * 0.3
            + throughput_score * 0.2
            + latency_score * 0.2
        )

        # Determine status
        if score >= 70:
            status = WorkerStatus.RUNNING
        elif score >= 30:
            status = WorkerStatus.DEGRADED
        else:
            status = WorkerStatus.DEGRADED  # Don't mark DEAD from score alone

        return WorkerHealth(
            score=round(score, 1),
            cpu_score=round(cpu_score, 1),
            memory_score=round(memory_score, 1),
            throughput_score=round(throughput_score, 1),
            latency_score=round(latency_score, 1),
            status=status,
            issues=issues,
        )

    def _compute_throughput_score(self, worker_id: str) -> float:
        """Score based on throughput stability over the last minute."""
        history = self._throughput_history.get(worker_id, [])
        if len(history) < 3:
            return 100.0  # Not enough data yet

        cutoff = datetime.utcnow() - timedelta(seconds=60)
        recent = [eps for ts, eps in history if ts >= cutoff]
        if not recent:
            return 100.0

        avg = sum(recent) / len(recent)
        if avg == 0:
            return 100.0

        # Check for sudden drops (current vs average)
        current = recent[-1]
        if current < avg * 0.5:
            return 30.0  # Throughput dropped by more than 50%
        elif current < avg * 0.7:
            return 60.0
        return 100.0

    # ---- Health Check Loop ----

    async def _health_check_loop(self) -> None:
        """Periodic check for dead workers and degraded health."""
        try:
            while self._running:
                await self._check_all_workers()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            pass

    async def _check_all_workers(self) -> None:
        """Check all known workers for failures."""
        if not self.runtime_manager:
            return

        now = datetime.utcnow()

        for pipeline_id, runtime in self.runtime_manager.runtimes.items():
            for worker_id, worker in list(runtime.workers.items()):
                last_heartbeat = self._last_heartbeat_time.get(worker_id)

                # Check for dead workers (no heartbeat)
                if last_heartbeat and (now - last_heartbeat) > self.heartbeat_timeout:
                    if worker.status not in (WorkerStatus.DEAD, WorkerStatus.STOPPED):
                        logger.warning(
                            f"Worker {worker_id} missed heartbeat "
                            f"(last: {(now - last_heartbeat).total_seconds():.1f}s ago)"
                        )
                        worker.status = WorkerStatus.DEAD
                        worker.health = WorkerHealth(
                            score=0, status=WorkerStatus.DEAD,
                            issues=["No heartbeat - worker dead"],
                        )
                        # Trigger self-healing
                        healing_event = await runtime.handle_worker_death(worker_id)
                        self.healing_log.append(healing_event)

                # Check for critical health (but still alive)
                elif worker.health.is_critical and worker.is_alive:
                    logger.warning(
                        f"Worker {worker_id} health critical: "
                        f"score={worker.health.score}, issues={worker.health.issues}"
                    )
                    # Could trigger scale-out or migration here

    # ---- Public API ----

    def get_worker_health(self, worker_id: str) -> WorkerHealth | None:
        return self._compute_health(worker_id) if worker_id in self._heartbeats else None

    def get_all_health(self, pipeline_id: str) -> dict[str, WorkerHealth]:
        result = {}
        if not self.runtime_manager:
            return result
        runtime = self.runtime_manager.get_runtime(pipeline_id)
        if not runtime:
            return result
        for worker_id in runtime.workers:
            health = self._compute_health(worker_id)
            result[worker_id] = health
        return result

    def get_healing_log(self, pipeline_id: str | None = None) -> list[HealingEvent]:
        if pipeline_id:
            return [e for e in self.healing_log if e.pipeline_id == pipeline_id]
        return self.healing_log
