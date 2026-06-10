export type Tier = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ScoredEvent {
  id: number | null;
  user: string;
  ip: string;
  device_fp: string;
  geo_lat: number;
  geo_lon: number;
  timestamp: string;
  login_hour: number;
  frequency: number;
  failed_attempts: number;
  ip_change: number;
  device_change: number;
  geo_velocity: number;
  impossible_travel: boolean;
  raw_score: number;
  risk: number;
  tier: Tier;
  action: string;
  contributions: Record<string, number>;
  alert_id?: number | null;
  threat_type?: string | null;
}

export interface Alert {
  id: number;
  event_id: number;
  severity: string;
  threat_type: string;
  description: string;
  affected_user: string;
  source_ip: string;
  risk: number;
  status: "open" | "ack" | "closed";
  created_at: string;
}

export interface Stats {
  events_24h: number;
  blocked: number;
  anomalies: number;
  active_sessions: number;
  hourly: number[];
  device_distribution: { known: number; new: number };
  tier_distribution: Record<string, number>;
}

export interface PipelineStep {
  step: string;
  detail: string;
  data?: Record<string, unknown> | null;
}

export interface SimulateResult {
  result: ScoredEvent;
  trace: PipelineStep[];
}

export interface SimulateInput {
  login_hour: number;
  ip_change: number;
  device_change: number;
  frequency: number;
  geo_velocity: number;
  failed_attempts: number;
}

export interface CurrentUser {
  id: number;
  username: string;
  role: string;
}
