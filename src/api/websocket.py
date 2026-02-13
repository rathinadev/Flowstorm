"""WebSocket handler for real-time pipeline events.

Pushes live updates to the frontend:
- Pipeline metrics (throughput, latency per node) every 500ms
- Health alerts
- Self-healing actions
- DAG optimization events
- Chaos mode events
- Worker lifecycle events
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per pipeline."""

    def __init__(self):
        # pipeline_id -> list of active WebSocket connections
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, pipeline_id: str) -> None:
        await websocket.accept()
        if pipeline_id not in self.connections:
            self.connections[pipeline_id] = []
        self.connections[pipeline_id].append(websocket)
        logger.info(f"WebSocket connected for pipeline {pipeline_id}")

    def disconnect(self, websocket: WebSocket, pipeline_id: str) -> None:
        if pipeline_id in self.connections:
            self.connections[pipeline_id] = [
                c for c in self.connections[pipeline_id] if c != websocket
            ]
            if not self.connections[pipeline_id]:
                del self.connections[pipeline_id]
        logger.info(f"WebSocket disconnected for pipeline {pipeline_id}")

    async def broadcast(self, pipeline_id: str, message: dict) -> None:
        """Send a message to all connections for a pipeline."""
        connections = self.connections.get(pipeline_id, [])
        dead_connections = []

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws, pipeline_id)

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            pass


# Global connection manager
ws_manager = ConnectionManager()


class PipelineEventForwarder:
    """
    Subscribes to Redis pub/sub channels and forwards events to WebSocket clients.
    One instance per pipeline.
    """

    def __init__(
        self,
        pipeline_id: str,
        redis_client: aioredis.Redis,
        manager: ConnectionManager,
    ):
        self.pipeline_id = pipeline_id
        self.redis = redis_client
        self.manager = manager
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start listening for Redis events and forwarding to WebSockets."""
        self._running = True
        self._task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _listen(self) -> None:
        """Subscribe to all event channels for this pipeline."""
        pubsub = self.redis.pubsub()

        channels = [
            f"flowstorm:events:{self.pipeline_id}",
            f"flowstorm:dashboard:{self.pipeline_id}",
            f"flowstorm:alert_events:{self.pipeline_id}",
        ]

        await pubsub.subscribe(*channels)
        logger.info(f"Event forwarder started for pipeline {self.pipeline_id}")

        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = {"raw": str(message["data"])}

                    await self.manager.broadcast(self.pipeline_id, data)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()


class MetricsPusher:
    """
    Periodically aggregates and pushes pipeline metrics to WebSocket clients.
    Runs every 500ms to give real-time dashboard updates.
    """

    def __init__(
        self,
        pipeline_id: str,
        redis_client: aioredis.Redis,
        manager: ConnectionManager,
        interval_ms: int = 500,
    ):
        self.pipeline_id = pipeline_id
        self.redis = redis_client
        self.manager = manager
        self.interval = interval_ms / 1000.0
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._push_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def _push_loop(self) -> None:
        try:
            while self._running:
                metrics = await self._collect_metrics()
                if metrics:
                    await self.manager.broadcast(self.pipeline_id, {
                        "type": "pipeline.metrics",
                        "pipeline_id": self.pipeline_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": metrics,
                    })
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass

    async def _collect_metrics(self) -> dict[str, Any] | None:
        """Collect latest metrics from Redis (written by worker heartbeats)."""
        metrics_key = f"flowstorm:metrics:{self.pipeline_id}"
        try:
            raw = await self.redis.hgetall(metrics_key)
            if not raw:
                return None

            # Parse per-worker metrics
            workers: dict[str, Any] = {}
            total_eps = 0.0
            total_events = 0

            for key, value in raw.items():
                try:
                    data = json.loads(value)
                    workers[key] = data
                    total_eps += data.get("events_per_second", 0)
                    total_events += data.get("events_processed", 0)
                except json.JSONDecodeError:
                    pass

            return {
                "workers": workers,
                "total_events_per_second": round(total_eps, 1),
                "total_events_processed": total_events,
                "active_workers": len(workers),
            }
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return None
