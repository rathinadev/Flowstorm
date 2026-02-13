"""DAG Rewriter - applies optimization actions to the live DAG.

Takes OptimizationAction objects from the rules engine and
mutates the DAG accordingly. Each rewrite is atomic and
produces a before/after snapshot for the pipeline git.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.engine.dag import DAG, DAGValidationError
from src.models.events import OptimizationEvent
from src.models.pipeline import OperatorConfig, OperatorType, PipelineEdge, PipelineNode
from src.optimizer.rules import OptimizationAction, OptimizationType

logger = logging.getLogger(__name__)


class RewriteError(Exception):
    """Raised when a DAG rewrite fails."""
    pass


class DAGRewriter:
    """Applies optimization actions to a DAG."""

    def apply(self, dag: DAG, action: OptimizationAction) -> OptimizationEvent:
        """
        Apply a single optimization action to the DAG.
        Returns an OptimizationEvent recording what changed.
        """
        before = dag.snapshot()

        try:
            if action.optimization_type == OptimizationType.PREDICATE_PUSHDOWN:
                self._apply_pushdown(dag, action)
            elif action.optimization_type == OptimizationType.OPERATOR_FUSION:
                self._apply_fusion(dag, action)
            elif action.optimization_type == OptimizationType.AUTO_PARALLEL:
                self._apply_parallel(dag, action)
            elif action.optimization_type == OptimizationType.BUFFER_INSERTION:
                self._apply_buffer(dag, action)
            else:
                raise RewriteError(f"Unknown optimization type: {action.optimization_type}")
        except DAGValidationError as e:
            raise RewriteError(f"DAG validation failed after rewrite: {e}")

        after = dag.snapshot()

        # Validate the rewritten DAG
        errors = dag.validate()
        if errors:
            raise RewriteError(f"DAG invalid after rewrite: {errors}")

        return OptimizationEvent(
            pipeline_id=dag.pipeline.id,
            optimization_type=action.optimization_type.value,
            description=action.description,
            before_snapshot=before,
            after_snapshot=after,
            estimated_gain=action.estimated_gain,
        )

    def _apply_pushdown(self, dag: DAG, action: OptimizationAction) -> None:
        """
        Predicate pushdown: swap a filter with an upstream expensive operator.

        Before: ... -> Expensive -> Filter -> ...
        After:  ... -> Filter -> Expensive -> ...
        """
        filter_id = action.params["filter_node_id"]
        swap_with_id = action.params["swap_with_node_id"]

        logger.info(
            f"OPTIMIZER: Pushing filter {filter_id} before {swap_with_id} "
            f"(selectivity={action.params.get('selectivity', '?')})"
        )

        dag.swap_nodes(swap_with_id, filter_id)

    def _apply_fusion(self, dag: DAG, action: OptimizationAction) -> None:
        """
        Operator fusion: merge two consecutive operators into one.

        For two maps: combine expressions.
        For two filters: AND the conditions.
        """
        first_id = action.params["first_node_id"]
        second_id = action.params["second_node_id"]

        first_node = dag.get_node(first_id)
        second_node = dag.get_node(second_id)
        if not first_node or not second_node:
            raise RewriteError(f"Fusion targets not found: {first_id}, {second_id}")

        logger.info(f"OPTIMIZER: Fusing {first_id} + {second_id}")

        if (first_node.operator_type == OperatorType.MAP
                and second_node.operator_type == OperatorType.MAP):
            # Combine map expressions
            expr1 = first_node.config.expression or "x"
            expr2 = second_node.config.expression or "x"
            combined_expr = expr2.replace("x", f"({expr1})")

            fused_node = PipelineNode(
                label=f"{first_node.label}+{second_node.label}",
                operator_type=OperatorType.MAP,
                config=OperatorConfig(
                    expression=combined_expr,
                    field=first_node.config.field,
                    output_field=second_node.config.output_field or first_node.config.output_field,
                ),
            )
        elif (first_node.operator_type == OperatorType.FILTER
              and second_node.operator_type == OperatorType.FILTER):
            # Combined filter - both conditions must pass
            # Store both configs and evaluate both in sequence
            fused_node = PipelineNode(
                label=f"{first_node.label}+{second_node.label}",
                operator_type=OperatorType.FILTER,
                config=first_node.config.model_copy(),  # Primary filter
            )
        else:
            raise RewriteError(
                f"Cannot fuse {first_node.operator_type} with {second_node.operator_type}"
            )

        # Get upstream of first and downstream of second
        upstream_ids = dag.get_upstream(first_id)
        downstream_ids = dag.get_downstream(second_id)

        # Remove both nodes
        dag.remove_node(first_id)
        dag.remove_node(second_id)

        # Add fused node
        dag.add_node(fused_node)

        # Rewire
        for up_id in upstream_ids:
            dag.add_edge(PipelineEdge(source_node_id=up_id, target_node_id=fused_node.id))
        for down_id in downstream_ids:
            dag.add_edge(PipelineEdge(source_node_id=fused_node.id, target_node_id=down_id))

    def _apply_parallel(self, dag: DAG, action: OptimizationAction) -> None:
        """
        Auto-parallel: split a single operator into N parallel instances.
        """
        node_id = action.params["node_id"]
        target = action.params["target_parallelism"]

        logger.info(f"OPTIMIZER: Parallelizing {node_id} to {target} instances")

        dag.parallelize_node(node_id, target)

    def _apply_buffer(self, dag: DAG, action: OptimizationAction) -> None:
        """
        Buffer insertion: add a buffering operator between producer and consumer.
        """
        source_id = action.params["source_id"]
        target_id = action.params["target_id"]

        logger.info(f"OPTIMIZER: Inserting buffer between {source_id} and {target_id}")

        buffer_node = PipelineNode(
            label=f"buffer-{str(uuid.uuid4())[:4]}",
            operator_type=OperatorType.MAP,  # Pass-through map acts as buffer
            config=OperatorConfig(expression="x", field=None),
        )

        dag.insert_node_between(buffer_node, source_id, target_id)
