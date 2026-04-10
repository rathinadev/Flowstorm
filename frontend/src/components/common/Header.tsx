import { useState } from "react";
import { useMetricsStore } from "../../store/metricsStore";
import { useChaosStore } from "../../store/chaosStore";

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  draft: { bg: "bg-gray-500/10", text: "text-gray-400", label: "DRAFT" },
  deploying: { bg: "bg-yellow-500/10", text: "text-yellow-400", label: "DEPLOYING" },
  running: { bg: "bg-green-500/10", text: "text-green-400", label: "RUNNING" },
  paused: { bg: "bg-blue-500/10", text: "text-blue-400", label: "PAUSED" },
  failed: { bg: "bg-red-500/10", text: "text-red-400", label: "FAILED" },
  stopped: { bg: "bg-gray-500/10", text: "text-gray-400", label: "STOPPED" },
};

interface HeaderProps {
  pipelineId: string | null;
  pipelineName: string;
  pipelineStatus: string;
  onNameChange: (name: string) => void;
  onStartDemo?: () => void;
  onStopDemo?: () => void;
  demoRunning?: boolean;
}

export function Header({ pipelineId, pipelineName, pipelineStatus, onNameChange, onStartDemo, onStopDemo, demoRunning }: HeaderProps) {
  const metrics = useMetricsStore((s) => s.metrics);
  const chaosActive = useChaosStore((s) => s.active);
  const [editing, setEditing] = useState(false);

  const statusStyle = STATUS_STYLES[pipelineStatus] || STATUS_STYLES.draft;

  return (
    <header className="h-12 bg-flowstorm-surface border-b border-flowstorm-border flex items-center justify-between px-4">
      {/* Left: Logo + Pipeline name */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-flowstorm-primary to-flowstorm-secondary flex items-center justify-center">
            <span className="text-white text-xs font-bold">FS</span>
          </div>
          <span className="text-sm font-bold text-flowstorm-text">
            FlowStorm
          </span>
        </div>

        <div className="w-px h-5 bg-flowstorm-border" />

        {/* Editable pipeline name */}
        {editing ? (
          <input
            className="text-xs bg-flowstorm-bg border border-flowstorm-border rounded px-2 py-1 text-flowstorm-text outline-none focus:border-flowstorm-primary"
            value={pipelineName}
            onChange={(e) => onNameChange(e.target.value)}
            onBlur={() => setEditing(false)}
            onKeyDown={(e) => e.key === "Enter" && setEditing(false)}
            autoFocus
          />
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-flowstorm-muted hover:text-flowstorm-text transition-colors"
            title="Click to rename"
          >
            {pipelineName || "Untitled Pipeline"}
          </button>
        )}

        {/* Pipeline status badge */}
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${statusStyle.bg} ${statusStyle.text}`}>
          {pipelineStatus === "deploying" && (
            <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
          )}
          {pipelineStatus === "running" && (
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          )}
          {statusStyle.label}
        </div>
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

        {/* Demo button */}
        {demoRunning ? (
          <button
            onClick={onStopDemo}
            className="px-3 py-1 rounded text-[10px] font-bold bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Stop Demo
          </button>
        ) : (
          <button
            onClick={onStartDemo}
            className="px-3 py-1 rounded text-[10px] font-bold bg-flowstorm-primary/20 text-flowstorm-primary hover:bg-flowstorm-primary/30 transition-colors"
          >
            Start Demo
          </button>
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

        {/* Keyboard shortcuts hint */}
        <div className="flex items-center gap-1 text-[9px] text-flowstorm-muted">
          <kbd className="px-1 py-0.5 bg-flowstorm-bg rounded border border-flowstorm-border">Space</kbd>
          <span>demo</span>
        </div>
      </div>
    </header>
  );
}
