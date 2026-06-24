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
    color: "#9ca3af",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    transition: "all 0.15s",
    outline: "none",
  };

  return (
    <div
      className="titlebar-drag"
      style={{
        height: 38,
        background: "#ffffff",
        borderBottom: "1px solid #e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      {/* Left: App Icon + Title */}
      <div style={{ display: "flex", alignItems: "center", paddingLeft: 16, gap: 10 }}>
        <div
          style={{
            width: 20,
            height: 20,
            borderRadius: 5,
            background: "#6366f1",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            fontWeight: 700,
            color: "#fff",
          }}
        >
          R
        </div>
        <span style={{ color: "#374151", fontSize: 12, fontWeight: 600, letterSpacing: "-0.2px" }}>
          RAgent Router
        </span>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: backendOnline ? "#10b981" : "#ef4444",
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
          onMouseEnter={(e) => (e.currentTarget.style.background = "#f3f4f6")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          title="Minimize"
        >
          <svg width="12" height="12" viewBox="0 0 12 12">
            <rect x="1" y="5.5" width="10" height="1" rx="0.5" fill="currentColor" />
          </svg>
        </button>

        <button
          style={btnBase}
          onClick={() => api?.maximize()}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#f3f4f6")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          title={maximized ? "Restore" : "Maximize"}
        >
          {maximized ? (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="2.5" y="-0.5" width="8" height="8" rx="1.5" fill="#fff" stroke="currentColor" strokeWidth="1" />
              <rect x="-0.5" y="3.5" width="8" height="8" rx="1.5" fill="#fff" stroke="currentColor" strokeWidth="1" />
            </svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12">
              <rect x="1.5" y="1.5" width="9" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
            </svg>
          )}
        </button>

        <button
          style={{ ...btnBase, color: "#9ca3af" }}
          onClick={() => api?.close()}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "#ef4444";
            e.currentTarget.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "#9ca3af";
          }}
          title="Close"
        >
          <svg width="12" height="12" viewBox="0 0 12 12">
            <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
