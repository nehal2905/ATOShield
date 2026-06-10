import type { SimulateInput } from "../api/types";

interface Props {
  value: SimulateInput;
  onChange: (v: SimulateInput) => void;
  onRun: () => void;
  busy: boolean;
}

function Slider({
  label, min, max, step, value, unit, onChange,
}: {
  label: string; min: number; max: number; step: number; value: number; unit?: string;
  onChange: (n: number) => void;
}) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-accent">
          {value}
          {unit ?? ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-accent"
      />
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: number; onChange: (n: number) => void }) {
  const on = value >= 1;
  return (
    <button
      type="button"
      onClick={() => onChange(on ? 0 : 1)}
      className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
        on ? "border-accent/50 bg-accent/10 text-accent" : "border-edge text-slate-400"
      }`}
    >
      <span>{label}</span>
      <span className={`h-4 w-8 rounded-full p-0.5 ${on ? "bg-accent" : "bg-edge"}`}>
        <span className={`block h-3 w-3 rounded-full bg-ink transition ${on ? "translate-x-4" : ""}`} />
      </span>
    </button>
  );
}

const PRESETS: Record<string, SimulateInput> = {
  Normal: { login_hour: 14, ip_change: 0, device_change: 0, frequency: 1, geo_velocity: 0, failed_attempts: 0 },
  "Credential stuffing": { login_hour: 3, ip_change: 1, device_change: 1, frequency: 30, geo_velocity: 0, failed_attempts: 18 },
  "Impossible travel": { login_hour: 11, ip_change: 1, device_change: 1, frequency: 2, geo_velocity: 3200, failed_attempts: 0 },
  "New device (odd hr)": { login_hour: 3, ip_change: 1, device_change: 1, frequency: 1, geo_velocity: 50, failed_attempts: 1 },
};

export function SimulationControls({ value, onChange, onRun, busy }: Props) {
  const set = (patch: Partial<SimulateInput>) => onChange({ ...value, ...patch });

  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-5">
      <h3 className="mb-4 font-semibold">Simulation controls</h3>

      <div className="mb-4 flex flex-wrap gap-2">
        {Object.entries(PRESETS).map(([name, preset]) => (
          <button
            key={name}
            onClick={() => onChange(preset)}
            className="rounded-full border border-edge px-3 py-1 text-xs text-slate-300 hover:bg-white/5"
          >
            {name}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        <Slider label="Login hour" min={0} max={23} step={1} value={value.login_hour} unit="h"
          onChange={(n) => set({ login_hour: n })} />
        <Slider label="Login frequency (per hr)" min={0} max={60} step={1} value={value.frequency}
          onChange={(n) => set({ frequency: n })} />
        <Slider label="Geo-velocity" min={0} max={5000} step={50} value={value.geo_velocity} unit=" km/h"
          onChange={(n) => set({ geo_velocity: n })} />
        <Slider label="Failed attempts" min={0} max={30} step={1} value={value.failed_attempts}
          onChange={(n) => set({ failed_attempts: n })} />
        <div className="grid grid-cols-2 gap-2">
          <Toggle label="New IP" value={value.ip_change} onChange={(n) => set({ ip_change: n })} />
          <Toggle label="New device" value={value.device_change} onChange={(n) => set({ device_change: n })} />
        </div>
      </div>

      <button
        onClick={onRun}
        disabled={busy}
        className="mt-5 w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-ink hover:brightness-110 disabled:opacity-60"
      >
        {busy ? "Scoring…" : "Run through model"}
      </button>
    </div>
  );
}
