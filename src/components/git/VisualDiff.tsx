import type { PipelineDiff } from "../../types/pipeline";

const CHANGE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  added: { bg: "bg-green-500/10", text: "text-green-400", label: "Added" },
  removed: { bg: "bg-red-500/10", text: "text-red-400", label: "Removed" },
  modified: { bg: "bg-yellow-500/10", text: "text-yellow-400", label: "Modified" },
  moved: { bg: "bg-blue-500/10", text: "text-blue-400", label: "Moved" },
  unchanged: { bg: "bg-flowstorm-bg", text: "text-flowstorm-muted", label: "Unchanged" },
};

interface VisualDiffProps {
  diff: PipelineDiff;
  versionFrom: number;
  versionTo: number;
}

export function VisualDiff({ diff, versionFrom, versionTo }: VisualDiffProps) {
  const changedNodes = diff.node_diffs.filter(
    (n) => n.change_type !== "unchanged"
  );
  const changedEdges = diff.edge_diffs.filter(
    (e) => e.change_type !== "unchanged"
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-flowstorm-text">
          v{versionFrom} &rarr; v{versionTo}
        </h3>
        <div className="flex gap-3 text-[10px]">
          <span className="text-green-400">
            +{diff.stats.nodes_added} nodes
          </span>
          <span className="text-red-400">
            -{diff.stats.nodes_removed} nodes
          </span>
          <span className="text-yellow-400">
            ~{diff.stats.nodes_modified} modified
          </span>
          <span className="text-green-400">
            +{diff.stats.edges_added} edges
          </span>
          <span className="text-red-400">
            -{diff.stats.edges_removed} edges
          </span>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-flowstorm-bg rounded-md px-3 py-2 text-xs text-flowstorm-muted">
        {diff.summary}
      </div>

      {/* Node changes */}
      {changedNodes.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-2">
            Node Changes
          </h4>
          <div className="space-y-2">
            {changedNodes.map((node) => {
              const change =
                CHANGE_COLORS[node.change_type] || CHANGE_COLORS.unchanged;
              return (
                <div
                  key={node.node_id}
                  className={`${change.bg} border border-flowstorm-border rounded-md px-3 py-2`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${change.bg} ${change.text}`}
                      >
                        {change.label}
                      </span>
                      <span className="text-xs font-semibold text-flowstorm-text">
                        {node.label}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-flowstorm-muted">
                      {node.node_id}
                    </span>
                  </div>

                  {/* Config changes */}
                  {node.config_changes &&
                    Object.keys(node.config_changes).length > 0 && (
                      <div className="mt-2 space-y-1">
                        {Object.entries(node.config_changes).map(
                          ([key, change]) => (
                            <div
                              key={key}
                              className="flex items-center gap-2 text-[10px] font-mono"
                            >
                              <span className="text-flowstorm-muted">
                                {key}:
                              </span>
                              {change.old !== undefined && (
                                <span className="text-red-400 line-through">
                                  {JSON.stringify(change.old)}
                                </span>
                              )}
                              <span className="text-flowstorm-muted">
                                &rarr;
                              </span>
                              {change.new !== undefined && (
                                <span className="text-green-400">
                                  {JSON.stringify(change.new)}
                                </span>
                              )}
                            </div>
                          )
                        )}
                      </div>
                    )}

                  {node.position_changed && (
                    <div className="mt-1 text-[10px] text-blue-400">
                      Position changed
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Edge changes */}
      {changedEdges.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-2">
            Edge Changes
          </h4>
          <div className="space-y-1.5">
            {changedEdges.map((edge, i) => {
              const change =
                CHANGE_COLORS[edge.change_type] || CHANGE_COLORS.unchanged;
              return (
                <div
                  key={`${edge.edge_id}-${i}`}
                  className={`${change.bg} border border-flowstorm-border rounded-md px-3 py-2 flex items-center gap-2`}
                >
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${change.bg} ${change.text}`}
                  >
                    {change.label}
                  </span>
                  <span className="text-xs font-mono text-flowstorm-text">
                    {edge.source_id}
                  </span>
                  <span className="text-flowstorm-muted">&rarr;</span>
                  <span className="text-xs font-mono text-flowstorm-text">
                    {edge.target_id}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {changedNodes.length === 0 && changedEdges.length === 0 && (
        <div className="text-center py-8">
          <p className="text-xs text-flowstorm-muted">
            No changes between these versions
          </p>
        </div>
      )}
    </div>
  );
}
