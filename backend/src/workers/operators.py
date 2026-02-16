"""Stream processing operator implementations.

Each operator extends BaseWorker and implements the process() method.
Stateful operators (Window, Aggregate, Join) also implement get_state()/restore_state().
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from src.models.events import StreamEvent
from src.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class FilterOperator(BaseWorker):
    """
    Filters events based on a condition.

    Config:
        field: str - the field in event.data to check
        condition: str - "gt", "lt", "eq", "neq", "gte", "lte", "contains"
        value: Any - the value to compare against

    Selectivity tracking: records what percentage of events pass the filter.
    This is used by the DAG optimizer for predicate pushdown decisions.
    """

    def __init__(self):
        super().__init__()
        self._total_seen = 0
        self._total_passed = 0

    @property
    def selectivity(self) -> float:
        """Ratio of events that pass the filter (0.0 to 1.0)."""
        if self._total_seen == 0:
            return 1.0
        return self._total_passed / self._total_seen

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        field = self.operator_config.get("field", "")
        condition = self.operator_config.get("condition", "gt")
        value = self.operator_config.get("value")

        self._total_seen += 1

        event_value = event.data.get(field)
        if event_value is None:
            event.add_lineage(self.node_id, "filter", "filtered_drop", f"field '{field}' missing")
            return None

        passed = self._evaluate(event_value, condition, value)

        if passed:
            self._total_passed += 1
            event.add_lineage(
                self.node_id, "filter", "filtered_pass",
                f"{field} ({event_value}) {condition} {value}"
            )
            return [event]
        else:
            event.add_lineage(
                self.node_id, "filter", "filtered_drop",
                f"{field} ({event_value}) not {condition} {value}"
            )
            return None

    @staticmethod
    def _evaluate(event_value: Any, condition: str, target_value: Any) -> bool:
        try:
            ev = float(event_value)
            tv = float(target_value)
            if condition == "gt":
                return ev > tv
            elif condition == "lt":
                return ev < tv
            elif condition == "gte":
                return ev >= tv
            elif condition == "lte":
                return ev <= tv
            elif condition == "eq":
                return ev == tv
            elif condition == "neq":
                return ev != tv
        except (ValueError, TypeError):
            pass

        # String comparison fallback
        if condition == "eq":
            return str(event_value) == str(target_value)
        elif condition == "neq":
            return str(event_value) != str(target_value)
        elif condition == "contains":
            return str(target_value) in str(event_value)

        return False

    async def get_state(self) -> dict[str, Any]:
        return {
            "total_seen": self._total_seen,
            "total_passed": self._total_passed,
            "selectivity": self.selectivity,
        }

    async def restore_state(self, state: dict[str, Any]) -> None:
        self._total_seen = state.get("total_seen", 0)
        self._total_passed = state.get("total_passed", 0)


class MapOperator(BaseWorker):
    """
    Transforms events by applying an expression to a field.

    Config:
        expression: str - Python expression where 'x' is the input value
                         and 'data' is the full event.data dict
        output_field: str - field name to store the result (if None, replaces in-place)
        field: str - input field to use as 'x' in the expression
    """

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        expression = self.operator_config.get("expression", "x")
        output_field = self.operator_config.get("output_field")
        field = self.operator_config.get("field")

        x = event.data.get(field) if field else None
        data = event.data

        try:
            result = eval(expression, {"__builtins__": {}}, {"x": x, "data": data})
        except Exception as e:
            logger.error(f"Map expression error: {e}")
            event.add_lineage(self.node_id, "map", "error", str(e))
            return [event]  # Pass through unchanged on error

        if output_field:
            event.data[output_field] = result
        elif field:
            event.data[field] = result

        event.add_lineage(
            self.node_id, "map", "transformed",
            f"{field}={x} -> {output_field or field}={result}"
        )
        return [event]


class WindowOperator(BaseWorker):
    """
    Groups events into time-based windows.

    Config:
        window_type: "tumbling" | "sliding"
        window_size_seconds: int
        slide_interval_seconds: int (only for sliding windows)
        agg_field: str - field to aggregate within the window
        agg_function: "avg" | "sum" | "min" | "max" | "count"
        group_by: str | None - optional field to group by within the window

    Emits one aggregated event per window (per group) when the window closes.
    """

    def __init__(self):
        super().__init__()
        # group_key -> list of (timestamp, value)
        self._buffers: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
        self._last_emit: datetime = datetime.utcnow()

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        window_size = self.operator_config.get("window_size_seconds", 60)
        agg_field = self.operator_config.get("agg_field", "value")
        group_by = self.operator_config.get("group_by")

        # Determine group key
        group_key = str(event.data.get(group_by, "all")) if group_by else "all"

        # Extract value
        value = event.data.get(agg_field)
        if value is not None:
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None
            self._buffers[group_key].append((event.timestamp, value))

        # Check if window should close
        now = datetime.utcnow()
        if (now - self._last_emit).total_seconds() >= window_size:
            return await self._emit_windows(now, window_size, event)

        return None

    async def _emit_windows(
        self, now: datetime, window_size: int, trigger_event: StreamEvent
    ) -> list[StreamEvent]:
        """Close current windows and emit aggregated events."""
        agg_function = self.operator_config.get("agg_function", "avg")
        cutoff = now - timedelta(seconds=window_size)
        output_events: list[StreamEvent] = []

        for group_key, buffer in self._buffers.items():
            # Get values within the window
            window_values = [v for ts, v in buffer if ts >= cutoff]

            if not window_values:
                continue

            result = self._aggregate(window_values, agg_function)

            out_event = StreamEvent(
                source_node_id=self.node_id,
                data={
                    "window_start": cutoff.isoformat(),
                    "window_end": now.isoformat(),
                    "group": group_key,
                    "agg_function": agg_function,
                    "result": result,
                    "count": len(window_values),
                },
                lineage=trigger_event.lineage.copy(),
            )
            out_event.add_lineage(
                self.node_id, "window", "aggregated",
                f"{agg_function}({len(window_values)} events)={result}, group={group_key}"
            )
            output_events.append(out_event)

            # Trim old data from buffer
            self._buffers[group_key] = [(ts, v) for ts, v in buffer if ts >= cutoff]

        self._last_emit = now
        return output_events

    @staticmethod
    def _aggregate(values: list[float], function: str) -> float:
        if not values:
            return 0.0
        if function == "avg":
            return sum(values) / len(values)
        elif function == "sum":
            return sum(values)
        elif function == "min":
            return min(values)
        elif function == "max":
            return max(values)
        elif function == "count":
            return float(len(values))
        return 0.0

    async def get_state(self) -> dict[str, Any]:
        return {
            "buffers": {
                k: [(ts.isoformat(), v) for ts, v in buf]
                for k, buf in self._buffers.items()
            },
            "last_emit": self._last_emit.isoformat(),
        }

    async def restore_state(self, state: dict[str, Any]) -> None:
        self._last_emit = datetime.fromisoformat(state.get("last_emit", datetime.utcnow().isoformat()))
        buffers_raw = state.get("buffers", {})
        self._buffers = defaultdict(list)
        for k, entries in buffers_raw.items():
            self._buffers[k] = [
                (datetime.fromisoformat(ts), v) for ts, v in entries
            ]


class AggregateOperator(BaseWorker):
    """
    Running aggregate - emits updated aggregate with every event.

    Config:
        agg_function: "avg" | "sum" | "min" | "max" | "count"
        agg_field: str
        group_by: str | None
    """

    def __init__(self):
        super().__init__()
        # group -> {"sum": float, "count": int, "min": float, "max": float}
        self._accumulators: dict[str, dict[str, float]] = defaultdict(
            lambda: {"sum": 0.0, "count": 0, "min": float("inf"), "max": float("-inf")}
        )

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        agg_function = self.operator_config.get("agg_function", "avg")
        agg_field = self.operator_config.get("agg_field", "value")
        group_by = self.operator_config.get("group_by")

        group_key = str(event.data.get(group_by, "all")) if group_by else "all"
        value = event.data.get(agg_field)

        if value is None:
            return None

        try:
            value = float(value)
        except (ValueError, TypeError):
            return None

        acc = self._accumulators[group_key]
        acc["sum"] += value
        acc["count"] += 1
        acc["min"] = min(acc["min"], value)
        acc["max"] = max(acc["max"], value)

        if agg_function == "avg":
            result = acc["sum"] / acc["count"]
        elif agg_function == "sum":
            result = acc["sum"]
        elif agg_function == "min":
            result = acc["min"]
        elif agg_function == "max":
            result = acc["max"]
        elif agg_function == "count":
            result = acc["count"]
        else:
            result = 0.0

        out_event = StreamEvent(
            source_node_id=self.node_id,
            data={
                "group": group_key,
                "agg_function": agg_function,
                "result": result,
                "count": int(acc["count"]),
                **event.data,
            },
            lineage=event.lineage.copy(),
        )
        out_event.add_lineage(
            self.node_id, "aggregate", "aggregated",
            f"{agg_function}={result}, count={int(acc['count'])}, group={group_key}"
        )
        return [out_event]

    async def get_state(self) -> dict[str, Any]:
        return {"accumulators": dict(self._accumulators)}

    async def restore_state(self, state: dict[str, Any]) -> None:
        raw = state.get("accumulators", {})
        self._accumulators = defaultdict(
            lambda: {"sum": 0.0, "count": 0, "min": float("inf"), "max": float("-inf")}
        )
        for k, v in raw.items():
            self._accumulators[k] = v


class JoinOperator(BaseWorker):
    """
    Joins events from two streams within a time window.

    Config:
        join_key: str - the field to join on
        join_window_seconds: int - time window for matching events
        join_stream: str - the secondary stream to join with

    Events from the primary input stream are matched with events
    from the join_stream based on the join_key within the time window.
    """

    def __init__(self):
        super().__init__()
        # join_key_value -> list of (timestamp, event_data)
        self._left_buffer: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)
        self._right_buffer: dict[str, list[tuple[datetime, dict]]] = defaultdict(list)

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        join_key = self.operator_config.get("join_key", "id")
        join_window = self.operator_config.get("join_window_seconds", 30)
        join_stream = self.operator_config.get("join_stream", "")

        key_value = str(event.data.get(join_key, ""))
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=join_window)

        # Determine which side this event belongs to
        is_right = join_stream and event.source_node_id == join_stream

        if is_right:
            self._right_buffer[key_value].append((now, event.data))
            other_buffer = self._left_buffer
        else:
            self._left_buffer[key_value].append((now, event.data))
            other_buffer = self._right_buffer

        # Try to match
        output_events: list[StreamEvent] = []
        if key_value in other_buffer:
            matches = [(ts, d) for ts, d in other_buffer[key_value] if ts >= cutoff]
            for match_ts, match_data in matches:
                joined_data = {**match_data, **event.data, "_joined": True}
                out_event = StreamEvent(
                    source_node_id=self.node_id,
                    data=joined_data,
                    lineage=event.lineage.copy(),
                )
                out_event.add_lineage(
                    self.node_id, "join", "joined",
                    f"matched on {join_key}={key_value}"
                )
                output_events.append(out_event)

        # Cleanup expired entries
        self._cleanup_buffer(self._left_buffer, cutoff)
        self._cleanup_buffer(self._right_buffer, cutoff)

        return output_events if output_events else None

    @staticmethod
    def _cleanup_buffer(
        buffer: dict[str, list[tuple[datetime, dict]]], cutoff: datetime
    ) -> None:
        expired_keys = []
        for key in buffer:
            buffer[key] = [(ts, d) for ts, d in buffer[key] if ts >= cutoff]
            if not buffer[key]:
                expired_keys.append(key)
        for key in expired_keys:
            del buffer[key]

    async def get_state(self) -> dict[str, Any]:
        return {
            "left_buffer": {
                k: [(ts.isoformat(), d) for ts, d in v]
                for k, v in self._left_buffer.items()
            },
            "right_buffer": {
                k: [(ts.isoformat(), d) for ts, d in v]
                for k, v in self._right_buffer.items()
            },
        }


# Registry for looking up operator classes by type
OPERATOR_REGISTRY: dict[str, type[BaseWorker]] = {
    "filter": FilterOperator,
    "map": MapOperator,
    "window": WindowOperator,
    "aggregate": AggregateOperator,
    "join": JoinOperator,
}
