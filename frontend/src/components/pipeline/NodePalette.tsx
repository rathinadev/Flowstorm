import { OPERATOR_LABELS, NODE_COLORS, type OperatorType, getNodeType } from "../../types/pipeline";

const PALETTE_GROUPS = [
  {
    title: "Sources",
    items: [
      { type: "mqtt_source" as OperatorType, icon: "S" },
      { type: "simulator_source" as OperatorType, icon: "S" },
    ],
  },
  {
    title: "Operators",
    items: [
      { type: "filter" as OperatorType, icon: "F" },
      { type: "map" as OperatorType, icon: "M" },
      { type: "window" as OperatorType, icon: "W" },
      { type: "aggregate" as OperatorType, icon: "A" },
      { type: "join" as OperatorType, icon: "J" },
    ],
  },
  {
    title: "Sinks",
    items: [
      { type: "console_sink" as OperatorType, icon: "C" },
      { type: "redis_sink" as OperatorType, icon: "R" },
      { type: "alert_sink" as OperatorType, icon: "!" },
      { type: "webhook_sink" as OperatorType, icon: "W" },
    ],
  },
];

interface NodePaletteProps {
  onDragStart: (operatorType: OperatorType) => void;
}

export function NodePalette({ onDragStart }: NodePaletteProps) {
  return (
    <div className="w-56 bg-flowstorm-surface border-r border-flowstorm-border p-4 overflow-y-auto">
      <h3 className="text-xs font-bold uppercase tracking-wider text-flowstorm-muted mb-4">
        Node Palette
      </h3>

      {PALETTE_GROUPS.map((group) => (
        <div key={group.title} className="mb-4">
          <h4 className="text-xs font-semibold text-flowstorm-muted mb-2">
            {group.title}
          </h4>
          <div className="space-y-1.5">
            {group.items.map((item) => {
              const nodeType = getNodeType(item.type);
              const color = NODE_COLORS[nodeType];
              return (
                <div
                  key={item.type}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("operator_type", item.type);
                    e.dataTransfer.effectAllowed = "move";
                    onDragStart(item.type);
                  }}
                  className="flex items-center gap-2 px-3 py-2 rounded-md
                    border border-flowstorm-border cursor-grab
                    hover:border-flowstorm-primary hover:bg-flowstorm-bg
                    active:cursor-grabbing transition-colors"
                >
                  <div
                    className="w-6 h-6 rounded flex items-center justify-center text-xs font-bold text-white"
                    style={{ backgroundColor: color }}
                  >
                    {item.icon}
                  </div>
                  <span className="text-xs text-flowstorm-text">
                    {OPERATOR_LABELS[item.type]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
