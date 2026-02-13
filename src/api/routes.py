"""FastAPI REST and WebSocket routes for FlowStorm."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.schemas import (
    ChaosRequest,
    ChaosResponse,
    CreatePipelineRequest,
    HealingEventResponse,
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
from src.ab_testing.manager import ABTestManager
from src.chaos.engine import ChaosEngine
from src.dlq.diagnostics import DLQDiagnostics
from src.engine.runtime import RuntimeManager
from src.models.pipeline import (
    OperatorConfig,
    Pipeline,
    PipelineEdge,
    PipelineNode,
    OperatorType,
)
from src.pipeline_git.versioner import PipelineVersioner, VersionTrigger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Injected via set_* functions from main.py
_runtime_manager: RuntimeManager | None = None
_versioner: PipelineVersioner | None = None
_chaos_engines: dict[str, ChaosEngine] = {}
_event_forwarders: dict[str, PipelineEventForwarder] = {}
_metrics_pushers: dict[str, MetricsPusher] = {}
_ab_manager = ABTestManager()
_dlq_diagnostics: DLQDiagnostics | None = None


def set_runtime_manager(manager: RuntimeManager) -> None:
    global _runtime_manager
    _runtime_manager = manager


def set_versioner(versioner: PipelineVersioner) -> None:
    global _versioner
    _versioner = versioner


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

    # Save initial version
    if _versioner:
        await _versioner.create_initial_version(runtime.dag)

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

    # Stop chaos if running
    chaos = _chaos_engines.pop(pipeline_id, None)
    if chaos:
        await chaos.stop()

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

    # Stop existing chaos if running
    if pipeline_id in _chaos_engines:
        await _chaos_engines[pipeline_id].stop()

    chaos = ChaosEngine(runtime, manager.redis)
    await chaos.start(
        intensity=request.intensity,
        duration_seconds=request.duration_seconds,
    )
    _chaos_engines[pipeline_id] = chaos

    return ChaosResponse(
        started=True,
        intensity=request.intensity,
        duration_seconds=request.duration_seconds,
    )


@router.delete("/pipelines/{pipeline_id}/chaos")
async def stop_chaos(pipeline_id: str):
    """Stop chaos mode."""
    chaos = _chaos_engines.pop(pipeline_id, None)
    if chaos:
        await chaos.stop()
    return {"status": "stopped", "pipeline_id": pipeline_id}


@router.get("/pipelines/{pipeline_id}/chaos/history")
async def get_chaos_history(pipeline_id: str):
    """Get chaos event history."""
    chaos = _chaos_engines.get(pipeline_id)
    if chaos:
        return {"events": chaos.get_history()}
    return {"events": []}


# ---- Pipeline Git ----

@router.get("/pipelines/{pipeline_id}/versions")
async def get_versions(pipeline_id: str):
    """Get pipeline version history."""
    if not _versioner:
        return []

    history = await _versioner.get_history(pipeline_id)
    return [
        {
            "version_id": v["version_number"],
            "trigger": v["trigger"],
            "description": v["description"],
            "timestamp": v["created_at"],
            "node_count": v["node_count"],
            "edge_count": v["edge_count"],
        }
        for v in history
    ]


@router.get("/pipelines/{pipeline_id}/versions/{from_v}/diff/{to_v}")
async def diff_versions(pipeline_id: str, from_v: int, to_v: int):
    """Get visual diff between two pipeline versions."""
    if not _versioner:
        raise HTTPException(status_code=503, detail="Versioner not initialized")

    diff = await _versioner.diff_versions(pipeline_id, from_v, to_v)
    if not diff:
        raise HTTPException(status_code=404, detail="Versions not found")

    return diff.to_dict()


@router.post("/pipelines/{pipeline_id}/rollback")
async def rollback_pipeline(pipeline_id: str, request: RollbackRequest):
    """Rollback pipeline to a previous version."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if not _versioner:
        raise HTTPException(status_code=503, detail="Versioner not initialized")

    # Get the target version's DAG snapshot
    snapshot = await _versioner.get_snapshot(pipeline_id, request.version_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Version {request.version_id} not found")

    # Save rollback version
    await _versioner.save_rollback_version(runtime.dag, request.version_id)

    return {
        "status": "rolled_back",
        "version_id": request.version_id,
        "snapshot": snapshot,
    }


# ---- Lineage ----

@router.get("/pipelines/{pipeline_id}/lineage/{event_id}")
async def get_lineage(pipeline_id: str, event_id: str):
    """Trace an event's lineage through the pipeline."""
    manager = _get_manager()
    runtime = manager.get_runtime(pipeline_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Read the event from the output stream
    output_key = f"flowstorm:output:{pipeline_id}"
    try:
        messages = await manager.redis.xrange(output_key, min=event_id, max=event_id)
        if messages:
            msg_id, fields = messages[0]
            lineage_raw = fields.get("lineage", "[]")
            lineage = json.loads(lineage_raw)
            data = json.loads(fields.get("data", "{}"))
            return {
                "event_id": msg_id,
                "data": data,
                "lineage": lineage,
                "node_id": fields.get("node_id", ""),
            }
    except Exception as e:
        logger.error(f"Lineage lookup error: {e}")

    # Fallback: search recent events
    try:
        messages = await manager.redis.xrevrange(output_key, count=100)
        for msg_id, fields in messages:
            if event_id in msg_id:
                lineage_raw = fields.get("lineage", "[]")
                lineage = json.loads(lineage_raw)
                data = json.loads(fields.get("data", "{}"))
                return {
                    "event_id": msg_id,
                    "data": data,
                    "lineage": lineage,
                }
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Event not found")


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
                "node_id": w.node_id,
                "operator_type": w.operator_type,
                "metrics": w.metrics.model_dump(),
                "issues": w.health.issues,
            }
            for wid, w in runtime.workers.items()
        },
    }


