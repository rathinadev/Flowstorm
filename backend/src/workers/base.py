"""Base worker class - runs inside a Docker container.

Every operator (filter, map, window, etc.) extends this base.
Handles:
- Reading from input Redis Streams
- Writing to output Redis Streams
- Heartbeat reporting to health monitor
- Periodic checkpointing for recovery
- Graceful shutdown and draining
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from src.models.events import Checkpoint, Heartbeat, StreamEvent

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for all stream processing operators."""

    def __init__(self):
        # Config from environment (set by Docker container)
        self.worker_id: str = os.getenv("WORKER_ID", "unknown")
        self.pipeline_id: str = os.getenv("PIPELINE_ID", "unknown")
        self.node_id: str = os.getenv("NODE_ID", "unknown")
        self.operator_type: str = os.getenv("OPERATOR_TYPE", "unknown")
        self.operator_config: dict = json.loads(os.getenv("OPERATOR_CONFIG", "{}"))
        self.input_streams: list[str] = json.loads(os.getenv("INPUT_STREAMS", "[]"))
        self.output_streams: list[str] = json.loads(os.getenv("OUTPUT_STREAMS", "[]"))
        self.consumer_group: str = os.getenv("CONSUMER_GROUP", "default")
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.heartbeat_interval_ms: int = int(os.getenv("HEARTBEAT_INTERVAL_MS", "500"))
        self.checkpoint_every_n: int = int(os.getenv("CHECKPOINT_EVERY_N", "1000"))

        # Runtime state
        self._redis: aioredis.Redis | None = None
        self._running: bool = False
        self._events_processed: int = 0
        self._errors: int = 0
        self._latencies: list[float] = []
        self._last_processed_ids: dict[str, str] = {}  # stream_key -> last msg ID
        self._start_time: float = 0.0

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = aioredis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True,
        )
        # Create consumer groups for input streams
        for stream_key in self.input_streams:
            try:
                await self._redis.xgroup_create(
                    stream_key, self.consumer_group, id="0", mkstream=True
                )
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()

    # ---- Core Processing Loop ----

    async def run(self) -> None:
        """Main run loop - read events, process, write output, repeat."""
        await self.connect()
        self._running = True
        self._start_time = time.time()

        logger.info(
            f"Worker {self.worker_id} starting: "
            f"operator={self.operator_type}, node={self.node_id}"
        )

        # Start heartbeat and checkpoint tasks
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        process_task = asyncio.create_task(self._process_loop())

        try:
            await asyncio.gather(heartbeat_task, process_task)
        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} shutting down...")
        finally:
            self._running = False
            await self._checkpoint()
            await self.disconnect()
            logger.info(f"Worker {self.worker_id} stopped.")

    async def _process_loop(self) -> None:
        """Read from input streams and process events."""
        while self._running:
            if not self.input_streams:
                # Source nodes generate their own events
                await self._source_loop()
                return

            try:
                # Read from all input streams using consumer group
                streams = {s: ">" for s in self.input_streams}
                results = await self._redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.worker_id,
                    streams=streams,
                    count=100,
                    block=1000,
                )

                if not results:
                    continue

                for stream_key, messages in results:
                    for msg_id, fields in messages:
                        start = time.time()
                        event = StreamEvent.from_redis(msg_id, fields)

                        try:
                            output_events = await self.process(event)
                        except Exception as e:
                            self._errors += 1
                            logger.error(
                                f"Worker {self.worker_id} error processing "
                                f"event {msg_id}: {e}"
                            )
                            # Send to dead letter queue
                            await self._send_to_dlq(event, str(e))
                            await self._redis.xack(
                                stream_key, self.consumer_group, msg_id
                            )
                            continue

                        # Write output events to all output streams
                        if output_events:
                            for out_event in output_events:
                                await self._emit(out_event)

                        # Acknowledge the message
                        await self._redis.xack(
                            stream_key, self.consumer_group, msg_id
                        )
                        self._last_processed_ids[stream_key] = msg_id

                        elapsed = (time.time() - start) * 1000
                        self._latencies.append(elapsed)
                        self._events_processed += 1

                        # Periodic checkpoint
                        if self._events_processed % self.checkpoint_every_n == 0:
                            await self._checkpoint()

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Worker {self.worker_id} loop error: {e}")
                await asyncio.sleep(1)

    async def _source_loop(self) -> None:
        """Override in source operators to generate events."""
        pass

    async def _emit(self, event: StreamEvent) -> None:
        """Write an event to all output streams."""
        data = event.to_redis()
        for stream_key in self.output_streams:
            await self._redis.xadd(stream_key, data)

    async def _send_to_dlq(self, event: StreamEvent, error: str) -> None:
        """Send a failed event to the dead letter queue stream."""
        dlq_key = f"flowstorm:{self.pipeline_id}:dlq"
        data = event.to_redis()
        data["error"] = error
        data["failed_at_node"] = self.node_id
        data["failed_at_worker"] = self.worker_id
        await self._redis.xadd(dlq_key, data)

    # ---- Heartbeat ----

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to health monitor via Redis pub/sub."""
        interval = self.heartbeat_interval_ms / 1000.0
        while self._running:
            try:
                heartbeat = self._build_heartbeat()
                channel = f"flowstorm:heartbeat:{self.pipeline_id}"
                await self._redis.publish(channel, heartbeat.model_dump_json())
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            await asyncio.sleep(interval)

    def _build_heartbeat(self) -> Heartbeat:
        """Build a heartbeat with current metrics."""
        import psutil

        process = psutil.Process()
        elapsed = time.time() - self._start_time if self._start_time else 1.0

        # Calculate average latency from recent samples
        recent_latencies = self._latencies[-100:] if self._latencies else [0]
        avg_latency = sum(recent_latencies) / len(recent_latencies)

        return Heartbeat(
            worker_id=self.worker_id,
            pipeline_id=self.pipeline_id,
            node_id=self.node_id,
            cpu_percent=process.cpu_percent(),
            memory_percent=process.memory_percent(),
            memory_mb=process.memory_info().rss / (1024 * 1024),
            events_processed=self._events_processed,
            events_per_second=self._events_processed / elapsed,
            avg_latency_ms=avg_latency,
            errors=self._errors,
        )

    # ---- Checkpointing ----

    async def _checkpoint(self) -> None:
        """Save current processing state for recovery."""
        if not self._last_processed_ids:
            return

        operator_state = await self.get_state()

        for stream_key, last_id in self._last_processed_ids.items():
            checkpoint = Checkpoint(
                worker_id=self.worker_id,
                pipeline_id=self.pipeline_id,
                node_id=self.node_id,
                stream_key=stream_key,
                last_processed_id=last_id,
                operator_state=operator_state,
            )
            ckp_key = f"flowstorm:checkpoint:{self.pipeline_id}:{self.node_id}"
            await self._redis.set(ckp_key, checkpoint.model_dump_json())

        logger.debug(
            f"Worker {self.worker_id} checkpointed at "
            f"event #{self._events_processed}"
        )

    # ---- Abstract Methods (implement in subclasses) ----

    @abstractmethod
    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        """
        Process a single input event.
        Return a list of output events (can be empty or None to drop the event).
        """
        ...

    async def get_state(self) -> dict[str, Any]:
        """
        Return operator-specific state for checkpointing.
        Override in stateful operators (Window, Aggregate, Join).
        """
        return {}

    async def restore_state(self, state: dict[str, Any]) -> None:
        """
        Restore operator state from a checkpoint.
        Override in stateful operators.
        """
        pass

    async def stop(self) -> None:
        """Signal the worker to stop gracefully."""
        self._running = False
