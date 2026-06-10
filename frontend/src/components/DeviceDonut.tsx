import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  distribution: { known: number; new: number };
}

const COLORS = ["#22c55e", "#f97316"];

export function DeviceDonut({ distribution }: Props) {
  const data = [
    { name: "Known device", value: distribution?.known ?? 0 },
    { name: "New device", value: distribution?.new ?? 0 },
  ];
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <h3 className="mb-2 font-semibold">Device distribution (24h)</h3>
      <div className="relative h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="55%"
              outerRadius="80%"
              paddingAngle={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i]} stroke="#0a0e17" />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#0a0e17", border: "1px solid #243049", borderRadius: 8 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold">{total}</span>
          <span className="text-xs text-slate-500">events</span>
        </div>
      </div>
      <div className="mt-2 flex justify-center gap-4 text-xs text-slate-400">
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: COLORS[0] }} />Known</span>
        <span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: COLORS[1] }} />New</span>
      </div>
    </div>
  );
}