@router.get("/pipelines/{pipeline_id}/healing-log")
async def get_healing_log(pipeline_id: str):
    """Get self-healing action history."""
    from src.main import health_monitor
    if not health_monitor:
        return {"events": []}

    events = health_monitor.get_healing_log(pipeline_id)
    return {
        "events": [
            {
                "action": e.action.value,
                "trigger": e.trigger,
                "target_node_id": e.target_node_id,
                "details": e.details,
                "events_replayed": e.events_replayed,
                "duration_ms": e.duration_ms,
                "success": e.success,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
    }


# ---- WebSocket ----

@router.websocket("/ws/pipeline/{pipeline_id}")
async def websocket_endpoint(websocket: WebSocket, pipeline_id: str):
    """WebSocket endpoint for real-time pipeline updates."""
    await ws_manager.connect(websocket, pipeline_id)

    try:
        while True:
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


# ---- Dead Letter Queue ----

@router.get("/pipelines/{pipeline_id}/dlq")
async def get_dlq(pipeline_id: str, count: int = 100):
    """Get dead letter queue entries with diagnostics."""
    manager = _get_manager()
    if not manager.redis:
        return {"entries": [], "total": 0}

    global _dlq_diagnostics
    if not _dlq_diagnostics:
        _dlq_diagnostics = DLQDiagnostics(manager.redis)

    entries = await _dlq_diagnostics.get_entries(pipeline_id, count)
    return {
        "entries": [e.to_dict() for e in entries],
        "total": len(entries),
    }


@router.get("/pipelines/{pipeline_id}/dlq/stats")
async def get_dlq_stats(pipeline_id: str):
    """Get aggregated DLQ statistics grouped by failure type."""
    manager = _get_manager()
    if not manager.redis:
        return {"total_failed": 0, "groups": [], "by_node": {}}

    global _dlq_diagnostics
    if not _dlq_diagnostics:
        _dlq_diagnostics = DLQDiagnostics(manager.redis)

    return await _dlq_diagnostics.get_stats(pipeline_id)


# ---- A/B Testing ----

@router.post("/ab-tests")
async def create_ab_test(
    pipeline_id_a: str,
    pipeline_id_b: str,
    split_percent: int = 50,
    name: str = "",
):
    """Create a new A/B test between two pipeline versions."""
    test_id = _ab_manager.create_test(
        pipeline_id_a, pipeline_id_b, split_percent, name
    )
    return {"test_id": test_id, "status": "running"}


@router.get("/ab-tests")
async def list_ab_tests():
    """List all A/B tests."""
    return {"tests": _ab_manager.list_tests()}


@router.get("/ab-tests/{test_id}")
async def get_ab_test(test_id: str):
    """Get A/B test results."""
    result = _ab_manager.get_result(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return result.model_dump()


@router.delete("/ab-tests/{test_id}")
async def stop_ab_test(test_id: str):
    """Stop an A/B test and return final results."""
    result = _ab_manager.stop_test(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="A/B test not found")
    return result.model_dump()


# ---- Predictive Scaling ----

@router.get("/pipelines/{pipeline_id}/prediction")
async def get_prediction(pipeline_id: str):
    """Get predictive scaling recommendation."""
    from src.main import health_monitor
    if not health_monitor:
        return {"recommendation": {"action": "none", "reason": "Monitor not running"}}
    return health_monitor.get_prediction(pipeline_id)
