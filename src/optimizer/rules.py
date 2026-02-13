"""Optimization rules engine - decides which optimizations to apply.

Each rule evaluates the AnalysisResult and returns a list of
optimization actions to apply to the DAG.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.optimizer.analyzer import AnalysisResult

logger = logging.getLogger(__name__)


class OptimizationType(str, Enum):
    PREDICATE_PUSHDOWN = "predicate_pushdown"
    OPERATOR_FUSION = "operator_fusion"
    AUTO_PARALLEL = "auto_parallel"
    WINDOW_OPTIMIZATION = "window_optimization"
    BUFFER_INSERTION = "buffer_insertion"


@dataclass
class OptimizationAction:
    """A single optimization action to apply to the DAG."""
    optimization_type: OptimizationType
    description: str
    target_nodes: list[str]
    params: dict[str, Any]
    estimated_gain: str  # Human-readable gain description
    priority: int = 0  # Higher = more important


class OptimizationRule(ABC):
    """Base class for optimization rules."""

    @abstractmethod
    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        """Evaluate the analysis and return optimization actions."""
        ...


class PredicatePushdownRule(OptimizationRule):
    """
    Move filters closer to the source to reduce data volume early.

    Trigger: Filter selectivity < 0.3 (drops > 70% of events)
             AND there's an expensive operator (join/aggregate/window) upstream.

    Action: Swap the filter with the expensive operator so filter runs first.
    Gain: Up to 10-20x reduction in processing cost.
    """

    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        actions = []

        for filter_id, expensive_id in analysis.pushdown_candidates:
            filter_stats = analysis.filter_stats.get(filter_id)
            selectivity = filter_stats.selectivity if filter_stats else 1.0
            drop_pct = (1 - selectivity) * 100

            actions.append(OptimizationAction(
                optimization_type=OptimizationType.PREDICATE_PUSHDOWN,
                description=(
                    f"Move filter '{filter_id}' before '{expensive_id}'. "
                    f"Filter drops {drop_pct:.0f}% of events - processing them "
                    f"through the expensive operator first wastes resources."
                ),
                target_nodes=[filter_id, expensive_id],
                params={
                    "filter_node_id": filter_id,
                    "swap_with_node_id": expensive_id,
                    "selectivity": selectivity,
                },
                estimated_gain=f"{1/selectivity:.0f}x cost reduction",
                priority=90,  # High priority - big impact
            ))

        return actions


class OperatorFusionRule(OptimizationRule):
    """
    Merge consecutive stateless operators into a single operator.

    Trigger: Two consecutive map or filter operators in sequence.
    Action: Merge them into a single combined operator.
    Gain: ~2x from eliminating serialization between them.
    """

    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        actions = []

        for node_a_id, node_b_id in analysis.fusion_candidates:
            actions.append(OptimizationAction(
                optimization_type=OptimizationType.OPERATOR_FUSION,
                description=(
                    f"Fuse operators '{node_a_id}' and '{node_b_id}' into a single "
                    f"operator. Eliminates serialization/deserialization overhead "
                    f"between them."
                ),
                target_nodes=[node_a_id, node_b_id],
                params={
                    "first_node_id": node_a_id,
                    "second_node_id": node_b_id,
                },
                estimated_gain="~2x throughput improvement",
                priority=50,  # Medium priority
            ))

        return actions


class AutoParallelRule(OptimizationRule):
    """
    Split a bottleneck operator across multiple parallel workers.

    Trigger: Operator CPU > 80% sustained.
    Action: Replace single operator with N parallel instances.
    Gain: Nx throughput.
    """

    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        actions = []

        for node_id in analysis.parallel_candidates:
            op_stats = analysis.operator_stats.get(node_id)
            cpu = op_stats.avg_cpu_percent if op_stats else 0

            # Determine target parallelism based on CPU load
            if cpu > 90:
                target = 4
            elif cpu > 80:
                target = 3
            else:
                target = 2

            actions.append(OptimizationAction(
                optimization_type=OptimizationType.AUTO_PARALLEL,
                description=(
                    f"Scale operator '{node_id}' from 1 to {target} parallel instances. "
                    f"Current CPU: {cpu:.0f}% - operator is a bottleneck."
                ),
                target_nodes=[node_id],
                params={
                    "node_id": node_id,
                    "target_parallelism": target,
                    "current_cpu": cpu,
                },
                estimated_gain=f"{target}x throughput",
                priority=80,  # High priority - affects pipeline health
            ))

        return actions


class BufferInsertionRule(OptimizationRule):
    """
    Insert a buffer between a fast producer and slow consumer to prevent backpressure.

    Trigger: Edge shows backpressure (consumer lag growing).
    Action: Insert a buffering operator between the two nodes.
    Gain: Prevents pipeline stall, absorbs burst traffic.
    """

    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        actions = []

        for edge_key, edge_stats in analysis.edge_stats.items():
            if edge_stats.backpressure_detected:
                actions.append(OptimizationAction(
                    optimization_type=OptimizationType.BUFFER_INSERTION,
                    description=(
                        f"Insert buffer between '{edge_stats.source_id}' and "
                        f"'{edge_stats.target_id}'. Backpressure detected - "
                        f"consumer is slower than producer."
                    ),
                    target_nodes=[edge_stats.source_id, edge_stats.target_id],
                    params={
                        "source_id": edge_stats.source_id,
                        "target_id": edge_stats.target_id,
                    },
                    estimated_gain="Prevents pipeline stall",
                    priority=70,
                ))

        return actions


class WindowOptimizationRule(OptimizationRule):
    """
    Switch windowing strategy based on data arrival patterns.

    Trigger: Window operator with high latency or excessive memory,
             suggesting the current strategy is a poor fit.

    Action: Recommend switching window type (e.g. sliding -> tumbling
            when slide_interval equals window_size, or session windows
            when data is bursty with long idle gaps).
    """

    def evaluate(self, analysis: AnalysisResult) -> list[OptimizationAction]:
        actions = []

        for node_id, stats in analysis.operator_stats.items():
            if stats.operator_type != "window":
                continue

            # High memory + high latency on a window operator -> wrong strategy
            if stats.avg_memory_percent > 70 and stats.avg_latency_ms > 200:
                actions.append(OptimizationAction(
                    optimization_type=OptimizationType.WINDOW_OPTIMIZATION,
                    description=(
                        f"Window operator '{node_id}' has high memory "
                        f"({stats.avg_memory_percent:.0f}%) and latency "
                        f"({stats.avg_latency_ms:.0f}ms). Consider switching "
                        f"to a tumbling window to reduce state size."
                    ),
                    target_nodes=[node_id],
                    params={
                        "node_id": node_id,
                        "suggested_window_type": "tumbling",
                        "current_memory_pct": stats.avg_memory_percent,
                        "current_latency_ms": stats.avg_latency_ms,
                    },
                    estimated_gain="~50% memory reduction",
                    priority=60,
                ))
            elif stats.avg_latency_ms > 300:
                # High latency alone -> suggest smaller window
                actions.append(OptimizationAction(
                    optimization_type=OptimizationType.WINDOW_OPTIMIZATION,
                    description=(
                        f"Window operator '{node_id}' has high latency "
                        f"({stats.avg_latency_ms:.0f}ms). Consider reducing "
                        f"window size or switching to session windows."
                    ),
                    target_nodes=[node_id],
                    params={
                        "node_id": node_id,
                        "suggested_window_type": "session",
                        "current_latency_ms": stats.avg_latency_ms,
                    },
                    estimated_gain="~40% latency reduction",
                    priority=60,
                ))

        return actions


# Registry of all active optimization rules
ALL_RULES: list[OptimizationRule] = [
    PredicatePushdownRule(),
    OperatorFusionRule(),
    AutoParallelRule(),
    BufferInsertionRule(),
    WindowOptimizationRule(),
]


def evaluate_all_rules(analysis: AnalysisResult) -> list[OptimizationAction]:
    """Run all optimization rules and return sorted actions."""
    all_actions: list[OptimizationAction] = []
    for rule in ALL_RULES:
        try:
            actions = rule.evaluate(analysis)
            all_actions.extend(actions)
        except Exception as e:
            logger.error(f"Rule {rule.__class__.__name__} failed: {e}")

    # Sort by priority (highest first)
    all_actions.sort(key=lambda a: a.priority, reverse=True)
    return all_actions
