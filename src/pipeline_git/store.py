"""Pipeline Git storage - SQLite backend for version history.

Stores every version of every pipeline with full DAG snapshots,
enabling diffing, rollback, and audit trail.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import aiosqlite

from config.settings import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.SQLITE_DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    trigger TEXT NOT NULL,
    description TEXT NOT NULL,
    dag_snapshot TEXT NOT NULL,
    node_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    performance_snapshot TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(pipeline_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_versions_pipeline_id
ON pipeline_versions(pipeline_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_versions_created_at
ON pipeline_versions(created_at);
"""


class PipelineVersionStore:
    """SQLite-backed storage for pipeline version history."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLE_SQL)
            await db.commit()
        self._initialized = True
        logger.info(f"Pipeline version store initialized at {self.db_path}")

    async def save_version(
        self,
        pipeline_id: str,
        version_number: int,
        trigger: str,
        description: str,
        dag_snapshot: dict[str, Any],
        performance_snapshot: dict[str, Any] | None = None,
    ) -> int:
        """Save a new version. Returns the version ID."""
        node_count = len(dag_snapshot.get("nodes", []))
        edge_count = len(dag_snapshot.get("edges", []))

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO pipeline_versions
                   (pipeline_id, version_number, trigger, description,
                    dag_snapshot, node_count, edge_count,
                    performance_snapshot, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pipeline_id,
                    version_number,
                    trigger,
                    description,
                    json.dumps(dag_snapshot),
                    node_count,
                    edge_count,
                    json.dumps(performance_snapshot or {}),
                    datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_version(
        self, pipeline_id: str, version_number: int
    ) -> dict[str, Any] | None:
        """Get a specific version."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM pipeline_versions
                   WHERE pipeline_id = ? AND version_number = ?""",
                (pipeline_id, version_number),
            )
            row = await cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    async def get_latest_version(self, pipeline_id: str) -> dict[str, Any] | None:
        """Get the most recent version of a pipeline."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM pipeline_versions
                   WHERE pipeline_id = ?
                   ORDER BY version_number DESC LIMIT 1""",
                (pipeline_id,),
            )
            row = await cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    async def get_history(
        self, pipeline_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for a pipeline (newest first)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM pipeline_versions
                   WHERE pipeline_id = ?
                   ORDER BY version_number DESC
                   LIMIT ?""",
                (pipeline_id, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    async def get_next_version_number(self, pipeline_id: str) -> int:
        """Get the next version number for a pipeline."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT MAX(version_number) FROM pipeline_versions
                   WHERE pipeline_id = ?""",
                (pipeline_id,),
            )
            row = await cursor.fetchone()
            current = row[0] if row and row[0] is not None else 0
            return current + 1

    @staticmethod
    def _row_to_dict(row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "pipeline_id": row["pipeline_id"],
            "version_number": row["version_number"],
            "trigger": row["trigger"],
            "description": row["description"],
            "dag_snapshot": json.loads(row["dag_snapshot"]),
            "node_count": row["node_count"],
            "edge_count": row["edge_count"],
            "performance_snapshot": json.loads(row["performance_snapshot"]),
            "created_at": row["created_at"],
        }
