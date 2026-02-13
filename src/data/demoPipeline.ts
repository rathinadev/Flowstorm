/**
 * Default demo pipeline - IoT Temperature Monitor.
 *
 * Node IDs match the backend demo simulator exactly so that
 * metrics flow to the correct nodes when the demo starts.
 */

import type { Node, Edge } from "reactflow";
import { getNodeType } from "../types/pipeline";
import type { OperatorType } from "../types/pipeline";

interface DemoNodeDef {
  id: string;
  label: string;
  operatorType: OperatorType;
  x: number;
  y: number;
}

const DEMO_NODES: DemoNodeDef[] = [
  { id: "src-mqtt",    label: "MQTT Source",       operatorType: "mqtt_source",    x: 50,  y: 200 },
  { id: "flt-temp",    label: "Temp > 30\u00B0C",  operatorType: "filter",         x: 300, y: 200 },
  { id: "map-enrich",  label: "Enrich Location",   operatorType: "map",            x: 550, y: 200 },
  { id: "win-5m",      label: "5min Window",       operatorType: "window",         x: 800, y: 200 },
  { id: "agg-avg",     label: "Avg Temperature",   operatorType: "aggregate",      x: 1050, y: 200 },
  { id: "sink-redis",  label: "Redis Sink",        operatorType: "redis_sink",     x: 1300, y: 100 },
  { id: "sink-alert",  label: "Alert Sink",        operatorType: "alert_sink",     x: 1300, y: 300 },
];

const DEMO_EDGES_DEF = [
  { source: "src-mqtt",   target: "flt-temp" },
  { source: "flt-temp",   target: "map-enrich" },
  { source: "map-enrich", target: "win-5m" },
  { source: "win-5m",     target: "agg-avg" },
  { source: "agg-avg",    target: "sink-redis" },
  { source: "agg-avg",    target: "sink-alert" },
];

export function getDemoNodes(): Node[] {
  return DEMO_NODES.map((n) => ({
    id: n.id,
    type: "flowstorm",
    position: { x: n.x, y: n.y },
    data: {
      label: n.label,
      operatorType: n.operatorType,
      nodeType: getNodeType(n.operatorType),
      nodeId: n.id,
      config: {},
    },
  }));
}

export function getDemoEdges(): Edge[] {
  return DEMO_EDGES_DEF.map((e, i) => ({
    id: `e-demo-${i}`,
    source: e.source,
    target: e.target,
    type: "flowstorm",
    animated: true,
  }));
}
