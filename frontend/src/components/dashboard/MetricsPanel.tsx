import { useMetricsStore } from "../../store/metricsStore";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

export function MetricsPanel() {
  const metrics = useMetricsStore((s) => s.metrics);
  const history = useMetricsStore((s) => s.throughputHistory);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <h3 className="text-sm font-bold text-flowstorm-text mb-3">Pipeline Throughput</h3>

      {/* Key stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-flowstorm-bg rounded-md p-2.5">
          <div className="text-[10px] text-flowstorm-muted uppercase">Events/sec</div>
          <div className="text-xl font-bold font-mono text-flowstorm-primary">
            {metrics?.total_events_per_second?.toFixed(0) ?? "0"}
          </div>
        </div>
        <div className="bg-flowstorm-bg rounded-md p-2.5">
          <div className="text-[10px] text-flowstorm-muted uppercase">Total Events</div>
          <div className="text-xl font-bold font-mono text-flowstorm-text">
            {metrics?.total_events_processed?.toLocaleString() ?? "0"}
          </div>
        </div>
        <div className="bg-flowstorm-bg rounded-md p-2.5">
          <div className="text-[10px] text-flowstorm-muted uppercase">Workers</div>
          <div className="text-xl font-bold font-mono text-flowstorm-success">
            {metrics?.active_workers ?? 0}
          </div>
        </div>
      </div>

      {/* Throughput chart */}
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history}>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              width={40}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1a1d27",
                border: "1px solid #2a2d3a",
                borderRadius: "6px",
                fontSize: "12px",
              }}
            />
            <Line
              type="monotone"
              dataKey="eps"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
              name="Events/sec"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
