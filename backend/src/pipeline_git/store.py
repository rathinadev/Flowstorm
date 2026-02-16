"""Pipeline Git storage - PostgreSQL backend with in-memory fallback.

Stores every version of every pipeline with full DAG snapshots,
enabling diffing, rollback, and audit trail.

Falls back to in-memory storage if PostgreSQL is unavailable, so the
application can run for demos and development without a database.

Tables:
  pipeline_versions - immutable version records with JSON snapshots
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


class PipelineVersionStore:
    """PostgreSQL-backed storage for pipeline version history.

    Falls back to in-memory storage when PostgreSQL is unavailable.
    """

    def __init__(self, dsn: str = settings.POSTGRES_DSN):
        self.dsn = dsn
        self._pool = None  # asyncpg.Pool or None
        self._use_memory = False
        # In-memory fallback
        self._memory_store: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Connect to Postgres and create tables if needed.

        Falls back to in-memory storage on connection failure.
        """
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)

            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_versions (
                        id SERIAL PRIMARY KEY,
                        pipeline_id TEXT NOT NULL,
                        version_number INTEGER NOT NULL,
                        trigger TEXT NOT NULL,
                        description TEXT NOT NULL,
                        dag_snapshot JSONB NOT NULL,
                        node_count INTEGER NOT NULL,
                        edge_count INTEGER NOT NULL,
                        performance_snapshot JSONB DEFAULT '{}',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(pipeline_id, version_number)
                    );

                    CREATE INDEX IF NOT EXISTS idx_pv_pipeline_id
                        ON pipeline_versions(pipeline_id);

                    CREATE INDEX IF NOT EXISTS idx_pv_created_at
                        ON pipeline_versions(created_at);
                """)

            logger.info("Pipeline version store initialized (PostgreSQL)")

        except Exception as e:
            logger.warning(
                f"PostgreSQL unavailable ({e}), using in-memory version store. "
                f"Pipeline versions will not persist across restarts."
            )
            self._pool = None
            self._use_memory = True

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

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

        if self._use_memory:
            self._memory_store.append({
                "id": len(self._memory_store) + 1,
                "pipeline_id": pipeline_id,
                "version_number": version_number,
                "trigger": trigger,
                "description": description,
                "dag_snapshot": dag_snapshot,
                "node_count": node_count,
                "edge_count": edge_count,
                "performance_snapshot": performance_snapshot or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(
                f"Saved version {version_number} for pipeline {pipeline_id} "
                f"[{trigger}] (in-memory)"
            )
            return version_number

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO pipeline_versions
                    (pipeline_id, version_number, trigger, description,
                     dag_snapshot, node_count, edge_count, performance_snapshot)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                pipeline_id,
                version_number,
                trigger,
                description,
                json.dumps(dag_snapshot),
                node_count,
                edge_count,
                json.dumps(performance_snapshot or {}),
            )

        logger.info(
            f"Saved version {version_number} for pipeline {pipeline_id} [{trigger}]"
        )
        return version_number

    async def get_version(
        self, pipeline_id: str, version_number: int
    ) -> dict[str, Any] | None:
        """Get a specific version."""
        if self._use_memory:
            for v in self._memory_store:
                if v["pipeline_id"] == pipeline_id and v["version_number"] == version_number:
                    return v
            return None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM pipeline_versions
                WHERE pipeline_id = $1 AND version_number = $2
                """,
                pipeline_id,
                version_number,
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def get_latest_version(self, pipeline_id: str) -> dict[str, Any] | None:
        """Get the most recent version of a pipeline."""
        if self._use_memory:
            versions = [
                v for v in self._memory_store if v["pipeline_id"] == pipeline_id
            ]
            if not versions:
                return None
            return max(versions, key=lambda v: v["version_number"])

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM pipeline_versions
                WHERE pipeline_id = $1
                ORDER BY version_number DESC LIMIT 1
                """,
                pipeline_id,
            )
        if not row:
            return None
        return self._row_to_dict(row)

    async def get_history(
        self, pipeline_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for a pipeline (newest first)."""
        if self._use_memory:
            versions = [
                v for v in self._memory_store if v["pipeline_id"] == pipeline_id
            ]
            versions.sort(key=lambda v: v["version_number"], reverse=True)
            return versions[:limit]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM pipeline_versions
                WHERE pipeline_id = $1
                ORDER BY version_number DESC
                LIMIT $2
                """,
                pipeline_id,
                limit,
            )
        return [self._row_to_dict(row) for row in rows]

    async def get_next_version_number(self, pipeline_id: str) -> int:
        """Get the next version number for a pipeline."""
        if self._use_memory:
            versions = [
                v["version_number"]
                for v in self._memory_store
                if v["pipeline_id"] == pipeline_id
            ]
            return (max(versions) if versions else 0) + 1

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT MAX(version_number) FROM pipeline_versions
                WHERE pipeline_id = $1
                """,
                pipeline_id,
            )
        return (result or 0) + 1

    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        dag = row["dag_snapshot"]
        perf = row["performance_snapshot"]
        return {
            "id": row["id"],
            "pipeline_id": row["pipeline_id"],
            "version_number": row["version_number"],
            "trigger": row["trigger"],
            "description": row["description"],
            "dag_snapshot": json.loads(dag) if isinstance(dag, str) else dag,
            "node_count": row["node_count"],
            "edge_count": row["edge_count"],
            "performance_snapshot": json.loads(perf) if isinstance(perf, str) else perf,
            "created_at": row["created_at"] if isinstance(row["created_at"], str) else row["created_at"].isoformat(),
        }
