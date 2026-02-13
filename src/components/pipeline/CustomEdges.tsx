import { memo } from "react";
import { getBezierPath, type EdgeProps } from "reactflow";

function FlowStormEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const eps = (data?.events_per_second as number) ?? 0;
  const animationDuration = eps > 0 ? Math.max(0.5, 5 / Math.log2(eps + 1)) : 0;

  return (
    <>
      {/* Background path */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          stroke: "#2a2d3a",
          strokeWidth: 3,
          ...style,
        }}
      />

      {/* Animated flow path */}
      {eps > 0 && (
        <path
          d={edgePath}
          style={{
            stroke: "#6366f1",
            strokeWidth: 2,
            strokeDasharray: "8 4",
            strokeDashoffset: 0,
            animation: `flowDash ${animationDuration}s linear infinite`,
            ...style,
          }}
        />
      )}

      {/* Edge label with throughput */}
      {eps > 0 && (
        <foreignObject
          width={60}
          height={24}
          x={labelX - 30}
          y={labelY - 12}
        >
          <div className="flex items-center justify-center w-full h-full">
            <span className="text-[10px] font-mono bg-flowstorm-bg text-flowstorm-muted px-1.5 py-0.5 rounded border border-flowstorm-border">
              {eps.toFixed(0)}/s
            </span>
          </div>
        </foreignObject>
      )}
    </>
  );
}

export const CustomEdge = memo(FlowStormEdge);

export const edgeTypes = {
  flowstorm: CustomEdge,
};
