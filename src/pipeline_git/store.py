"""Pipeline Git storage - PostgreSQL backend for version history.

Stores every version of every pipeline with full DAG snapshots,
enabling diffing, rollback, and audit trail.

Tables:
  pipeline_versions - immutable version records with JSON snapshots
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg

from config.settings import settings

logger = logging.getLogger(__name__)


class PipelineVersionStore:
    """PostgreSQL-backed storage for pipeline version history."""

    def __init__(self, dsn: str = settings.POSTGRES_DSN):
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        """Connect to Postgres and create tables if needed."""
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
    def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
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
            "created_at": row["created_at"].isoformat(),
        }
