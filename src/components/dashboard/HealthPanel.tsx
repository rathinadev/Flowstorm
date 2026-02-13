import { useMetricsStore } from "../../store/metricsStore";
import { getHealthStatus, HEALTH_COLORS } from "../../types/metrics";

export function HealthPanel() {
  const metrics = useMetricsStore((s) => s.metrics);

  const workers = metrics?.workers ? Object.values(metrics.workers) : [];

  // Overall cluster health
  const avgHealth = workers.length > 0
    ? workers.reduce((sum, w) => sum + 80, 0) / workers.length // Placeholder until real health
    : 0;

  const overallStatus = getHealthStatus(avgHealth);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <h3 className="text-sm font-bold text-flowstorm-text mb-3">Cluster Health</h3>

      {/* Overall health bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-flowstorm-muted">Overall</span>
          <span
            className="font-bold"
            style={{ color: HEALTH_COLORS[overallStatus] }}
          >
            {avgHealth.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-flowstorm-bg rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all duration-500"
            style={{
              width: `${avgHealth}%`,
              backgroundColor: HEALTH_COLORS[overallStatus],
            }}
          />
        </div>
      </div>

      {/* Per-worker health */}
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {workers.length === 0 && (
          <p className="text-xs text-flowstorm-muted">No active workers</p>
        )}
        {workers.map((w) => {
          const status = getHealthStatus(80);
          return (
            <div
              key={w.worker_id}
              className="flex items-center gap-2 bg-flowstorm-bg rounded-md px-3 py-2"
            >
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: HEALTH_COLORS[status] }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-flowstorm-text truncate">
                  {w.node_id}
                </div>
                <div className="text-[10px] text-flowstorm-muted">
                  {w.events_per_second?.toFixed(0)} e/s | {w.avg_latency_ms?.toFixed(0)}ms
                </div>
              </div>
              <div className="text-xs font-mono text-flowstorm-muted">
                CPU {w.cpu_percent?.toFixed(0)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
