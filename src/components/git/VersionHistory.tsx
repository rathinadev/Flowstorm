import { useState, useEffect } from "react";
import { usePipelineStore } from "../../store/pipelineStore";
import { api } from "../../services/api";
import type { PipelineVersion, PipelineDiff } from "../../types/pipeline";
import { VisualDiff } from "./VisualDiff";

const TRIGGER_COLORS: Record<string, string> = {
  USER: "#3b82f6",
  AUTO_OPTIMIZE: "#8b5cf6",
  AUTO_HEAL: "#22c55e",
  NLP_COMMAND: "#f59e0b",
  ROLLBACK: "#ef4444",
};

const TRIGGER_LABELS: Record<string, string> = {
  USER: "Manual",
  AUTO_OPTIMIZE: "Auto-Optimize",
  AUTO_HEAL: "Auto-Heal",
  NLP_COMMAND: "NLP",
  ROLLBACK: "Rollback",
};

interface VersionHistoryProps {
  pipelineId: string | null;
}

export function VersionHistory({ pipelineId }: VersionHistoryProps) {
  const versions = usePipelineStore((s) => s.versions);
  const setVersions = usePipelineStore((s) => s.setVersions);
  const [loading, setLoading] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDiff, setSelectedDiff] = useState<PipelineDiff | null>(null);
  const [compareFrom, setCompareFrom] = useState<number | null>(null);
  const [compareTo, setCompareTo] = useState<number | null>(null);
  const [rollbackTarget, setRollbackTarget] = useState<number | null>(null);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  useEffect(() => {
    if (pipelineId) loadVersions();
  }, [pipelineId]);

  const loadVersions = async () => {
    if (!pipelineId) return;
    setLoading(true);
    try {
      const data = await api.getVersions(pipelineId);
      setVersions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load versions");
    } finally {
      setLoading(false);
    }
  };

  const handleDiff = async (from: number, to: number) => {
    if (!pipelineId) return;
    setDiffLoading(true);
    setSelectedDiff(null);
    try {
      const diff = (await api.diffVersions(
        pipelineId,
        from,
        to
      )) as PipelineDiff;
      setSelectedDiff(diff);
      setCompareFrom(from);
      setCompareTo(to);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to compute diff");
    } finally {
      setDiffLoading(false);
    }
  };

  const handleRollback = async (versionId: number) => {
    if (!pipelineId) return;
    setRollbackLoading(true);
    try {
      await api.rollback(pipelineId, versionId);
      setRollbackTarget(null);
      await loadVersions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rollback failed");
    } finally {
      setRollbackLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">&#128218;</span>
            <h2 className="text-sm font-bold text-flowstorm-text">
              Pipeline Git
            </h2>
          </div>
          <button
            onClick={loadVersions}
            disabled={loading || !pipelineId}
            className="text-xs text-flowstorm-muted hover:text-flowstorm-primary transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
        <p className="text-[10px] text-flowstorm-muted mt-0.5">
          Version history with visual diffs and rollback
        </p>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {/* Version list */}
        <div className="w-72 border-r border-flowstorm-border overflow-y-auto p-3 space-y-1.5">
          {!pipelineId && (
            <p className="text-xs text-flowstorm-muted text-center py-4">
              Deploy a pipeline to see version history
            </p>
          )}

          {loading && (
            <p className="text-xs text-flowstorm-muted text-center py-4">
              Loading versions...
            </p>
          )}

          {versions.length === 0 && !loading && pipelineId && (
            <p className="text-xs text-flowstorm-muted text-center py-4">
              No versions yet
            </p>
          )}

          <div className="relative">
            {/* Timeline line */}
            {versions.length > 1 && (
              <div className="absolute left-[11px] top-6 bottom-6 w-0.5 bg-flowstorm-border" />
            )}

            {versions.map((v, i) => {
              const color =
                TRIGGER_COLORS[v.trigger] || "#6b7280";
              const label =
                TRIGGER_LABELS[v.trigger] || v.trigger;
              return (
                <div
                  key={v.version_id}
                  className="flex gap-3 relative mb-3"
                >
                  {/* Version dot */}
                  <div className="flex-shrink-0 z-10">
                    <div
                      className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
                      style={{ backgroundColor: color }}
                    >
                      v{v.version_id}
                    </div>
                  </div>

                  {/* Version card */}
                  <div className="flex-1 bg-flowstorm-bg rounded-md px-3 py-2 border border-flowstorm-border hover:border-flowstorm-primary/50 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: color + "20",
                          color,
                        }}
                      >
                        {label}
                      </span>
                      <span className="text-[10px] text-flowstorm-muted">
                        {new Date(v.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs text-flowstorm-text truncate">
                      {v.description}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-flowstorm-muted">
                      <span>{v.node_count} nodes</span>
                      <span>{v.edge_count} edges</span>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-1.5 mt-2">
                      {i > 0 && (
                        <button
                          onClick={() =>
                            handleDiff(
                              versions[i - 1]?.version_id,
                              v.version_id
                            )
                          }
                          disabled={diffLoading}
                          className="text-[10px] px-2 py-0.5 rounded bg-flowstorm-surface border border-flowstorm-border
                            text-flowstorm-muted hover:text-flowstorm-primary hover:border-flowstorm-primary/50 transition-colors"
                        >
                          Diff
                        </button>
                      )}
                      {i > 0 && (
                        <button
                          onClick={() =>
                            setRollbackTarget(v.version_id)
                          }
                          className="text-[10px] px-2 py-0.5 rounded bg-flowstorm-surface border border-flowstorm-border
                            text-flowstorm-muted hover:text-red-400 hover:border-red-400/50 transition-colors"
                        >
                          Rollback
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Diff panel */}
        <div className="flex-1 overflow-y-auto p-4">
          {!selectedDiff && !diffLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-3xl text-flowstorm-muted mb-2">
                  &#128203;
                </div>
                <p className="text-xs text-flowstorm-muted">
                  Select a version and click "Diff" to compare changes
                </p>
              </div>
            </div>
          )}

          {diffLoading && (
            <div className="flex items-center justify-center h-full">
              <p className="text-xs text-flowstorm-muted">
                Computing diff...
              </p>
            </div>
          )}

          {selectedDiff && (
            <VisualDiff
              diff={selectedDiff}
              versionFrom={compareFrom!}
              versionTo={compareTo!}
            />
          )}
        </div>
      </div>

      {/* Rollback confirmation modal */}
      {rollbackTarget !== null && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-sm font-bold text-flowstorm-text mb-2">
              Confirm Rollback
            </h3>
            <p className="text-xs text-flowstorm-muted mb-4">
              This will rollback the pipeline to version{" "}
              <span className="font-bold text-flowstorm-text">
                v{rollbackTarget}
              </span>
              . The current state will be saved as a new version before
              rolling back.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setRollbackTarget(null)}
                className="px-3 py-1.5 rounded-md border border-flowstorm-border text-xs text-flowstorm-muted
                  hover:border-flowstorm-primary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleRollback(rollbackTarget)}
                disabled={rollbackLoading}
                className="px-3 py-1.5 rounded-md bg-red-600 hover:bg-red-700 text-white text-xs font-bold
                  transition-colors disabled:opacity-50"
              >
                {rollbackLoading ? "Rolling back..." : "Rollback"}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/30">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}
