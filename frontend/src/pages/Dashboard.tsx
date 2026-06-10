import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Alert, ScoredEvent, Stats } from "../api/types";
import { AlertPanel } from "../components/AlertPanel";
import { BehaviorRadar } from "../components/BehaviorRadar";
import { DeviceDonut } from "../components/DeviceDonut";
import { HourlyTrend } from "../components/HourlyTrend";
import { LoginFeed } from "../components/LoginFeed";
import { RiskGauge } from "../components/RiskGauge";
import { StatCard } from "../components/StatCard";
import { useStats } from "../hooks/useStats";
import { useWebSocket, type WsMessage } from "../hooks/useWebSocket";

export default function Dashboard() {
  const [events, setEvents] = useState<ScoredEvent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const { stats, setStats } = useStats();

  useEffect(() => {
    api.events(30).then(setEvents).catch(() => undefined);
    api.alerts().then(setAlerts).catch(() => undefined);
  }, []);

  const onMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "event") {
      setEvents((prev) => [msg.payload as ScoredEvent, ...prev].slice(0, 30));
    } else if (msg.type === "alert") {
      setAlerts((prev) => [msg.payload as Alert, ...prev].slice(0, 100));
    } else if (msg.type === "stats") {
      setStats(msg.payload as Stats);
    }
  }, []);

  const { connected } = useWebSocket(onMessage);

  async function updateAlert(id: number, status: "ack" | "closed") {
    const updated = await api.updateAlert(id, status);
    setAlerts((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  const latest = events[0];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Security operations</h1>
        <span
          className={`flex items-center gap-2 text-xs ${connected ? "text-green-400" : "text-slate-500"}`}
        >
          <span className={`h-2 w-2 rounded-full ${connected ? "bg-green-400" : "bg-slate-600"}`} />
          {connected ? "live" : "reconnecting…"}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Events (24h)" value={stats?.events_24h ?? 0} icon="📈" />
        <StatCard label="Blocked" value={stats?.blocked ?? 0} accent="#ef4444" icon="🚫" />
        <StatCard label="Anomalies" value={stats?.anomalies ?? 0} accent="#f97316" icon="⚠️" />
        <StatCard label="Active sessions" value={stats?.active_sessions ?? 0} accent="#22c55e" icon="🟢" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-edge bg-panel/60 p-4">
          <h3 className="mb-3 self-start font-semibold">Latest event risk</h3>
          <RiskGauge risk={latest?.risk ?? 0} tier={latest?.tier ?? "LOW"} />
          {latest && (
            <p className="mt-3 text-center text-xs text-slate-400">
              {latest.user} · {latest.threat_type ?? "no threat type"}
            </p>
          )}
        </div>
        <BehaviorRadar contributions={latest?.contributions ?? {}} />
        <DeviceDonut distribution={stats?.device_distribution ?? { known: 0, new: 0 }} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <LoginFeed events={events} />
        <AlertPanel alerts={alerts} onUpdate={updateAlert} />
      </div>

      <HourlyTrend hourly={stats?.hourly ?? new Array(24).fill(0)} />
    </div>
  );
}
