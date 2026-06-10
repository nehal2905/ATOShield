import type { ScoredEvent } from "../api/types";
import { tierBadgeClass, timeAgo } from "../lib/format";

export function LoginFeed({ events }: { events: ScoredEvent[] }) {
  return (
    <div className="rounded-2xl border border-edge bg-panel/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">Live login feed</h3>
        <span className="text-xs text-slate-500">last {events.length}</span>
      </div>
      <div className="max-h-[420px] space-y-1 overflow-y-auto pr-1">
        {events.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-500">
            Waiting for events… run the event generator or POST to /api/events.
          </div>
        )}
        {events.map((e, i) => (
          <div
            key={e.id ?? i}
            className="flex items-center justify-between rounded-lg border border-transparent px-2 py-2 hover:border-edge hover:bg-white/5"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium">{e.user}</span>
                {e.impossible_travel && (
                  <span className="rounded bg-red-500/15 px-1.5 text-[10px] text-red-400">
                    impossible travel
                  </span>
                )}
              </div>
              <div className="truncate text-xs text-slate-500">
                {e.ip} · {e.geo_velocity > 0 ? `${e.geo_velocity.toFixed(0)} km/h · ` : ""}
                {timeAgo(e.timestamp)}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tabular-nums">{e.risk}</span>
              <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${tierBadgeClass(e.tier)}`}>
                {e.tier}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
