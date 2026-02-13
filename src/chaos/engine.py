"""Chaos Engine - orchestrates chaos scenarios on live pipelines.

The "Unleash Chaos" button. Picks random failure scenarios and
executes them at configurable intervals. The self-healing system
should recover from everything this throws at it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Any

from src.chaos.scenarios import (
    ALL_SCENARIOS,
    HIGH_SCENARIOS,
    LOW_SCENARIOS,
    MEDIUM_SCENARIOS,
    ChaosResult,
    ChaosScenario,
)

logger = logging.getLogger(__name__)


class ChaosEngine:
    """
    Orchestrates chaos on a pipeline.

    Intensity levels:
    - low: Only mild disruptions every 15-30s
    - medium: Mix of mild and moderate every 10-20s
    - high: Everything including worker kills every 5-15s
    """

    def __init__(self, runtime: Any, redis_client: Any):
        self.runtime = runtime
        self.redis = redis_client
        self._running = False
        self._task: asyncio.Task | None = None
        self.intensity: str = "medium"
        self.history: list[ChaosResult] = []
        self._min_interval: int = 10
        self._max_interval: int = 20

    async def start(self, intensity: str = "medium", duration_seconds: int = 60) -> None:
        """Start the chaos engine."""
        self.intensity = intensity
        self._running = True

        if intensity == "low":
            self._min_interval = 15
            self._max_interval = 30
        elif intensity == "medium":
            self._min_interval = 10
            self._max_interval = 20
        elif intensity == "high":
            self._min_interval = 5
            self._max_interval = 15

        self._task = asyncio.create_task(self._chaos_loop(duration_seconds))
        logger.warning(
            f"CHAOS ENGINE STARTED: intensity={intensity}, "
            f"duration={duration_seconds}s, "
            f"interval={self._min_interval}-{self._max_interval}s"
        )

        # Publish start event
        await self._publish_event("chaos.started", {
            "intensity": intensity,
            "duration_seconds": duration_seconds,
        })

    async def stop(self) -> None:
        """Stop the chaos engine."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Chaos engine stopped")

        await self._publish_event("chaos.stopped", {
            "total_events": len(self.history),
        })

    async def _chaos_loop(self, duration: int) -> None:
        """Main chaos loop - pick and execute scenarios."""
        start_time = asyncio.get_event_loop().time()

        try:
            while self._running:
                # Check duration
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= duration:
                    logger.info(f"Chaos duration ({duration}s) reached. Stopping.")
                    break

                # Pick a scenario
                scenario = self._pick_scenario()

                # Execute it
                result = await scenario.execute(self.runtime)
                self.history.append(result)

                # Publish event
                await self._publish_event("chaos.event", {
                    "scenario": result.scenario_name,
                    "target": result.target,
                    "description": result.description,
                    "severity": scenario.severity,
                    "timestamp": result.timestamp.isoformat(),
                })

                logger.warning(
                    f"CHAOS [{result.scenario_name}]: {result.description}"
                )

                # Random interval before next chaos
                interval = random.randint(self._min_interval, self._max_interval)
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    def _pick_scenario(self) -> ChaosScenario:
        """Pick a random scenario based on intensity."""
        if self.intensity == "low":
            pool = MEDIUM_SCENARIOS or ALL_SCENARIOS
        elif self.intensity == "medium":
            pool = MEDIUM_SCENARIOS or ALL_SCENARIOS
        else:
            pool = HIGH_SCENARIOS or ALL_SCENARIOS

        return random.choice(pool)

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Publish chaos events for the frontend."""
        channel = f"flowstorm:events:{self.runtime.pipeline_id}"
        message = json.dumps({
            "type": event_type,
            "pipeline_id": self.runtime.pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        })
        try:
            await self.redis.publish(channel, message)
        except Exception as e:
            logger.error(f"Failed to publish chaos event: {e}")

    def get_history(self) -> list[dict]:
        """Get chaos event history."""
        return [
            {
                "scenario": r.scenario_name,
                "target": r.target,
                "description": r.description,
                "timestamp": r.timestamp.isoformat(),
                "success": r.success,
            }
            for r in self.history
        ]
