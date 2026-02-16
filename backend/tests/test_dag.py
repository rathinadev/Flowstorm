"""Tests for the DAG data structure and operations."""

import pytest
from src.models.pipeline import (
    Pipeline,
    PipelineNode,
    PipelineEdge,
    OperatorType,
    OperatorConfig,
)
from src.engine.dag import DAG, DAGValidationError


# ---- Fixtures ----


def make_node(label: str, op_type: OperatorType, node_id: str | None = None) -> PipelineNode:
    node = PipelineNode(
        label=label,
        operator_type=op_type,
        config=OperatorConfig(),
    )
    if node_id:
        node.id = node_id
    return node


def make_edge(source: str, target: str, edge_id: str | None = None) -> PipelineEdge:
    edge = PipelineEdge(source_node_id=source, target_node_id=target)
    if edge_id:
        edge.id = edge_id
    return edge


def make_linear_pipeline() -> Pipeline:
    """Source -> Filter -> Aggregate -> Console Sink"""
    src = make_node("MQTT Source", OperatorType.MQTT_SOURCE, "src")
    flt = make_node("Filter", OperatorType.FILTER, "flt")
    agg = make_node("Aggregate", OperatorType.AGGREGATE, "agg")
    sink = make_node("Console Sink", OperatorType.CONSOLE_SINK, "sink")

    return Pipeline(
        name="test-linear",
        nodes=[src, flt, agg, sink],
        edges=[
            make_edge("src", "flt", "e1"),
            make_edge("flt", "agg", "e2"),
            make_edge("agg", "sink", "e3"),
        ],
    )


def make_diamond_pipeline() -> Pipeline:
    """
    Source -> Filter -> Aggregate -> Sink
           -> Map    /
    """
    src = make_node("Source", OperatorType.MQTT_SOURCE, "src")
    flt = make_node("Filter", OperatorType.FILTER, "flt")
    mp = make_node("Map", OperatorType.MAP, "mp")
    agg = make_node("Aggregate", OperatorType.AGGREGATE, "agg")
    sink = make_node("Sink", OperatorType.CONSOLE_SINK, "sink")

    return Pipeline(
        name="test-diamond",
        nodes=[src, flt, mp, agg, sink],
        edges=[
            make_edge("src", "flt", "e1"),
            make_edge("src", "mp", "e2"),
            make_edge("flt", "agg", "e3"),
            make_edge("mp", "agg", "e4"),
            make_edge("agg", "sink", "e5"),
        ],
    )


# ---- Topological Sort ----


class TestTopologicalSort:
    def test_linear_pipeline(self):
        dag = DAG(make_linear_pipeline())
        order = dag.topological_sort()
        assert order == ["src", "flt", "agg", "sink"]

    def test_diamond_pipeline(self):
        dag = DAG(make_diamond_pipeline())
        order = dag.topological_sort()
        # src must come first, sink last, flt/mp before agg
        assert order[0] == "src"
        assert order[-1] == "sink"
        assert order.index("flt") < order.index("agg")
        assert order.index("mp") < order.index("agg")

    def test_single_node(self):
        pipeline = Pipeline(
            name="single",
            nodes=[make_node("Source", OperatorType.MQTT_SOURCE, "s")],
            edges=[],
        )
        dag = DAG(pipeline)
        assert dag.topological_sort() == ["s"]

    def test_cycle_detection(self):
        pipeline = Pipeline(
            name="cyclic",
            nodes=[
                make_node("A", OperatorType.FILTER, "a"),
                make_node("B", OperatorType.MAP, "b"),
                make_node("C", OperatorType.AGGREGATE, "c"),
            ],
            edges=[
                make_edge("a", "b", "e1"),
                make_edge("b", "c", "e2"),
                make_edge("c", "a", "e3"),  # cycle
            ],
        )
        dag = DAG(pipeline)
        with pytest.raises(DAGValidationError, match="Cycle detected"):
            dag.topological_sort()


# ---- Validation ----


