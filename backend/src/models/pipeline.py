"""Pipeline, Node, and Edge models - the core data structures of FlowStorm."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Top-level classification of a node."""
    SOURCE = "source"
    OPERATOR = "operator"
    SINK = "sink"


class OperatorType(str, Enum):
    """Specific operator types available in FlowStorm."""
    # Sources
    MQTT_SOURCE = "mqtt_source"
    HTTP_SOURCE = "http_source"
    SIMULATOR_SOURCE = "simulator_source"

    # Operators
    FILTER = "filter"
    MAP = "map"
    WINDOW = "window"
    JOIN = "join"
    AGGREGATE = "aggregate"

    # Sinks
    CONSOLE_SINK = "console_sink"
    REDIS_SINK = "redis_sink"
    ALERT_SINK = "alert_sink"
    WEBHOOK_SINK = "webhook_sink"


# Classify operator types into node types
SOURCE_OPERATORS = {
    OperatorType.MQTT_SOURCE,
    OperatorType.HTTP_SOURCE,
    OperatorType.SIMULATOR_SOURCE,
}
SINK_OPERATORS = {
    OperatorType.CONSOLE_SINK,
    OperatorType.REDIS_SINK,
    OperatorType.ALERT_SINK,
    OperatorType.WEBHOOK_SINK,
}


def get_node_type(operator_type: OperatorType) -> NodeType:
    if operator_type in SOURCE_OPERATORS:
        return NodeType.SOURCE
    if operator_type in SINK_OPERATORS:
        return NodeType.SINK
    return NodeType.OPERATOR


class OperatorConfig(BaseModel):
    """Configuration for a specific operator instance."""
    # Filter config
    field: str | None = None
    condition: str | None = None  # "gt", "lt", "eq", "neq", "gte", "lte", "contains"
    value: Any | None = None

    # Map config
    expression: str | None = None  # Python expression for transformation
    output_field: str | None = None

    # Window config
    window_type: str | None = None  # "tumbling", "sliding", "session"
    window_size_seconds: int | None = None
    slide_interval_seconds: int | None = None

    # Aggregate config
    agg_function: str | None = None  # "avg", "sum", "min", "max", "count"
    agg_field: str | None = None
    group_by: str | None = None

    # Join config
    join_stream: str | None = None
    join_key: str | None = None
    join_window_seconds: int | None = None

    # MQTT Source config
    mqtt_topic: str | None = None
    mqtt_broker: str | None = None
    mqtt_port: int | None = None

    # Alert config
    alert_channel: str | None = None  # "console", "webhook", "telegram"
    alert_webhook_url: str | None = None
    alert_message_template: str | None = None

    # Simulator config
    sensor_count: int | None = None
    interval_ms: int | None = None
    chaos_enabled: bool | None = None


class PipelineNode(BaseModel):
    """A single node in the pipeline DAG."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str
    operator_type: OperatorType
    node_type: NodeType = NodeType.OPERATOR
    config: OperatorConfig = Field(default_factory=OperatorConfig)

    # Position in the visual editor (from React Flow)
    position_x: float = 0.0
    position_y: float = 0.0

    # Runtime state (not set by user)
    worker_id: str | None = None
    parallelism: int = 1

    def model_post_init(self, __context: Any) -> None:
        self.node_type = get_node_type(self.operator_type)


class PipelineEdge(BaseModel):
    """A directed edge connecting two nodes."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_node_id: str
    target_node_id: str
    stream_key: str | None = None  # Redis Stream key for this edge


class PipelineStatus(str, Enum):
    DRAFT = "draft"
    DEPLOYING = "deploying"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    STOPPED = "stopped"


class Pipeline(BaseModel):
    """A complete pipeline definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    nodes: list[PipelineNode] = Field(default_factory=list)
    edges: list[PipelineEdge] = Field(default_factory=list)
    status: PipelineStatus = PipelineStatus.DRAFT
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_node(self, node_id: str) -> PipelineNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_sources(self) -> list[PipelineNode]:
        return [n for n in self.nodes if n.node_type == NodeType.SOURCE]

    def get_sinks(self) -> list[PipelineNode]:
        return [n for n in self.nodes if n.node_type == NodeType.SINK]

    def get_operators(self) -> list[PipelineNode]:
        return [n for n in self.nodes if n.node_type == NodeType.OPERATOR]

    def get_downstream(self, node_id: str) -> list[str]:
        """Get IDs of nodes downstream from the given node."""
        return [e.target_node_id for e in self.edges if e.source_node_id == node_id]

    def get_upstream(self, node_id: str) -> list[str]:
        """Get IDs of nodes upstream from the given node."""
        return [e.source_node_id for e in self.edges if e.target_node_id == node_id]
