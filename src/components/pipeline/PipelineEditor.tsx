import { useCallback, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Node,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { nodeTypes } from "./CustomNodes";
import { edgeTypes } from "./CustomEdges";
import { NodePalette } from "./NodePalette";
import { usePipelineStore } from "../../store/pipelineStore";
import { OPERATOR_LABELS, getNodeType, NODE_COLORS, type OperatorType } from "../../types/pipeline";

let nodeIdCounter = 0;
function nextNodeId() {
  return `n-${++nodeIdCounter}`;
}

export function PipelineEditor() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] =
    useState<ReactFlowInstance | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const selectNode = usePipelineStore((s) => s.selectNode);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          { ...params, type: "flowstorm", animated: true },
          eds
        )
      );
    },
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const operatorType = event.dataTransfer.getData("operator_type") as OperatorType;
      if (!operatorType || !reactFlowInstance || !reactFlowWrapper.current) return;

      const bounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.project({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const nodeType = getNodeType(operatorType);
      const id = nextNodeId();

      const newNode: Node = {
        id,
        type: "flowstorm",
        position,
        data: {
          label: OPERATOR_LABELS[operatorType],
          operatorType,
          nodeType,
          nodeId: id,
          config: {},
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, setNodes]
  );

  return (
    <div className="flex h-full">
      <NodePalette onDragStart={() => {}} />

      <div className="flex-1" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onInit={setReactFlowInstance}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          defaultEdgeOptions={{ type: "flowstorm", animated: true }}
          fitView
          snapToGrid
          snapGrid={[16, 16]}
          className="bg-flowstorm-bg"
        >
          <Background color="#1e2030" gap={16} size={1} />
          <Controls className="!bg-flowstorm-surface !border-flowstorm-border !shadow-lg" />
          <MiniMap
            className="!bg-flowstorm-surface !border-flowstorm-border"
            nodeColor={(node) => {
              const nt = node.data?.nodeType || "operator";
              return NODE_COLORS[nt as keyof typeof NODE_COLORS] || "#8b5cf6";
            }}
            maskColor="rgba(15, 17, 23, 0.7)"
          />
        </ReactFlow>
      </div>

      {/* CSS for animated edges */}
      <style>{`
        @keyframes flowDash {
          to { stroke-dashoffset: -24; }
        }
      `}</style>
    </div>
  );
}
