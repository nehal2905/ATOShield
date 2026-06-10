interface Props {
  label: string;
  value: number | string;
  hint?: string;
  accent?: string;
  icon?: string;
}

export function StatCard({ label, value, hint, accent = "#38bdf8", icon }: Props) {
  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className="mt-2 text-3xl font-semibold" style={{ color: accent }}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}
