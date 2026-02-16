"""DAG Compiler - transforms a pipeline definition into an executable plan.

Takes the pipeline JSON from the frontend (nodes + edges) and produces:
1. A validated DAG
2. Redis Stream keys for all edges
3. WorkerConfig for each node (ready to spawn as Docker containers)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.engine.dag import DAG, DAGValidationError
from src.models.pipeline import (
    OperatorType,
    Pipeline,
    PipelineEdge,
    PipelineNode,
)
from src.models.worker import WorkerConfig

logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when pipeline compilation fails."""
    pass


class CompiledPipeline:
    """Result of compiling a pipeline - contains everything needed to deploy."""

    def __init__(
        self,
        pipeline: Pipeline,
        dag: DAG,
        worker_configs: list[WorkerConfig],
        stream_keys: list[str],
        execution_order: list[str],
    ):
        self.pipeline = pipeline
        self.dag = dag
        self.worker_configs = worker_configs
        self.stream_keys = stream_keys
        self.execution_order = execution_order


class PipelineCompiler:
    """Compiles pipeline definitions into executable deployment plans."""

    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port

    def compile(self, pipeline: Pipeline) -> CompiledPipeline:
        """
        Compile a pipeline into an executable plan.

        Steps:
        1. Build DAG from pipeline definition
        2. Validate the DAG structure
        3. Assign Redis Stream keys to all edges
        4. Determine execution order (topological sort)
        5. Generate WorkerConfig for each node
        """
        logger.info(f"Compiling pipeline '{pipeline.name}' ({pipeline.id})")

        # Build and validate DAG
        dag = DAG(pipeline)
        errors = dag.validate()
        if errors:
            raise CompilationError(
                f"Pipeline validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        # Assign stream keys
        dag.assign_stream_keys()

        # Topological sort for execution order
        execution_order = dag.topological_sort()
        logger.info(f"Execution order: {execution_order}")

        # Collect all stream keys
        stream_keys = [
            edge.stream_key
            for edge in dag.edges.values()
            if edge.stream_key
        ]

        # Generate worker configs
        worker_configs = self._generate_worker_configs(dag, execution_order)

        logger.info(
            f"Compiled pipeline '{pipeline.name}': "
            f"{len(worker_configs)} workers, {len(stream_keys)} streams"
        )

        return CompiledPipeline(
            pipeline=pipeline,
            dag=dag,
            worker_configs=worker_configs,
            stream_keys=stream_keys,
            execution_order=execution_order,
        )

    def _generate_worker_configs(
        self, dag: DAG, execution_order: list[str]
    ) -> list[WorkerConfig]:
        """Generate a WorkerConfig for each node in the DAG."""
        configs: list[WorkerConfig] = []

        for node_id in execution_order:
            node = dag.get_node(node_id)
            if not node:
                continue

            # Determine input streams (edges coming into this node)
            input_streams: list[str] = []
            for upstream_id in dag.get_upstream(node_id):
                edge = dag.get_edge_between(upstream_id, node_id)
                if edge and edge.stream_key:
                    input_streams.append(edge.stream_key)

            # Determine output streams (edges going out of this node)
            output_streams: list[str] = []
            for downstream_id in dag.get_downstream(node_id):
                edge = dag.get_edge_between(node_id, downstream_id)
                if edge and edge.stream_key:
                    output_streams.append(edge.stream_key)

            worker_id = f"w-{node.id}-{str(uuid.uuid4())[:6]}"

            config = WorkerConfig(
                worker_id=worker_id,
                pipeline_id=dag.pipeline.id,
                node_id=node_id,
                operator_type=node.operator_type.value,
                operator_config=node.config.model_dump(exclude_none=True),
                input_streams=input_streams,
                output_streams=output_streams,
                consumer_group=f"cg-{dag.pipeline.id}-{node_id}",
                redis_host=self.redis_host,
                redis_port=self.redis_port,
            )
            configs.append(config)

        return configs

    def compile_from_dict(self, data: dict[str, Any]) -> CompiledPipeline:
        """
        Compile from a raw dict (as received from the frontend API).

        Expected format:
        {
            "name": "My Pipeline",
            "description": "...",
            "nodes": [
                {"id": "n1", "label": "MQTT Source", "operator_type": "mqtt_source", ...},
                ...
            ],
            "edges": [
                {"source_node_id": "n1", "target_node_id": "n2"},
                ...
            ]
        }
        """
        nodes = [PipelineNode(**n) for n in data.get("nodes", [])]
        edges = [PipelineEdge(**e) for e in data.get("edges", [])]

        pipeline = Pipeline(
            name=data.get("name", "Untitled Pipeline"),
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
        )

        return self.compile(pipeline)

    def recompile(self, dag: DAG) -> CompiledPipeline:
        """
        Recompile an already-running DAG after a mutation (optimization, healing).
        Returns only the NEW/CHANGED worker configs for incremental deployment.
        """
        errors = dag.validate()
        if errors:
            raise CompilationError(
                f"DAG validation failed after mutation:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        dag.assign_stream_keys()
        execution_order = dag.topological_sort()

        stream_keys = [
            edge.stream_key for edge in dag.edges.values() if edge.stream_key
        ]
        worker_configs = self._generate_worker_configs(dag, execution_order)

        return CompiledPipeline(
            pipeline=dag.pipeline,
            dag=dag,
            worker_configs=worker_configs,
            stream_keys=stream_keys,
            execution_order=execution_order,
        )
