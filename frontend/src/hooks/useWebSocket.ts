import { useEffect, useRef } from "react";
import { wsClient } from "../services/websocket";
import { useMetricsStore } from "../store/metricsStore";
import { useChaosStore } from "../store/chaosStore";
import type { WSMessage } from "../types/websocket";
import type { PipelineMetrics, ChaosEvent, OptimizationEvent } from "../types/metrics";

export function useWebSocket(pipelineId: string | null) {
  const cleanupRef = useRef<(() => void) | null>(null);
  const setMetrics = useMetricsStore((s) => s.setMetrics);
  const setWorkerHealth = useMetricsStore((s) => s.setWorkerHealth);
  const addHealingEvent = useMetricsStore((s) => s.addHealingEvent);
  const addOptimizationEvent = useMetricsStore((s) => s.addOptimizationEvent);
  const addChaosEvent = useChaosStore((s) => s.addEvent);
  const setChaosActive = useChaosStore((s) => s.setActive);

  useEffect(() => {
    if (!pipelineId) return;

    wsClient.connect(pipelineId);

    const unsubs: Array<() => void> = [];

    unsubs.push(
      wsClient.on("pipeline.metrics", (msg: WSMessage) => {
        if (msg.data) {
          const metrics = msg.data as unknown as PipelineMetrics;
          setMetrics(metrics);

          // Derive worker health from metrics and update store
          if (metrics.workers) {
            for (const [workerId, wm] of Object.entries(metrics.workers)) {
              const cpuScore = Math.max(0, 100 - wm.cpu_percent);
              const memScore = wm.memory_percent < 60 ? 100 : Math.max(0, 100 - (wm.memory_percent - 60) * 2.5);
              const latScore = wm.avg_latency_ms < 50 ? 100 : wm.avg_latency_ms < 500 ? 100 - ((wm.avg_latency_ms - 50) / 450) * 100 : 0;
              const score = cpuScore * 0.3 + memScore * 0.3 + 100 * 0.2 + latScore * 0.2;

              const issues: string[] = [];
              if (wm.cpu_percent > 80) issues.push(`High CPU: ${wm.cpu_percent.toFixed(0)}%`);
              if (wm.memory_percent > 75) issues.push(`High memory: ${wm.memory_percent.toFixed(0)}%`);
              if (wm.avg_latency_ms > 200) issues.push(`High latency: ${wm.avg_latency_ms.toFixed(0)}ms`);

              setWorkerHealth(workerId, {
                worker_id: workerId,
                node_id: wm.node_id,
                operator_type: "",
                status: score >= 70 ? "running" : score >= 30 ? "degraded" : "critical",
                health_score: Math.round(score * 10) / 10,
                metrics: wm,
                issues,
              });
            }
          }
        }
      })
    );

    unsubs.push(
      wsClient.on("worker.recovered", (msg: WSMessage) => {
        if (msg.data) {
          addHealingEvent({
            action: "failover",
            trigger: `Worker ${(msg.data as Record<string, unknown>).old_worker_id} died`,
            target_node_id: (msg.data as Record<string, unknown>).node_id as string,
            details: `Recovered as ${(msg.data as Record<string, unknown>).new_worker_id}`,
            events_replayed: (msg.data as Record<string, unknown>).events_replayed as number,
            duration_ms: (msg.data as Record<string, unknown>).duration_ms as number,
            success: true,
            timestamp: msg.timestamp || new Date().toISOString(),
          });
        }
      })
    );

    unsubs.push(
      wsClient.on("worker.scaled", (msg: WSMessage) => {
        if (msg.data) {
          addHealingEvent({
            action: "scale_out",
            trigger: "Bottleneck detected",
            target_node_id: (msg.data as Record<string, unknown>).node_id as string,
            details: `Scaled from ${(msg.data as Record<string, unknown>).old_count} to ${(msg.data as Record<string, unknown>).new_count}`,
            events_replayed: 0,
            duration_ms: (msg.data as Record<string, unknown>).duration_ms as number,
            success: true,
            timestamp: msg.timestamp || new Date().toISOString(),
          });
        }
      })
    );

    unsubs.push(
      wsClient.on("optimizer.applied", (msg: WSMessage) => {
        if (msg.data) {
          addOptimizationEvent(msg.data as unknown as OptimizationEvent);
        }
      })
    );

    unsubs.push(
      wsClient.on("chaos.event", (msg: WSMessage) => {
        if (msg.data) {
          addChaosEvent(msg.data as unknown as ChaosEvent);
        }
      })
    );

    unsubs.push(
      wsClient.on("chaos.started", () => setChaosActive(true))
    );

    unsubs.push(
      wsClient.on("chaos.stopped", () => setChaosActive(false))
    );

    cleanupRef.current = () => {
      unsubs.forEach((u) => u());
      wsClient.disconnect();
    };

    return () => {
      cleanupRef.current?.();
    };
  }, [pipelineId, setMetrics, setWorkerHealth, addHealingEvent, addOptimizationEvent, addChaosEvent, setChaosActive]);

  return { connected: wsClient.connected };
}
