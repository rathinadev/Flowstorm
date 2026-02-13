import { MetricsPanel } from "./MetricsPanel";
import { HealthPanel } from "./HealthPanel";
import { HealingLog } from "./HealingLog";
import { OptimizationLog } from "./OptimizationLog";

export function Dashboard() {
  return (
    <div className="grid grid-cols-2 gap-4 p-4 h-full overflow-y-auto">
      <MetricsPanel />
      <HealthPanel />
      <HealingLog />
      <OptimizationLog />
    </div>
  );
}
