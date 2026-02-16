"""Chaos scenarios - individual failure types that can be injected.

Each scenario simulates a specific real-world failure mode.
The chaos engine picks scenarios randomly based on intensity.
"""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChaosResult:
    """Result of executing a chaos scenario."""
    scenario_name: str
    target: str
    description: str
    timestamp: datetime
    success: bool = True


class ChaosScenario(ABC):
    """Base class for chaos scenarios."""

    name: str = "unknown"
    description: str = ""
    severity: str = "medium"  # "low", "medium", "high"

    @abstractmethod
    async def execute(self, runtime: Any) -> ChaosResult:
        ...


class KillRandomWorker(ChaosScenario):
    """Kill a random worker container instantly."""

    name = "kill_worker"
    description = "Instantly kills a random worker container"
    severity = "high"

    async def execute(self, runtime: Any) -> ChaosResult:
        workers = list(runtime.workers.values())
        if not workers:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No workers to kill", timestamp=datetime.utcnow(),
                success=False,
            )

        victim = random.choice(workers)
        logger.warning(f"CHAOS: Killing worker {victim.id} ({victim.operator_type})")

        try:
            if runtime.docker:
                container = runtime.docker.containers.get(victim.container_id)
                container.kill()
        except Exception as e:
            logger.debug(f"Container kill (may be in dev mode): {e}")

        # Mark as dead so health monitor picks it up
        from src.models.worker import WorkerStatus
        victim.status = WorkerStatus.DEAD

        return ChaosResult(
            scenario_name=self.name,
            target=f"worker:{victim.id} ({victim.operator_type})",
            description=f"Killed worker {victim.id} running {victim.operator_type}",
            timestamp=datetime.utcnow(),
        )


class InjectLatency(ChaosScenario):
    """Inject artificial latency into a random stream."""

    name = "inject_latency"
    description = "Adds 500ms-2s delay to a random stream"
    severity = "medium"

    async def execute(self, runtime: Any) -> ChaosResult:
        streams = runtime.compiled.stream_keys
        if not streams:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No streams available", timestamp=datetime.utcnow(),
                success=False,
            )

        target_stream = random.choice(streams)
        delay_ms = random.randint(500, 2000)

        # Set a latency flag in Redis that workers can check
        latency_key = f"flowstorm:chaos:latency:{target_stream}"
        await runtime.redis.set(latency_key, str(delay_ms), ex=30)

        logger.warning(f"CHAOS: Injecting {delay_ms}ms latency on {target_stream}")

        return ChaosResult(
            scenario_name=self.name,
            target=f"stream:{target_stream}",
            description=f"Injected {delay_ms}ms latency on stream {target_stream} for 30s",
            timestamp=datetime.utcnow(),
        )


class CorruptEvents(ChaosScenario):
    """Inject corrupt/malformed events into a random stream."""

    name = "corrupt_events"
    description = "Injects malformed events into the pipeline"
    severity = "medium"

    async def execute(self, runtime: Any) -> ChaosResult:
        streams = runtime.compiled.stream_keys
        if not streams:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No streams available", timestamp=datetime.utcnow(),
                success=False,
            )

        target_stream = random.choice(streams)
        corrupt_count = random.randint(10, 50)

        # Inject corrupt events
        for i in range(corrupt_count):
            corrupt_type = random.choice(["missing_data", "wrong_type", "empty", "garbage"])

            if corrupt_type == "missing_data":
                data = {"timestamp": datetime.utcnow().isoformat(), "_chaos": "missing_data"}
            elif corrupt_type == "wrong_type":
                data = {
                    "data": "not_a_valid_json_number",
                    "temperature": "hot",
                    "timestamp": "not-a-date",
                    "_chaos": "wrong_type",
                }
            elif corrupt_type == "empty":
                data = {"_chaos": "empty_event"}
            else:
                data = {"garbage": "x" * 1000, "_chaos": "garbage"}

            await runtime.redis.xadd(target_stream, {
                "data": str(data),
                "timestamp": datetime.utcnow().isoformat(),
                "source_node_id": "chaos_engine",
                "lineage": "[]",
            })

        logger.warning(f"CHAOS: Injected {corrupt_count} corrupt events into {target_stream}")

        return ChaosResult(
            scenario_name=self.name,
            target=f"stream:{target_stream}",
            description=f"Injected {corrupt_count} corrupt events into {target_stream}",
            timestamp=datetime.utcnow(),
        )


