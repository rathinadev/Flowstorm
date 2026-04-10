import { useMetricsStore } from "../../store/metricsStore";
import { getHealthStatus, HEALTH_COLORS, type HealthStatus } from "../../types/metrics";

function HealthBadge({ status }: { status: HealthStatus }) {
  const color = HEALTH_COLORS[status] || "#6b7280";
  const isPulsing = status === "healthy";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${
        isPulsing ? "animate-pulse" : ""
      }`}
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${isPulsing ? "animate-ping" : ""}`}
        style={{ backgroundColor: color }}
      />
      {status}
    </span>
  );
}

function ProgressBar({ value, color, label }: { value: number; color: string; label?: string }) {
  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-[10px] text-flowstorm-muted w-10">{label}</span>}
      <div className="flex-1 bg-flowstorm-bg rounded-full h-1.5 overflow-hidden">
        <div
          className="h-1.5 rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${Math.max(0, Math.min(100, value))}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span className="text-[10px] text-flowstorm-muted w-8 text-right">{value.toFixed(0)}%</span>
    </div>
  );
}

export function HealthPanel() {
  const metrics = useMetricsStore((s) => s.metrics);
  const workerHealth = useMetricsStore((s) => s.workerHealth);

  const workers = metrics?.workers ? Object.values(metrics.workers) : [];

  // Compute real health per worker from workerHealth store
  const workerScores = workers.map((w) => {
    const health = workerHealth[w.worker_id];
    return health?.health_score ?? 0;
  });

  const avgHealth = workerScores.length > 0
    ? workerScores.reduce((sum, s) => sum + s, 0) / workerScores.length
    : 0;

  const overallStatus = getHealthStatus(avgHealth);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text">Cluster Health</h3>
        <HealthBadge status={overallStatus} />
      </div>

      {/* Overall health bar */}
      <div className="mb-4 p-3 bg-flowstorm-bg rounded-lg">
        <div className="flex justify-between text-xs mb-2">
          <span className="text-flowstorm-muted">Overall Health</span>
          <span
            className="font-bold"
            style={{ color: HEALTH_COLORS[overallStatus] }}
          >
            {avgHealth.toFixed(0)}%
          </span>
        </div>
        <ProgressBar value={avgHealth} color={HEALTH_COLORS[overallStatus]} />
      </div>

      {/* Per-worker health */}
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {workers.length === 0 && (
          <p className="text-xs text-flowstorm-muted text-center py-4">
            Waiting for worker metrics...
          </p>
        )}
        {workers.map((w) => {
          const health = workerHealth[w.worker_id];
          const score = health?.health_score ?? 0;
          const status = getHealthStatus(score);
          const issues = health?.issues || [];

          return (
            <div
              key={w.worker_id}
              className="bg-flowstorm-bg rounded-lg p-3 border border-flowstorm-border/50"
            >
              {/* Header with status */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      status === "healthy" ? "animate-pulse" : ""
                    }`}
                    style={{ backgroundColor: HEALTH_COLORS[status] }}
                  />
                  <span className="text-xs font-medium text-flowstorm-text truncate max-w-[120px]">
                    {w.node_id}
                  </span>
                </div>
                <HealthBadge status={status} />
              </div>

              {/* Metrics row */}
              <div className="flex items-center gap-3 text-[10px] text-flowstorm-muted mb-2">
                <span>{w.events_per_second?.toFixed(0)} e/s</span>
                <span>•</span>
                <span>{w.avg_latency_ms?.toFixed(0)}ms</span>
                <span>•</span>
                <span>CPU {w.cpu_percent?.toFixed(0)}%</span>
              </div>

              {/* Progress bars */}
              <div className="space-y-1.5">
                <ProgressBar
                  value={100 - (w.cpu_percent ?? 0)}
                  color={w.cpu_percent! > 80 ? "#ef4444" : "#22c55e"}
                  label="CPU"
                />
                <ProgressBar
                  value={w.memory_percent! < 60 ? 100 : 100 - (w.memory_percent! - 60) * 2.5}
                  color={w.memory_percent! > 75 ? "#ef4444" : "#22c55e"}
                  label="MEM"
                />
              </div>

              {/* Issues */}
              {issues.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {issues.map((issue, i) => (
                    <span
                      key={i}
                      className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400"
                    >
                      {issue}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}