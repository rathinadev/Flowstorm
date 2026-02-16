"""Self-Healer - takes autonomous actions to fix pipeline issues.

Receives anomalies from the detector and decides what healing
action to take. Works with the runtime to execute the healing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.health.detector import Anomaly, AnomalyType
from src.models.events import HealingAction, HealingEvent

logger = logging.getLogger(__name__)


class SelfHealer:
    """Decides and executes healing actions based on detected anomalies."""

    def __init__(self):
        self.healing_log: list[HealingEvent] = []
        # Cooldown: don't heal the same node twice within this many seconds
        self._cooldowns: dict[str, datetime] = {}
        self._cooldown_seconds = 30

    async def handle_anomaly(self, anomaly: Anomaly, runtime: Any) -> HealingEvent | None:
        """
        Decide what to do about an anomaly and execute the healing action.
        """
        # Check cooldown
        cooldown_key = f"{anomaly.node_id}:{anomaly.anomaly_type}"
        last_healed = self._cooldowns.get(cooldown_key)
        if last_healed:
            elapsed = (datetime.utcnow() - last_healed).total_seconds()
            if elapsed < self._cooldown_seconds:
                logger.debug(
                    f"Skipping healing for {cooldown_key} "
                    f"(cooldown: {self._cooldown_seconds - elapsed:.0f}s remaining)"
                )
                return None

        healing_event = None

        if anomaly.anomaly_type == AnomalyType.THROUGHPUT_DROP:
            healing_event = await self._handle_throughput_drop(anomaly, runtime)

        elif anomaly.anomaly_type == AnomalyType.ERROR_SPIKE:
            healing_event = await self._handle_error_spike(anomaly, runtime)

        elif anomaly.anomaly_type == AnomalyType.MEMORY_LEAK:
            healing_event = await self._handle_memory_leak(anomaly, runtime)

        elif anomaly.anomaly_type == AnomalyType.LATENCY_SPIKE:
            healing_event = await self._handle_latency_spike(anomaly, runtime)

        elif anomaly.anomaly_type == AnomalyType.CONSUMER_LAG:
            healing_event = await self._handle_consumer_lag(anomaly, runtime)

        if healing_event:
            self.healing_log.append(healing_event)
            self._cooldowns[cooldown_key] = datetime.utcnow()

        return healing_event

    async def _handle_throughput_drop(
        self, anomaly: Anomaly, runtime: Any
    ) -> HealingEvent:
        """Handle throughput drop - try restarting the worker."""
        logger.warning(
            f"HEAL: Throughput drop on {anomaly.worker_id} - "
            f"restarting worker"
        )

        start = datetime.utcnow()
        new_worker = await runtime._restart_worker(anomaly.worker_id)
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        return HealingEvent(
            pipeline_id=runtime.pipeline_id,
            action=HealingAction.RESTART,
            trigger=anomaly.description,
            target_worker_id=new_worker.id if new_worker else anomaly.worker_id,
            target_node_id=anomaly.node_id,
            details="Restarted worker due to throughput drop",
            duration_ms=elapsed,
            success=new_worker is not None,
        )

    async def _handle_error_spike(
        self, anomaly: Anomaly, runtime: Any
    ) -> HealingEvent:
        """Handle error spike - restart the worker with a fresh state."""
        logger.warning(
            f"HEAL: Error spike on {anomaly.worker_id} ({anomaly.current_value} errors) - "
            f"restarting"
        )

        start = datetime.utcnow()
        new_worker = await runtime._restart_worker(anomaly.worker_id)
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        return HealingEvent(
            pipeline_id=runtime.pipeline_id,
            action=HealingAction.RESTART,
            trigger=anomaly.description,
            target_worker_id=new_worker.id if new_worker else anomaly.worker_id,
            target_node_id=anomaly.node_id,
            details=f"Restarted worker due to {int(anomaly.current_value)} errors",
            duration_ms=elapsed,
            success=new_worker is not None,
        )

    async def _handle_memory_leak(
        self, anomaly: Anomaly, runtime: Any
    ) -> HealingEvent:
        """Handle memory leak - migrate operator to a fresh worker."""
        logger.warning(
            f"HEAL: Memory leak on {anomaly.worker_id} "
            f"({anomaly.current_value:.0f}%) - migrating"
        )

        start = datetime.utcnow()
        # Kill and respawn - the new worker starts with fresh memory
        new_worker = await runtime._restart_worker(anomaly.worker_id)
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        return HealingEvent(
            pipeline_id=runtime.pipeline_id,
            action=HealingAction.MIGRATE,
            trigger=anomaly.description,
            target_worker_id=new_worker.id if new_worker else anomaly.worker_id,
            target_node_id=anomaly.node_id,
            details=f"Migrated operator to fresh worker (memory was at {anomaly.current_value:.0f}%)",
            duration_ms=elapsed,
            success=new_worker is not None,
        )

    async def _handle_latency_spike(
        self, anomaly: Anomaly, runtime: Any
    ) -> HealingEvent:
        """Handle latency spike - scale out the operator."""
        logger.warning(
            f"HEAL: Latency spike on {anomaly.worker_id} "
            f"({anomaly.current_value:.0f}ms) - scaling out"
        )

        start = datetime.utcnow()
        healing = await runtime.handle_scale_out(anomaly.node_id, 2)
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        healing.trigger = anomaly.description
        healing.duration_ms = elapsed
        return healing

    async def _handle_consumer_lag(
        self, anomaly: Anomaly, runtime: Any
    ) -> HealingEvent:
        """Handle consumer lag - scale out the slow consumer."""
        logger.warning(
            f"HEAL: Consumer lag on {anomaly.worker_id} - scaling out"
        )

        start = datetime.utcnow()
        healing = await runtime.handle_scale_out(anomaly.node_id, 3)
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000

        healing.trigger = anomaly.description
        healing.duration_ms = elapsed
        return healing
