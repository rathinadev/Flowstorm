import { useEffect, useRef } from "react";
import { wsClient } from "../services/websocket";
import { useMetricsStore } from "../store/metricsStore";
import { useChaosStore } from "../store/chaosStore";
import type { WSMessage } from "../types/websocket";
import type { PipelineMetrics, ChaosEvent, OptimizationEvent } from "../types/metrics";

export function useWebSocket(pipelineId: string | null) {
  const cleanupRef = useRef<(() => void) | null>(null);
  const setMetrics = useMetricsStore((s) => s.setMetrics);
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
          setMetrics(msg.data as unknown as PipelineMetrics);
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
  }, [pipelineId, setMetrics, addHealingEvent, addOptimizationEvent, addChaosEvent, setChaosActive]);

  return { connected: wsClient.connected };
}
