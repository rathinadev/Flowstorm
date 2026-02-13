"""FlowStorm - Self-Healing Stream Processing Engine.

Main FastAPI application entry point.
Wires together all subsystems: runtime, health monitor, optimizer,
chaos engine, pipeline git, NLP parser.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.routes import router, set_runtime_manager, set_versioner, set_nlp
from src.engine.runtime import RuntimeManager
from src.health.monitor import HealthMonitor
from src.nlp.mapper import NLPMapper
from src.nlp.parser import NLPParser
from src.pipeline_git.versioner import PipelineVersioner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("flowstorm")

# Global instances
runtime_manager: RuntimeManager | None = None
health_monitor: HealthMonitor | None = None
versioner: PipelineVersioner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    global runtime_manager, health_monitor, versioner

    logger.info("FlowStorm engine starting up...")

    # Initialize runtime manager
    runtime_manager = RuntimeManager(
        redis_host=settings.REDIS_HOST,
        redis_port=settings.REDIS_PORT,
        worker_image=settings.WORKER_IMAGE,
    )
    await runtime_manager.initialize()
    set_runtime_manager(runtime_manager)

    # Initialize health monitor
    health_monitor = HealthMonitor(
        redis_host=settings.REDIS_HOST,
        redis_port=settings.REDIS_PORT,
        runtime_manager=runtime_manager,
    )
    await health_monitor.start()

    # Initialize pipeline versioner
    versioner = PipelineVersioner()
    await versioner.initialize()
    set_versioner(versioner)

    # Initialize NLP parser and mapper
    nlp_parser = NLPParser()
    nlp_mapper = NLPMapper()
    set_nlp(nlp_parser, nlp_mapper)

    logger.info("FlowStorm engine ready.")

    yield

    # Shutdown
    logger.info("FlowStorm engine shutting down...")
    if health_monitor:
        await health_monitor.stop()
    if runtime_manager:
        await runtime_manager.shutdown()
    logger.info("FlowStorm engine stopped.")


app = FastAPI(
    title="FlowStorm",
    description="Self-healing, self-optimizing real-time stream processing engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router)


@app.get("/health")
async def health_check():
    pipelines = runtime_manager.get_all_status() if runtime_manager else {}
    return {
        "status": "ok",
        "engine": "flowstorm",
        "version": "0.1.0",
        "active_pipelines": len(pipelines),
    }
