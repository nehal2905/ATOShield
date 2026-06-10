import { useEffect, useRef, useState } from "react";

export interface WsMessage {
  type: "event" | "alert" | "stats";
  payload: unknown;
}

/**
 * Connects to /ws (same origin; the httpOnly auth cookie rides the handshake).
 * Auto-reconnects with exponential backoff. Dispatches parsed messages to the
 * provided handler.
 */
export function useWebSocket(onMessage: (msg: WsMessage) => void) {
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closedByUs = false;
    let backoff = 1000;
    let timer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws`);

      ws.onopen = () => {
        setConnected(true);
        backoff = 1000;
      };
      ws.onmessage = (ev) => {
        try {
          handlerRef.current(JSON.parse(ev.data) as WsMessage);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closedByUs) {
          timer = setTimeout(connect, backoff);
          backoff = Math.min(backoff * 2, 15000);
        }
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { connected };
}
