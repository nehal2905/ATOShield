import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Stats } from "../api/types";

/**
 * Fetches aggregate stats once on mount. Live updates arrive separately via the
 * WebSocket "stats" message (see Dashboard), which calls `setStats`.
 */
export function useStats() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.stats().then(setStats).catch(() => undefined);
  }, []);

  return { stats, setStats };
}
