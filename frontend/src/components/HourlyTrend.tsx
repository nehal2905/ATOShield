import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function HourlyTrend({ hourly }: { hourly: number[] }) {
  const data = (hourly ?? []).map((count, hour) => ({ hour: `${hour}`, count }));
  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <h3 className="mb-2 font-semibold">Logins by hour (24h)</h3>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -22 }}>
            <CartesianGrid vertical={false} stroke="#1e293b" />
            <XAxis dataKey="hour" tick={{ fill: "#64748b", fontSize: 10 }} interval={1} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: "#0a0e17", border: "1px solid #243049", borderRadius: 8 }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Bar dataKey="count" fill="#38bdf8" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
