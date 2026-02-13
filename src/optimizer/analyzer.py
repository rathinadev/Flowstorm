"""Data pattern analyzer - observes runtime metrics to find optimization opportunities.

Watches:
- Filter selectivity ratios (what % of events pass each filter)
- Operator CPU/memory usage
- Throughput per edge (to find bottlenecks)
- Data distribution patterns (bursty vs steady)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as aioredis

from src.engine.dag import DAG
from src.models.pipeline import OperatorType

logger = logging.getLogger(__name__)


@dataclass
class FilterStats:
    """Statistics for a filter operator."""
    node_id: str
    total_seen: int = 0
    total_passed: int = 0

    @property
    def selectivity(self) -> float:
        """Ratio of events passing (0.0 = drops everything, 1.0 = passes everything)."""
        if self.total_seen == 0:
            return 1.0
        return self.total_passed / self.total_seen

    @property
    def drop_rate(self) -> float:
        return 1.0 - self.selectivity


@dataclass
class OperatorStats:
    """Runtime statistics for any operator."""
    node_id: str
    operator_type: str
    avg_cpu_percent: float = 0.0
    avg_memory_percent: float = 0.0
    avg_throughput_eps: float = 0.0
    avg_latency_ms: float = 0.0
    is_bottleneck: bool = False
    samples: int = 0


@dataclass
class EdgeStats:
    """Statistics for a pipeline edge (data flow between two operators)."""
    source_id: str
    target_id: str
    events_per_second: float = 0.0
    backpressure_detected: bool = False


@dataclass
class AnalysisResult:
    """Complete analysis of a pipeline's runtime behavior."""
    pipeline_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    filter_stats: dict[str, FilterStats] = field(default_factory=dict)
    operator_stats: dict[str, OperatorStats] = field(default_factory=dict)
    edge_stats: dict[str, EdgeStats] = field(default_factory=dict)
    bottleneck_nodes: list[str] = field(default_factory=list)
    pushdown_candidates: list[tuple[str, str]] = field(default_factory=list)
    fusion_candidates: list[tuple[str, str]] = field(default_factory=list)
    parallel_candidates: list[str] = field(default_factory=list)


