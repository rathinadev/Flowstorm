import { useMemo } from "react";
import { useMetricsStore } from "../../store/metricsStore";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, AreaChart, Area } from "recharts";

export function MetricsPanel() {
  const metrics = useMetricsStore((s) => s.metrics);
  const history = useMetricsStore((s) => s.throughputHistory);

  // Calculate stats
  const eps = metrics?.total_events_per_second ?? 0;
  const totalEvents = metrics?.total_events_processed ?? 0;
  const activeWorkers = metrics?.active_workers ?? 0;

  // Calculate trend
  const trend = useMemo(() => {
    if (history.length < 2) return 0;
    const recent = history.slice(-10);
    if (recent.length < 2) return 0;
    const first = recent[0].eps;
    const last = recent[recent.length - 1].eps;
    return ((last - first) / (first || 1)) * 100;
  }, [history]);

  // Current vs avg
  const avgEps = useMemo(() => {
    if (history.length === 0) return 0;
    return history.reduce((sum, h) => sum + h.eps, 0) / history.length;
  }, [history]);

  return (
    <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-flowstorm-text flex items-center gap-2">
          <span className="text-indigo-400">📊</span>
          Throughput
        </h3>
        <div className="flex items-center gap-2">
          {/* Mini sparkline */}
          <div className="w-16 h-6">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history.slice(-20)}>
                <Area
                  type="monotone"
                  dataKey="eps"
                  stroke="#6366f1"
                  fill="#6366f120"
                  strokeWidth={1.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Key stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-flowstorm-bg rounded-lg p-3">
          <div className="text-[9px] text-flowstorm-muted uppercase tracking-wider">Current</div>
          <div className="text-xl font-bold font-mono text-indigo-400 flex items-end gap-1">
            {eps.toFixed(0)}
            <span className="text-[10px] font-normal text-flowstorm-muted">e/s</span>
          </div>
          {/* Trend indicator */}
          <div className={`text-[10px] flex items-center gap-1 ${
            trend > 5 ? "text-green-400" : trend < -5 ? "text-red-400" : "text-flowstorm-muted"
          }`}>
            {trend > 5 ? "↑" : trend < -5 ? "↓" : "→"}
            {Math.abs(trend).toFixed(0)}%
          </div>
        </div>

        <div className="bg-flowstorm-bg rounded-lg p-3">
          <div className="text-[9px] text-flowstorm-muted uppercase tracking-wider">Total</div>
          <div className="text-lg font-bold font-mono text-flowstorm-text">
            {totalEvents > 1000 
              ? `${(totalEvents / 1000).toFixed(1)}k`
              : totalEvents.toLocaleString()}
          </div>
          <div className="text-[10px] text-flowstorm-muted">events</div>
        </div>

        <div className="bg-flowstorm-bg rounded-lg p-3">
          <div className="text-[9px] text-flowstorm-muted uppercase tracking-wider">Avg</div>
          <div className="text-lg font-bold font-mono text-green-400">
            {avgEps.toFixed(0)}
          </div>
          <div className="text-[10px] text-flowstorm-muted">e/s avg</div>
        </div>
      </div>

      {/* Throughput chart with gradient */}
      <div className="h-32 relative">
        <div className="absolute inset-0 bg-gradient-to-t from-flowstorm-surface to transparent z-10 pointer-events-none" />
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history}>
            <defs>
              <linearGradient id="colorEps" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis 
              tick={{ fontSize: 9, fill: "#64748b" }} 
              width={30}
              tickFormatter={(v) => `${Math.round(v)}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1a1d27",
                border: "1px solid #2a2d3a",
                borderRadius: "6px",
                fontSize: "11px",
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area
              type="monotone"
              dataKey="eps"
              stroke="#6366f1"
              strokeWidth={2}
              fill="url(#colorEps)"
              dot={false}
              name="Events/sec"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Workers row */}
      <div className="mt-3 pt-3 border-t border-flowstorm-border/50">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-flowstorm-muted">Active Workers</span>
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(activeWorkers, 7) }).map((_, i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-green-500 animate-pulse"
                style={{ animationDelay: `${i * 100}ms` }}
              />
            ))}
            {activeWorkers > 7 && (
              <span className="text-[10px] text-flowstorm-muted">+{activeWorkers - 7}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}