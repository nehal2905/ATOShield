import type { Alert } from "../api/types";
import { timeAgo } from "../lib/format";

interface Props {
  alerts: Alert[];
  onUpdate: (id: number, status: "ack" | "closed") => void;
}

function sevColor(sev: string): string {
  if (sev === "critical") return "border-red-500/40 bg-red-500/10";
  if (sev === "high") return "border-orange-500/40 bg-orange-500/10";
  return "border-yellow-500/40 bg-yellow-500/10";
}

export function AlertPanel({ alerts, onUpdate }: Props) {
  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">Active alerts</h3>
        <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-xs text-red-400">
          {alerts.filter((a) => a.status === "open").length} open
        </span>
      </div>
      <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
        {alerts.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-500">No alerts. All clear.</div>
        )}
        {alerts.map((a) => (
          <div key={a.id} className={`rounded-xl border p-3 ${sevColor(a.severity)}`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">{a.threat_type}</div>
                <div className="mt-0.5 text-xs text-slate-300">{a.description}</div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {a.affected_user} · {a.source_ip} · risk {a.risk} · {timeAgo(a.created_at)}
                </div>
              </div>
              <span className="rounded bg-black/30 px-2 py-0.5 text-[10px] uppercase">
                {a.status}
              </span>
            </div>
            {a.status !== "closed" && (
              <div className="mt-2 flex gap-2">
                {a.status === "open" && (
                  <button
                    onClick={() => onUpdate(a.id, "ack")}
                    className="rounded-md border border-edge px-2 py-1 text-xs hover:bg-white/5"
                  >
                    Acknowledge
                  </button>
                )}
                <button
                  onClick={() => onUpdate(a.id, "closed")}
                  className="rounded-md border border-edge px-2 py-1 text-xs hover:bg-white/5"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
