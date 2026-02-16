"""Event and message models flowing through the stream processing engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """A single event flowing through the pipeline."""
    id: str = ""  # Redis Stream message ID, set by transport
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_node_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)

    # Lineage tracking - records which nodes this event passed through
    lineage: list[LineageEntry] = Field(default_factory=list)

    def add_lineage(self, node_id: str, operator_type: str, action: str, details: str = ""):
        self.lineage.append(LineageEntry(
            node_id=node_id,
            operator_type=operator_type,
            action=action,
            details=details,
            timestamp=datetime.utcnow(),
        ))

    def to_redis(self) -> dict[str, str]:
        """Serialize to flat dict for Redis Streams XADD."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "source_node_id": self.source_node_id,
            "data": self._serialize_data(self.data),
            "lineage": self._serialize_data([e.model_dump() for e in self.lineage]),
        }

    @classmethod
    def from_redis(cls, msg_id: str, fields: dict[str, str]) -> StreamEvent:
        """Deserialize from Redis Streams XREADGROUP result."""
        import json
        data = json.loads(fields.get("data", "{}"))
        lineage_raw = json.loads(fields.get("lineage", "[]"))
        lineage = [LineageEntry(**entry) for entry in lineage_raw]
        return cls(
            id=msg_id,
            timestamp=datetime.fromisoformat(fields.get("timestamp", datetime.utcnow().isoformat())),
            source_node_id=fields.get("source_node_id", ""),
            data=data,
            lineage=lineage,
        )

    @staticmethod
    def _serialize_data(obj: Any) -> str:
        import json
        return json.dumps(obj, default=str)


class LineageEntry(BaseModel):
    """A single step in an event's journey through the pipeline."""
    node_id: str
    operator_type: str
    action: str  # "ingested", "filtered_pass", "filtered_drop", "transformed", "aggregated", "emitted"
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Heartbeat(BaseModel):
    """Heartbeat message sent by workers to the health monitor."""
    worker_id: str
    pipeline_id: str
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    events_processed: int = 0
    events_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    errors: int = 0


class Checkpoint(BaseModel):
    """Checkpoint state for exactly-once recovery."""
    worker_id: str
    pipeline_id: str
    node_id: str
    stream_key: str
    last_processed_id: str  # Redis Stream message ID
    operator_state: dict[str, Any] = Field(default_factory=dict)  # Window buffers, aggregation state, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealingAction(str, Enum):
    FAILOVER = "failover"
    SCALE_OUT = "scale_out"
    SCALE_IN = "scale_in"
    MIGRATE = "migrate"
    INSERT_BUFFER = "insert_buffer"
    RESTART = "restart"
    SPILL_TO_DISK = "spill_to_disk"


class HealingEvent(BaseModel):
    """Record of a self-healing action taken by the engine."""
    id: str = ""
    pipeline_id: str
    action: HealingAction
    trigger: str  # What caused this healing action
    target_worker_id: str | None = None
    target_node_id: str | None = None
    details: str = ""
    events_replayed: int = 0
    duration_ms: float = 0.0
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OptimizationEvent(BaseModel):
    """Record of a DAG optimization applied by the engine."""
    id: str = ""
    pipeline_id: str
    optimization_type: str  # "predicate_pushdown", "operator_fusion", "auto_parallel", "window_switch"
    description: str
    before_snapshot: dict[str, Any] = Field(default_factory=dict)
    after_snapshot: dict[str, Any] = Field(default_factory=dict)
    estimated_gain: str = ""  # "20x cost reduction", "2x throughput"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
