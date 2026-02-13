export interface WorkerMetrics {
  worker_id: string;
  node_id: string;
  cpu_percent: number;
  memory_percent: number;
  events_per_second: number;
  events_processed: number;
  avg_latency_ms: number;
  errors: number;
  timestamp: string;
}

export interface WorkerHealth {
  worker_id: string;
  node_id: string;
  operator_type: string;
  status: string;
  health_score: number;
  metrics: WorkerMetrics;
  issues: string[];
}

export interface PipelineMetrics {
  workers: Record<string, WorkerMetrics>;
  total_events_per_second: number;
  total_events_processed: number;
  active_workers: number;
}

export interface HealingEvent {
  action: string;
  trigger: string;
  target_node_id: string | null;
  details: string;
  events_replayed: number;
  duration_ms: number;
  success: boolean;
  timestamp: string;
}

export interface ChaosEvent {
  scenario: string;
  target: string;
  description: string;
  severity: string;
  timestamp: string;
}

export interface OptimizationEvent {
  optimization_type: string;
  description: string;
  estimated_gain: string;
  workers_added: number;
  workers_removed: number;
  duration_ms: number;
}

export type HealthStatus = "healthy" | "degraded" | "critical" | "dead";

export function getHealthStatus(score: number): HealthStatus {
  if (score >= 70) return "healthy";
  if (score >= 30) return "degraded";
  if (score > 0) return "critical";
  return "dead";
}

export const HEALTH_COLORS: Record<HealthStatus, string> = {
  healthy: "#22c55e",
  degraded: "#f59e0b",
  critical: "#ef4444",
  dead: "#6b7280",
};
