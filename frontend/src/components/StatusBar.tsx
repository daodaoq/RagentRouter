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
    const clock = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);

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
        height: 30,
        background: "#fafbfc",
        borderTop: "1px solid #e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        flexShrink: 0,
        fontSize: 11,
        color: "#9ca3af",
      }}
    >
      {/* Left */}
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: backendOnline ? "#10b981" : "#ef4444",
              display: "inline-block",
            }}
          />
          <span
            style={{
              color: backendOnline ? "#10b981" : "#ef4444",
              fontWeight: 500,
            }}
          >
            {backendOnline ? `Backend :${backendPort}` : "Offline"}
          </span>
        </div>

        {requestCount !== undefined && (
          <span>
            Requests: <b style={{ color: "#6b7280" }}>{requestCount}</b>
          </span>
        )}

        {todayCost !== undefined && (
          <span>
            Today: <b style={{ color: "#6b7280" }}>${todayCost.toFixed(4)}</b>
          </span>
        )}
      </div>

      {/* Right */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <span style={{ color: "#6366f1", fontSize: 10, fontWeight: 600 }}>
          {api ? "Electron" : ""}
        </span>
        <span style={{ color: "#9ca3af" }}>{time}</span>
      </div>
    </div>
  );
}
