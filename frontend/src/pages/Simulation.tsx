import { useState } from "react";
import { api } from "../api/client";
import type { SimulateInput, SimulateResult } from "../api/types";
import { BehaviorRadar } from "../components/BehaviorRadar";
import { RiskGauge } from "../components/RiskGauge";
import { SimulationControls } from "../components/SimulationControls";
import { TerminalLog } from "../components/TerminalLog";
import { tierBadgeClass } from "../lib/format";

const DEFAULT: SimulateInput = {
  login_hour: 14,
  ip_change: 0,
  device_change: 0,
  frequency: 1,
  geo_velocity: 0,
  failed_attempts: 0,
};

export default function Simulation() {
  const [input, setInput] = useState<SimulateInput>(DEFAULT);
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.simulate(input);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }

  const r = result?.result;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Scoring simulation</h1>
        <p className="text-sm text-slate-400">
          Adjust behavioral signals and run them through the <em>real</em> Isolation Forest.
          The score is computed by the backend model — not a client-side copy.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SimulationControls value={input} onChange={setInput} onRun={run} busy={busy} />

        <div className="lg:col-span-2 space-y-6">
          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="grid gap-6 sm:grid-cols-2">
            <div className="flex flex-col items-center justify-center rounded-2xl border border-edge bg-panel/60 p-4">
              <RiskGauge risk={r?.risk ?? 0} tier={r?.tier ?? "LOW"} />
              {r && (
                <div className="mt-4 text-center">
                  <span className={`rounded px-2 py-1 text-xs font-semibold ${tierBadgeClass(r.tier)}`}>
                    {r.tier}
                  </span>
                  <p className="mt-2 text-sm text-slate-300">{r.action}</p>
                  {r.impossible_travel && (
                    <p className="mt-1 text-xs text-red-400">⚠ impossible travel detected</p>
                  )}
                  <p className="mt-2 text-[11px] text-slate-500">
                    raw decision_function: {r.raw_score.toFixed(4)}
                  </p>
                </div>
              )}
            </div>
            <BehaviorRadar contributions={r?.contributions ?? {}} />
          </div>

          <TerminalLog trace={result?.trace ?? []} />
        </div>
      </div>
    </div>
  );
}
