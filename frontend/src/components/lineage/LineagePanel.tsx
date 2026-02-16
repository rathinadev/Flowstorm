import { useState } from "react";
import { api } from "../../services/api";

interface LineageEntry {
  node_id: string;
  operator_type: string;
  timestamp: string;
  input_event_id?: string;
  output_event_id?: string;
  processing_time_ms?: number;
}

interface LineageResult {
  event_id: string;
  pipeline_id: string;
  lineage: LineageEntry[];
}

interface LineagePanelProps {
  pipelineId: string | null;
}

export function LineagePanel({ pipelineId }: LineagePanelProps) {
  const [eventId, setEventId] = useState("");
  const [lineage, setLineage] = useState<LineageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrace = async () => {
    if (!pipelineId || !eventId.trim()) return;
    setLoading(true);
    setError(null);
    setLineage(null);

    try {
      const result = (await api.getLineage(
        pipelineId,
        eventId.trim()
      )) as LineageResult;
      setLineage(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to trace event");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">&#128269;</span>
          <h2 className="text-sm font-bold text-flowstorm-text">
            Data Lineage Tracker
          </h2>
        </div>
        <p className="text-[10px] text-flowstorm-muted mt-0.5">
          Trace any event through the entire pipeline to see its journey
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!pipelineId ? (
          <div className="bg-flowstorm-bg rounded-lg p-4 text-center">
            <p className="text-xs text-flowstorm-muted">
              Deploy a pipeline first to trace events
            </p>
          </div>
        ) : (
          <>
            {/* Search */}
            <div className="flex gap-2">
              <input
                type="text"
                value={eventId}
                onChange={(e) => setEventId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTrace()}
                placeholder="Enter event ID to trace..."
                className="flex-1 bg-flowstorm-bg border border-flowstorm-border rounded-md px-3 py-2
                  text-xs text-flowstorm-text placeholder-flowstorm-muted
                  focus:outline-none focus:border-flowstorm-primary transition-colors"
              />
              <button
                onClick={handleTrace}
                disabled={loading || !eventId.trim()}
                className="px-4 py-2 rounded-md bg-flowstorm-primary hover:bg-flowstorm-primary/80
                  text-white text-xs font-bold transition-colors disabled:opacity-50"
              >
                {loading ? "Tracing..." : "Trace"}
              </button>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-md px-3 py-2">
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}

            {/* Lineage visualization */}
            {lineage && (
              <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-bold text-flowstorm-text">
                    Event Journey
                  </h3>
                  <span className="text-[10px] text-flowstorm-muted font-mono">
                    {lineage.event_id}
                  </span>
                </div>

                <div className="relative">
                  {/* Vertical line */}
                  <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-flowstorm-border" />

                  <div className="space-y-4">
                    {lineage.lineage.map((entry, i) => (
                      <div key={i} className="flex gap-3 relative">
                        {/* Dot */}
                        <div className="flex-shrink-0 z-10">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold text-white ${
                              i === 0
                                ? "bg-blue-500"
                                : i === lineage.lineage.length - 1
                                ? "bg-green-500"
                                : "bg-purple-500"
                            }`}
                          >
                            {i + 1}
                          </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 bg-flowstorm-bg rounded-md px-3 py-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-flowstorm-text">
                              {entry.node_id}
                            </span>
                            <span className="text-[10px] font-mono text-flowstorm-primary px-1.5 py-0.5 bg-flowstorm-primary/10 rounded">
                              {entry.operator_type}
                            </span>
                          </div>
                          <div className="flex gap-3 mt-1 text-[10px] text-flowstorm-muted">
                            {entry.processing_time_ms !== undefined && (
                              <span>
                                Processing: {entry.processing_time_ms}ms
                              </span>
                            )}
                            <span>
                              {new Date(entry.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {lineage.lineage.length === 0 && (
                  <p className="text-xs text-flowstorm-muted text-center py-4">
                    No lineage data found for this event
                  </p>
                )}
              </div>
            )}

            {/* Instructions */}
            {!lineage && !loading && (
              <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
                <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-3">
                  How it works
                </h3>
                <div className="space-y-2 text-xs text-flowstorm-muted">
                  <p>
                    Each event processed by FlowStorm carries lineage metadata
                    as it passes through operators.
                  </p>
                  <p>
                    Enter an event ID above to trace its complete journey
                    through the pipeline, including processing times at each
                    node.
                  </p>
                  <div className="flex items-center gap-2 mt-3">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span>Source (entry point)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500" />
                    <span>Operator (processing stage)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span>Sink (output destination)</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
