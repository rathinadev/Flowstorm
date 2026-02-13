import { useState } from "react";
import { Header } from "./components/common/Header";
import { Sidebar, type View } from "./components/common/Sidebar";
import { PipelineEditor } from "./components/pipeline/PipelineEditor";
import { Dashboard } from "./components/dashboard/Dashboard";
import { ChaosPanel } from "./components/chaos/ChaosPanel";
import { NLPChat } from "./components/nlp/NLPChat";
import { LineagePanel } from "./components/lineage/LineagePanel";
import { VersionHistory } from "./components/git/VersionHistory";
import { useWebSocket } from "./hooks/useWebSocket";

function App() {
  const [activeView, setActiveView] = useState<View>("pipeline");
  const [pipelineId] = useState<string | null>(null);
  const [pipelineName] = useState("Demo Pipeline");

  // Connect WebSocket when pipeline is active
  useWebSocket(pipelineId);

  const renderView = () => {
    switch (activeView) {
      case "pipeline":
        return <PipelineEditor />;
      case "dashboard":
        return <Dashboard />;
      case "chaos":
        return <ChaosPanel pipelineId={pipelineId} />;
      case "nlp":
        return <NLPChat pipelineId={pipelineId} />;
      case "lineage":
        return <LineagePanel pipelineId={pipelineId} />;
      case "git":
        return <VersionHistory pipelineId={pipelineId} />;
      default:
        return <PipelineEditor />;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-flowstorm-bg text-flowstorm-text overflow-hidden">
      <Header pipelineId={pipelineId} pipelineName={pipelineName} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeView={activeView} onViewChange={setActiveView} />
        <main className="flex-1 overflow-hidden">{renderView()}</main>
      </div>
    </div>
  );
}

export default App;
