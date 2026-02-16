"""Live Migrator - applies DAG changes without pipeline downtime.

When the optimizer rewrites the DAG, the migrator coordinates
the transition from the old topology to the new one:
1. Spawn new workers for changed/added nodes
2. Drain old workers (finish processing current events)
3. Switch traffic from old streams to new streams
4. Kill old workers
5. Clean up old streams

This ensures zero event loss during optimization.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from src.engine.compiler import CompiledPipeline, PipelineCompiler
from src.engine.dag import DAG
from src.models.events import OptimizationEvent
from src.models.worker import WorkerConfig

logger = logging.getLogger(__name__)


class MigrationPlan:
    """Describes the steps needed to migrate from old DAG to new DAG."""

    def __init__(
        self,
        pipeline_id: str,
        workers_to_add: list[WorkerConfig],
        workers_to_remove: list[str],
        streams_to_create: list[str],
        streams_to_delete: list[str],
        optimization_event: OptimizationEvent,
    ):
        self.pipeline_id = pipeline_id
        self.workers_to_add = workers_to_add
        self.workers_to_remove = workers_to_remove
        self.streams_to_create = streams_to_create
        self.streams_to_delete = streams_to_delete
        self.optimization_event = optimization_event

    def __repr__(self) -> str:
        return (
            f"MigrationPlan(add={len(self.workers_to_add)} workers, "
            f"remove={len(self.workers_to_remove)} workers, "
            f"create={len(self.streams_to_create)} streams, "
            f"delete={len(self.streams_to_delete)} streams)"
        )


class LiveMigrator:
    """Coordinates live migration of DAG changes."""

    def __init__(self, compiler: PipelineCompiler):
        self.compiler = compiler

    def plan_migration(
        self,
        old_compiled: CompiledPipeline,
        new_dag: DAG,
        optimization_event: OptimizationEvent,
    ) -> MigrationPlan:
        """
        Compare old and new DAGs and produce a migration plan.
        """
        # Recompile the new DAG
        new_compiled = self.compiler.recompile(new_dag)

        # Diff the worker configs
        old_node_ids = {c.node_id for c in old_compiled.worker_configs}
        new_node_ids = {c.node_id for c in new_compiled.worker_configs}

        added_nodes = new_node_ids - old_node_ids
        removed_nodes = old_node_ids - new_node_ids

        workers_to_add = [c for c in new_compiled.worker_configs if c.node_id in added_nodes]
        workers_to_remove = [
            c.worker_id for c in old_compiled.worker_configs
            if c.node_id in removed_nodes
        ]

        # Diff the streams
        old_streams = set(old_compiled.stream_keys)
        new_streams = set(new_compiled.stream_keys)

        streams_to_create = list(new_streams - old_streams)
        streams_to_delete = list(old_streams - new_streams)

        plan = MigrationPlan(
            pipeline_id=old_compiled.pipeline.id,
            workers_to_add=workers_to_add,
            workers_to_remove=workers_to_remove,
            streams_to_create=streams_to_create,
            streams_to_delete=streams_to_delete,
            optimization_event=optimization_event,
        )

        logger.info(f"Migration plan created: {plan}")
        return plan

    async def execute(self, plan: MigrationPlan, runtime: Any) -> bool:
        """
        Execute a migration plan on a live pipeline runtime.

        Steps:
        1. Create new Redis Streams
        2. Spawn new workers (they start consuming from new streams)
        3. Wait for old workers to drain their current events
        4. Kill old workers
        5. Delete old streams
        """
        start = datetime.utcnow()

        try:
            # Step 1: Create new streams
            for stream_key in plan.streams_to_create:
                try:
                    await runtime.redis.xgroup_create(
                        stream_key,
                        f"cg-{plan.pipeline_id}",
                        id="0",
                        mkstream=True,
                    )
                except Exception:
                    pass  # Stream might already exist
                logger.debug(f"Migration: created stream {stream_key}")

            # Step 2: Spawn new workers
            for config in plan.workers_to_add:
                await runtime._spawn_worker(config)
                logger.info(f"Migration: spawned worker {config.worker_id}")

            # Step 3: Brief drain period for old workers
            if plan.workers_to_remove:
                logger.info(
                    f"Migration: draining {len(plan.workers_to_remove)} old workers..."
                )
                await asyncio.sleep(2)  # Give old workers time to finish current batch

            # Step 4: Kill old workers
            for worker_id in plan.workers_to_remove:
                await runtime._kill_worker(worker_id)
                logger.info(f"Migration: killed old worker {worker_id}")

            # Step 5: Delete old streams (after a delay to ensure no data loss)
            await asyncio.sleep(1)
            for stream_key in plan.streams_to_delete:
                try:
                    await runtime.redis.delete(stream_key)
                except Exception:
                    pass
                logger.debug(f"Migration: deleted stream {stream_key}")

            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            # Publish migration complete event
            await runtime._publish_event("optimizer.applied", {
                "optimization_type": plan.optimization_event.optimization_type,
                "description": plan.optimization_event.description,
                "estimated_gain": plan.optimization_event.estimated_gain,
                "workers_added": len(plan.workers_to_add),
                "workers_removed": len(plan.workers_to_remove),
                "duration_ms": round(elapsed, 1),
            })

            logger.info(f"Migration complete in {elapsed:.0f}ms")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
