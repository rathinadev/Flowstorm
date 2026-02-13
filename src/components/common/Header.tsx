import { useMetricsStore } from "../../store/metricsStore";
import { useChaosStore } from "../../store/chaosStore";

interface HeaderProps {
  pipelineId: string | null;
  pipelineName: string;
}

export function Header({ pipelineId, pipelineName }: HeaderProps) {
  const metrics = useMetricsStore((s) => s.metrics);
  const chaosActive = useChaosStore((s) => s.active);

  return (
    <header className="h-12 bg-flowstorm-surface border-b border-flowstorm-border flex items-center justify-between px-4">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-flowstorm-primary to-flowstorm-secondary flex items-center justify-center">
            <span className="text-white text-xs font-bold">FS</span>
          </div>
          <span className="text-sm font-bold text-flowstorm-text">
            FlowStorm
          </span>
        </div>

        {pipelineId && (
          <>
            <div className="w-px h-5 bg-flowstorm-border" />
            <span className="text-xs text-flowstorm-muted">
              {pipelineName || "Untitled Pipeline"}
            </span>
          </>
        )}
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-4">
        {/* Throughput */}
        {metrics && (
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-flowstorm-success animate-pulse" />
            <span className="text-xs font-mono text-flowstorm-text">
              {metrics.total_events_per_second?.toFixed(0) || "0"} e/s
            </span>
          </div>
        )}

        {/* Workers */}
        {metrics && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-flowstorm-muted">Workers:</span>
            <span className="text-xs font-mono font-bold text-flowstorm-success">
              {metrics.active_workers || 0}
            </span>
          </div>
        )}

        {/* Chaos indicator */}
        {chaosActive && (
          <div className="flex items-center gap-1.5 bg-red-500/10 px-2 py-1 rounded">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[10px] font-bold text-red-400">
              CHAOS
            </span>
          </div>
        )}

        {/* Connection status */}
        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              pipelineId ? "bg-flowstorm-success" : "bg-flowstorm-muted"
            }`}
          />
          <span className="text-[10px] text-flowstorm-muted">
            {pipelineId ? "Connected" : "No Pipeline"}
          </span>
        </div>
      </div>
    </header>
  );
}
