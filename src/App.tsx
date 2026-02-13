import { useState, useEffect, useCallback } from "react";
import { Header } from "./components/common/Header";
import { Sidebar, type View } from "./components/common/Sidebar";
import { PipelineEditor } from "./components/pipeline/PipelineEditor";
import { Dashboard } from "./components/dashboard/Dashboard";
import { ChaosPanel } from "./components/chaos/ChaosPanel";
import { LineagePanel } from "./components/lineage/LineagePanel";
import { VersionHistory } from "./components/git/VersionHistory";
import { DLQPanel } from "./components/dlq/DLQPanel";
import { ABTestPanel } from "./components/ab/ABTestPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { api } from "./services/api";

const VALID_VIEWS: View[] = ["pipeline", "dashboard", "chaos", "lineage", "git", "dlq", "ab"];

function getInitialView(): View {
  const hash = window.location.hash.replace("#", "");
  if (VALID_VIEWS.includes(hash as View)) return hash as View;
  return "pipeline";
}

function App() {
  const [activeView, setActiveView] = useState<View>(getInitialView);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [pipelineStatus, setPipelineStatus] = useState<string>("draft");

  useEffect(() => {
    window.location.hash = activeView;
  }, [activeView]);

  // Connect WebSocket when pipeline is active
  useWebSocket(pipelineId);

  const handleDeploy = useCallback(
    async (nodes: Array<{
      id: string;
      label: string;
      operator_type: string;
      config: Record<string, unknown>;
      position_x: number;
      position_y: number;
    }>, edges: Array<{ source_node_id: string; target_node_id: string }>) => {
      setPipelineStatus("deploying");
      try {
        const result = await api.createPipeline({
          name: pipelineName,
          description: "",
          nodes,
          edges,
        }) as { id: string; status: string };
        setPipelineId(result.id);
        setPipelineStatus(result.status || "running");
      } catch (err) {
        setPipelineStatus("failed");
        console.error("Deploy failed:", err);
      }
    },
    [pipelineName]
  );

  const handleStop = useCallback(async () => {
    if (!pipelineId) return;
    try {
      await api.deletePipeline(pipelineId);
      setPipelineId(null);
      setPipelineStatus("stopped");
    } catch (err) {
      console.error("Stop failed:", err);
    }
  }, [pipelineId]);

  const renderView = () => {
    switch (activeView) {
      case "pipeline":
        return (
          <PipelineEditor
            onDeploy={handleDeploy}
            onStop={handleStop}
            pipelineId={pipelineId}
            pipelineStatus={pipelineStatus}
          />
        );
      case "dashboard":
        return <Dashboard />;
      case "chaos":
        return <ChaosPanel pipelineId={pipelineId} />;
      case "lineage":
        return <LineagePanel pipelineId={pipelineId} />;
      case "git":
        return <VersionHistory pipelineId={pipelineId} />;
      case "dlq":
        return <DLQPanel pipelineId={pipelineId} />;
      case "ab":
        return <ABTestPanel pipelineId={pipelineId} />;
      default:
        return (
          <PipelineEditor
            onDeploy={handleDeploy}
            onStop={handleStop}
            pipelineId={pipelineId}
            pipelineStatus={pipelineStatus}
          />
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-flowstorm-bg text-flowstorm-text overflow-hidden">
      <Header
        pipelineId={pipelineId}
        pipelineName={pipelineName}
        pipelineStatus={pipelineStatus}
        onNameChange={setPipelineName}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeView={activeView} onViewChange={setActiveView} />
        <main className="flex-1 overflow-hidden">{renderView()}</main>
      </div>
    </div>
  );
}

export default App;
