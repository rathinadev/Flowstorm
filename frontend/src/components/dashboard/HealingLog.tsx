import { useMetricsStore } from "../../store/metricsStore";
import { HEALTH_COLORS } from "../../types/metrics";

const ACTION_ICONS: Record<string, string> = {
  failover: "⟳",
  restart: "↻",
  scale_out: "⤢",
  migrate: "⇄",
};

const ACTION_LABELS: Record<string, string> = {
  failover: "Failover",
  restart: "Restart",
  scale_out: "Scale Out",
  migrate: "Migrate",
};

const ACTION_COLORS: Record<string, string> = {
  failover: "#ef4444",
  restart: "#f59e0b",
  scale_out: "#8b5cf6",
  migrate: "#3b82f6",
};

export function HealingLog() {
  const healingLog = useMetricsStore((s) => s.healingLog);

  // Check if there's recent activity
  const hasRecentActivity = healingLog.length > 0;
  const lastEvent = healingLog[0];
  const timeSinceLastEvent = lastEvent
    ? (Date.now() - new Date(lastEvent.timestamp).getTime()) / 1000
    : Infinity;

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text flex items-center gap-2">
          <span className="text-flowstorm-primary">⚡</span>
          Self-Healing
        </h3>
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              hasRecentActivity && timeSinceLastEvent < 30 ? "animate-pulse bg-flowstorm-success" : "bg-flowstorm-muted"
            }`}
          />
          <span className="text-[10px] text-flowstorm-muted">
            {hasRecentActivity && timeSinceLastEvent < 30 ? "Active" : "Idle"}
          </span>
        </div>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {healingLog.length === 0 && (
          <div className="text-center py-6">
            <div className="text-3xl mb-2 text-flowstorm-muted/30">🛡️</div>
            <p className="text-xs text-flowstorm-muted">No healing events yet</p>
            <p className="text-[10px] text-flowstorm-muted/70 mt-1">
              System will auto-heal when issues detected
            </p>
          </div>
        )}

        {healingLog.map((event, i) => {
          const icon = ACTION_ICONS[event.action] || "⚙";
          const color = ACTION_COLORS[event.action] || "#6b7280";
          const label = ACTION_LABELS[event.action] || event.action;
          const isRecent = i === 0 && timeSinceLastEvent < 5;

          return (
            <div
              key={`${event.timestamp}-${i}`}
              className={`relative ${
                isRecent ? "bg-flowstorm-bg ring-1 ring-flowstorm-primary/30" : "bg-flowstorm-bg"
              } rounded-lg px-3 py-2.5 transition-all`}
            >
              {/* Success indicator line */}
              <div
                className="absolute left-0 top-2 bottom-2 w-1 rounded-full"
                style={{ backgroundColor: event.success ? "#22c55e" : "#ef4444" }}
              />

              <div className="flex items-start gap-3 ml-2">
                {/* Icon */}
                <div
                  className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm ${
                    isRecent ? "animate-spin" : ""
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
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded flex items-center gap-1"
                      style={{
                        backgroundColor: event.success
                          ? "#22c55e20"
                          : "#ef444420",
                        color: event.success ? "#22c55e" : "#ef4444",
                      }}
                    >
                      <span
                        className={`w-1 h-1 rounded-full ${
                          event.success ? "bg-green-500" : "bg-red-500"
                        }`}
                      />
                      {event.success ? "Success" : "Failed"}
                    </span>
                  </div>

                  <p className="text-[10px] text-flowstorm-muted mt-1 truncate">
                    {event.details || event.trigger}
                  </p>

                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-[10px] text-flowstorm-muted/80">
                    {event.target_node_id && (
                      <span className="flex items-center gap-1">
                        <span className="text-flowstorm-primary">◆</span>
                        {event.target_node_id}
                      </span>
                    )}
                    {event.duration_ms > 0 && (
                      <span className="flex items-center gap-1">
                        <span className="text-yellow-500">⏱</span>
                        {event.duration_ms}ms
                      </span>
                    )}
                    {event.events_replayed > 0 && (
                      <span className="flex items-center gap-1">
                        <span className="text-blue-400">↩</span>
                        {event.events_replayed} replayed
                      </span>
                    )}
                  </div>
                </div>

                {/* Timestamp */}
                <div className="text-[9px] text-flowstorm-muted flex-shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString([], {
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
      {healingLog.length > 0 && (
        <div className="mt-3 pt-3 border-t border-flowstorm-border/50 flex items-center justify-between text-[10px] text-flowstorm-muted">
          <span>{healingLog.length} events total</span>
          <span>
            {healingLog.filter((e) => e.success).length} successful •{" "}
            {healingLog.filter((e) => !e.success).length} failed
          </span>
        </div>
      )}
    </div>
  );
}