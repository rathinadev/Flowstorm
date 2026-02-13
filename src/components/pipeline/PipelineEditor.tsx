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
import { NodeConfigPanel } from "./NodeConfigPanel";
import { usePipelineStore } from "../../store/pipelineStore";
import { OPERATOR_LABELS, getNodeType, NODE_COLORS, type OperatorType } from "../../types/pipeline";

let nodeIdCounter = 0;
function nextNodeId() {
  return `n-${++nodeIdCounter}`;
}

interface PipelineEditorProps {
  onDeploy: (
    nodes: Array<{
      id: string;
      label: string;
      operator_type: string;
      config: Record<string, unknown>;
      position_x: number;
      position_y: number;
    }>,
    edges: Array<{ source_node_id: string; target_node_id: string }>
  ) => void;
  onStop: () => void;
  pipelineId: string | null;
  pipelineStatus: string;
}

export function PipelineEditor({ onDeploy, onStop, pipelineId, pipelineStatus }: PipelineEditorProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] =
    useState<ReactFlowInstance | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

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
      setSelectedNode(node);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
    setSelectedNode(null);
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

  const handleDeploy = useCallback(() => {
    if (nodes.length === 0) return;

    const apiNodes = nodes.map((n) => ({
      id: n.id,
      label: n.data.label,
      operator_type: n.data.operatorType,
      config: n.data.config || {},
      position_x: n.position.x,
      position_y: n.position.y,
    }));

    const apiEdges = edges.map((e) => ({
      source_node_id: e.source,
      target_node_id: e.target,
    }));

    onDeploy(apiNodes, apiEdges);
  }, [nodes, edges, onDeploy]);

  const handleConfigChange = useCallback(
    (nodeId: string, config: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, config } }
            : n
        )
      );
    },
    [setNodes]
  );

  const isRunning = pipelineStatus === "running";
  const isDeploying = pipelineStatus === "deploying";
  const canDeploy = nodes.length > 0 && !isRunning && !isDeploying;

  return (
    <div className="flex h-full">
      <NodePalette onDragStart={() => {}} />

      <div className="flex-1 relative" ref={reactFlowWrapper}>
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

        {/* Deploy / Stop toolbar */}
        <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
          {nodes.length === 0 && (
            <div className="bg-flowstorm-surface/90 border border-flowstorm-border rounded-lg px-3 py-2 text-xs text-flowstorm-muted">
              Drag nodes from the palette to start
            </div>
          )}

          {isRunning && pipelineId && (
            <button
              onClick={onStop}
              className="px-4 py-2 rounded-lg text-xs font-semibold
                bg-red-500/20 text-red-400 border border-red-500/30
                hover:bg-red-500/30 transition-colors"
            >
              Stop Pipeline
            </button>
          )}

          <button
            onClick={handleDeploy}
            disabled={!canDeploy}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              canDeploy
                ? "bg-flowstorm-primary text-white hover:bg-flowstorm-primary/80 shadow-lg shadow-flowstorm-primary/20"
                : "bg-flowstorm-surface text-flowstorm-muted border border-flowstorm-border cursor-not-allowed"
            }`}
          >
            {isDeploying ? (
              <span className="flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Deploying...
              </span>
            ) : isRunning ? (
              "Deployed"
            ) : (
              "Deploy Pipeline"
            )}
          </button>
        </div>

        {/* Node count indicator */}
        {nodes.length > 0 && (
          <div className="absolute bottom-4 right-4 z-10 bg-flowstorm-surface/90 border border-flowstorm-border rounded px-2 py-1 text-[10px] text-flowstorm-muted">
            {nodes.length} node{nodes.length !== 1 && "s"} / {edges.length} edge{edges.length !== 1 && "s"}
          </div>
        )}
      </div>

      {/* Node config panel */}
      {selectedNode && (
        <NodeConfigPanel
          node={selectedNode}
          onConfigChange={handleConfigChange}
          onClose={() => {
            setSelectedNode(null);
            selectNode(null);
          }}
        />
      )}

      {/* CSS for animated edges */}
      <style>{`
        @keyframes flowDash {
          to { stroke-dashoffset: -24; }
        }
      `}</style>
    </div>
  );
}
