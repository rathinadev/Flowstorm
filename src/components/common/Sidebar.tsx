type View =
  | "pipeline"
  | "dashboard"
  | "chaos"
  | "lineage"
  | "git"
  | "dlq"
  | "ab";

interface NavItem {
  id: View;
  label: string;
  icon: string;
  description: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "pipeline",
    label: "Pipeline",
    icon: "P",
    description: "Visual DAG editor",
  },
  {
    id: "dashboard",
    label: "Dashboard",
    icon: "D",
    description: "Live metrics & health",
  },
  {
    id: "chaos",
    label: "Chaos",
    icon: "C",
    description: "Chaos engineering",
  },
  {
    id: "lineage",
    label: "Lineage",
    icon: "L",
    description: "Data lineage tracking",
  },
  {
    id: "git",
    label: "Git",
    icon: "G",
    description: "Version history",
  },
  {
    id: "dlq",
    label: "DLQ",
    icon: "Q",
    description: "Dead letter queue",
  },
  {
    id: "ab",
    label: "A/B",
    icon: "AB",
    description: "A/B pipeline testing",
  },
];

interface SidebarProps {
  activeView: View;
  onViewChange: (view: View) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  return (
    <aside className="w-14 bg-flowstorm-surface border-r border-flowstorm-border flex flex-col items-center py-3 gap-1">
      {NAV_ITEMS.map((item) => {
        const isActive = activeView === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            title={`${item.label} - ${item.description}`}
            className={`w-10 h-10 rounded-lg flex flex-col items-center justify-center transition-all group relative ${
              isActive
                ? "bg-flowstorm-primary/20 text-flowstorm-primary"
                : "text-flowstorm-muted hover:text-flowstorm-text hover:bg-flowstorm-bg"
            }`}
          >
            <span
              className={`text-xs font-bold ${
                isActive ? "text-flowstorm-primary" : ""
              }`}
            >
              {item.icon}
            </span>
            <span className="text-[8px] mt-0.5">{item.label}</span>

            {/* Tooltip */}
            <div className="absolute left-full ml-2 px-2 py-1 bg-flowstorm-surface border border-flowstorm-border rounded text-xs text-flowstorm-text whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
              {item.description}
            </div>
          </button>
        );
      })}
    </aside>
  );
}

export type { View };
