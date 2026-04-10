import { useMetricsStore } from "../../store/metricsStore";

const OPT_ICONS: Record<string, string> = {
  predicate_pushdown: "▼",
  operator_fusion: "⊕",
  auto_parallel: "⤢",
  buffer_insertion: "▦",
  window_optimization: "⟳",
};

const OPT_LABELS: Record<string, string> = {
  predicate_pushdown: "Predicate Pushdown",
  operator_fusion: "Operator Fusion",
  auto_parallel: "Auto-Parallel",
  buffer_insertion: "Buffer Insertion",
  window_optimization: "Window Opt",
};

const OPT_COLORS: Record<string, string> = {
  predicate_pushdown: "#8b5cf6",
  operator_fusion: "#3b82f6",
  auto_parallel: "#f59e0b",
  buffer_insertion: "#22c55e",
  window_optimization: "#ec4899",
};

function GainBadge({ gain }: { gain?: string }) {
  if (!gain) return null;

  // Extract numbers from gain string
  const numbers = gain.match(/(\d+(?:\.\d+)?)([x%]?)/);
  if (!numbers) {
    return (
      <span className="text-xs font-bold text-emerald-400">+{gain}</span>
    );
  }

  return (
    <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
      <span>▲</span>
      {gain}
    </span>
  );
}

function WorkersBadge({ added, removed }: { added: number; removed: number }) {
  if (added === 0 && removed === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {added > 0 && (
        <span className="text-xs px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">
          +{added}
        </span>
      )}
      {removed > 0 && (
        <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
          -{removed}
        </span>
      )}
      <span className="text-[10px] text-flowstorm-muted">workers</span>
    </div>
  );
}

export function OptimizationLog() {
  const optimizationLog = useMetricsStore((s) => s.optimizationLog);

  // Check recent activity
  const hasRecentActivity = optimizationLog.length > 0;
  const lastEvent = optimizationLog[0];
  const timeSinceLastEvent = lastEvent
    ? (Date.now() - new Date(lastEvent.timestamp || Date.now()).getTime()) / 1000
    : Infinity;

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text flex items-center gap-2">
          <span className="text-violet-400">⚡</span>
          Auto-Optimization
        </h3>
        <span className="text-[10px] text-flowstorm-muted bg-flowstorm-bg px-2 py-0.5 rounded">
          {optimizationLog.length} applied
        </span>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {optimizationLog.length === 0 && (
          <div className="text-center py-6">
            <div className="text-3xl mb-2 text-flowstorm-muted/30">🔧</div>
            <p className="text-xs text-flowstorm-muted">No optimizations yet</p>
            <p className="text-[10px] text-flowstorm-muted/70 mt-1">
              Engine optimizes based on data patterns
            </p>
          </div>
        )}

        {optimizationLog.map((event, i) => {
          const icon = OPT_ICONS[event.optimization_type] || "⚙";
          const color = OPT_COLORS[event.optimization_type] || "#6b7280";
          const label = OPT_LABELS[event.optimization_type] || event.optimization_type;
          const isRecent = i === 0 && timeSinceLastEvent < 10;

          return (
            <div
              key={`opt-${i}`}
              className={`relative ${
                isRecent
                  ? "bg-gradient-to-r from-violet-500/10 to-flowstorm-bg ring-1 ring-violet-500/30"
                  : "bg-flowstorm-bg"
              } rounded-lg px-3 py-2.5 transition-all`}
            >
              {/* Color indicator */}
              <div
                className="absolute left-0 top-2 bottom-2 w-1 rounded-full"
                style={{ backgroundColor: color }}
              />

              <div className="flex items-start gap-3 ml-2">
                {/* Icon */}
                <div
                  className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm ${
                    isRecent ? "animate-bounce" : ""
                  }`}
                  style={{ backgroundColor: `${color}20`, color }}
                >
                  {icon}
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-flowstorm-text">
                      {label}
                    </span>
                    {isRecent && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/30 text-violet-300 animate-pulse">
                        NEW
                      </span>
                    )}
                  </div>

                  <p className="text-[10px] text-flowstorm-muted mt-1">
                    {event.description}
                  </p>

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2">
                    {event.estimated_gain && (
                      <GainBadge gain={event.estimated_gain} />
                    )}
                    <WorkersBadge
                      added={event.workers_added}
                      removed={event.workers_removed}
                    />
                    {event.duration_ms > 0 && (
                      <span className="text-[10px] text-flowstorm-muted flex items-center gap-1">
                        <span className="text-yellow-500">⏱</span>
                        {event.duration_ms}ms
                      </span>
                    )}
                  </div>
                </div>

                {/* Timestamp */}
                <div className="text-[9px] text-flowstorm-muted flex-shrink-0">
                  {new Date(event.timestamp || Date.now()).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary footer */}
      {optimizationLog.length > 0 && (
        <div className="mt-3 pt-3 border-t border-flowstorm-border/50 text-[10px] text-flowstorm-muted">
          <span>Last: </span>
          <span className="text-violet-400">
            {OPT_LABELS[optimizationLog[0]?.optimization_type] || "Unknown"}
          </span>
          <span className="mx-2">•</span>
          <span>Total gain: </span>
          <span className="text-emerald-400">
            {optimizationLog.filter((e) => e.workers_added > 0).length} scaled
          </span>
        </div>
      )}
    </div>
  );
}