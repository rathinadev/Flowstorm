import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { NODE_COLORS, OPERATOR_LABELS, type OperatorType, type NodeType } from "../../types/pipeline";
import { useMetricsStore } from "../../store/metricsStore";
import { getHealthStatus, HEALTH_COLORS } from "../../types/metrics";

interface FlowStormNodeData {
  label: string;
  operatorType: OperatorType;
  nodeType: NodeType;
  nodeId: string;
  config: Record<string, unknown>;
}

function FlowStormNode({ data, selected }: NodeProps<FlowStormNodeData>) {
  const metrics = useMetricsStore((s) => s.metrics);

  // Find worker metrics for this node
  const workerMetrics = metrics?.workers
    ? Object.values(metrics.workers).find((w) => w.node_id === data.nodeId)
    : null;

  const healthScore = workerMetrics ? 80 : 0; // Will be replaced with real health
  const healthStatus = workerMetrics ? getHealthStatus(healthScore) : "dead";
  const borderColor = workerMetrics
    ? HEALTH_COLORS[healthStatus]
    : NODE_COLORS[data.nodeType];
  const eps = workerMetrics?.events_per_second ?? 0;
  const latency = workerMetrics?.avg_latency_ms ?? 0;

  const isSource = data.nodeType === "source";
  const isSink = data.nodeType === "sink";

  return (
    <div
      className={`
        relative px-4 py-3 rounded-lg border-2 min-w-[180px]
        bg-flowstorm-surface shadow-lg
        transition-all duration-300
        ${selected ? "ring-2 ring-flowstorm-primary ring-offset-2 ring-offset-flowstorm-bg" : ""}
      `}
      style={{
        borderColor,
        boxShadow: workerMetrics
          ? `0 0 12px ${borderColor}40`
          : "0 4px 6px rgba(0,0,0,0.3)",
      }}
    >
      {/* Health indicator dot */}
      {workerMetrics && (
        <div
          className="absolute -top-1 -right-1 w-3 h-3 rounded-full animate-pulse"
          style={{ backgroundColor: borderColor }}
        />
      )}

      {/* Node type badge */}
      <div
        className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-70"
        style={{ color: NODE_COLORS[data.nodeType] }}
      >
        {data.nodeType}
      </div>

      {/* Label */}
      <div className="text-sm font-semibold text-flowstorm-text truncate">
        {data.label}
      </div>

      {/* Operator type */}
      <div className="text-xs text-flowstorm-muted mt-0.5">
        {OPERATOR_LABELS[data.operatorType] || data.operatorType}
      </div>

      {/* Live metrics */}
      {workerMetrics && (
        <div className="flex gap-3 mt-2 text-[10px]">
          <span className="text-flowstorm-muted">
            <span className="text-flowstorm-text font-mono">{eps.toFixed(0)}</span> e/s
          </span>
          <span className="text-flowstorm-muted">
            <span className="text-flowstorm-text font-mono">{latency.toFixed(0)}</span> ms
          </span>
        </div>
      )}

      {/* Handles */}
      {!isSource && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !border-2 !border-flowstorm-border !bg-flowstorm-surface"
        />
      )}
      {!isSink && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !border-2 !border-flowstorm-border !bg-flowstorm-surface"
        />
      )}
    </div>
  );
}

export const CustomNode = memo(FlowStormNode);

export const nodeTypes = {
  flowstorm: CustomNode,
};
