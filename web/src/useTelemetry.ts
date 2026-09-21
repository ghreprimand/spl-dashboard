import { useEffect, useState } from "react";
import { validFrame } from "./api";
import type { TelemetryFrame } from "./types";

export function useTelemetry() {
  const [frame, setFrame] = useState<TelemetryFrame | null>(null);
  const [connection, setConnection] = useState<"connecting" | "live" | "stale">(
    "connecting",
  );
  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout>;
    let last = Date.now();
    let seen = false;
    let lastIdentity = "";
    const connect = () => {
      if (stopped) return;
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const current = new WebSocket(
        `${protocol}//${location.host}/ws/telemetry`,
      );
      socket = current;
      last = Date.now();
      current.onmessage = (event) => {
        if (stopped || socket !== current) return;
        try {
          const next: unknown = JSON.parse(event.data);
          if (!validFrame(next)) throw new Error("Unsupported telemetry");
          const identity = `${next.timestamp}:${next.sequence}`;
          if (identity === lastIdentity) return;
          lastIdentity = identity;
          last = Date.now();
          seen = true;
          setFrame(next);
          setConnection("live");
        } catch {
          setConnection("stale");
          current.close();
        }
      };
      current.onclose = () => {
        if (stopped || socket !== current) return;
        setConnection("stale");
        clearTimeout(retry);
        retry = setTimeout(connect, 1500);
      };
      current.onerror = () => current.close();
    };
    connect();
    const timer = setInterval(() => {
      if (Date.now() - last > 2000) setConnection("stale");
      if (Date.now() - last > 5000 && socket && socket.readyState < 2)
        socket.close();
    }, 500);
    const wake = () => {
      if (
        document.visibilityState === "visible" &&
        (seen || Date.now() - last > 2000)
      ) {
        setConnection("stale");
        clearTimeout(retry);
        const old = socket;
        socket = null;
        old?.close();
        connect();
      }
    };
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("pageshow", wake);
    return () => {
      stopped = true;
      clearTimeout(retry);
      clearInterval(timer);
      socket?.close();
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("pageshow", wake);
    };
  }, []);
  return { frame, connection };
}