class MemoryPressure(ChaosScenario):
    """Simulate memory pressure on a random worker."""

    name = "memory_pressure"
    description = "Simulates high memory usage on a worker"
    severity = "medium"

    async def execute(self, runtime: Any) -> ChaosResult:
        workers = list(runtime.workers.values())
        if not workers:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No workers available", timestamp=datetime.utcnow(),
                success=False,
            )

        victim = random.choice(workers)

        # Set a memory pressure flag
        pressure_key = f"flowstorm:chaos:memory_pressure:{victim.id}"
        await runtime.redis.set(pressure_key, "true", ex=30)

        logger.warning(f"CHAOS: Memory pressure on worker {victim.id}")

        return ChaosResult(
            scenario_name=self.name,
            target=f"worker:{victim.id}",
            description=f"Simulating memory pressure on {victim.id} for 30s",
            timestamp=datetime.utcnow(),
        )


class FloodSource(ChaosScenario):
    """Flood a source with 50x normal data volume."""

    name = "flood_source"
    description = "Floods a source stream with 50x data volume"
    severity = "high"

    async def execute(self, runtime: Any) -> ChaosResult:
        streams = runtime.compiled.stream_keys
        if not streams:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No streams available", timestamp=datetime.utcnow(),
                success=False,
            )

        # Target the first stream (closest to source)
        target_stream = streams[0]
        flood_count = 5000

        # Rapid-fire events
        for i in range(flood_count):
            await runtime.redis.xadd(target_stream, {
                "data": f'{{"sensor_id": "flood-{i}", "temperature": {random.uniform(20, 40):.1f}, "zone": "chaos"}}',
                "timestamp": datetime.utcnow().isoformat(),
                "source_node_id": "chaos_flood",
                "lineage": "[]",
            })

        logger.warning(f"CHAOS: Flooded {target_stream} with {flood_count} events")

        return ChaosResult(
            scenario_name=self.name,
            target=f"stream:{target_stream}",
            description=f"Flooded {target_stream} with {flood_count} events (50x normal)",
            timestamp=datetime.utcnow(),
        )


class NetworkPartition(ChaosScenario):
    """Simulate a network partition by pausing a worker's streams."""

    name = "network_partition"
    description = "Simulates network partition - worker can't read/write"
    severity = "high"

    async def execute(self, runtime: Any) -> ChaosResult:
        workers = list(runtime.workers.values())
        if not workers:
            return ChaosResult(
                scenario_name=self.name, target="none",
                description="No workers available", timestamp=datetime.utcnow(),
                success=False,
            )

        victim = random.choice(workers)
        partition_key = f"flowstorm:chaos:partition:{victim.id}"
        duration = random.randint(5, 15)
        await runtime.redis.set(partition_key, "true", ex=duration)

        logger.warning(
            f"CHAOS: Network partition for worker {victim.id} ({duration}s)"
        )

        return ChaosResult(
            scenario_name=self.name,
            target=f"worker:{victim.id}",
            description=f"Network partition on {victim.id} for {duration}s",
            timestamp=datetime.utcnow(),
        )


# All available scenarios
ALL_SCENARIOS: list[ChaosScenario] = [
    KillRandomWorker(),
    InjectLatency(),
    CorruptEvents(),
    MemoryPressure(),
    FloodSource(),
    NetworkPartition(),
]

# Scenarios by severity
LOW_SCENARIOS = [s for s in ALL_SCENARIOS if s.severity == "low"]
MEDIUM_SCENARIOS = [s for s in ALL_SCENARIOS if s.severity in ("low", "medium")]
HIGH_SCENARIOS = ALL_SCENARIOS  # All scenarios at high intensity
