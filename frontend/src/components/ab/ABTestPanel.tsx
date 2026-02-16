import { useState, useEffect } from "react";
import { api } from "../../services/api";

interface ABTest {
  test_id: string;
  name: string;
  pipeline_a: string;
  pipeline_b: string;
  split_percent_a: number;
  samples_a: number;
  samples_b: number;
}

interface ABTestResult {
  test_id: string;
  name: string;
  version_a: {
    pipeline_id: string;
    avg_throughput_eps: number;
    avg_latency_ms: number;
    total_events: number;
    error_count: number;
    avg_cpu_percent: number;
    avg_memory_percent: number;
    samples: number;
  };
  version_b: {
    pipeline_id: string;
    avg_throughput_eps: number;
    avg_latency_ms: number;
    total_events: number;
    error_count: number;
    avg_cpu_percent: number;
    avg_memory_percent: number;
    samples: number;
  };
  winner: string | null;
  summary: string;
  duration_seconds: number;
}

interface ABTestPanelProps {
  pipelineId: string | null;
}

export function ABTestPanel({ pipelineId }: ABTestPanelProps) {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [selectedResult, setSelectedResult] = useState<ABTestResult | null>(null);
  const [creating, setCreating] = useState(false);
  const [pipelineIdB, setPipelineIdB] = useState("");
  const [splitPercent, setSplitPercent] = useState(50);
  const [testName, setTestName] = useState("");

  useEffect(() => {
    loadTests();
  }, []);

  const loadTests = async () => {
    try {
      const res = await api.listABTests();
      setTests(res.tests as unknown as ABTest[]);
    } catch {
      // May not have tests yet
    }
  };

  const handleCreate = async () => {
    if (!pipelineId || !pipelineIdB) return;
    try {
      await api.createABTest(pipelineId, pipelineIdB, splitPercent, testName);
      setCreating(false);
      setPipelineIdB("");
      setTestName("");
      loadTests();
    } catch (err) {
      console.error("Failed to create A/B test:", err);
    }
  };

  const handleViewResult = async (testId: string) => {
    try {
      const result = (await api.getABTest(testId)) as ABTestResult;
      setSelectedResult(result);
    } catch {
      // Test may have ended
    }
  };

  const handleStop = async (testId: string) => {
    try {
      const result = (await api.stopABTest(testId)) as ABTestResult;
      setSelectedResult(result);
      loadTests();
    } catch {
      // Already stopped
    }
  };

  const MetricBar = ({
    label,
    valueA,
    valueB,
    unit,
    lowerIsBetter = false,
  }: {
    label: string;
    valueA: number;
    valueB: number;
    unit: string;
    lowerIsBetter?: boolean;
  }) => {
    const max = Math.max(valueA, valueB, 1);
    const aWins = lowerIsBetter ? valueA < valueB : valueA > valueB;
    const bWins = lowerIsBetter ? valueB < valueA : valueB > valueA;

    return (
      <div className="space-y-1">
        <div className="text-[10px] text-flowstorm-muted uppercase tracking-wider">
          {label}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] w-6 text-right font-bold text-blue-400">
            A
          </span>
          <div className="flex-1 h-4 bg-flowstorm-bg rounded overflow-hidden">
            <div
              className={`h-full rounded transition-all ${
                aWins ? "bg-green-500/60" : "bg-blue-500/40"
              }`}
              style={{ width: `${(valueA / max) * 100}%` }}
            />
          </div>
          <span
            className={`text-xs font-mono w-20 text-right ${
              aWins ? "text-green-400" : "text-flowstorm-muted"
            }`}
          >
            {valueA.toFixed(1)} {unit}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] w-6 text-right font-bold text-purple-400">
            B
          </span>
          <div className="flex-1 h-4 bg-flowstorm-bg rounded overflow-hidden">
            <div
              className={`h-full rounded transition-all ${
                bWins ? "bg-green-500/60" : "bg-purple-500/40"
              }`}
              style={{ width: `${(valueB / max) * 100}%` }}
            />
          </div>
          <span
            className={`text-xs font-mono w-20 text-right ${
              bWins ? "text-green-400" : "text-flowstorm-muted"
            }`}
          >
            {valueB.toFixed(1)} {unit}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-flowstorm-text">
              A/B Pipeline Testing
            </h2>
            <p className="text-[10px] text-flowstorm-muted mt-0.5">
              Compare two pipeline versions side-by-side
            </p>
          </div>
          <button
            onClick={() => setCreating(!creating)}
            className="px-3 py-1.5 rounded text-xs bg-flowstorm-primary text-white hover:bg-flowstorm-primary/80 transition-colors"
          >
            {creating ? "Cancel" : "New Test"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Create form */}
        {creating && (
          <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4 space-y-3">
            <h3 className="text-xs font-bold text-flowstorm-text">
              Create A/B Test
            </h3>
            <div>
              <label className="text-[10px] text-flowstorm-muted uppercase tracking-wider block mb-1">
                Version A (current)
              </label>
              <div className="text-xs font-mono text-flowstorm-text bg-flowstorm-bg rounded px-2 py-1.5 border border-flowstorm-border">
                {pipelineId || "No pipeline deployed"}
              </div>
            </div>
            <div>
              <label className="text-[10px] text-flowstorm-muted uppercase tracking-wider block mb-1">
                Version B (pipeline ID)
              </label>
              <input
                type="text"
                value={pipelineIdB}
                onChange={(e) => setPipelineIdB(e.target.value)}
                placeholder="Enter pipeline ID for version B"
                className="w-full bg-flowstorm-bg border border-flowstorm-border rounded px-2 py-1.5 text-xs text-flowstorm-text placeholder:text-flowstorm-muted/50 outline-none focus:border-flowstorm-primary"
              />
            </div>
            <div>
              <label className="text-[10px] text-flowstorm-muted uppercase tracking-wider block mb-1">
                Test Name
              </label>
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="Optional name"
                className="w-full bg-flowstorm-bg border border-flowstorm-border rounded px-2 py-1.5 text-xs text-flowstorm-text placeholder:text-flowstorm-muted/50 outline-none focus:border-flowstorm-primary"
              />
            </div>
            <div>
              <label className="text-[10px] text-flowstorm-muted uppercase tracking-wider block mb-1">
                Traffic Split: {splitPercent}% A / {100 - splitPercent}% B
              </label>
              <input
                type="range"
                min={10}
                max={90}
                step={10}
                value={splitPercent}
                onChange={(e) => setSplitPercent(Number(e.target.value))}
                className="w-full"
              />
            </div>
            <button
              onClick={handleCreate}
              disabled={!pipelineId || !pipelineIdB}
              className="w-full px-3 py-2 rounded text-xs font-bold bg-flowstorm-primary text-white hover:bg-flowstorm-primary/80 transition-colors disabled:opacity-50"
            >
              Start A/B Test
            </button>
          </div>
        )}

        {/* Active tests */}
        {tests.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-flowstorm-muted uppercase tracking-wider">
              Active Tests
            </h3>
            {tests.map((test) => (
              <div
                key={test.test_id}
                className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-flowstorm-text">
                    {test.name || test.test_id}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleViewResult(test.test_id)}
                      className="px-2 py-1 rounded text-[10px] bg-flowstorm-bg border border-flowstorm-border text-flowstorm-muted hover:text-flowstorm-text"
                    >
                      Results
                    </button>
                    <button
                      onClick={() => handleStop(test.test_id)}
                      className="px-2 py-1 rounded text-[10px] bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20"
                    >
                      Stop
                    </button>
                  </div>
                </div>
                <div className="flex gap-4 text-[10px] text-flowstorm-muted">
                  <span>A: {test.pipeline_a} ({test.split_percent_a}%)</span>
                  <span>B: {test.pipeline_b} ({100 - test.split_percent_a}%)</span>
                </div>
                <div className="flex gap-4 mt-1 text-[10px] text-flowstorm-muted">
                  <span>Samples: {test.samples_a} / {test.samples_b}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Result comparison */}
        {selectedResult && (
          <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-flowstorm-text">
                {selectedResult.name} - Results
              </h3>
              {selectedResult.winner && (
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded ${
                    selectedResult.winner === "a"
                      ? "text-blue-400 bg-blue-500/10"
                      : "text-purple-400 bg-purple-500/10"
                  }`}
                >
                  Version {selectedResult.winner.toUpperCase()} wins
                </span>
              )}
            </div>

            <div className="space-y-3">
              <MetricBar
                label="Throughput"
                valueA={selectedResult.version_a.avg_throughput_eps}
                valueB={selectedResult.version_b.avg_throughput_eps}
                unit="e/s"
              />
              <MetricBar
                label="Latency"
                valueA={selectedResult.version_a.avg_latency_ms}
                valueB={selectedResult.version_b.avg_latency_ms}
                unit="ms"
                lowerIsBetter
              />
              <MetricBar
                label="CPU Usage"
                valueA={selectedResult.version_a.avg_cpu_percent}
                valueB={selectedResult.version_b.avg_cpu_percent}
                unit="%"
                lowerIsBetter
              />
              <MetricBar
                label="Errors"
                valueA={selectedResult.version_a.error_count}
                valueB={selectedResult.version_b.error_count}
                unit=""
                lowerIsBetter
              />
            </div>

            {selectedResult.summary && (
              <div className="bg-flowstorm-bg rounded p-2 text-xs text-flowstorm-muted">
                {selectedResult.summary}
              </div>
            )}
          </div>
        )}

        {tests.length === 0 && !creating && (
          <div className="bg-flowstorm-surface border border-flowstorm-border rounded-lg p-6 text-center">
            <p className="text-xs text-flowstorm-muted">
              No active A/B tests. Deploy two pipelines and create a test to
              compare them side-by-side.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
