"""Checkpoint Manager - coordinates state checkpointing across workers.

Ensures consistent snapshots of operator state for recovery.
When a worker dies, the new worker restores from the latest checkpoint
and replays events from that point.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from src.models.events import Checkpoint

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoints for all workers in a pipeline."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a worker's checkpoint to Redis."""
        key = self._checkpoint_key(checkpoint.pipeline_id, checkpoint.node_id)
        await self.redis.set(key, checkpoint.model_dump_json())

        # Also keep a history (last 10 checkpoints per node)
        history_key = f"{key}:history"
        await self.redis.lpush(history_key, checkpoint.model_dump_json())
        await self.redis.ltrim(history_key, 0, 9)

    async def get_latest_checkpoint(
        self, pipeline_id: str, node_id: str
    ) -> Checkpoint | None:
        """Get the most recent checkpoint for a node."""
        key = self._checkpoint_key(pipeline_id, node_id)
        raw = await self.redis.get(key)
        if raw:
            return Checkpoint(**json.loads(raw))
        return None

    async def get_checkpoint_history(
        self, pipeline_id: str, node_id: str, count: int = 10
    ) -> list[Checkpoint]:
        """Get recent checkpoints for a node."""
        key = f"{self._checkpoint_key(pipeline_id, node_id)}:history"
        raw_list = await self.redis.lrange(key, 0, count - 1)
        return [Checkpoint(**json.loads(raw)) for raw in raw_list]

    async def get_all_checkpoints(self, pipeline_id: str) -> dict[str, Checkpoint]:
        """Get latest checkpoint for all nodes in a pipeline."""
        pattern = f"flowstorm:checkpoint:{pipeline_id}:*"
        checkpoints = {}

        # Scan for matching keys (avoid history keys)
        async for key in self.redis.scan_iter(match=pattern):
            key_str = key if isinstance(key, str) else key.decode()
            if ":history" in key_str:
                continue
            raw = await self.redis.get(key_str)
            if raw:
                ckp = Checkpoint(**json.loads(raw))
                checkpoints[ckp.node_id] = ckp

        return checkpoints

    async def delete_checkpoints(self, pipeline_id: str) -> int:
        """Delete all checkpoints for a pipeline."""
        pattern = f"flowstorm:checkpoint:{pipeline_id}:*"
        deleted = 0
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
            deleted += 1
        return deleted

    async def get_replay_position(
        self, pipeline_id: str, node_id: str
    ) -> str | None:
        """Get the stream position to replay from for a node."""
        checkpoint = await self.get_latest_checkpoint(pipeline_id, node_id)
        if checkpoint:
            return checkpoint.last_processed_id
        return None

    @staticmethod
    def _checkpoint_key(pipeline_id: str, node_id: str) -> str:
        return f"flowstorm:checkpoint:{pipeline_id}:{node_id}"
