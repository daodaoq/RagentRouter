import { useEffect, useState } from "react";
import TitleBar from "./components/TitleBar";
import Sidebar from "./components/Sidebar";
import StatusBar from "./components/StatusBar";
import Dashboard from "./pages/Dashboard";
import RuleManager from "./components/RuleManager";
import TestConsole from "./components/TestConsole";
import Settings from "./components/Settings";
import { useDashboardStore } from "./stores/dashboard";

type Page = "dashboard" | "rules" | "test" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const { overview, fetchAll } = useDashboardStore();

  // Auto-refresh dashboard data
  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 15000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
        background: "var(--bg-primary)",
      }}
    >
      {/* Custom Title Bar */}
      <TitleBar />

      {/* Main body: Sidebar + Content */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Sidebar active={page} onChange={setPage} />

        {/* Content area */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            background:
              "radial-gradient(ellipse at 50% 0%, rgba(108, 92, 231, 0.04) 0%, transparent 60%)",
          }}
        >
          {page === "dashboard" && <Dashboard />}
          {page === "rules" && <RuleManager />}
          {page === "test" && <TestConsole />}
          {page === "settings" && <Settings />}
        </div>
      </div>

      {/* Status Bar */}
      <StatusBar
        requestCount={overview?.total_requests}
        todayCost={overview?.today_cost}
      />
    </div>
  );
}
