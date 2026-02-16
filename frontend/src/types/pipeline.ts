export type NodeType = "source" | "operator" | "sink";

export type OperatorType =
  | "mqtt_source"
  | "http_source"
  | "simulator_source"
  | "filter"
  | "map"
  | "window"
  | "join"
  | "aggregate"
  | "console_sink"
  | "redis_sink"
  | "alert_sink"
  | "webhook_sink";

export interface OperatorConfig {
  field?: string;
  condition?: string;
  value?: number | string;
  expression?: string;
  output_field?: string;
  window_type?: string;
  window_size_seconds?: number;
  slide_interval_seconds?: number;
  agg_function?: string;
  agg_field?: string;
  group_by?: string;
  join_stream?: string;
  join_key?: string;
  join_window_seconds?: number;
  mqtt_topic?: string;
  mqtt_broker?: string;
  mqtt_port?: number;
  alert_channel?: string;
  alert_webhook_url?: string;
  alert_message_template?: string;
  sensor_count?: number;
  interval_ms?: number;
  chaos_enabled?: boolean;
}

export interface PipelineNode {
  id: string;
  label: string;
  operator_type: OperatorType;
  node_type: NodeType;
  config: OperatorConfig;
  position_x: number;
  position_y: number;
  worker_id?: string;
  parallelism: number;
}

export interface PipelineEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  stream_key?: string;
}

export type PipelineStatus =
  | "draft"
  | "deploying"
  | "running"
  | "paused"
  | "failed"
  | "stopped";

export interface Pipeline {
  id: string;
  name: string;
  description: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  status: PipelineStatus;
  version: number;
}

export interface PipelineVersion {
  version_id: number;
  trigger: string;
  description: string;
  timestamp: string;
  node_count: number;
  edge_count: number;
}

export interface PipelineDiff {
  version_from: number;
  version_to: number;
  summary: string;
  stats: {
    nodes_added: number;
    nodes_removed: number;
    nodes_modified: number;
    edges_added: number;
    edges_removed: number;
  };
  node_diffs: Array<{
    node_id: string;
    label: string;
    change_type: string;
    config_changes: Record<string, { old: unknown; new: unknown }>;
    position_changed: boolean;
  }>;
  edge_diffs: Array<{
    edge_id: string;
    source_id: string;
    target_id: string;
    change_type: string;
  }>;
}

export function getNodeType(operatorType: OperatorType): NodeType {
  const sources: OperatorType[] = [
    "mqtt_source",
    "http_source",
    "simulator_source",
  ];
  const sinks: OperatorType[] = [
    "console_sink",
    "redis_sink",
    "alert_sink",
    "webhook_sink",
  ];
  if (sources.includes(operatorType)) return "source";
  if (sinks.includes(operatorType)) return "sink";
  return "operator";
}

export const OPERATOR_LABELS: Record<OperatorType, string> = {
  mqtt_source: "MQTT Source",
  http_source: "HTTP Source",
  simulator_source: "Simulator",
  filter: "Filter",
  map: "Map",
  window: "Window",
  join: "Join",
  aggregate: "Aggregate",
  console_sink: "Console",
  redis_sink: "Redis Store",
  alert_sink: "Alert",
  webhook_sink: "Webhook",
};

export const NODE_COLORS: Record<NodeType, string> = {
  source: "#3b82f6",
  operator: "#8b5cf6",
  sink: "#22c55e",
};
