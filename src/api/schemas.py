"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---- Pipeline CRUD ----

class NodeSchema(BaseModel):
    id: str | None = None
    label: str
    operator_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0


class EdgeSchema(BaseModel):
    id: str | None = None
    source_node_id: str
    target_node_id: str


class CreatePipelineRequest(BaseModel):
    name: str
    description: str = ""
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]


class PipelineResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    version: int
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]
    created_at: str
    updated_at: str


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    name: str
    status: str
    workers: dict[str, Any]
    total_workers: int
    stream_keys: list[str]


# ---- NLP ----

class NLPCommandRequest(BaseModel):
    text: str


class NLPCommandResponse(BaseModel):
    success: bool
    interpretation: str
    changes: list[dict[str, Any]] = Field(default_factory=list)
    new_nodes: list[NodeSchema] = Field(default_factory=list)
    new_edges: list[EdgeSchema] = Field(default_factory=list)
    removed_nodes: list[str] = Field(default_factory=list)


# ---- Chaos ----

class ChaosRequest(BaseModel):
    intensity: str = "medium"  # "low", "medium", "high"
    duration_seconds: int = 60


class ChaosResponse(BaseModel):
    started: bool
    intensity: str
    duration_seconds: int


# ---- Pipeline Git ----

class PipelineVersionResponse(BaseModel):
    version_id: int
    trigger: str  # "USER", "AUTO_OPTIMIZE", "AUTO_HEAL"
    description: str
    timestamp: str
    node_count: int
    edge_count: int


class RollbackRequest(BaseModel):
    version_id: int


# ---- Lineage ----

class LineageStepResponse(BaseModel):
    node_id: str
    operator_type: str
    action: str
    details: str
    timestamp: str


class LineageResponse(BaseModel):
    event_id: str
    path: list[LineageStepResponse]
    source_data: dict[str, Any]
    final_data: dict[str, Any]


# ---- Health ----

class WorkerHealthResponse(BaseModel):
    worker_id: str
    node_id: str
    operator_type: str
    status: str
    health_score: float
    cpu_percent: float
    memory_percent: float
    events_per_second: float
    avg_latency_ms: float
    errors: int


class HealingEventResponse(BaseModel):
    action: str
    trigger: str
    target_node_id: str | None
    details: str
    events_replayed: int
    duration_ms: float
    success: bool
    timestamp: str
