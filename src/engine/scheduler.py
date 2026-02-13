"""Scheduler - decides how to place operators on available worker slots.

In FlowStorm, each operator runs in its own Docker container.
The scheduler determines:
- How many containers to spawn per operator (parallelism)
- Resource limits per container
- Placement preferences (co-locate operators that communicate heavily)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.engine.dag import DAG
from src.models.pipeline import NodeType
from src.models.worker import WorkerConfig

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for a worker container."""
    cpu_shares: int = 1024  # Docker CPU shares (1024 = 1 CPU)
    memory_mb: int = 256    # Memory limit in MB
    memory_reservation_mb: int = 128


@dataclass
class PlacementDecision:
    """Scheduling decision for a single operator."""
    node_id: str
    parallelism: int = 1
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    preferred_colocate_with: list[str] = field(default_factory=list)


class Scheduler:
    """
    Decides operator placement and resource allocation.

    Scheduling strategy:
    - Sources: 1 instance each (they manage their own parallelism)
    - Operators: start with 1 instance, auto-scale based on health metrics
    - Sinks: 1 instance each
    - Heavy operators (join, aggregate with large state): more memory
    - Co-locate operators connected by edges to reduce network hops
    """

    def __init__(self, max_workers: int = 20, default_memory_mb: int = 256):
        self.max_workers = max_workers
        self.default_memory_mb = default_memory_mb

    def schedule(self, dag: DAG) -> list[PlacementDecision]:
        """Generate placement decisions for all nodes in the DAG."""
        decisions: list[PlacementDecision] = []
        execution_order = dag.topological_sort()

        for node_id in execution_order:
            node = dag.get_node(node_id)
            if not node:
                continue

            parallelism = self._determine_parallelism(node.operator_type.value, node.node_type)
            resources = self._determine_resources(node.operator_type.value)

            # Find nodes to co-locate with (immediate upstream/downstream)
            colocate = []
            for upstream in dag.get_upstream(node_id):
                colocate.append(upstream)
            for downstream in dag.get_downstream(node_id):
                colocate.append(downstream)

            decisions.append(PlacementDecision(
                node_id=node_id,
                parallelism=parallelism,
                resource_limits=resources,
                preferred_colocate_with=colocate,
            ))

        total_workers = sum(d.parallelism for d in decisions)
        if total_workers > self.max_workers:
            logger.warning(
                f"Scheduled {total_workers} workers exceeds max {self.max_workers}. "
                f"Consider reducing parallelism."
            )

        logger.info(
            f"Scheduled {len(decisions)} operators, "
            f"{total_workers} total worker instances"
        )

        return decisions

    def _determine_parallelism(self, operator_type: str, node_type: NodeType) -> int:
        """Determine initial parallelism for an operator type."""
        # Sources and sinks start with 1
        if node_type in (NodeType.SOURCE, NodeType.SINK):
            return 1
        # All operators start with 1, auto-scaler will increase if needed
        return 1

    def _determine_resources(self, operator_type: str) -> ResourceLimits:
        """Determine resource limits based on operator type."""
        # Stateful operators get more memory
        heavy_operators = {"window", "join", "aggregate"}
        if operator_type in heavy_operators:
            return ResourceLimits(
                cpu_shares=1024,
                memory_mb=512,
                memory_reservation_mb=256,
            )
        return ResourceLimits(
            cpu_shares=512,
            memory_mb=self.default_memory_mb,
            memory_reservation_mb=128,
        )

    def reschedule_node(
        self, dag: DAG, node_id: str, new_parallelism: int
    ) -> PlacementDecision:
        """
        Create a new placement decision for a single node.
        Used by the auto-scaler when scaling out/in.
        """
        node = dag.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in DAG")

        resources = self._determine_resources(node.operator_type.value)

        colocate = list(dag.get_upstream(node_id)) + list(dag.get_downstream(node_id))

        return PlacementDecision(
            node_id=node_id,
            parallelism=new_parallelism,
            resource_limits=resources,
            preferred_colocate_with=colocate,
        )
