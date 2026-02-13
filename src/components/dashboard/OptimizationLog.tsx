import { useMetricsStore } from "../../store/metricsStore";

const OPT_ICONS: Record<string, string> = {
  predicate_pushdown: "PP",
  operator_fusion: "OF",
  auto_parallel: "AP",
  buffer_insertion: "BI",
};

const OPT_COLORS: Record<string, string> = {
  predicate_pushdown: "#8b5cf6",
  operator_fusion: "#3b82f6",
  auto_parallel: "#f59e0b",
  buffer_insertion: "#22c55e",
};

export function OptimizationLog() {
  const optimizationLog = useMetricsStore((s) => s.optimizationLog);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text">
          DAG Optimizations
        </h3>
        <span className="text-[10px] text-flowstorm-muted bg-flowstorm-bg px-2 py-0.5 rounded">
          {optimizationLog.length} applied
        </span>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {optimizationLog.length === 0 && (
          <div className="text-center py-6">
            <div className="text-2xl mb-2 text-flowstorm-muted">&#9881;</div>
            <p className="text-xs text-flowstorm-muted">
              No optimizations applied yet
            </p>
            <p className="text-[10px] text-flowstorm-muted mt-1">
              The engine will auto-optimize based on live metrics
            </p>
          </div>
        )}

        {optimizationLog.map((event, i) => {
          const icon = OPT_ICONS[event.optimization_type] || "O";
          const color = OPT_COLORS[event.optimization_type] || "#6b7280";
          return (
            <div
              key={`opt-${i}`}
              className="flex gap-3 bg-flowstorm-bg rounded-md px-3 py-2"
            >
              <div className="flex-shrink-0 mt-0.5">
                <div
                  className="w-7 h-6 rounded flex items-center justify-center text-[9px] font-bold text-white"
                  style={{ backgroundColor: color }}
                >
                  {icon}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-flowstorm-text">
                  {event.optimization_type.replace(/_/g, " ")}
                </div>
                <p className="text-[10px] text-flowstorm-muted mt-0.5">
                  {event.description}
                </p>
                <div className="flex gap-3 mt-1 text-[10px]">
                  {event.estimated_gain && (
                    <span className="text-flowstorm-success">
                      +{event.estimated_gain}
                    </span>
                  )}
                  {event.workers_added > 0 && (
                    <span className="text-flowstorm-primary">
                      +{event.workers_added} workers
                    </span>
                  )}
                  {event.workers_removed > 0 && (
                    <span className="text-flowstorm-danger">
                      -{event.workers_removed} workers
                    </span>
                  )}
                  {event.duration_ms > 0 && (
                    <span className="text-flowstorm-muted">
                      {event.duration_ms}ms
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
