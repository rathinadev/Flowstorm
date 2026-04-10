import { memo } from "react";
import { getBezierPath, type EdgeProps } from "reactflow";

function getEdgeColor(eps: number): string {
  if (eps > 1000) return "#22c55e"; // Green - high throughput
  if (eps > 500) return "#3b82f6"; // Blue - good
  if (eps > 100) return "#f59e0b"; // Yellow - moderate
  if (eps > 0) return "#f97316"; // Orange - low
  return "#6b7280"; // Gray - none
}

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
  const edgeColor = getEdgeColor(eps);
  const animationDuration = eps > 0 ? Math.max(0.3, 4 / Math.log2(eps + 1)) : 0;

  return (
    <>
      {/* Shadow/glow effect */}
      <path
        id={`${id}-glow`}
        d={edgePath}
        style={{
          stroke: eps > 0 ? `${edgeColor}30` : "transparent",
          strokeWidth: 8,
          fill: "none",
        }}
      />

      {/* Background path */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          stroke: "#1a1d27",
          strokeWidth: 4,
          ...style,
        }}
      />

      {/* Animated flow path */}
      {eps > 0 && (
        <path
          d={edgePath}
          style={{
            stroke: edgeColor,
            strokeWidth: 2.5,
            strokeDasharray: "10 5",
            strokeDashoffset: 0,
            animation: `flowDash ${animationDuration}s linear infinite`,
            ...style,
          }}
        />
      )}

      {/* Edge label with throughput - enhanced */}
      {eps > 0 && (
        <foreignObject
          width={80}
          height={28}
          x={labelX - 40}
          y={labelY - 14}
        >
          <div 
            className="flex items-center justify-center w-full h-full"
            style={{ pointerEvents: "none" }}
          >
            <div 
              className="px-2 py-1 rounded-md text-[11px] font-bold font-mono"
              style={{
                backgroundColor: `${edgeColor}20`,
                color: edgeColor,
                border: `1.5px solid ${edgeColor}40`,
                boxShadow: `0 0 8px ${edgeColor}20`,
              }}
            >
              {eps > 1000 
                ? `${(eps / 1000).toFixed(1)}k/s`
                : `${eps.toFixed(0)}/s`
              }
            </div>
          </div>
        </foreignObject>
      )}

      {/* Little dots flowing when active */}
      {eps > 100 && (
        <>
          <circle r={2} fill={edgeColor}>
            <animateMotion
              dur={`${animationDuration}s`}
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
          <circle r={2} fill={edgeColor} opacity={0.5}>
            <animateMotion
              dur={`${animationDuration}s`}
              repeatCount="indefinite"
              path={edgePath}
              begin={`${animationDuration * 0.5}s`}
            />
          </circle>
        </>
      )}
    </>
  );
}

export const CustomEdge = memo(FlowStormEdge);

export const edgeTypes = {
  flowstorm: CustomEdge,
};