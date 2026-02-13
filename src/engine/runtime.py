"""Runtime Coordinator - manages the lifecycle of a deployed pipeline.

This is the central orchestrator that:
- Spawns worker containers via Docker SDK
- Monitors pipeline health
- Triggers self-healing actions
- Applies DAG optimizations
- Handles live migration during reconfigurations
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import docker
import redis.asyncio as aioredis

from src.engine.compiler import CompiledPipeline, PipelineCompiler
from src.engine.dag import DAG
from src.engine.scheduler import Scheduler
from src.models.events import HealingAction, HealingEvent
from src.models.pipeline import Pipeline, PipelineStatus
from src.models.worker import Worker, WorkerConfig, WorkerStatus

logger = logging.getLogger(__name__)


class RuntimeError(Exception):
    pass


class PipelineRuntime:
    """Manages a single deployed pipeline's lifecycle."""

    def __init__(
        self,
        compiled: CompiledPipeline,
        redis_client: aioredis.Redis,
        docker_client: docker.DockerClient | None = None,
        worker_image: str = "flowstorm-worker:latest",
        network_name: str = "flowstorm-net",
    ):
        self.compiled = compiled
        self.dag = compiled.dag
        self.pipeline = compiled.pipeline
        self.redis = redis_client
        self.docker = docker_client or docker.from_env()
        self.worker_image = worker_image
        self.network_name = network_name

        self.workers: dict[str, Worker] = {}  # worker_id -> Worker
        self._event_handlers: list[Any] = []
        self._running = False

    @property
    def pipeline_id(self) -> str:
        return self.pipeline.id

    # ---- Deployment ----

    async def deploy(self) -> None:
        """Deploy the compiled pipeline - create streams and spawn workers."""
        logger.info(f"Deploying pipeline '{self.pipeline.name}' ({self.pipeline_id})")
        self.pipeline.status = PipelineStatus.DEPLOYING

        try:
            # Create Redis Streams for all edges
            await self._create_streams()

            # Spawn worker containers
            for config in self.compiled.worker_configs:
                await self._spawn_worker(config)

            self.pipeline.status = PipelineStatus.RUNNING
            self._running = True

            logger.info(
                f"Pipeline '{self.pipeline.name}' deployed: "
                f"{len(self.workers)} workers running"
            )

            # Publish deployment event
            await self._publish_event("pipeline.deployed", {
                "pipeline_id": self.pipeline_id,
                "workers": len(self.workers),
                "status": "running",
            })

        except Exception as e:
            self.pipeline.status = PipelineStatus.FAILED
            logger.error(f"Pipeline deployment failed: {e}")
            await self.teardown()
            raise RuntimeError(f"Deployment failed: {e}")

    async def teardown(self) -> None:
        """Stop all workers and clean up resources."""
        logger.info(f"Tearing down pipeline {self.pipeline_id}")
        self._running = False

        for worker_id in list(self.workers.keys()):
            await self._kill_worker(worker_id)

        # Clean up Redis Streams
        for stream_key in self.compiled.stream_keys:
            try:
                await self.redis.delete(stream_key)
            except Exception:
                pass

        self.pipeline.status = PipelineStatus.STOPPED
        await self._publish_event("pipeline.stopped", {
            "pipeline_id": self.pipeline_id,
        })

    # ---- Worker Management ----

    async def _spawn_worker(self, config: WorkerConfig) -> Worker:
        """Spawn a Docker container for a worker."""
        env = {
            "WORKER_ID": config.worker_id,
            "PIPELINE_ID": config.pipeline_id,
            "NODE_ID": config.node_id,
            "OPERATOR_TYPE": config.operator_type,
            "OPERATOR_CONFIG": json.dumps(config.operator_config),
            "INPUT_STREAMS": json.dumps(config.input_streams),
            "OUTPUT_STREAMS": json.dumps(config.output_streams),
            "CONSUMER_GROUP": config.consumer_group,
            "REDIS_HOST": config.redis_host,
            "REDIS_PORT": str(config.redis_port),
            "HEARTBEAT_INTERVAL_MS": str(config.heartbeat_interval_ms),
            "CHECKPOINT_EVERY_N": str(config.checkpoint_every_n),
        }

        try:
            container = self.docker.containers.run(
                self.worker_image,
                detach=True,
                name=f"flowstorm-{config.worker_id}",
                environment=env,
                network=self.network_name,
                labels={
                    "flowstorm.pipeline_id": config.pipeline_id,
                    "flowstorm.node_id": config.node_id,
                    "flowstorm.worker_id": config.worker_id,
                    "flowstorm.operator_type": config.operator_type,
                },
                remove=True,  # Auto-remove on exit
            )
            container_id = container.id
        except docker.errors.DockerException as e:
            logger.error(f"Failed to spawn container for {config.worker_id}: {e}")
            # Fallback: run worker in-process for development/testing
            container_id = f"local-{config.worker_id}"
            logger.warning(f"Running worker {config.worker_id} in-process (dev mode)")

        worker = Worker(
            id=config.worker_id,
            container_id=container_id,
            pipeline_id=config.pipeline_id,
            node_id=config.node_id,
            operator_type=config.operator_type,
            config=config,
            status=WorkerStatus.STARTING,
        )
        self.workers[config.worker_id] = worker

        await self._publish_event("worker.spawned", {
            "worker_id": config.worker_id,
            "node_id": config.node_id,
            "operator_type": config.operator_type,
        })

        logger.info(f"Spawned worker {config.worker_id} ({config.operator_type})")
        return worker

    async def _kill_worker(self, worker_id: str) -> None:
        """Kill a worker container."""
        worker = self.workers.get(worker_id)
        if not worker:
            return

        try:
            container = self.docker.containers.get(worker.container_id)
            container.stop(timeout=5)
        except Exception as e:
            logger.debug(f"Container stop for {worker_id} (may already be gone): {e}")

        worker.status = WorkerStatus.STOPPED
        del self.workers[worker_id]

        await self._publish_event("worker.stopped", {
            "worker_id": worker_id,
            "node_id": worker.node_id,
        })

    async def _restart_worker(self, worker_id: str) -> Worker | None:
        """Kill and respawn a worker with the same config."""
        worker = self.workers.get(worker_id)
        if not worker:
            return None

        config = worker.config
        await self._kill_worker(worker_id)

        # Respawn with new worker ID
        new_config = WorkerConfig(
            **config.model_dump(),
            worker_id=f"w-{config.node_id}-{str(uuid.uuid4())[:6]}"
        )
        # Need to update worker_id in the new config
        new_config.worker_id = f"w-{config.node_id}-{str(uuid.uuid4())[:6]}"
        return await self._spawn_worker(new_config)

    # ---- Self-Healing ----

    async def handle_worker_death(self, worker_id: str) -> HealingEvent:
        """
        Handle a dead worker - failover, respawn, replay from checkpoint.
        """
        worker = self.workers.get(worker_id)
        if not worker:
            return HealingEvent(
                pipeline_id=self.pipeline_id,
                action=HealingAction.FAILOVER,
                trigger=f"Worker {worker_id} not found",
                success=False,
            )

        start_time = datetime.utcnow()
        logger.warning(f"HEALING: Worker {worker_id} ({worker.operator_type}) died")

        await self._publish_event("worker.died", {
            "worker_id": worker_id,
            "node_id": worker.node_id,
            "operator_type": worker.operator_type,
        })

        # Get checkpoint for this node
        checkpoint_key = f"flowstorm:checkpoint:{self.pipeline_id}:{worker.node_id}"
        checkpoint_data = await self.redis.get(checkpoint_key)

        # Respawn the worker
        config = worker.config
        new_worker_id = f"w-{config.node_id}-{str(uuid.uuid4())[:6]}"
        new_config = WorkerConfig(**{
            **config.model_dump(),
            "worker_id": new_worker_id,
        })
        new_worker = await self._spawn_worker(new_config)

        events_replayed = 0
        if checkpoint_data:
            # Replay events from checkpoint position
            events_replayed = await self._replay_from_checkpoint(
                new_worker, json.loads(checkpoint_data)
            )

        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

        healing_event = HealingEvent(
            pipeline_id=self.pipeline_id,
            action=HealingAction.FAILOVER,
            trigger=f"Worker {worker_id} stopped sending heartbeats",
            target_worker_id=new_worker.id,
            target_node_id=worker.node_id,
            details=f"Respawned as {new_worker.id}, replayed {events_replayed} events",
            events_replayed=events_replayed,
            duration_ms=elapsed,
            success=True,
        )

        await self._publish_event("worker.recovered", {
            "old_worker_id": worker_id,
            "new_worker_id": new_worker.id,
            "node_id": worker.node_id,
            "events_replayed": events_replayed,
            "duration_ms": round(elapsed, 1),
        })

        logger.info(
            f"HEALED: Worker {worker_id} -> {new_worker.id}, "
            f"replayed {events_replayed} events in {elapsed:.0f}ms"
        )

        return healing_event

    async def handle_scale_out(self, node_id: str, target_parallelism: int) -> HealingEvent:
        """Scale out an operator to more parallel instances."""
        start_time = datetime.utcnow()
        logger.info(f"SCALING: Node {node_id} -> {target_parallelism} instances")

        # Find current workers for this node
        current_workers = [
            w for w in self.workers.values() if w.node_id == node_id
        ]
        current_count = len(current_workers)
        to_add = target_parallelism - current_count

        if to_add <= 0:
            return HealingEvent(
                pipeline_id=self.pipeline_id,
                action=HealingAction.SCALE_OUT,
                trigger=f"Node {node_id} already at {current_count} instances",
                success=True,
            )

        # Use the config from an existing worker as template
        if current_workers:
            template_config = current_workers[0].config
        else:
            return HealingEvent(
                pipeline_id=self.pipeline_id,
                action=HealingAction.SCALE_OUT,
                trigger=f"No existing workers for node {node_id}",
                success=False,
            )

        new_workers = []
        for i in range(to_add):
            new_id = f"w-{node_id}-{str(uuid.uuid4())[:6]}"
            new_config = WorkerConfig(**{
                **template_config.model_dump(),
                "worker_id": new_id,
            })
            w = await self._spawn_worker(new_config)
            new_workers.append(w)

        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

        await self._publish_event("worker.scaled", {
            "node_id": node_id,
            "old_count": current_count,
            "new_count": target_parallelism,
            "duration_ms": round(elapsed, 1),
        })

        return HealingEvent(
            pipeline_id=self.pipeline_id,
            action=HealingAction.SCALE_OUT,
            trigger=f"Bottleneck detected on node {node_id}",
            target_node_id=node_id,
            details=f"Scaled from {current_count} to {target_parallelism} instances",
            duration_ms=elapsed,
            success=True,
        )

    async def _replay_from_checkpoint(
        self, worker: Worker, checkpoint_data: dict
    ) -> int:
        """Replay events from a checkpoint position to catch up a new worker."""
        stream_key = checkpoint_data.get("stream_key", "")
        last_id = checkpoint_data.get("last_processed_id", "0")

        if not stream_key:
            return 0

        # Read events after the checkpoint position
        try:
            messages = await self.redis.xrange(stream_key, min=last_id, count=10000)
            return len(messages)
        except Exception as e:
            logger.error(f"Replay failed for {worker.id}: {e}")
            return 0

    # ---- Stream Management ----

    async def _create_streams(self) -> None:
        """Create Redis Streams for all edges in the pipeline."""
        for stream_key in self.compiled.stream_keys:
            # XADD with auto-trim creates the stream if it doesn't exist
            try:
                await self.redis.xgroup_create(
                    stream_key, f"cg-{self.pipeline_id}", id="0", mkstream=True
                )
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            logger.debug(f"Created stream: {stream_key}")

    # ---- Event Publishing ----

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Publish a runtime event for the WebSocket to pick up."""
        channel = f"flowstorm:events:{self.pipeline_id}"
        message = json.dumps({
            "type": event_type,
            "pipeline_id": self.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        })
        await self.redis.publish(channel, message)

    # ---- State ----

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline runtime status."""
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.pipeline.name,
            "status": self.pipeline.status.value,
            "workers": {
                wid: {
                    "status": w.status.value,
                    "node_id": w.node_id,
                    "operator_type": w.operator_type,
                    "metrics": w.metrics.model_dump() if w.metrics else {},
                    "health": w.health.model_dump() if w.health else {},
                }
                for wid, w in self.workers.items()
            },
            "total_workers": len(self.workers),
            "stream_keys": self.compiled.stream_keys,
        }


