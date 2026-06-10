import type { Tier } from "../api/types";

export function tierColor(tier: Tier | string): string {
  switch (tier) {
    case "CRITICAL":
      return "#ef4444";
    case "HIGH":
      return "#f97316";
    case "MEDIUM":
      return "#eab308";
    default:
      return "#22c55e";
  }
}

export function riskColor(risk: number): string {
  if (risk >= 75) return "#ef4444";
  if (risk >= 50) return "#f97316";
  if (risk >= 25) return "#eab308";
  return "#22c55e";
}

export function tierBadgeClass(tier: Tier | string): string {
  switch (tier) {
    case "CRITICAL":
      return "bg-red-500/15 text-red-400 border border-red-500/30";
    case "HIGH":
      return "bg-orange-500/15 text-orange-400 border border-orange-500/30";
    case "MEDIUM":
      return "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30";
    default:
      return "bg-green-500/15 text-green-400 border border-green-500/30";
  }
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.max(0, Math.floor(diff))}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
