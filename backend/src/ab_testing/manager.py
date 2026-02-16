"""A/B Pipeline Testing - split traffic between two pipeline versions.

Deploys two versions of a pipeline simultaneously, routes a configurable
percentage of traffic to each, and collects side-by-side metrics for comparison.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ABTestConfig(BaseModel):
    """Configuration for an A/B test."""
    pipeline_id_a: str
    pipeline_id_b: str
    split_percent_a: int = 50  # 0-100, rest goes to B
    name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ABTestMetrics(BaseModel):
    """Collected metrics for one side of an A/B test."""
    pipeline_id: str
    avg_throughput_eps: float = 0.0
    avg_latency_ms: float = 0.0
    total_events: int = 0
    error_count: int = 0
    avg_cpu_percent: float = 0.0
    avg_memory_percent: float = 0.0
    samples: int = 0


class ABTestResult(BaseModel):
    """Side-by-side comparison of two pipeline versions."""
    test_id: str
    name: str
    version_a: ABTestMetrics
    version_b: ABTestMetrics
    winner: str | None = None  # "a", "b", or None if inconclusive
    summary: str = ""
    started_at: str = ""
    duration_seconds: float = 0.0


class ABTestManager:
    """Manages A/B tests between pipeline versions."""

    def __init__(self):
        self._tests: dict[str, ABTestConfig] = {}
        self._metrics_a: dict[str, list[dict[str, float]]] = {}
        self._metrics_b: dict[str, list[dict[str, float]]] = {}
        self._test_counter = 0

    def create_test(
        self,
        pipeline_id_a: str,
        pipeline_id_b: str,
        split_percent: int = 50,
        name: str = "",
    ) -> str:
        """Create a new A/B test. Returns test ID."""
        self._test_counter += 1
        test_id = f"ab-{self._test_counter}"

        self._tests[test_id] = ABTestConfig(
            pipeline_id_a=pipeline_id_a,
            pipeline_id_b=pipeline_id_b,
            split_percent_a=split_percent,
            name=name or f"Test {self._test_counter}",
        )
        self._metrics_a[test_id] = []
        self._metrics_b[test_id] = []

        logger.info(
            f"A/B test {test_id} created: {pipeline_id_a} ({split_percent}%) "
            f"vs {pipeline_id_b} ({100 - split_percent}%)"
        )
        return test_id

    def record_metrics(
        self,
        test_id: str,
        pipeline_id: str,
        throughput: float,
        latency: float,
        errors: int,
        cpu: float,
        memory: float,
    ) -> None:
        """Record a metric sample for one side of an A/B test."""
        config = self._tests.get(test_id)
        if not config:
            return

        sample = {
            "throughput": throughput,
            "latency": latency,
            "errors": errors,
            "cpu": cpu,
            "memory": memory,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if pipeline_id == config.pipeline_id_a:
            self._metrics_a[test_id].append(sample)
            # Keep last 1000
            self._metrics_a[test_id] = self._metrics_a[test_id][-1000:]
        elif pipeline_id == config.pipeline_id_b:
            self._metrics_b[test_id].append(sample)
            self._metrics_b[test_id] = self._metrics_b[test_id][-1000:]

    def get_result(self, test_id: str) -> ABTestResult | None:
        """Get the current comparison result for an A/B test."""
        config = self._tests.get(test_id)
        if not config:
            return None

        metrics_a = self._aggregate(test_id, config.pipeline_id_a, self._metrics_a)
        metrics_b = self._aggregate(test_id, config.pipeline_id_b, self._metrics_b)

        winner, summary = self._determine_winner(metrics_a, metrics_b)

        elapsed = (datetime.utcnow() - config.created_at).total_seconds()

        return ABTestResult(
            test_id=test_id,
            name=config.name,
            version_a=metrics_a,
            version_b=metrics_b,
            winner=winner,
            summary=summary,
            started_at=config.created_at.isoformat(),
            duration_seconds=round(elapsed, 1),
        )

    def list_tests(self) -> list[dict[str, Any]]:
        """List all A/B tests."""
        results = []
        for test_id, config in self._tests.items():
            results.append({
                "test_id": test_id,
                "name": config.name,
                "pipeline_a": config.pipeline_id_a,
                "pipeline_b": config.pipeline_id_b,
                "split_percent_a": config.split_percent_a,
                "created_at": config.created_at.isoformat(),
                "samples_a": len(self._metrics_a.get(test_id, [])),
                "samples_b": len(self._metrics_b.get(test_id, [])),
            })
        return results

    def stop_test(self, test_id: str) -> ABTestResult | None:
        """Stop an A/B test and return final results."""
        result = self.get_result(test_id)
        self._tests.pop(test_id, None)
        self._metrics_a.pop(test_id, None)
        self._metrics_b.pop(test_id, None)
        return result

    def _aggregate(
        self, test_id: str, pipeline_id: str, store: dict[str, list[dict]]
    ) -> ABTestMetrics:
        """Aggregate metric samples into summary stats."""
        samples = store.get(test_id, [])
        if not samples:
            return ABTestMetrics(pipeline_id=pipeline_id)

        n = len(samples)
        return ABTestMetrics(
            pipeline_id=pipeline_id,
            avg_throughput_eps=sum(s["throughput"] for s in samples) / n,
            avg_latency_ms=sum(s["latency"] for s in samples) / n,
            total_events=int(sum(s["throughput"] for s in samples)),
            error_count=sum(s["errors"] for s in samples),
            avg_cpu_percent=sum(s["cpu"] for s in samples) / n,
            avg_memory_percent=sum(s["memory"] for s in samples) / n,
            samples=n,
        )

    def _determine_winner(
        self, a: ABTestMetrics, b: ABTestMetrics
    ) -> tuple[str | None, str]:
        """Compare metrics and determine the winner."""
        if a.samples < 10 or b.samples < 10:
            return None, "Insufficient data - need at least 10 samples per version"

        score_a = 0
        score_b = 0
        reasons = []

        # Higher throughput is better
        if a.avg_throughput_eps > b.avg_throughput_eps * 1.1:
            score_a += 1
            reasons.append(
                f"A has {a.avg_throughput_eps:.0f} vs B {b.avg_throughput_eps:.0f} eps"
            )
        elif b.avg_throughput_eps > a.avg_throughput_eps * 1.1:
            score_b += 1
            reasons.append(
                f"B has {b.avg_throughput_eps:.0f} vs A {a.avg_throughput_eps:.0f} eps"
            )

        # Lower latency is better
        if a.avg_latency_ms < b.avg_latency_ms * 0.9:
            score_a += 1
            reasons.append(
                f"A latency {a.avg_latency_ms:.0f}ms vs B {b.avg_latency_ms:.0f}ms"
            )
        elif b.avg_latency_ms < a.avg_latency_ms * 0.9:
            score_b += 1
            reasons.append(
                f"B latency {b.avg_latency_ms:.0f}ms vs A {a.avg_latency_ms:.0f}ms"
            )

        # Fewer errors is better
        if a.error_count < b.error_count:
            score_a += 1
        elif b.error_count < a.error_count:
            score_b += 1

        # Lower CPU is better (more efficient)
        if a.avg_cpu_percent < b.avg_cpu_percent * 0.9:
            score_a += 1
        elif b.avg_cpu_percent < a.avg_cpu_percent * 0.9:
            score_b += 1

        if score_a > score_b:
            return "a", f"Version A wins ({score_a}-{score_b}). " + "; ".join(reasons)
        elif score_b > score_a:
            return "b", f"Version B wins ({score_b}-{score_a}). " + "; ".join(reasons)
        else:
            return None, "Inconclusive - versions perform similarly. " + "; ".join(reasons)
