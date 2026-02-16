import { useState, useEffect } from "react";
import { api } from "../../services/api";

interface DLQStats {
  total_failed: number;
  groups: Array<{
    failure_type: string;
    count: number;
    affected_nodes: string[];
    suggestions: string[];
  }>;
  by_node: Record<string, number>;
}

interface DLQEntry {
  event_id: string;
  node_id: string;
  error_message: string;
  failure_type: string;
  suggestions: string[];
  timestamp: string;
}

const FAILURE_COLORS: Record<string, string> = {
  missing_field: "text-orange-400 bg-orange-500/10",
  type_mismatch: "text-yellow-400 bg-yellow-500/10",
  null_value: "text-blue-400 bg-blue-500/10",
  schema_violation: "text-red-400 bg-red-500/10",
  operator_error: "text-red-400 bg-red-500/10",
  timeout: "text-purple-400 bg-purple-500/10",
  unknown: "text-gray-400 bg-gray-500/10",
};

interface DLQPanelProps {
  pipelineId: string | null;
}

export function DLQPanel({ pipelineId }: DLQPanelProps) {
  const [stats, setStats] = useState<DLQStats | null>(null);
  const [entries, setEntries] = useState<DLQEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  useEffect(() => {
    if (!pipelineId) return;
    loadData();
  }, [pipelineId]);

  const loadData = async () => {
    if (!pipelineId) return;
    setLoading(true);
    try {
      const [statsRes, dlqRes] = await Promise.all([
        api.getDLQStats(pipelineId),
        api.getDLQ(pipelineId, 50),
      ]);
      setStats(statsRes);
      setEntries(dlqRes.entries);
    } catch {
      // Pipeline may not have DLQ data yet
    } finally {
      setLoading(false);
    }
  };

  const filteredEntries = selectedGroup
    ? entries.filter((e) => e.failure_type === selectedGroup)
    : entries;

  return (
    <div className="flex flex-col h-full">
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-flowstorm-text">
              Dead Letter Queue
            </h2>
            <p className="text-[10px] text-flowstorm-muted mt-0.5">
              Failed events with root cause analysis and fix suggestions
            </p>
          </div>
          {pipelineId && (
            <button
              onClick={loadData}
              disabled={loading}
              className="px-3 py-1.5 rounded text-xs bg-flowstorm-bg border border-flowstorm-border text-flowstorm-muted hover:text-flowstorm-text transition-colors"
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!pipelineId ? (
          <div className="bg-flowstorm-bg rounded-lg p-4 text-center">
            <p className="text-xs text-flowstorm-muted">
              Deploy a pipeline first to view DLQ
            </p>
          </div>
        ) : (
          <>
            {/* Summary stats */}
            {stats && (
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-3">
                  <div className="text-[10px] text-flowstorm-muted uppercase tracking-wider">
                    Total Failed
                  </div>
                  <div className="text-lg font-bold text-red-400 mt-1">
                    {stats.total_failed}
                  </div>
                </div>
                <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-3">
                  <div className="text-[10px] text-flowstorm-muted uppercase tracking-wider">
                    Failure Types
                  </div>
                  <div className="text-lg font-bold text-flowstorm-text mt-1">
                    {stats.groups.length}
                  </div>
                </div>
                <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-3">
                  <div className="text-[10px] text-flowstorm-muted uppercase tracking-wider">
                    Affected Nodes
                  </div>
                  <div className="text-lg font-bold text-flowstorm-text mt-1">
                    {Object.keys(stats.by_node).length}
                  </div>
                </div>
              </div>
            )}

            {/* Failure groups with suggestions */}
            {stats && stats.groups.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider">
                  Failure Groups
                </h3>
                {stats.groups.map((group) => (
                  <button
                    key={group.failure_type}
                    onClick={() =>
                      setSelectedGroup(
                        selectedGroup === group.failure_type
                          ? null
                          : group.failure_type
                      )
                    }
                    className={`w-full text-left bg-flowstorm-surface border rounded-lg p-3 transition-colors ${
                      selectedGroup === group.failure_type
                        ? "border-flowstorm-primary"
                        : "border-flowstorm-border hover:border-flowstorm-muted"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded ${
                          FAILURE_COLORS[group.failure_type] || FAILURE_COLORS.unknown
                        }`}
                      >
                        {group.failure_type.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs font-mono text-flowstorm-muted">
                        {group.count} events
                      </span>
                    </div>

                    <div className="text-[10px] text-flowstorm-muted mb-2">
                      Nodes: {group.affected_nodes.join(", ")}
                    </div>

                    <div className="space-y-1">
                      {group.suggestions.map((s, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-1.5 text-[10px] text-flowstorm-text"
                        >
                          <span className="text-flowstorm-primary mt-0.5">
                            -
                          </span>
                          {s}
                        </div>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Individual entries */}
            {filteredEntries.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider">
                  {selectedGroup
                    ? `${selectedGroup.replace(/_/g, " ")} events`
                    : "Recent Failed Events"}
                </h3>
                {filteredEntries.slice(0, 20).map((entry) => (
                  <div
                    key={entry.event_id}
                    className="bg-flowstorm-bg border border-flowstorm-border rounded p-2"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono text-flowstorm-muted">
                        {entry.event_id}
                      </span>
                      <span className="text-[10px] text-flowstorm-muted">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-xs text-red-400 mb-1">
                      {entry.error_message}
                    </div>
                    <div className="text-[10px] text-flowstorm-muted">
                      Node: {entry.node_id}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {stats && stats.total_failed === 0 && (
              <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-6 text-center">
                <div className="text-2xl mb-2">0</div>
                <p className="text-xs text-flowstorm-muted">
                  No failed events in the dead letter queue
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
