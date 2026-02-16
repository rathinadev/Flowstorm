"""Predictive Scaler - predicts future load and pre-scales workers.

Instead of reacting AFTER a traffic spike, this module:
1. Collects throughput history over time
2. Detects patterns (time-of-day, periodic spikes)
3. Predicts load for the next 15 minutes
4. Pre-scales workers BEFORE the spike arrives
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class TrafficPattern:
    """Detected traffic pattern for a pipeline."""

    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        # hour_of_day (0-23) -> list of observed throughput values
        self.hourly_averages: dict[int, list[float]] = defaultdict(list)
        # Recent throughput samples: (timestamp, events_per_second)
        self.recent_samples: list[tuple[datetime, float]] = []
        self.trend: str = "stable"  # "stable", "increasing", "decreasing", "spike"

    def add_sample(self, timestamp: datetime, eps: float) -> None:
        """Record a throughput sample."""
        self.recent_samples.append((timestamp, eps))
        self.hourly_averages[timestamp.hour].append(eps)

        # Keep only last 24h of samples
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.recent_samples = [
            (ts, v) for ts, v in self.recent_samples if ts >= cutoff
        ]

        # Keep only last 7 days of hourly data
        for hour in self.hourly_averages:
            self.hourly_averages[hour] = self.hourly_averages[hour][-168:]  # 7*24

        self._update_trend()

    def _update_trend(self) -> None:
        """Analyze recent samples to determine trend."""
        if len(self.recent_samples) < 5:
            self.trend = "stable"
            return

        recent = [v for _, v in self.recent_samples[-10:]]
        older = [v for _, v in self.recent_samples[-20:-10]] if len(self.recent_samples) >= 20 else recent[:5]

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older) if older else avg_recent

        if avg_older == 0:
            self.trend = "stable"
            return

        change_ratio = avg_recent / avg_older

        if change_ratio > 3.0:
            self.trend = "spike"
        elif change_ratio > 1.3:
            self.trend = "increasing"
        elif change_ratio < 0.7:
            self.trend = "decreasing"
        else:
            self.trend = "stable"


class PredictiveScaler:
    """Predicts future load and recommends scaling actions."""

    def __init__(self):
        self.patterns: dict[str, TrafficPattern] = {}
        self.predictions: dict[str, list[dict[str, Any]]] = {}

    def record_throughput(
        self, pipeline_id: str, timestamp: datetime, eps: float
    ) -> None:
        """Record a throughput observation."""
        if pipeline_id not in self.patterns:
            self.patterns[pipeline_id] = TrafficPattern(pipeline_id)
        self.patterns[pipeline_id].add_sample(timestamp, eps)

    def predict_next_interval(
        self, pipeline_id: str, minutes_ahead: int = 15
    ) -> dict[str, Any]:
        """
        Predict throughput for the next N minutes.

        Uses a combination of:
        1. Historical hourly averages (time-of-day pattern)
        2. Recent trend (short-term momentum)
        3. Simple exponential smoothing
        """
        pattern = self.patterns.get(pipeline_id)
        if not pattern or len(pattern.recent_samples) < 10:
            return {
                "predicted_eps": 0,
                "confidence": "low",
                "recommendation": "insufficient_data",
                "trend": "unknown",
            }

        now = datetime.utcnow()
        target_time = now + timedelta(minutes=minutes_ahead)
        target_hour = target_time.hour

        # Historical average for the target hour
        hourly_data = pattern.hourly_averages.get(target_hour, [])
        historical_avg = sum(hourly_data) / len(hourly_data) if hourly_data else 0

        # Current throughput (average of last 5 samples)
        recent = [v for _, v in pattern.recent_samples[-5:]]
        current_avg = sum(recent) / len(recent) if recent else 0

        # Weighted prediction: 40% historical, 60% recent trend
        if historical_avg > 0 and current_avg > 0:
            predicted = historical_avg * 0.4 + current_avg * 0.6
            confidence = "medium"
        elif current_avg > 0:
            predicted = current_avg
            confidence = "low"
        else:
            predicted = historical_avg
            confidence = "low"

        # Adjust for trend
        if pattern.trend == "increasing":
            predicted *= 1.5
        elif pattern.trend == "spike":
            predicted *= 3.0
        elif pattern.trend == "decreasing":
            predicted *= 0.7

        # Determine recommendation
        recommendation = self._get_recommendation(
            current_avg, predicted, pattern.trend
        )

        prediction = {
            "pipeline_id": pipeline_id,
            "prediction_time": target_time.isoformat(),
            "predicted_eps": round(predicted, 1),
            "current_eps": round(current_avg, 1),
            "historical_avg_eps": round(historical_avg, 1),
            "trend": pattern.trend,
            "confidence": confidence,
            "recommendation": recommendation,
        }

        # Store prediction for later comparison with actual
        if pipeline_id not in self.predictions:
            self.predictions[pipeline_id] = []
        self.predictions[pipeline_id].append(prediction)
        # Keep last 100 predictions
        self.predictions[pipeline_id] = self.predictions[pipeline_id][-100:]

        return prediction

    def _get_recommendation(
        self, current: float, predicted: float, trend: str
    ) -> dict[str, Any]:
        """Determine scaling recommendation."""
        if current == 0:
            return {"action": "none", "reason": "no_traffic"}

        ratio = predicted / current if current > 0 else 1.0

        if ratio > 2.0 or trend == "spike":
            # Big increase coming - pre-scale
            scale_factor = min(int(math.ceil(ratio)), 5)
            return {
                "action": "scale_up",
                "scale_factor": scale_factor,
                "reason": f"Predicted {ratio:.1f}x traffic increase",
                "urgency": "high" if trend == "spike" else "medium",
            }
        elif ratio > 1.3:
            return {
                "action": "scale_up",
                "scale_factor": 2,
                "reason": f"Predicted {ratio:.1f}x traffic increase",
                "urgency": "low",
            }
        elif ratio < 0.3:
            return {
                "action": "scale_down",
                "reason": f"Predicted {ratio:.1f}x traffic decrease",
                "urgency": "low",
            }
        else:
            return {"action": "none", "reason": "stable_traffic"}

    def get_prediction_accuracy(self, pipeline_id: str) -> dict[str, Any]:
        """Compare past predictions with actual outcomes."""
        predictions = self.predictions.get(pipeline_id, [])
        pattern = self.patterns.get(pipeline_id)

        if not predictions or not pattern or len(pattern.recent_samples) < 2:
            return {"accuracy": "unknown", "samples": 0}

        # Compare predictions made 15+ minutes ago with what actually happened
        now = datetime.utcnow()
        errors = []

        for pred in predictions:
            pred_time = datetime.fromisoformat(pred["prediction_time"])
            if pred_time > now:
                continue  # Future prediction, can't verify yet

            # Find actual throughput around the predicted time
            actual_samples = [
                v for ts, v in pattern.recent_samples
                if abs((ts - pred_time).total_seconds()) < 120  # Within 2 min
            ]
            if actual_samples:
                actual = sum(actual_samples) / len(actual_samples)
                predicted = pred["predicted_eps"]
                if actual > 0:
                    error = abs(predicted - actual) / actual
                    errors.append(error)

        if not errors:
            return {"accuracy": "unknown", "samples": 0}

        avg_error = sum(errors) / len(errors)
        accuracy = max(0, (1 - avg_error) * 100)

        return {
            "accuracy_percent": round(accuracy, 1),
            "avg_error_percent": round(avg_error * 100, 1),
            "samples": len(errors),
        }
