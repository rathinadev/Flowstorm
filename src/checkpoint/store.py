"""Checkpoint Store - Redis-backed storage for operator state."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Low-level Redis operations for checkpoint data."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def save_operator_state(
        self, pipeline_id: str, node_id: str, state: dict[str, Any]
    ) -> None:
        """Save operator-specific state (window buffers, aggregation accumulators, etc.)."""
        key = f"flowstorm:state:{pipeline_id}:{node_id}"
        await self.redis.set(key, json.dumps(state, default=str))

    async def get_operator_state(
        self, pipeline_id: str, node_id: str
    ) -> dict[str, Any] | None:
        """Retrieve operator-specific state."""
        key = f"flowstorm:state:{pipeline_id}:{node_id}"
        raw = await self.redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def save_consumer_offset(
        self, pipeline_id: str, node_id: str, stream_key: str, offset: str
    ) -> None:
        """Save the last consumed message ID for a stream."""
        key = f"flowstorm:offset:{pipeline_id}:{node_id}:{stream_key}"
        await self.redis.set(key, offset)

    async def get_consumer_offset(
        self, pipeline_id: str, node_id: str, stream_key: str
    ) -> str | None:
        """Get the last consumed message ID."""
        key = f"flowstorm:offset:{pipeline_id}:{node_id}:{stream_key}"
        return await self.redis.get(key)

    async def get_pending_count(
        self, stream_key: str, consumer_group: str
    ) -> int:
        """Get number of pending (unacknowledged) messages in a consumer group."""
        try:
            info = await self.redis.xpending(stream_key, consumer_group)
            return info.get("pending", 0) if isinstance(info, dict) else 0
        except Exception:
            return 0

    async def get_stream_length(self, stream_key: str) -> int:
        """Get total number of messages in a stream."""
        try:
            return await self.redis.xlen(stream_key)
        except Exception:
            return 0

    async def get_consumer_lag(
        self, stream_key: str, consumer_group: str
    ) -> int:
        """Estimate consumer lag (unprocessed messages)."""
        try:
            info_list = await self.redis.xinfo_groups(stream_key)
            for info in info_list:
                name = info.get("name", "")
                if isinstance(name, bytes):
                    name = name.decode()
                if name == consumer_group:
                    return info.get("lag", 0)
        except Exception:
            pass
        return 0
