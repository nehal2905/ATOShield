import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

const LABELS: Record<string, string> = {
  hour_sin: "Hour",
  hour_cos: "Hour°",
  ip_change: "New IP",
  device_change: "New Device",
  frequency: "Frequency",
  geo_velocity: "Geo-velocity",
  failed_attempts: "Failed",
};

export function BehaviorRadar({ contributions }: { contributions: Record<string, number> }) {
  const entries = Object.entries(contributions);
  const max = Math.max(1e-6, ...entries.map(([, v]) => Math.abs(v)));
  const data = entries.map(([k, v]) => ({
    feature: LABELS[k] ?? k,
    value: Math.abs(v) / max,
  }));

  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <h3 className="mb-2 font-semibold">Why flagged — behavior radar</h3>
      <p className="mb-2 text-xs text-slate-500">
        Per-feature attribution (SHAP) for the most recent / selected event.
      </p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="75%">
            <PolarGrid stroke="#243049" />
            <PolarAngleAxis dataKey="feature" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Radar
              dataKey="value"
              stroke="#38bdf8"
              fill="#38bdf8"
              fillOpacity={0.35}
              isAnimationActive
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
