export type WSMessageType =
  | "pipeline.metrics"
  | "pipeline.deployed"
  | "pipeline.stopped"
  | "health.alert"
  | "worker.spawned"
  | "worker.died"
  | "worker.recovered"
  | "worker.scaled"
  | "worker.stopped"
  | "optimizer.applied"
  | "chaos.started"
  | "chaos.stopped"
  | "chaos.event"
  | "chaos.healed"
  | "nlp.result"
  | "pipeline_git.version"
  | "pong"
  | "subscribed";

export interface WSMessage {
  type: WSMessageType;
  pipeline_id?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}