class TestValidation:
    def test_valid_linear_pipeline(self):
        dag = DAG(make_linear_pipeline())
        errors = dag.validate()
        assert errors == []

    def test_valid_diamond_pipeline(self):
        dag = DAG(make_diamond_pipeline())
        errors = dag.validate()
        assert errors == []

    def test_empty_pipeline(self):
        dag = DAG(Pipeline(name="empty"))
        errors = dag.validate()
        assert any("no nodes" in e.lower() for e in errors)

    def test_no_source(self):
        pipeline = Pipeline(
            name="no-src",
            nodes=[
                make_node("Filter", OperatorType.FILTER, "f"),
                make_node("Sink", OperatorType.CONSOLE_SINK, "s"),
            ],
            edges=[make_edge("f", "s", "e1")],
        )
        dag = DAG(pipeline)
        errors = dag.validate()
        assert any("source" in e.lower() for e in errors)

    def test_no_sink(self):
        pipeline = Pipeline(
            name="no-sink",
            nodes=[
                make_node("Source", OperatorType.MQTT_SOURCE, "s"),
                make_node("Filter", OperatorType.FILTER, "f"),
            ],
            edges=[make_edge("s", "f", "e1")],
        )
        dag = DAG(pipeline)
        errors = dag.validate()
        assert any("sink" in e.lower() for e in errors)

    def test_disconnected_node(self):
        pipeline = Pipeline(
            name="disconnected",
            nodes=[
                make_node("Source", OperatorType.MQTT_SOURCE, "src"),
                make_node("Sink", OperatorType.CONSOLE_SINK, "sink"),
                make_node("Orphan", OperatorType.FILTER, "orphan"),
            ],
            edges=[make_edge("src", "sink", "e1")],
        )
        dag = DAG(pipeline)
        errors = dag.validate()
        assert any("disconnected" in e.lower() or "reachable" in e.lower() for e in errors)

    def test_source_with_incoming_edge(self):
        pipeline = Pipeline(
            name="bad-source",
            nodes=[
                make_node("Source", OperatorType.MQTT_SOURCE, "src"),
                make_node("Filter", OperatorType.FILTER, "flt"),
                make_node("Sink", OperatorType.CONSOLE_SINK, "sink"),
            ],
            edges=[
                make_edge("flt", "src", "e1"),  # edge INTO source
                make_edge("src", "sink", "e2"),
            ],
        )
        dag = DAG(pipeline)
        errors = dag.validate()
        assert any("incoming" in e.lower() for e in errors)

    def test_sink_with_outgoing_edge(self):
        pipeline = Pipeline(
            name="bad-sink",
            nodes=[
                make_node("Source", OperatorType.MQTT_SOURCE, "src"),
                make_node("Sink", OperatorType.CONSOLE_SINK, "sink"),
                make_node("After", OperatorType.FILTER, "after"),
            ],
            edges=[
                make_edge("src", "sink", "e1"),
                make_edge("sink", "after", "e2"),  # edge OUT of sink
            ],
        )
        dag = DAG(pipeline)
        errors = dag.validate()
        assert any("outgoing" in e.lower() for e in errors)


# ---- Live Mutation ----


