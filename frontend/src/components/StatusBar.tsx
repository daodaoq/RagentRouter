import { useEffect, useState } from "react";

// @ts-ignore
const api = window.electronAPI;

interface Props {
  requestCount?: number;
  todayCost?: number;
}

export default function StatusBar({ requestCount, todayCost }: Props) {
  const [backendOnline, setBackendOnline] = useState(false);
  const [backendPort, setBackendPort] = useState(8000);
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    // Clock
    const clock = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);

    // Backend status from Electron
    if (api) {
      api.getBackendStatus().then((s: { online: boolean; port: number }) => {
        setBackendOnline(s.online);
        setBackendPort(s.port);
      });
      api.onBackendStatus((s: { online: boolean; port: number }) => {
        setBackendOnline(s.online);
        setBackendPort(s.port);
      });
    }

    return () => clearInterval(clock);
  }, []);

  return (
    <div
      style={{
        height: 32,
        background: "#0c0c20",
        borderTop: "1px solid #1a1a40",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        flexShrink: 0,
        fontSize: 11,
        color: "#555",
      }}
    >
      {/* Left: backend status */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: backendOnline ? "#00b894" : "#d63031",
              display: "inline-block",
            }}
          />
          <span style={{ color: backendOnline ? "#00b894" : "#d63031" }}>
            {backendOnline ? `Backend :${backendPort}` : "Backend Offline"}
          </span>
        </div>

        {requestCount !== undefined && (
          <span>
            Requests: <b style={{ color: "#888" }}>{requestCount}</b>
          </span>
        )}

        {todayCost !== undefined && (
          <span>
            Today: <b style={{ color: "#888" }}>${todayCost.toFixed(4)}</b>
          </span>
        )}
      </div>

      {/* Right: clock + electron info */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        {api ? (
          <span style={{ color: "#6c5ce7", fontSize: 10 }}>⚡ Electron</span>
        ) : (
          <span style={{ color: "#555", fontSize: 10 }}>Browser</span>
        )}
        <span>{time}</span>
      </div>
    </div>
  );
}
