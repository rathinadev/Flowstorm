"""FastAPI REST and WebSocket routes for FlowStorm."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.schemas import (
    ChaosRequest,
    ChaosResponse,
    CreatePipelineRequest,
    HealingEventResponse,
    NLPCommandRequest,
    NLPCommandResponse,
    PipelineResponse,
    PipelineStatusResponse,
    PipelineVersionResponse,
    RollbackRequest,
)
from src.api.websocket import (
    MetricsPusher,
    PipelineEventForwarder,
    ws_manager,
)
from src.engine.runtime import RuntimeManager
from src.models.pipeline import (
    OperatorConfig,
    Pipeline,
    PipelineEdge,
    PipelineNode,
    OperatorType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# These will be injected via app state in main.py
_runtime_manager: RuntimeManager | None = None
_event_forwarders: dict[str, PipelineEventForwarder] = {}
_metrics_pushers: dict[str, MetricsPusher] = {}


def set_runtime_manager(manager: RuntimeManager) -> None:
    global _runtime_manager
    _runtime_manager = manager


def _get_manager() -> RuntimeManager:
    if not _runtime_manager:
        raise HTTPException(status_code=503, detail="Runtime manager not initialized")
    return _runtime_manager


# ---- Pipeline CRUD ----

@router.post("/pipelines", response_model=PipelineStatusResponse)
async def create_pipeline(request: CreatePipelineRequest):
    """Create and deploy a new pipeline."""
    manager = _get_manager()

    nodes = [
        PipelineNode(
            id=n.id or None,
            label=n.label,
            operator_type=OperatorType(n.operator_type),
            config=OperatorConfig(**n.config),
            position_x=n.position_x,
            position_y=n.position_y,
        )
        for n in request.nodes
    ]
    edges = [
        PipelineEdge(
            id=e.id or None,
            source_node_id=e.source_node_id,
            target_node_id=e.target_node_id,
        )
        for e in request.edges
    ]

    pipeline = Pipeline(
        name=request.name,
        description=request.description,
        nodes=nodes,
        edges=edges,
    )

    try:
        runtime = await manager.deploy_pipeline(pipeline)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Start event forwarding and metrics pushing
    if manager.redis:
        forwarder = PipelineEventForwarder(pipeline.id, manager.redis, ws_manager)
        await forwarder.start()
        _event_forwarders[pipeline.id] = forwarder

        pusher = MetricsPusher(pipeline.id, manager.redis, ws_manager)
        await pusher.start()
        _metrics_pushers[pipeline.id] = pusher

    return PipelineStatusResponse(**runtime.get_status())


@router.get("/pipelines", response_model=list[PipelineStatusResponse])
async def list_pipelines():
    """List all active pipelines."""
    manager = _get_manager()
    statuses = manager.get_all_status()
    return [PipelineStatusResponse(**s) for s in statuses.values()]


@router.get("/pipelines/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline(pipeline_id: str):
    """Get a pipeline's status."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return PipelineStatusResponse(**runtime.get_status())


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Stop and remove a pipeline."""
    manager = _get_manager()

    # Stop event forwarding
    forwarder = _event_forwarders.pop(pipeline_id, None)
    if forwarder:
        await forwarder.stop()
    pusher = _metrics_pushers.pop(pipeline_id, None)
    if pusher:
        await pusher.stop()

    await manager.stop_pipeline(pipeline_id)
    return {"status": "stopped", "pipeline_id": pipeline_id}


# ---- Chaos Mode ----

@router.post("/pipelines/{pipeline_id}/chaos", response_model=ChaosResponse)
async def start_chaos(pipeline_id: str, request: ChaosRequest):
    """Start chaos mode on a pipeline."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Chaos engine will be implemented in src/chaos/
    # For now, return acknowledgment
    return ChaosResponse(
        started=True,
        intensity=request.intensity,
        duration_seconds=request.duration_seconds,
    )


@router.delete("/pipelines/{pipeline_id}/chaos")
async def stop_chaos(pipeline_id: str):
    """Stop chaos mode."""
    return {"status": "stopped", "pipeline_id": pipeline_id}


# ---- NLP ----

@router.post("/pipelines/{pipeline_id}/nlp", response_model=NLPCommandResponse)
async def nlp_command(pipeline_id: str, request: NLPCommandRequest):
    """Process a natural language command to modify the pipeline."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # NLP parser will be implemented in src/nlp/
    return NLPCommandResponse(
        success=True,
        interpretation=f"Understood: {request.text}",
        changes=[],
    )


# ---- Pipeline Git ----

@router.get("/pipelines/{pipeline_id}/versions", response_model=list[PipelineVersionResponse])
async def get_versions(pipeline_id: str):
    """Get pipeline version history."""
    # Pipeline Git will be implemented in src/pipeline_git/
    return []


@router.post("/pipelines/{pipeline_id}/rollback")
async def rollback_pipeline(pipeline_id: str, request: RollbackRequest):
    """Rollback pipeline to a previous version."""
    return {"status": "rolled_back", "version_id": request.version_id}


# ---- Lineage ----

@router.get("/pipelines/{pipeline_id}/lineage/{event_id}")
async def get_lineage(pipeline_id: str, event_id: str):
    """Trace an event's lineage through the pipeline."""
    return {"event_id": event_id, "path": [], "message": "Lineage tracing coming soon"}


# ---- Health ----

@router.get("/pipelines/{pipeline_id}/health")
async def get_health(pipeline_id: str):
    """Get health status of all workers in a pipeline."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "pipeline_id": pipeline_id,
        "workers": {
            wid: {
                "status": w.status.value,
                "health_score": w.health.score,
                "metrics": w.metrics.model_dump(),
            }
            for wid, w in runtime.workers.items()
        },
    }


# ---- WebSocket ----

@router.websocket("/ws/pipeline/{pipeline_id}")
async def websocket_endpoint(websocket: WebSocket, pipeline_id: str):
    """WebSocket endpoint for real-time pipeline updates."""
    await ws_manager.connect(websocket, pipeline_id)

    try:
        while True:
            # Listen for commands from the frontend
            data = await websocket.receive_json()
            command = data.get("type", "")

            if command == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})

            elif command == "subscribe_metrics":
                await ws_manager.send_personal(websocket, {
                    "type": "subscribed",
                    "channel": "metrics",
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, pipeline_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, pipeline_id)