class TestLiveMutation:
    def test_add_node(self):
        dag = DAG(make_linear_pipeline())
        assert len(dag.nodes) == 4

        new_node = make_node("New Map", OperatorType.MAP, "new")
        dag.add_node(new_node)
        assert len(dag.nodes) == 5
        assert dag.get_node("new") is not None

    def test_remove_node(self):
        dag = DAG(make_linear_pipeline())
        removed = dag.remove_node("flt")
        assert removed is not None
        assert removed.label == "Filter"
        assert len(dag.nodes) == 3
        assert dag.get_node("flt") is None
        # Edges to/from flt should also be gone
        assert "flt" not in dag.get_downstream("src")
        assert "flt" not in dag.get_upstream("agg")

    def test_remove_nonexistent_node(self):
        dag = DAG(make_linear_pipeline())
        assert dag.remove_node("nonexistent") is None

    def test_add_edge(self):
        pipeline = Pipeline(
            name="test",
            nodes=[
                make_node("Source", OperatorType.MQTT_SOURCE, "s"),
                make_node("Sink", OperatorType.CONSOLE_SINK, "k"),
            ],
            edges=[],
        )
        dag = DAG(pipeline)
        assert dag.get_downstream("s") == []

        dag.add_edge(make_edge("s", "k", "e1"))
        assert dag.get_downstream("s") == ["k"]
        assert dag.get_upstream("k") == ["s"]

    def test_remove_edge(self):
        dag = DAG(make_linear_pipeline())
        assert "flt" in dag.get_downstream("src")

        removed = dag.remove_edge("src", "flt")
        assert removed is not None
        assert "flt" not in dag.get_downstream("src")

    def test_insert_node_between(self):
        dag = DAG(make_linear_pipeline())
        # Insert a map between src and flt
        new_map = make_node("Inserted Map", OperatorType.MAP, "mp")
        dag.insert_node_between(new_map, "src", "flt")

        assert dag.get_edge_between("src", "flt") is None
        assert dag.get_edge_between("src", "mp") is not None
        assert dag.get_edge_between("mp", "flt") is not None
        # Still valid DAG
        order = dag.topological_sort()
        assert order.index("src") < order.index("mp") < order.index("flt")

    def test_swap_adjacent_nodes(self):
        dag = DAG(make_linear_pipeline())
        # Before: src -> flt -> agg -> sink
        dag.swap_nodes("flt", "agg")
        # After:  src -> agg -> flt -> sink
        assert "agg" in dag.get_downstream("src")
        assert "flt" in dag.get_downstream("agg")
        assert "sink" in dag.get_downstream("flt")
        order = dag.topological_sort()
        assert order.index("agg") < order.index("flt")

    def test_swap_non_adjacent_fails(self):
        dag = DAG(make_linear_pipeline())
        with pytest.raises(DAGValidationError, match="no direct edge"):
            dag.swap_nodes("src", "agg")

    def test_parallelize_node(self):
        dag = DAG(make_linear_pipeline())
        # Parallelize filter into 3 copies
        parallel = dag.parallelize_node("flt", 3)
        assert len(parallel) == 3
        # Original filter should be gone
        assert dag.get_node("flt") is None
        # Each parallel node should be connected src -> parallel -> agg
        for pnode in parallel:
            assert "src" in dag.get_upstream(pnode.id)
            assert "agg" in dag.get_downstream(pnode.id)


# ---- Snapshot and Clone ----


class TestSnapshotClone:
    def test_snapshot(self):
        dag = DAG(make_linear_pipeline())
        snap = dag.snapshot()
        assert "nodes" in snap
        assert "edges" in snap
        assert len(snap["nodes"]) == 4
        assert len(snap["edges"]) == 3

    def test_clone_is_independent(self):
        dag = DAG(make_linear_pipeline())
        clone = dag.clone()
        # Mutating clone doesn't affect original
        clone.remove_node("flt")
        assert dag.get_node("flt") is not None
        assert clone.get_node("flt") is None


# ---- Execution Layers ----


class TestExecutionLayers:
    def test_linear_layers(self):
        dag = DAG(make_linear_pipeline())
        layers = dag.get_execution_layers()
        assert len(layers) == 4
        assert layers[0] == ["src"]
        assert layers[1] == ["flt"]
        assert layers[2] == ["agg"]
        assert layers[3] == ["sink"]

    def test_diamond_layers(self):
        dag = DAG(make_diamond_pipeline())
        layers = dag.get_execution_layers()
        # Layer 0: src, Layer 1: flt + mp (parallel), Layer 2: agg, Layer 3: sink
        assert len(layers) == 4
        assert layers[0] == ["src"]
        assert set(layers[1]) == {"flt", "mp"}
        assert layers[2] == ["agg"]
        assert layers[3] == ["sink"]


# ---- Stream Keys ----


class TestStreamKeys:
    def test_assign_stream_keys(self):
        dag = DAG(make_linear_pipeline())
        dag.assign_stream_keys()
        edge = dag.get_edge_between("src", "flt")
        assert edge is not None
        assert edge.stream_key is not None
        assert "src" in edge.stream_key
        assert "flt" in edge.stream_key
