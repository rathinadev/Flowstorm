import { useState } from "react";
import { useChaosStore } from "../../store/chaosStore";
import { api } from "../../services/api";

const INTENSITIES = [
  {
    value: "low",
    label: "Low",
    description: "Mild disruptions",
    color: "#f59e0b",
  },
  {
    value: "medium",
    label: "Medium",
    description: "Moderate chaos",
    color: "#f97316",
  },
  {
    value: "high",
    label: "High",
    description: "Maximum disruption",
    color: "#ef4444",
  },
];

const SCENARIO_INFO = [
  { name: "Kill Worker", description: "Randomly terminates a running worker container" },
  { name: "Inject Latency", description: "Adds artificial delay to message processing" },
  { name: "Corrupt Events", description: "Sends malformed events into the pipeline" },
  { name: "Memory Pressure", description: "Forces high memory allocation in workers" },
  { name: "Flood Source", description: "Sends burst of events to overwhelm the pipeline" },
  { name: "Network Partition", description: "Simulates network isolation between workers" },
];

interface ChaosPanelProps {
  pipelineId: string | null;
}

export function ChaosPanel({ pipelineId }: ChaosPanelProps) {
  const { active, intensity, events, setActive } = useChaosStore();
  const [selectedIntensity, setSelectedIntensity] = useState(intensity);
  const [duration, setDuration] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    if (!pipelineId) return;
    setLoading(true);
    setError(null);
    try {
      await api.startChaos(pipelineId, selectedIntensity, duration);
      setActive(true, selectedIntensity);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start chaos");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!pipelineId) return;
    setLoading(true);
    try {
      await api.stopChaos(pipelineId);
      setActive(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop chaos");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">&#9888;</span>
            <h2 className="text-sm font-bold text-flowstorm-text">
              Chaos Engineering
            </h2>
          </div>
          {active && (
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-xs text-red-400 font-semibold">
                CHAOS ACTIVE
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!pipelineId && (
          <div className="bg-flowstorm-bg rounded-lg p-4 text-center">
            <p className="text-xs text-flowstorm-muted">
              Deploy a pipeline first to enable chaos testing
            </p>
          </div>
        )}

        {pipelineId && (
          <>
            {/* Controls */}
            <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
              <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-3">
                Configuration
              </h3>

              {/* Intensity selector */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                {INTENSITIES.map((int) => (
                  <button
                    key={int.value}
                    onClick={() => setSelectedIntensity(int.value)}
                    disabled={active}
                    className={`px-3 py-2 rounded-md border text-xs transition-colors ${
                      selectedIntensity === int.value
                        ? "border-flowstorm-primary bg-flowstorm-primary/10 text-flowstorm-primary"
                        : "border-flowstorm-border text-flowstorm-muted hover:border-flowstorm-primary/50"
                    } ${active ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <div className="font-bold">{int.label}</div>
                    <div className="text-[10px] opacity-70">
                      {int.description}
                    </div>
                  </button>
                ))}
              </div>

              {/* Duration */}
              <div className="flex items-center gap-3 mb-4">
                <label className="text-xs text-flowstorm-muted">
                  Duration:
                </label>
                <input
                  type="range"
                  min={15}
                  max={300}
                  step={15}
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  disabled={active}
                  className="flex-1 accent-flowstorm-primary"
                />
                <span className="text-xs font-mono text-flowstorm-text w-10 text-right">
                  {duration}s
                </span>
              </div>

              {/* Start/Stop button */}
              {!active ? (
                <button
                  onClick={handleStart}
                  disabled={loading}
                  className="w-full py-2.5 rounded-md bg-red-600 hover:bg-red-700 text-white text-sm font-bold transition-colors disabled:opacity-50"
                >
                  {loading ? "Starting..." : "Start Chaos"}
                </button>
              ) : (
                <button
                  onClick={handleStop}
                  disabled={loading}
                  className="w-full py-2.5 rounded-md bg-flowstorm-border hover:bg-flowstorm-muted/20 text-flowstorm-text text-sm font-bold transition-colors disabled:opacity-50"
                >
                  {loading ? "Stopping..." : "Stop Chaos"}
                </button>
              )}

              {error && (
                <p className="text-xs text-red-400 mt-2">{error}</p>
              )}
            </div>

            {/* Scenarios info */}
            <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
              <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-3">
                Chaos Scenarios
              </h3>
              <div className="space-y-2">
                {SCENARIO_INFO.map((s) => (
                  <div
                    key={s.name}
                    className="flex gap-2 bg-flowstorm-bg rounded-md px-3 py-2"
                  >
                    <div className="w-1 rounded-full bg-red-500/50 flex-shrink-0" />
                    <div>
                      <div className="text-xs font-semibold text-flowstorm-text">
                        {s.name}
                      </div>
                      <div className="text-[10px] text-flowstorm-muted">
                        {s.description}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Event feed */}
            <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4">
              <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider mb-3">
                Event Feed
              </h3>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {events.length === 0 && (
                  <p className="text-xs text-flowstorm-muted text-center py-4">
                    No chaos events yet
                  </p>
                )}
                {events.map((event, i) => (
                  <div
                    key={`${event.timestamp}-${i}`}
                    className="flex items-start gap-2 bg-flowstorm-bg rounded px-2.5 py-1.5"
                  >
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        event.severity === "high"
                          ? "bg-red-500/20 text-red-400"
                          : event.severity === "medium"
                          ? "bg-yellow-500/20 text-yellow-400"
                          : "bg-blue-500/20 text-blue-400"
                      }`}
                    >
                      {event.severity?.toUpperCase() || "MED"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-flowstorm-text">
                        {event.scenario}
                      </span>
                      <p className="text-[10px] text-flowstorm-muted truncate">
                        {event.description}
                      </p>
                    </div>
                    <span className="text-[10px] text-flowstorm-muted flex-shrink-0">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
