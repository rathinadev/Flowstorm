"""Smart Dead Letter Queue - diagnoses failed events and suggests fixes.

Reads from the DLQ Redis stream, classifies failures by type,
groups them, and generates fix suggestions.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class FailureType:
    SCHEMA_VIOLATION = "schema_violation"
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    NULL_VALUE = "null_value"
    OPERATOR_ERROR = "operator_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


FAILURE_SUGGESTIONS: dict[str, list[str]] = {
    FailureType.MISSING_FIELD: [
        "Add a default value for the missing field in the Map operator",
        "Add a Filter operator to drop events without required fields",
        "Check the source for schema changes",
    ],
    FailureType.TYPE_MISMATCH: [
        "Add a Map operator to cast the field to the expected type",
        "Update the Filter condition to handle mixed types",
        "Add input validation at the source",
    ],
    FailureType.NULL_VALUE: [
        "Add a Filter to remove events with null values",
        "Add a Map operator with a coalesce/default expression",
    ],
    FailureType.SCHEMA_VIOLATION: [
        "Update the operator config to match the new schema",
        "Add a schema validation Filter before the operator",
    ],
    FailureType.OPERATOR_ERROR: [
        "Check operator expression syntax",
        "Review the operator config for invalid parameters",
        "Restart the operator worker",
    ],
    FailureType.TIMEOUT: [
        "Increase the operator timeout setting",
        "Scale out the operator to reduce per-event processing time",
        "Check downstream dependencies for slowness",
    ],
    FailureType.UNKNOWN: [
        "Inspect the event data manually",
        "Check operator logs for more details",
    ],
}


class DLQEntry:
    """A single dead letter queue entry with diagnostic info."""

    def __init__(
        self,
        event_id: str,
        pipeline_id: str,
        node_id: str,
        error_message: str,
        event_data: dict[str, Any],
        timestamp: str,
    ):
        self.event_id = event_id
        self.pipeline_id = pipeline_id
        self.node_id = node_id
        self.error_message = error_message
        self.event_data = event_data
        self.timestamp = timestamp
        self.failure_type = self._classify()
        self.suggestions = FAILURE_SUGGESTIONS.get(
            self.failure_type, FAILURE_SUGGESTIONS[FailureType.UNKNOWN]
        )

    def _classify(self) -> str:
        """Classify the failure type based on the error message."""
        msg = self.error_message.lower()

        if "keyerror" in msg or "missing" in msg or "not found" in msg:
            return FailureType.MISSING_FIELD
        if "typeerror" in msg or "type" in msg and ("cast" in msg or "convert" in msg):
            return FailureType.TYPE_MISMATCH
        if "none" in msg or "null" in msg or "nonetype" in msg:
            return FailureType.NULL_VALUE
        if "schema" in msg or "validation" in msg:
            return FailureType.SCHEMA_VIOLATION
        if "timeout" in msg or "timed out" in msg:
            return FailureType.TIMEOUT
        if "error" in msg or "exception" in msg or "failed" in msg:
            return FailureType.OPERATOR_ERROR

        return FailureType.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "pipeline_id": self.pipeline_id,
            "node_id": self.node_id,
            "error_message": self.error_message,
            "failure_type": self.failure_type,
            "suggestions": self.suggestions,
            "event_data": self.event_data,
            "timestamp": self.timestamp,
        }


class DLQDiagnostics:
    """Reads and analyzes the dead letter queue."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def get_entries(
        self, pipeline_id: str, count: int = 100
    ) -> list[DLQEntry]:
        """Fetch recent DLQ entries for a pipeline."""
        dlq_key = f"flowstorm:{pipeline_id}:dlq"
        entries: list[DLQEntry] = []

        try:
            messages = await self.redis.xrevrange(dlq_key, count=count)
            for msg_id, fields in messages:
                entries.append(DLQEntry(
                    event_id=msg_id if isinstance(msg_id, str) else msg_id.decode(),
                    pipeline_id=pipeline_id,
                    node_id=fields.get("node_id", "unknown"),
                    error_message=fields.get("error", "Unknown error"),
                    event_data=json.loads(fields.get("data", "{}")),
                    timestamp=fields.get("timestamp", datetime.utcnow().isoformat()),
                ))
        except Exception as e:
            logger.error(f"Failed to read DLQ for {pipeline_id}: {e}")

        return entries

    async def get_stats(self, pipeline_id: str) -> dict[str, Any]:
        """Get aggregated DLQ statistics grouped by failure type and node."""
        entries = await self.get_entries(pipeline_id, count=500)

        by_type: dict[str, int] = defaultdict(int)
        by_node: dict[str, int] = defaultdict(int)
        by_type_node: dict[str, list[str]] = defaultdict(list)

        for entry in entries:
            by_type[entry.failure_type] += 1
            by_node[entry.node_id] += 1
            key = entry.failure_type
            if entry.node_id not in by_type_node[key]:
                by_type_node[key].append(entry.node_id)

        # Build grouped results with suggestions
        groups = []
        for failure_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
            groups.append({
                "failure_type": failure_type,
                "count": count,
                "affected_nodes": by_type_node[failure_type],
                "suggestions": FAILURE_SUGGESTIONS.get(
                    failure_type, FAILURE_SUGGESTIONS[FailureType.UNKNOWN]
                ),
            })

        return {
            "pipeline_id": pipeline_id,
            "total_failed": len(entries),
            "groups": groups,
            "by_node": dict(by_node),
        }
