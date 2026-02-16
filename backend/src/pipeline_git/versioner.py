"""Pipeline Versioner - manages version lifecycle for pipelines.

Every change to a pipeline (user action, optimization, healing) creates
a new version. Supports rollback, diffing, and forking.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.engine.dag import DAG
from src.pipeline_git.differ import PipelineDiff, PipelineDiffer
from src.pipeline_git.store import PipelineVersionStore

logger = logging.getLogger(__name__)


class VersionTrigger:
    """Constants for what triggered a version change."""
    USER = "USER"
    AUTO_OPTIMIZE = "AUTO_OPTIMIZE"
    AUTO_HEAL = "AUTO_HEAL"
    AB_TEST = "AB_TEST"
    ROLLBACK = "ROLLBACK"


class PipelineVersioner:
    """Manages pipeline version lifecycle."""

    def __init__(self, store: PipelineVersionStore | None = None):
        self.store = store or PipelineVersionStore()
        self.differ = PipelineDiffer()

    async def initialize(self) -> None:
        """Initialize the version store."""
        await self.store.initialize()

    async def save_version(
        self,
        dag: DAG,
        trigger: str,
        description: str,
        performance_snapshot: dict[str, Any] | None = None,
    ) -> int:
        """
        Save the current DAG state as a new version.
        Returns the new version number.
        """
        pipeline_id = dag.pipeline.id
        version_number = await self.store.get_next_version_number(pipeline_id)

        snapshot = dag.snapshot()

        await self.store.save_version(
            pipeline_id=pipeline_id,
            version_number=version_number,
            trigger=trigger,
            description=description,
            dag_snapshot=snapshot,
            performance_snapshot=performance_snapshot,
        )

        # Update the pipeline's version counter
        dag.pipeline.version = version_number

        logger.info(
            f"Pipeline '{dag.pipeline.name}' saved as v{version_number} "
            f"[{trigger}]: {description}"
        )

        return version_number

    async def get_history(
        self, pipeline_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for a pipeline."""
        return await self.store.get_history(pipeline_id, limit)

    async def get_version(
        self, pipeline_id: str, version_number: int
    ) -> dict[str, Any] | None:
        """Get a specific version."""
        return await self.store.get_version(pipeline_id, version_number)

    async def diff_versions(
        self, pipeline_id: str, from_version: int, to_version: int
    ) -> PipelineDiff | None:
        """Generate a diff between two versions."""
        old = await self.store.get_version(pipeline_id, from_version)
        new = await self.store.get_version(pipeline_id, to_version)

        if not old or not new:
            return None

        return self.differ.diff(
            old["dag_snapshot"],
            new["dag_snapshot"],
            version_from=from_version,
            version_to=to_version,
        )

    async def get_snapshot(
        self, pipeline_id: str, version_number: int
    ) -> dict[str, Any] | None:
        """Get the DAG snapshot for a specific version."""
        version = await self.store.get_version(pipeline_id, version_number)
        if version:
            return version["dag_snapshot"]
        return None

    async def get_latest_snapshot(
        self, pipeline_id: str
    ) -> dict[str, Any] | None:
        """Get the most recent DAG snapshot."""
        version = await self.store.get_latest_version(pipeline_id)
        if version:
            return version["dag_snapshot"]
        return None

    async def create_initial_version(self, dag: DAG) -> int:
        """Create the first version when a pipeline is deployed."""
        return await self.save_version(
            dag,
            trigger=VersionTrigger.USER,
            description="Pipeline created and deployed",
        )

    async def save_optimization_version(
        self,
        dag: DAG,
        optimization_type: str,
        description: str,
        gain: str = "",
    ) -> int:
        """Save a version after an automatic optimization."""
        desc = f"[{optimization_type}] {description}"
        if gain:
            desc += f" ({gain})"
        return await self.save_version(
            dag,
            trigger=VersionTrigger.AUTO_OPTIMIZE,
            description=desc,
        )

    async def save_healing_version(
        self,
        dag: DAG,
        healing_action: str,
        description: str,
    ) -> int:
        """Save a version after a self-healing action."""
        return await self.save_version(
            dag,
            trigger=VersionTrigger.AUTO_HEAL,
            description=f"[HEAL:{healing_action}] {description}",
        )

    async def save_rollback_version(
        self,
        dag: DAG,
        rolled_back_to: int,
    ) -> int:
        """Save a version recording a rollback event."""
        return await self.save_version(
            dag,
            trigger=VersionTrigger.ROLLBACK,
            description=f"Rolled back to version {rolled_back_to}",
        )