class PatternAnalyzer:
    """
    Analyzes runtime data patterns to identify optimization opportunities.

    Runs periodically (default every 30s) and produces an AnalysisResult
    that the optimizer rules engine uses to decide what to rewrite.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def analyze(self, dag: DAG, pipeline_id: str) -> AnalysisResult:
        """Run full analysis on a pipeline."""
        result = AnalysisResult(pipeline_id=pipeline_id)

        # Collect metrics from Redis (written by health monitor)
        metrics = await self._get_worker_metrics(pipeline_id)

        # Analyze each node
        for node_id, node in dag.nodes.items():
            op_type = node.operator_type.value

            # Build operator stats from metrics
            worker_metrics = [m for m in metrics if m.get("node_id") == node_id]
            if worker_metrics:
                avg_cpu = sum(m.get("cpu_percent", 0) for m in worker_metrics) / len(worker_metrics)
                avg_mem = sum(m.get("memory_percent", 0) for m in worker_metrics) / len(worker_metrics)
                avg_eps = sum(m.get("events_per_second", 0) for m in worker_metrics) / len(worker_metrics)
                avg_lat = sum(m.get("avg_latency_ms", 0) for m in worker_metrics) / len(worker_metrics)

                op_stats = OperatorStats(
                    node_id=node_id,
                    operator_type=op_type,
                    avg_cpu_percent=avg_cpu,
                    avg_memory_percent=avg_mem,
                    avg_throughput_eps=avg_eps,
                    avg_latency_ms=avg_lat,
                    is_bottleneck=avg_cpu > 80 or avg_lat > 200,
                    samples=len(worker_metrics),
                )
                result.operator_stats[node_id] = op_stats

                if op_stats.is_bottleneck:
                    result.bottleneck_nodes.append(node_id)

            # Filter selectivity analysis
            if op_type == "filter":
                filter_state = await self._get_filter_state(pipeline_id, node_id)
                if filter_state:
                    stats = FilterStats(
                        node_id=node_id,
                        total_seen=filter_state.get("total_seen", 0),
                        total_passed=filter_state.get("total_passed", 0),
                    )
                    result.filter_stats[node_id] = stats

        # Identify predicate pushdown candidates
        result.pushdown_candidates = self._find_pushdown_candidates(dag, result)

        # Identify operator fusion candidates
        result.fusion_candidates = self._find_fusion_candidates(dag, result)

        # Identify parallel scaling candidates
        result.parallel_candidates = self._find_parallel_candidates(dag, result)

        return result

    def _find_pushdown_candidates(
        self, dag: DAG, result: AnalysisResult
    ) -> list[tuple[str, str]]:
        """
        Find filters that should be moved earlier in the pipeline.

        A filter is a pushdown candidate if:
        1. It has low selectivity (drops > 70% of events)
        2. There's a more expensive operator upstream (join, aggregate, window)
        3. Moving the filter before that operator would reduce work
        """
        candidates = []
        expensive_ops = {"join", "aggregate", "window"}

        for node_id, stats in result.filter_stats.items():
            if stats.selectivity > 0.3:
                continue  # Only push down aggressive filters

            # Check upstream for expensive operators
            upstream_ids = dag.get_upstream(node_id)
            for up_id in upstream_ids:
                up_node = dag.get_node(up_id)
                if up_node and up_node.operator_type.value in expensive_ops:
                    candidates.append((node_id, up_id))
                    logger.info(
                        f"Pushdown candidate: move filter {node_id} "
                        f"(selectivity={stats.selectivity:.2f}) before "
                        f"{up_node.operator_type.value} {up_id}"
                    )

        return candidates

    def _find_fusion_candidates(
        self, dag: DAG, result: AnalysisResult
    ) -> list[tuple[str, str]]:
        """
        Find consecutive stateless operators that can be fused.

        Two map operators in sequence can be merged into one,
        eliminating serialization/deserialization overhead.
        """
        candidates = []
        fusable_types = {"map", "filter"}

        for node_id, node in dag.nodes.items():
            if node.operator_type.value not in fusable_types:
                continue

            downstream_ids = dag.get_downstream(node_id)
            if len(downstream_ids) != 1:
                continue

            down_node = dag.get_node(downstream_ids[0])
            if not down_node:
                continue

            # Two consecutive maps can be fused
            if (node.operator_type.value == "map"
                    and down_node.operator_type.value == "map"):
                candidates.append((node_id, downstream_ids[0]))
                logger.info(f"Fusion candidate: merge map {node_id} + map {downstream_ids[0]}")

            # Two consecutive filters can be fused (AND logic)
            if (node.operator_type.value == "filter"
                    and down_node.operator_type.value == "filter"):
                candidates.append((node_id, downstream_ids[0]))
                logger.info(f"Fusion candidate: merge filter {node_id} + filter {downstream_ids[0]}")

        return candidates

    def _find_parallel_candidates(
        self, dag: DAG, result: AnalysisResult
    ) -> list[str]:
        """
        Find operators that should be parallelized.

        An operator is a parallel candidate if:
        1. CPU > 80% sustained
        2. It's a stateless operator (filter, map) or partitionable (aggregate with group_by)
        """
        candidates = []
        parallelizable = {"filter", "map", "aggregate"}

        for node_id in result.bottleneck_nodes:
            node = dag.get_node(node_id)
            if not node:
                continue
            if node.operator_type.value in parallelizable:
                candidates.append(node_id)
                logger.info(
                    f"Parallel candidate: {node.operator_type.value} {node_id} "
                    f"(CPU={result.operator_stats.get(node_id, OperatorStats(node_id=node_id, operator_type='')).avg_cpu_percent:.0f}%)"
                )

        return candidates

    async def _get_worker_metrics(self, pipeline_id: str) -> list[dict]:
        """Fetch latest worker metrics from Redis."""
        metrics_key = f"flowstorm:metrics:{pipeline_id}"
        try:
            raw = await self.redis.hgetall(metrics_key)
            return [json.loads(v) for v in raw.values()]
        except Exception:
            return []

    async def _get_filter_state(self, pipeline_id: str, node_id: str) -> dict | None:
        """Fetch filter operator state from checkpoint."""
        ckp_key = f"flowstorm:checkpoint:{pipeline_id}:{node_id}"
        try:
            raw = await self.redis.get(ckp_key)
            if raw:
                data = json.loads(raw)
                return data.get("operator_state", {})
        except Exception:
            pass
        return None
