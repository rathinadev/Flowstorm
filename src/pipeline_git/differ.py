"""Pipeline Differ - generates visual diffs between two pipeline versions.

Compares two DAG snapshots and produces a structured diff showing:
- Nodes added, removed, moved, modified
- Edges added, removed
- Config changes per node
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeDiff:
    """Diff for a single node."""
    node_id: str
    label: str
    change_type: str  # "added", "removed", "modified", "moved", "unchanged"
    old_config: dict[str, Any] | None = None
    new_config: dict[str, Any] | None = None
    config_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    position_changed: bool = False


@dataclass
class EdgeDiff:
    """Diff for a single edge."""
    edge_id: str
    source_id: str
    target_id: str
    change_type: str  # "added", "removed"


@dataclass
class PipelineDiff:
    """Complete diff between two pipeline versions."""
    version_from: int
    version_to: int
    node_diffs: list[NodeDiff]
    edge_diffs: list[EdgeDiff]
    summary: str

    @property
    def nodes_added(self) -> int:
        return sum(1 for d in self.node_diffs if d.change_type == "added")

    @property
    def nodes_removed(self) -> int:
        return sum(1 for d in self.node_diffs if d.change_type == "removed")

    @property
    def nodes_modified(self) -> int:
        return sum(1 for d in self.node_diffs if d.change_type == "modified")

    @property
    def edges_added(self) -> int:
        return sum(1 for d in self.edge_diffs if d.change_type == "added")

    @property
    def edges_removed(self) -> int:
        return sum(1 for d in self.edge_diffs if d.change_type == "removed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_from": self.version_from,
            "version_to": self.version_to,
            "summary": self.summary,
            "stats": {
                "nodes_added": self.nodes_added,
                "nodes_removed": self.nodes_removed,
                "nodes_modified": self.nodes_modified,
                "edges_added": self.edges_added,
                "edges_removed": self.edges_removed,
            },
            "node_diffs": [
                {
                    "node_id": d.node_id,
                    "label": d.label,
                    "change_type": d.change_type,
                    "config_changes": {
                        k: {"old": old, "new": new}
                        for k, (old, new) in d.config_changes.items()
                    },
                    "position_changed": d.position_changed,
                }
                for d in self.node_diffs
                if d.change_type != "unchanged"
            ],
            "edge_diffs": [
                {
                    "edge_id": d.edge_id,
                    "source_id": d.source_id,
                    "target_id": d.target_id,
                    "change_type": d.change_type,
                }
                for d in self.edge_diffs
            ],
        }


class PipelineDiffer:
    """Generates diffs between two DAG snapshots."""

    def diff(
        self,
        old_snapshot: dict[str, Any],
        new_snapshot: dict[str, Any],
        version_from: int = 0,
        version_to: int = 0,
    ) -> PipelineDiff:
        """Compare two snapshots and produce a diff."""
        old_nodes = {n["id"]: n for n in old_snapshot.get("nodes", [])}
        new_nodes = {n["id"]: n for n in new_snapshot.get("nodes", [])}
        old_edges = {self._edge_key(e): e for e in old_snapshot.get("edges", [])}
        new_edges = {self._edge_key(e): e for e in new_snapshot.get("edges", [])}

        node_diffs: list[NodeDiff] = []

        # Nodes added
        for nid in new_nodes:
            if nid not in old_nodes:
                node_diffs.append(NodeDiff(
                    node_id=nid,
                    label=new_nodes[nid].get("label", ""),
                    change_type="added",
                    new_config=new_nodes[nid].get("config", {}),
                ))

        # Nodes removed
        for nid in old_nodes:
            if nid not in new_nodes:
                node_diffs.append(NodeDiff(
                    node_id=nid,
                    label=old_nodes[nid].get("label", ""),
                    change_type="removed",
                    old_config=old_nodes[nid].get("config", {}),
                ))

        # Nodes that exist in both - check for modifications
        for nid in old_nodes:
            if nid in new_nodes:
                old = old_nodes[nid]
                new = new_nodes[nid]

                config_changes = self._diff_configs(
                    old.get("config", {}),
                    new.get("config", {}),
                )

                position_changed = (
                    old.get("position_x") != new.get("position_x")
                    or old.get("position_y") != new.get("position_y")
                )

                if config_changes or position_changed:
                    change_type = "modified" if config_changes else "moved"
                else:
                    change_type = "unchanged"

                node_diffs.append(NodeDiff(
                    node_id=nid,
                    label=new.get("label", old.get("label", "")),
                    change_type=change_type,
                    old_config=old.get("config", {}),
                    new_config=new.get("config", {}),
                    config_changes=config_changes,
                    position_changed=position_changed,
                ))

        # Edge diffs
        edge_diffs: list[EdgeDiff] = []

        for ekey in new_edges:
            if ekey not in old_edges:
                e = new_edges[ekey]
                edge_diffs.append(EdgeDiff(
                    edge_id=e.get("id", ekey),
                    source_id=e["source_node_id"],
                    target_id=e["target_node_id"],
                    change_type="added",
                ))

        for ekey in old_edges:
            if ekey not in new_edges:
                e = old_edges[ekey]
                edge_diffs.append(EdgeDiff(
                    edge_id=e.get("id", ekey),
                    source_id=e["source_node_id"],
                    target_id=e["target_node_id"],
                    change_type="removed",
                ))

        # Generate summary
        parts = []
        added = sum(1 for d in node_diffs if d.change_type == "added")
        removed = sum(1 for d in node_diffs if d.change_type == "removed")
        modified = sum(1 for d in node_diffs if d.change_type == "modified")
        if added:
            parts.append(f"{added} node(s) added")
        if removed:
            parts.append(f"{removed} node(s) removed")
        if modified:
            parts.append(f"{modified} node(s) modified")
        e_added = sum(1 for d in edge_diffs if d.change_type == "added")
        e_removed = sum(1 for d in edge_diffs if d.change_type == "removed")
        if e_added:
            parts.append(f"{e_added} edge(s) added")
        if e_removed:
            parts.append(f"{e_removed} edge(s) removed")

        summary = ", ".join(parts) if parts else "No changes"

        return PipelineDiff(
            version_from=version_from,
            version_to=version_to,
            node_diffs=node_diffs,
            edge_diffs=edge_diffs,
            summary=summary,
        )

    @staticmethod
    def _edge_key(edge: dict) -> str:
        return f"{edge['source_node_id']}->{edge['target_node_id']}"

    @staticmethod
    def _diff_configs(old: dict, new: dict) -> dict[str, tuple[Any, Any]]:
        """Find differences between two config dicts."""
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes[key] = (old_val, new_val)
        return changes
