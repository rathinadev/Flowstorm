"""Anomaly Detector - detects unusual patterns in pipeline health.

Monitors for:
- Sudden throughput drops (bottleneck detection)
- Error rate spikes
- Consumer lag growth (backpressure)
- Memory leaks (steady memory increase)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyType:
    THROUGHPUT_DROP = "throughput_drop"
    ERROR_SPIKE = "error_spike"
    CONSUMER_LAG = "consumer_lag"
    MEMORY_LEAK = "memory_leak"
    LATENCY_SPIKE = "latency_spike"


class Anomaly:
    """A detected anomaly."""

    def __init__(
        self,
        anomaly_type: str,
        worker_id: str,
        node_id: str,
        severity: str,
        description: str,
        current_value: float,
        expected_value: float,
    ):
        self.anomaly_type = anomaly_type
        self.worker_id = worker_id
        self.node_id = node_id
        self.severity = severity  # "warning", "critical"
        self.description = description
        self.current_value = current_value
        self.expected_value = expected_value
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.anomaly_type,
            "worker_id": self.worker_id,
            "node_id": self.node_id,
            "severity": self.severity,
            "description": self.description,
            "current_value": self.current_value,
            "expected_value": self.expected_value,
            "timestamp": self.timestamp.isoformat(),
        }


class AnomalyDetector:
    """Detects anomalies in worker metrics."""

    def __init__(self):
        # worker_id -> list of (timestamp, metric_value)
        self._throughput_history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        self._error_history: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
        self._memory_history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        self._latency_history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

    def record_metrics(
        self,
        worker_id: str,
        node_id: str,
        eps: float,
        errors: int,
        memory_pct: float,
        latency_ms: float,
    ) -> list[Anomaly]:
        """Record metrics and check for anomalies."""
        now = datetime.utcnow()
        anomalies: list[Anomaly] = []

        # Record
        self._throughput_history[worker_id].append((now, eps))
        self._error_history[worker_id].append((now, errors))
        self._memory_history[worker_id].append((now, memory_pct))
        self._latency_history[worker_id].append((now, latency_ms))

        # Trim to last 10 minutes
        cutoff = now - timedelta(minutes=10)
        for hist in [self._throughput_history, self._error_history,
                     self._memory_history, self._latency_history]:
            hist[worker_id] = [(ts, v) for ts, v in hist[worker_id] if ts >= cutoff]

        # Check for anomalies
        anomalies.extend(self._check_throughput(worker_id, node_id))
        anomalies.extend(self._check_errors(worker_id, node_id))
        anomalies.extend(self._check_memory(worker_id, node_id))
        anomalies.extend(self._check_latency(worker_id, node_id))

        return anomalies

    def _check_throughput(self, worker_id: str, node_id: str) -> list[Anomaly]:
        """Detect sudden throughput drops."""
        history = self._throughput_history[worker_id]
        if len(history) < 5:
            return []

        recent = [v for _, v in history[-3:]]
        older = [v for _, v in history[-10:-3]] if len(history) >= 10 else [v for _, v in history[:3]]

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older) if older else avg_recent

        if avg_older > 0 and avg_recent < avg_older * 0.3:
            return [Anomaly(
                anomaly_type=AnomalyType.THROUGHPUT_DROP,
                worker_id=worker_id,
                node_id=node_id,
                severity="critical",
                description=f"Throughput dropped from {avg_older:.0f} to {avg_recent:.0f} eps",
                current_value=avg_recent,
                expected_value=avg_older,
            )]

        return []

    def _check_errors(self, worker_id: str, node_id: str) -> list[Anomaly]:
        """Detect error rate spikes."""
        history = self._error_history[worker_id]
        if len(history) < 3:
            return []

        recent_errors = history[-1][1]
        prev_errors = history[-3][1] if len(history) >= 3 else 0
        new_errors = recent_errors - prev_errors

        if new_errors > 10:
            return [Anomaly(
                anomaly_type=AnomalyType.ERROR_SPIKE,
                worker_id=worker_id,
                node_id=node_id,
                severity="warning" if new_errors < 50 else "critical",
                description=f"{new_errors} new errors in last interval",
                current_value=new_errors,
                expected_value=0,
            )]

        return []

    def _check_memory(self, worker_id: str, node_id: str) -> list[Anomaly]:
        """Detect memory leaks (steady increase)."""
        history = self._memory_history[worker_id]
        if len(history) < 10:
            return []

        values = [v for _, v in history]
        # Check if memory is consistently increasing
        increases = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
        if increases > len(values) * 0.8 and values[-1] > 80:
            return [Anomaly(
                anomaly_type=AnomalyType.MEMORY_LEAK,
                worker_id=worker_id,
                node_id=node_id,
                severity="critical" if values[-1] > 90 else "warning",
                description=f"Memory steadily increasing: {values[0]:.0f}% -> {values[-1]:.0f}%",
                current_value=values[-1],
                expected_value=values[0],
            )]

        return []

    def _check_latency(self, worker_id: str, node_id: str) -> list[Anomaly]:
        """Detect latency spikes."""
        history = self._latency_history[worker_id]
        if len(history) < 3:
            return []

        current = history[-1][1]
        avg = sum(v for _, v in history[:-1]) / max(len(history) - 1, 1)

        if avg > 0 and current > avg * 5 and current > 100:
            return [Anomaly(
                anomaly_type=AnomalyType.LATENCY_SPIKE,
                worker_id=worker_id,
                node_id=node_id,
                severity="critical" if current > 1000 else "warning",
                description=f"Latency spiked from avg {avg:.0f}ms to {current:.0f}ms",
                current_value=current,
                expected_value=avg,
            )]

        return []