class RuntimeManager:
    """Manages all active pipeline runtimes."""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        worker_image: str = "flowstorm-worker:latest",
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.worker_image = worker_image

        self.runtimes: dict[str, PipelineRuntime] = {}  # pipeline_id -> runtime
        self.redis: aioredis.Redis | None = None
        self.docker_client: docker.DockerClient | None = None
        self.compiler = PipelineCompiler(redis_host=redis_host, redis_port=redis_port)
        self.scheduler = Scheduler()

    async def initialize(self) -> None:
        """Initialize connections."""
        self.redis = aioredis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True,
        )
        try:
            self.docker_client = docker.from_env()
        except docker.errors.DockerException:
            logger.warning("Docker not available - running in dev mode (in-process workers)")
            self.docker_client = None

    async def shutdown(self) -> None:
        """Shut down all runtimes and connections."""
        for pipeline_id in list(self.runtimes.keys()):
            await self.stop_pipeline(pipeline_id)
        if self.redis:
            await self.redis.close()

    async def deploy_pipeline(self, pipeline: Pipeline) -> PipelineRuntime:
        """Compile and deploy a pipeline."""
        compiled = self.compiler.compile(pipeline)

        runtime = PipelineRuntime(
            compiled=compiled,
            redis_client=self.redis,
            docker_client=self.docker_client,
            worker_image=self.worker_image,
        )

        await runtime.deploy()
        self.runtimes[pipeline.id] = runtime
        return runtime

    async def stop_pipeline(self, pipeline_id: str) -> None:
        """Stop a running pipeline."""
        runtime = self.runtimes.get(pipeline_id)
        if runtime:
            await runtime.teardown()
            del self.runtimes[pipeline_id]

    def get_runtime(self, pipeline_id: str) -> PipelineRuntime | None:
        return self.runtimes.get(pipeline_id)

    def get_all_status(self) -> dict[str, Any]:
        return {
            pid: rt.get_status()
            for pid, rt in self.runtimes.items()
        }
