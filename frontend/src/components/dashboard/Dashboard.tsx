import { useEffect, useState } from "react";
import { MetricsPanel } from "./MetricsPanel";
import { HealthPanel } from "./HealthPanel";
import { HealingLog } from "./HealingLog";
import { OptimizationLog } from "./OptimizationLog";
import { useMetricsStore } from "../../store/metricsStore";

function StatCard({
  label,
  value,
  unit,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  unit?: string;
  icon: string;
  color: string;
}) {
  return (
    <div className="bg-flowstorm-bg rounded-lg p-3 flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
        style={{ backgroundColor: `${color}20`, color }}
      >
        {icon}
      </div>
      <div>
        <div className="text-[10px] text-flowstorm-muted uppercase tracking-wider">
          {label}
        </div>
        <div className="text-lg font-bold text-flowstorm-text">
          {value}
          {unit && <span className="text-sm font-normal text-flowstorm-muted ml-1">{unit}</span>}
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  const metrics = useMetricsStore((s) => s.metrics);
  const workerHealth = useMetricsStore((s) => s.workerHealth);

  // Calculate stats
  const totalEps = metrics?.total_events_per_second || 0;
  const activeWorkers = metrics?.active_workers || 0;
  const workers = metrics?.workers ? Object.values(metrics.workers) : [];
  const avgHealth =
    workers.length > 0
      ? Object.values(workerHealth).reduce(
          (sum, w) => sum + (w?.health_score || 0),
          0
        ) / workers.length
      : 0;

  // Uptime counter
  const [uptime, setUptime] = useState(0);
  useEffect(() => {
    if (!metrics) return;
    const interval = setInterval(() => {
      setUptime((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [metrics]);

  const formatUptime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-flowstorm-text flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-flowstorm-success animate-pulse" />
              Live Dashboard
            </h2>
            <p className="text-xs text-flowstorm-muted mt-0.5">
              Real-time pipeline monitoring
            </p>
          </div>

          {/* Live indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-flowstorm-bg rounded-full">
            <div className="w-2 h-2 rounded-full bg-flowstorm-success animate-pulse" />
            <span className="text-xs text-flowstorm-success font-medium">LIVE</span>
            <span className="text-xs text-flowstorm-muted">{formatUptime(uptime)}</span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-3 px-4 py-2">
        <StatCard
          label="Throughput"
          value={totalEps.toFixed(0)}
          unit="e/s"
          icon="📊"
          color="#22c55e"
        />
        <StatCard
          label="Workers"
          value={activeWorkers}
          unit="active"
          icon="⚙"
          color="#8b5cf6"
        />
        <StatCard
          label="Health"
          value={avgHealth.toFixed(0)}
          unit="%"
          icon="💚"
          color={avgHealth > 70 ? "#22c55e" : avgHealth > 30 ? "#f59e0b" : "#ef4444"}
        />
        <StatCard
          label="Events"
          value={(metrics?.total_events_processed || 0) > 1000 
            ? `${((metrics?.total_events_processed || 0) / 1000).toFixed(1)}k`
            : metrics?.total_events_processed || 0}
          unit="total"
          icon="📨"
          color="#3b82f6"
        />
      </div>

      {/* Main Panels Grid */}
      <div className="grid grid-cols-2 gap-4 p-4 pt-2">
        <MetricsPanel />
        <HealthPanel />
        <HealingLog />
        <OptimizationLog />
      </div>
    </div>
  );
}