"""Worker state and health models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkerStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    DEAD = "dead"
    DRAINING = "draining"  # Finishing current events before shutdown
    STOPPED = "stopped"


class WorkerMetrics(BaseModel):
    """Real-time metrics reported by a worker via heartbeat."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_mb: float = 0.0
    events_processed: int = 0
    events_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    errors: int = 0
    last_event_at: datetime | None = None


class WorkerHealth(BaseModel):
    """Computed health assessment of a worker."""
    score: float = 100.0  # 0-100
    cpu_score: float = 100.0
    memory_score: float = 100.0
    throughput_score: float = 100.0
    latency_score: float = 100.0
    status: WorkerStatus = WorkerStatus.RUNNING
    issues: list[str] = Field(default_factory=list)

    @property
    def is_healthy(self) -> bool:
        return self.score >= 70

    @property
    def is_critical(self) -> bool:
        return self.score < 30


class WorkerConfig(BaseModel):
    """Configuration for spawning a worker container."""
    worker_id: str
    pipeline_id: str
    node_id: str
    operator_type: str
    operator_config: dict
    input_streams: list[str] = Field(default_factory=list)
    output_streams: list[str] = Field(default_factory=list)
    consumer_group: str = "default"
    redis_host: str = "redis"
    redis_port: int = 6379
    heartbeat_interval_ms: int = 500
    checkpoint_every_n: int = 1000


class Worker(BaseModel):
    """Full state of a running worker."""
    id: str
    container_id: str | None = None
    pipeline_id: str
    node_id: str
    operator_type: str
    status: WorkerStatus = WorkerStatus.STARTING
    config: WorkerConfig
    metrics: WorkerMetrics = Field(default_factory=WorkerMetrics)
    health: WorkerHealth = Field(default_factory=WorkerHealth)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat_at: datetime | None = None
    checkpoint_offset: str | None = None  # Last checkpointed Redis Stream ID

    @property
    def is_alive(self) -> bool:
        return self.status in {WorkerStatus.RUNNING, WorkerStatus.DEGRADED, WorkerStatus.STARTING}
