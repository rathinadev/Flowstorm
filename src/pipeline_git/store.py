"""Pipeline Git storage - Redis backend for version history.

Stores every version of every pipeline with full DAG snapshots,
enabling diffing, rollback, and audit trail.

Redis keys:
  flowstorm:versions:{pipeline_id}        - sorted set (score = version_number, member = version_number)
  flowstorm:version:{pipeline_id}:{ver}   - hash with version metadata + snapshot
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

from config.settings import settings

logger = logging.getLogger(__name__)


class PipelineVersionStore:
    """Redis-backed storage for pipeline version history."""

    def __init__(
        self,
        redis_host: str = settings.REDIS_HOST,
        redis_port: int = settings.REDIS_PORT,
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self._redis: redis.Redis | None = None

    async def initialize(self) -> None:
        """Connect to Redis."""
        self._redis = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("Pipeline version store initialized (Redis)")

    def _index_key(self, pipeline_id: str) -> str:
        return f"flowstorm:versions:{pipeline_id}"

    def _version_key(self, pipeline_id: str, version_number: int) -> str:
        return f"flowstorm:version:{pipeline_id}:{version_number}"

    async def save_version(
        self,
        pipeline_id: str,
        version_number: int,
        trigger: str,
        description: str,
        dag_snapshot: dict[str, Any],
        performance_snapshot: dict[str, Any] | None = None,
    ) -> int:
        """Save a new version. Returns the version number."""
        node_count = len(dag_snapshot.get("nodes", []))
        edge_count = len(dag_snapshot.get("edges", []))
        created_at = datetime.now(timezone.utc).isoformat()

        version_data = {
            "pipeline_id": pipeline_id,
            "version_number": version_number,
            "trigger": trigger,
            "description": description,
            "dag_snapshot": json.dumps(dag_snapshot),
            "node_count": node_count,
            "edge_count": edge_count,
            "performance_snapshot": json.dumps(performance_snapshot or {}),
            "created_at": created_at,
        }

        pipe = self._redis.pipeline()
        pipe.hset(self._version_key(pipeline_id, version_number), mapping=version_data)
        pipe.zadd(self._index_key(pipeline_id), {str(version_number): version_number})
        await pipe.execute()

        logger.info(
            f"Saved version {version_number} for pipeline {pipeline_id} [{trigger}]"
        )
        return version_number

    async def get_version(
        self, pipeline_id: str, version_number: int
    ) -> dict[str, Any] | None:
        """Get a specific version."""
        data = await self._redis.hgetall(
            self._version_key(pipeline_id, version_number)
        )
        if not data:
            return None
        return self._parse_version(data)

    async def get_latest_version(self, pipeline_id: str) -> dict[str, Any] | None:
        """Get the most recent version of a pipeline."""
        members = await self._redis.zrevrange(
            self._index_key(pipeline_id), 0, 0
        )
        if not members:
            return None
        return await self.get_version(pipeline_id, int(members[0]))

    async def get_history(
        self, pipeline_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for a pipeline (newest first)."""
        members = await self._redis.zrevrange(
            self._index_key(pipeline_id), 0, limit - 1
        )
        versions = []
        for m in members:
            v = await self.get_version(pipeline_id, int(m))
            if v:
                versions.append(v)
        return versions

    async def get_next_version_number(self, pipeline_id: str) -> int:
        """Get the next version number for a pipeline."""
        members = await self._redis.zrevrange(
            self._index_key(pipeline_id), 0, 0, withscores=True
        )
        if not members:
            return 1
        return int(members[0][1]) + 1

    @staticmethod
    def _parse_version(data: dict[str, str]) -> dict[str, Any]:
        return {
            "pipeline_id": data["pipeline_id"],
            "version_number": int(data["version_number"]),
            "trigger": data["trigger"],
            "description": data["description"],
            "dag_snapshot": json.loads(data["dag_snapshot"]),
            "node_count": int(data["node_count"]),
            "edge_count": int(data["edge_count"]),
            "performance_snapshot": json.loads(data["performance_snapshot"]),
            "created_at": data["created_at"],
        }
