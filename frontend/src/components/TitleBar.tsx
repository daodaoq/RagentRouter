import { useEffect, useState } from "react";

// @ts-ignore - injected by preload
const api = window.electronAPI;

export default function TitleBar() {
  const [maximized, setMaximized] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    if (!api) return;
    api.isMaximized().then(setMaximized);
    api.onMaximizeChange((v: boolean) => setMaximized(v));
    api.getBackendStatus().then((s: { online: boolean }) => setBackendOnline(s.online));
    api.onBackendStatus((s: { online: boolean }) => setBackendOnline(s.online));
  }, []);

  const btnBase: React.CSSProperties = {
    width: 46,
    height: 38,
    border: "none",
    background: "transparent",
    color: "#999",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
    transition: "all 0.15s",
    outline: "none",
  };

  return (
    <div
      className="titlebar-drag"
      style={{
        height: 38,
        background: "linear-gradient(180deg, #12122a 0%, #0e0e24 100%)",
        borderBottom: "1px solid #1a1a40",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      {/* Left: App Icon + Title */}
      <div style={{ display: "flex", alignItems: "center", paddingLeft: 14, gap: 10 }}>
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: 4,
            background: "linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            fontWeight: 800,
            color: "#fff",
          }}
        >
          R
        </div>
        <span style={{ color: "#ccc", fontSize: 12, fontWeight: 500 }}>
          RAgent Router
        </span>
        {/* Backend status dot */}
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: backendOnline ? "#00b894" : "#d63031",
            boxShadow: `0 0 6px ${backendOnline ? "#00b894" : "#d63031"}`,
            transition: "background 0.3s",
          }}
          title={backendOnline ? "Backend Online" : "Backend Offline"}
        />
      </div>

      {/* Right: Window Controls */}
      <div className="titlebar-no-drag" style={{ display: "flex", height: "100%" }}>
        <button
          style={btnBase}
          onClick={() => api?.minimize()}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          title="Minimize"
        >
          <svg width="12" height="12" viewBox="0 0 12 12">
            <rect x="1" y="5.5" width="10" height="1" fill="currentColor" />
          </svg>
        </button>

        <button
          style={btnBase}
          onClick={() => api?.maximize()}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          title={maximized ? "Restore" : "Maximize"}
        >
          {maximized ? (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="2" y="0" width="8" height="8" rx="1" fill="none" stroke="currentColor" strokeWidth="1.2" />
              <rect x="0" y="4" width="8" height="8" rx="1" fill="#0e0e24" stroke="currentColor" strokeWidth="1.2" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="1" y="1" width="10" height="10" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
            </svg>
          )}
        </button>

        <button
          style={{ ...btnBase, color: "#e0e0e0" }}
          onClick={() => api?.close()}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "#d63031";
            e.currentTarget.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "#e0e0e0";
          }}
          title="Close to Tray"
        >
          <svg width="12" height="12" viewBox="0 0 12 12">
            <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
