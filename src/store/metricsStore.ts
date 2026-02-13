import { create } from "zustand";
import type {
  PipelineMetrics,
  HealingEvent,
  OptimizationEvent,
  WorkerHealth,
} from "../types/metrics";

interface MetricsState {
  metrics: PipelineMetrics | null;
  workerHealth: Record<string, WorkerHealth>;
  healingLog: HealingEvent[];
  optimizationLog: OptimizationEvent[];
  throughputHistory: Array<{ time: string; eps: number }>;

  setMetrics: (metrics: PipelineMetrics) => void;
  setWorkerHealth: (workerId: string, health: WorkerHealth) => void;
  addHealingEvent: (event: HealingEvent) => void;
  addOptimizationEvent: (event: OptimizationEvent) => void;
  addThroughputSample: (eps: number) => void;
  reset: () => void;
}

export const useMetricsStore = create<MetricsState>((set) => ({
  metrics: null,
  workerHealth: {},
  healingLog: [],
  optimizationLog: [],
  throughputHistory: [],

  setMetrics: (metrics) =>
    set((state) => {
      const now = new Date().toLocaleTimeString();
      const history = [
        ...state.throughputHistory.slice(-60),
        { time: now, eps: metrics.total_events_per_second },
      ];
      return { metrics, throughputHistory: history };
    }),

  setWorkerHealth: (workerId, health) =>
    set((state) => ({
      workerHealth: { ...state.workerHealth, [workerId]: health },
    })),

  addHealingEvent: (event) =>
    set((state) => ({
      healingLog: [event, ...state.healingLog].slice(0, 100),
    })),

  addOptimizationEvent: (event) =>
    set((state) => ({
      optimizationLog: [event, ...state.optimizationLog].slice(0, 50),
    })),

  addThroughputSample: (eps) =>
    set((state) => ({
      throughputHistory: [
        ...state.throughputHistory.slice(-60),
        { time: new Date().toLocaleTimeString(), eps },
      ],
    })),

  reset: () =>
    set({
      metrics: null,
      workerHealth: {},
      healingLog: [],
      optimizationLog: [],
      throughputHistory: [],
    }),
}));
