import { useState, useEffect } from "react";
import type { Node } from "reactflow";
import { NODE_COLORS, type OperatorType, type NodeType } from "../../types/pipeline";

interface ConfigField {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  placeholder?: string;
  options?: Array<{ value: string; label: string }>;
}

const OPERATOR_FIELDS: Record<string, ConfigField[]> = {
  mqtt_source: [
    { key: "mqtt_topic", label: "MQTT Topic", type: "text", placeholder: "sensors/temperature" },
    { key: "mqtt_broker", label: "Broker Host", type: "text", placeholder: "localhost" },
    { key: "mqtt_port", label: "Broker Port", type: "number", placeholder: "1883" },
  ],
  simulator_source: [
    { key: "sensor_count", label: "Sensor Count", type: "number", placeholder: "50" },
    { key: "interval_ms", label: "Interval (ms)", type: "number", placeholder: "100" },
    {
      key: "chaos_enabled",
      label: "Chaos Data",
      type: "select",
      options: [
        { value: "false", label: "Disabled" },
        { value: "true", label: "Enabled" },
      ],
    },
  ],
  http_source: [
    { key: "http_port", label: "Listen Port", type: "number", placeholder: "9090" },
    { key: "http_path", label: "Endpoint Path", type: "text", placeholder: "/ingest" },
  ],
  filter: [
    { key: "field", label: "Field Name", type: "text", placeholder: "temperature" },
    {
      key: "condition",
      label: "Condition",
      type: "select",
      options: [
        { value: "gt", label: "> Greater than" },
        { value: "gte", label: ">= Greater or equal" },
        { value: "lt", label: "< Less than" },
        { value: "lte", label: "<= Less or equal" },
        { value: "eq", label: "= Equals" },
        { value: "neq", label: "!= Not equals" },
        { value: "contains", label: "Contains" },
      ],
    },
    { key: "value", label: "Value", type: "text", placeholder: "30" },
  ],
  map: [
    { key: "expression", label: "Expression", type: "text", placeholder: "value * 1.8 + 32" },
    { key: "output_field", label: "Output Field", type: "text", placeholder: "temperature_f" },
  ],
  window: [
    {
      key: "window_type",
      label: "Window Type",
      type: "select",
      options: [
        { value: "tumbling", label: "Tumbling" },
        { value: "sliding", label: "Sliding" },
        { value: "session", label: "Session" },
      ],
    },
    { key: "window_size_seconds", label: "Window Size (s)", type: "number", placeholder: "60" },
    { key: "slide_interval_seconds", label: "Slide Interval (s)", type: "number", placeholder: "10" },
  ],
  aggregate: [
    {
      key: "agg_function",
      label: "Function",
      type: "select",
      options: [
        { value: "avg", label: "Average" },
        { value: "sum", label: "Sum" },
        { value: "min", label: "Min" },
        { value: "max", label: "Max" },
        { value: "count", label: "Count" },
      ],
    },
    { key: "agg_field", label: "Field", type: "text", placeholder: "temperature" },
    { key: "group_by", label: "Group By", type: "text", placeholder: "sensor_id" },
  ],
  join: [
    { key: "join_stream", label: "Join Stream", type: "text", placeholder: "stream:enrichment" },
    { key: "join_key", label: "Join Key", type: "text", placeholder: "sensor_id" },
    { key: "join_window_seconds", label: "Window (s)", type: "number", placeholder: "30" },
  ],
  console_sink: [],
  redis_sink: [
    { key: "redis_key_prefix", label: "Key Prefix", type: "text", placeholder: "flowstorm:output" },
  ],
  alert_sink: [
    {
      key: "alert_channel",
      label: "Channel",
      type: "select",
      options: [
        { value: "console", label: "Console" },
        { value: "webhook", label: "Webhook" },
      ],
    },
    { key: "alert_webhook_url", label: "Webhook URL", type: "text", placeholder: "https://..." },
    { key: "alert_message_template", label: "Message Template", type: "text", placeholder: "Alert: {{field}} = {{value}}" },
  ],
  webhook_sink: [
    { key: "webhook_url", label: "Webhook URL", type: "text", placeholder: "https://..." },
  ],
};

interface NodeConfigPanelProps {
  node: Node;
  onConfigChange: (nodeId: string, config: Record<string, unknown>) => void;
  onClose: () => void;
}

export function NodeConfigPanel({ node, onConfigChange, onClose }: NodeConfigPanelProps) {
  const operatorType = node.data.operatorType as OperatorType;
  const nodeType = node.data.nodeType as NodeType;
  const fields = OPERATOR_FIELDS[operatorType] || [];
  const [config, setConfig] = useState<Record<string, unknown>>(node.data.config || {});

  // Reset config when node changes
  useEffect(() => {
    setConfig(node.data.config || {});
  }, [node.id, node.data.config]);

  const handleChange = (key: string, value: string) => {
    const field = fields.find((f) => f.key === key);
    let parsed: unknown = value;
    if (field?.type === "number" && value !== "") {
      parsed = Number(value);
    }
    const updated = { ...config, [key]: parsed };
    setConfig(updated);
    onConfigChange(node.id, updated);
  };

  const borderColor = NODE_COLORS[nodeType] || "#8b5cf6";

  return (
    <div className="w-72 bg-flowstorm-surface border-l border-flowstorm-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-flowstorm-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: borderColor }}
          />
          <span className="text-xs font-bold text-flowstorm-text">
            Configure Node
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-flowstorm-muted hover:text-flowstorm-text text-sm transition-colors"
        >
          x
        </button>
      </div>

      {/* Node info */}
      <div className="px-3 py-2 border-b border-flowstorm-border">
        <div className="text-sm font-semibold text-flowstorm-text">
          {node.data.label}
        </div>
        <div
          className="text-[10px] font-bold uppercase tracking-wider mt-0.5"
          style={{ color: borderColor }}
        >
          {nodeType} / {operatorType}
        </div>
        <div className="text-[10px] text-flowstorm-muted mt-1">
          ID: {node.id}
        </div>
      </div>

      {/* Config fields */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {fields.length === 0 && (
          <div className="text-xs text-flowstorm-muted text-center py-4">
            No configuration needed for this operator.
          </div>
        )}

        {fields.map((field) => (
          <div key={field.key}>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-flowstorm-muted block mb-1">
              {field.label}
            </label>

            {field.type === "select" ? (
              <select
                value={String(config[field.key] ?? "")}
                onChange={(e) => handleChange(field.key, e.target.value)}
                className="w-full bg-flowstorm-bg border border-flowstorm-border rounded px-2 py-1.5 text-xs text-flowstorm-text outline-none focus:border-flowstorm-primary transition-colors"
              >
                <option value="">Select...</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.type}
                value={String(config[field.key] ?? "")}
                onChange={(e) => handleChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                className="w-full bg-flowstorm-bg border border-flowstorm-border rounded px-2 py-1.5 text-xs text-flowstorm-text placeholder:text-flowstorm-muted/50 outline-none focus:border-flowstorm-primary transition-colors"
              />
            )}
          </div>
        ))}
      </div>

      {/* Footer hint */}
      <div className="p-3 border-t border-flowstorm-border">
        <div className="text-[10px] text-flowstorm-muted">
          Click the canvas to deselect. Config is saved automatically.
        </div>
      </div>
    </div>
  );
}
