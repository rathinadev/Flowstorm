import { useMetricsStore } from "../../store/metricsStore";
import { HEALTH_COLORS } from "../../types/metrics";

const ACTION_ICONS: Record<string, string> = {
  restart_worker: "R",
  migrate_worker: "M",
  scale_out: "S",
  checkpoint_replay: "C",
};

const ACTION_COLORS: Record<string, string> = {
  restart_worker: "#f59e0b",
  migrate_worker: "#3b82f6",
  scale_out: "#8b5cf6",
  checkpoint_replay: "#22c55e",
};

export function HealingLog() {
  const healingLog = useMetricsStore((s) => s.healingLog);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text">
          Self-Healing Activity
        </h3>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-flowstorm-success animate-pulse" />
          <span className="text-[10px] text-flowstorm-muted">Active</span>
        </div>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {healingLog.length === 0 && (
          <div className="text-center py-6">
            <div className="text-2xl mb-2 text-flowstorm-muted">&#9729;</div>
            <p className="text-xs text-flowstorm-muted">
              No healing events yet
            </p>
            <p className="text-[10px] text-flowstorm-muted mt-1">
              The engine will auto-heal when anomalies are detected
            </p>
          </div>
        )}

        {healingLog.map((event, i) => {
          const icon = ACTION_ICONS[event.action] || "H";
          const color = ACTION_COLORS[event.action] || "#6b7280";
          return (
            <div
              key={`${event.timestamp}-${i}`}
              className="flex gap-3 bg-flowstorm-bg rounded-md px-3 py-2"
            >
              <div className="flex-shrink-0 mt-0.5">
                <div
                  className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold text-white"
                  style={{ backgroundColor: color }}
                >
                  {icon}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-flowstorm-text">
                    {event.action.replace(/_/g, " ")}
                  </span>
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: event.success
                        ? HEALTH_COLORS.healthy + "20"
                        : HEALTH_COLORS.critical + "20",
                      color: event.success
                        ? HEALTH_COLORS.healthy
                        : HEALTH_COLORS.critical,
                    }}
                  >
                    {event.success ? "OK" : "FAIL"}
                  </span>
                </div>
                <p className="text-[10px] text-flowstorm-muted mt-0.5 truncate">
                  {event.details}
                </p>
                <div className="flex gap-3 mt-1 text-[10px] text-flowstorm-muted">
                  {event.target_node_id && (
                    <span>node: {event.target_node_id}</span>
                  )}
                  <span>trigger: {event.trigger}</span>
                  {event.duration_ms > 0 && (
                    <span>{event.duration_ms}ms</span>
                  )}
                  {event.events_replayed > 0 && (
                    <span>{event.events_replayed} replayed</span>
                  )}
                </div>
              </div>
              <div className="text-[10px] text-flowstorm-muted flex-shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
