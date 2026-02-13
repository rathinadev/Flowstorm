"""DAG (Directed Acyclic Graph) data structure and operations.

This is the core computation graph that represents a stream processing pipeline.
Supports topological sorting, validation, subgraph extraction, and live mutation
for self-healing and optimization rewrites.
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from src.models.pipeline import (
    NodeType,
    Pipeline,
    PipelineEdge,
    PipelineNode,
)


class DAGValidationError(Exception):
    """Raised when a pipeline DAG is invalid."""
    pass


class DAG:
    """
    Executable DAG representation of a stream processing pipeline.

    Provides:
    - Topological sort for execution ordering
    - Cycle detection
    - Validation (connectivity, source/sink rules)
    - Subgraph extraction (for parallel execution planning)
    - Live mutation (add/remove nodes, rewire edges) for healing/optimization
    """

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        self._nodes: dict[str, PipelineNode] = {}
        self._edges: dict[str, PipelineEdge] = {}

        self._build_from_pipeline()

    def _build_from_pipeline(self):
        """Build internal graph structures from pipeline definition."""
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._nodes.clear()
        self._edges.clear()

        for node in self.pipeline.nodes:
            self._nodes[node.id] = node
            # Initialize adjacency entries even for nodes with no edges
            if node.id not in self._adjacency:
                self._adjacency[node.id] = []
            if node.id not in self._reverse_adjacency:
                self._reverse_adjacency[node.id] = []

        for edge in self.pipeline.edges:
            self._edges[edge.id] = edge
            self._adjacency[edge.source_node_id].append(edge.target_node_id)
            self._reverse_adjacency[edge.target_node_id].append(edge.source_node_id)

    @property
    def nodes(self) -> dict[str, PipelineNode]:
        return self._nodes

    @property
    def edges(self) -> dict[str, PipelineEdge]:
        return self._edges

    def get_node(self, node_id: str) -> PipelineNode | None:
        return self._nodes.get(node_id)

    def get_downstream(self, node_id: str) -> list[str]:
        return self._adjacency.get(node_id, [])

    def get_upstream(self, node_id: str) -> list[str]:
        return self._reverse_adjacency.get(node_id, [])

    def get_edge_between(self, source_id: str, target_id: str) -> PipelineEdge | None:
        for edge in self._edges.values():
            if edge.source_node_id == source_id and edge.target_node_id == target_id:
                return edge
        return None

    # ---- Topological Sort ----

    def topological_sort(self) -> list[str]:
        """
        Kahn's algorithm for topological ordering.
        Returns node IDs in execution order (sources first, sinks last).
        Raises DAGValidationError if a cycle is detected.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for nid in self._nodes:
            for downstream in self._adjacency[nid]:
                in_degree[downstream] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        result: list[str] = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            for downstream in self._adjacency[node_id]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

        if len(result) != len(self._nodes):
            raise DAGValidationError(
                "Cycle detected in pipeline DAG. "
                f"Processed {len(result)}/{len(self._nodes)} nodes."
            )

        return result

    # ---- Validation ----

    def validate(self) -> list[str]:
        """
        Validate the DAG structure. Returns list of error messages (empty = valid).

        Checks:
        1. No cycles
        2. At least one source and one sink
        3. Sources have no incoming edges
        4. Sinks have no outgoing edges
        5. All nodes are reachable from at least one source
        6. No disconnected nodes
        """
        errors: list[str] = []

        if not self._nodes:
            errors.append("Pipeline has no nodes.")
            return errors

        # Check for cycles
        try:
            self.topological_sort()
        except DAGValidationError as e:
            errors.append(str(e))
            return errors  # Can't do further checks with cycles

        # Check sources and sinks exist
        sources = [n for n in self._nodes.values() if n.node_type == NodeType.SOURCE]
        sinks = [n for n in self._nodes.values() if n.node_type == NodeType.SINK]

        if not sources:
            errors.append("Pipeline must have at least one source node.")
        if not sinks:
            errors.append("Pipeline must have at least one sink node.")

        # Sources should have no incoming edges
        for source in sources:
            if self._reverse_adjacency.get(source.id):
                errors.append(f"Source node '{source.label}' ({source.id}) has incoming edges.")

        # Sinks should have no outgoing edges
        for sink in sinks:
            if self._adjacency.get(sink.id):
                errors.append(f"Sink node '{sink.label}' ({sink.id}) has outgoing edges.")

        # All nodes should be reachable from a source (BFS from all sources)
        reachable: set[str] = set()
        queue = deque([s.id for s in sources])
        while queue:
            nid = queue.popleft()
            if nid in reachable:
                continue
            reachable.add(nid)
            for downstream in self._adjacency[nid]:
                if downstream not in reachable:
                    queue.append(downstream)

        unreachable = set(self._nodes.keys()) - reachable
        if unreachable:
            labels = [self._nodes[nid].label for nid in unreachable]
            errors.append(f"Disconnected nodes not reachable from any source: {labels}")

        return errors

    # ---- Live Mutation (for self-healing and optimization) ----

    def add_node(self, node: PipelineNode) -> None:
        """Add a node to the DAG."""
        self.pipeline.nodes.append(node)
        self._nodes[node.id] = node
        self._adjacency[node.id] = []
        self._reverse_adjacency[node.id] = []

    def remove_node(self, node_id: str) -> PipelineNode | None:
        """Remove a node and all its edges from the DAG."""
        node = self._nodes.pop(node_id, None)
        if not node:
            return None

        # Remove from pipeline
        self.pipeline.nodes = [n for n in self.pipeline.nodes if n.id != node_id]

        # Remove all edges involving this node
        edges_to_remove = [
            eid for eid, e in self._edges.items()
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]
        for eid in edges_to_remove:
            self._remove_edge_by_id(eid)

        # Clean adjacency
        self._adjacency.pop(node_id, None)
        self._reverse_adjacency.pop(node_id, None)
        for nid in self._adjacency:
            self._adjacency[nid] = [n for n in self._adjacency[nid] if n != node_id]
        for nid in self._reverse_adjacency:
            self._reverse_adjacency[nid] = [n for n in self._reverse_adjacency[nid] if n != node_id]

        return node

    def add_edge(self, edge: PipelineEdge) -> None:
        """Add an edge to the DAG."""
        self.pipeline.edges.append(edge)
        self._edges[edge.id] = edge
        self._adjacency[edge.source_node_id].append(edge.target_node_id)
        self._reverse_adjacency[edge.target_node_id].append(edge.source_node_id)

    def remove_edge(self, source_id: str, target_id: str) -> PipelineEdge | None:
        """Remove an edge between two nodes."""
        edge = self.get_edge_between(source_id, target_id)
        if edge:
            self._remove_edge_by_id(edge.id)
        return edge

    def _remove_edge_by_id(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if not edge:
            return
        self.pipeline.edges = [e for e in self.pipeline.edges if e.id != edge_id]
        adj = self._adjacency.get(edge.source_node_id, [])
        if edge.target_node_id in adj:
            adj.remove(edge.target_node_id)
        rev = self._reverse_adjacency.get(edge.target_node_id, [])
        if edge.source_node_id in rev:
            rev.remove(edge.source_node_id)

    def insert_node_between(
        self, new_node: PipelineNode, source_id: str, target_id: str
    ) -> None:
        """
        Insert a new node between two existing connected nodes.
        Removes the edge source->target, adds source->new->target.
        Used by optimizer for inserting buffers, splitting operators, etc.
        """
        self.remove_edge(source_id, target_id)
        self.add_node(new_node)
        self.add_edge(PipelineEdge(source_node_id=source_id, target_node_id=new_node.id))
        self.add_edge(PipelineEdge(source_node_id=new_node.id, target_node_id=target_id))

    def swap_nodes(self, node_a_id: str, node_b_id: str) -> None:
        """
        Swap two adjacent nodes in the DAG.
        Used by optimizer for predicate pushdown (moving filter before join).
        Only works if A->B is a direct edge.
        """
        edge = self.get_edge_between(node_a_id, node_b_id)
        if not edge:
            raise DAGValidationError(
                f"Cannot swap: no direct edge from {node_a_id} to {node_b_id}"
            )

        # Get A's upstream and B's downstream (copy to avoid mutation during rewire)
        a_upstream = list(self.get_upstream(node_a_id))
        b_downstream = list(self.get_downstream(node_b_id))

        # Remove all edges involving A and B
        for up_id in a_upstream:
            self.remove_edge(up_id, node_a_id)
        self.remove_edge(node_a_id, node_b_id)
        for down_id in b_downstream:
            self.remove_edge(node_b_id, down_id)

        # Rewire: upstream -> B -> A -> downstream
        for up_id in a_upstream:
            self.add_edge(PipelineEdge(source_node_id=up_id, target_node_id=node_b_id))
        self.add_edge(PipelineEdge(source_node_id=node_b_id, target_node_id=node_a_id))
        for down_id in b_downstream:
            self.add_edge(PipelineEdge(source_node_id=node_a_id, target_node_id=down_id))

    def parallelize_node(self, node_id: str, parallelism: int) -> list[PipelineNode]:
        """
        Split a node into N parallel instances.
        Used by optimizer/healer to scale out a bottleneck operator.
        Returns list of new parallel nodes.
        """
        original = self._nodes.get(node_id)
        if not original:
            raise DAGValidationError(f"Node {node_id} not found")

        upstream_ids = list(self.get_upstream(node_id))
        downstream_ids = list(self.get_downstream(node_id))

        # Remove the original node
        self.remove_node(node_id)

        # Create N parallel copies
        parallel_nodes: list[PipelineNode] = []
        for i in range(parallelism):
            new_node = PipelineNode(
                label=f"{original.label}-p{i}",
                operator_type=original.operator_type,
                config=original.config.model_copy(),
                position_x=original.position_x + (i * 50),
                position_y=original.position_y + (i * 80),
                parallelism=1,
            )
            self.add_node(new_node)
            parallel_nodes.append(new_node)

            # Wire: all upstreams -> this copy, this copy -> all downstreams
            for up_id in upstream_ids:
                self.add_edge(PipelineEdge(source_node_id=up_id, target_node_id=new_node.id))
            for down_id in downstream_ids:
                self.add_edge(PipelineEdge(source_node_id=new_node.id, target_node_id=down_id))

        return parallel_nodes

    # ---- Snapshot for versioning ----

    def snapshot(self) -> dict[str, Any]:
        """Create a serializable snapshot of the current DAG state."""
        return {
            "nodes": [n.model_dump() for n in self._nodes.values()],
            "edges": [e.model_dump() for e in self._edges.values()],
        }

    def clone(self) -> DAG:
        """Create a deep copy of this DAG."""
        return DAG(deepcopy(self.pipeline))

    # ---- Utility ----

    def get_execution_layers(self) -> list[list[str]]:
        """
        Group nodes into layers for parallel execution.
        Nodes in the same layer have no dependencies between them.
        """
        topo = self.topological_sort()
        # Longest path from any source to this node determines its layer
        layer_map: dict[str, int] = {}
        for nid in topo:
            upstream_layers = [layer_map[uid] for uid in self.get_upstream(nid) if uid in layer_map]
            layer_map[nid] = (max(upstream_layers) + 1) if upstream_layers else 0

        layers: dict[int, list[str]] = defaultdict(list)
        for nid, layer in layer_map.items():
            layers[layer].append(nid)

        return [layers[i] for i in sorted(layers.keys())]

    def get_stream_key(self, source_id: str, target_id: str) -> str:
        """Generate the Redis Stream key for an edge."""
        pipeline_id = self.pipeline.id
        return f"flowstorm:{pipeline_id}:{source_id}:{target_id}"

    def assign_stream_keys(self) -> None:
        """Assign Redis Stream keys to all edges."""
        for edge in self._edges.values():
            edge.stream_key = self.get_stream_key(edge.source_node_id, edge.target_node_id)

    def __repr__(self) -> str:
        return (
            f"DAG(nodes={len(self._nodes)}, edges={len(self._edges)}, "
            f"pipeline='{self.pipeline.name}')"
        )
