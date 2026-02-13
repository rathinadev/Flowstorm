"""NLP Mapper - converts parsed NLP actions into actual DAG mutations.

Takes the structured output from the NLP parser and applies it to the live DAG.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.engine.dag import DAG
from src.models.pipeline import OperatorConfig, OperatorType, PipelineEdge, PipelineNode

logger = logging.getLogger(__name__)


class NLPMapper:
    """Maps parsed NLP actions to DAG mutations."""

    def apply_actions(
        self, dag: DAG, parsed: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply parsed NLP actions to the DAG.

        Returns a summary of changes made.
        """
        actions = parsed.get("actions", [])
        changes = {
            "nodes_added": [],
            "nodes_removed": [],
            "nodes_modified": [],
            "edges_added": [],
            "edges_removed": [],
        }

        for action in actions:
            action_type = action.get("action", "")

            if action_type == "add_node":
                result = self._add_node(dag, action)
                if result:
                    changes["nodes_added"].append(result)

            elif action_type == "remove_node":
                result = self._remove_node(dag, action)
                if result:
                    changes["nodes_removed"].append(result)

            elif action_type == "modify_node":
                result = self._modify_node(dag, action)
                if result:
                    changes["nodes_modified"].append(result)

            elif action_type == "add_edge":
                result = self._add_edge(dag, action)
                if result:
                    changes["edges_added"].append(result)

            elif action_type == "remove_edge":
                result = self._remove_edge(dag, action)
                if result:
                    changes["edges_removed"].append(result)

            elif action_type == "scale_node":
                result = self._scale_node(dag, action)
                if result:
                    changes["nodes_modified"].append(result)

        return changes

    def _add_node(self, dag: DAG, action: dict) -> dict | None:
        """Add a new node and optionally wire it in."""
        node_def = action.get("node", {})
        if not node_def:
            return None

        try:
            operator_type = OperatorType(node_def.get("operator_type", "filter"))
        except ValueError:
            logger.error(f"Unknown operator type: {node_def.get('operator_type')}")
            return None

        config = OperatorConfig(**node_def.get("config", {}))
        new_node = PipelineNode(
            label=node_def.get("label", f"NLP-{str(uuid.uuid4())[:4]}"),
            operator_type=operator_type,
            config=config,
        )

        dag.add_node(new_node)

        # Auto-wire: connect after specified node
        connect_after = action.get("connect_after")
        connect_before = action.get("connect_before")

        if connect_after:
            after_node = self._resolve_node(dag, connect_after)
            if after_node:
                # Get existing downstream connections
                downstream = dag.get_downstream(after_node)

                if connect_before:
                    before_node = self._resolve_node(dag, connect_before)
                    if before_node:
                        dag.remove_edge(after_node, before_node)
                        dag.add_edge(PipelineEdge(
                            source_node_id=after_node,
                            target_node_id=new_node.id,
                        ))
                        dag.add_edge(PipelineEdge(
                            source_node_id=new_node.id,
                            target_node_id=before_node,
                        ))
                elif downstream:
                    # Insert between after_node and its first downstream
                    first_down = downstream[0]
                    dag.remove_edge(after_node, first_down)
                    dag.add_edge(PipelineEdge(
                        source_node_id=after_node,
                        target_node_id=new_node.id,
                    ))
                    dag.add_edge(PipelineEdge(
                        source_node_id=new_node.id,
                        target_node_id=first_down,
                    ))
                else:
                    dag.add_edge(PipelineEdge(
                        source_node_id=after_node,
                        target_node_id=new_node.id,
                    ))

        logger.info(f"NLP: Added node '{new_node.label}' ({new_node.id})")

        return {
            "id": new_node.id,
            "label": new_node.label,
            "operator_type": new_node.operator_type.value,
        }

    def _remove_node(self, dag: DAG, action: dict) -> dict | None:
        """Remove a node by ID or label."""
        node_ref = action.get("node_id") or action.get("label", "")
        node_id = self._resolve_node(dag, node_ref)

        if not node_id:
            logger.warning(f"NLP: Could not find node '{node_ref}' to remove")
            return None

        node = dag.get_node(node_id)
        if not node:
            return None

        # Rewire: connect upstream directly to downstream
        upstream_ids = dag.get_upstream(node_id)
        downstream_ids = dag.get_downstream(node_id)

        removed = dag.remove_node(node_id)

        for up_id in upstream_ids:
            for down_id in downstream_ids:
                dag.add_edge(PipelineEdge(source_node_id=up_id, target_node_id=down_id))

        logger.info(f"NLP: Removed node '{node.label}' ({node_id})")

        return {"id": node_id, "label": node.label}

    def _modify_node(self, dag: DAG, action: dict) -> dict | None:
        """Modify a node's configuration."""
        node_ref = action.get("node_id") or action.get("label", "")
        node_id = self._resolve_node(dag, node_ref)

        if not node_id:
            return None

        node = dag.get_node(node_id)
        if not node:
            return None

        new_config = action.get("config", {})
        for key, value in new_config.items():
            if hasattr(node.config, key):
                setattr(node.config, key, value)

        logger.info(f"NLP: Modified node '{node.label}' config: {new_config}")

        return {"id": node_id, "label": node.label, "changes": new_config}

    def _add_edge(self, dag: DAG, action: dict) -> dict | None:
        """Add an edge between two nodes."""
        source_ref = action.get("source")
        target_ref = action.get("target")
        source_id = self._resolve_node(dag, source_ref)
        target_id = self._resolve_node(dag, target_ref)

        if source_id and target_id:
            edge = PipelineEdge(source_node_id=source_id, target_node_id=target_id)
            dag.add_edge(edge)
            return {"source": source_id, "target": target_id}
        return None

    def _remove_edge(self, dag: DAG, action: dict) -> dict | None:
        """Remove an edge between two nodes."""
        source_ref = action.get("source")
        target_ref = action.get("target")
        source_id = self._resolve_node(dag, source_ref)
        target_id = self._resolve_node(dag, target_ref)

        if source_id and target_id:
            dag.remove_edge(source_id, target_id)
            return {"source": source_id, "target": target_id}
        return None

    def _scale_node(self, dag: DAG, action: dict) -> dict | None:
        """Scale a node's parallelism."""
        node_ref = action.get("node_id") or action.get("label", "")
        target = action.get("target_parallelism", 3)

        node_id = self._resolve_node(dag, node_ref)
        if not node_id:
            # Scale the first bottleneck or first operator
            for nid, node in dag.nodes.items():
                if node.node_type.value == "operator":
                    node_id = nid
                    break

        if node_id:
            dag.parallelize_node(node_id, target)
            return {"id": node_id, "parallelism": target}
        return None

    def _resolve_node(self, dag: DAG, ref: str | None) -> str | None:
        """Resolve a node reference (ID or label) to a node ID."""
        if not ref:
            return None

        # Try direct ID match
        if ref in dag.nodes:
            return ref

        # Try label match (case-insensitive)
        ref_lower = ref.lower()
        for nid, node in dag.nodes.items():
            if node.label.lower() == ref_lower:
                return nid
            if ref_lower in node.label.lower():
                return nid

        return None
