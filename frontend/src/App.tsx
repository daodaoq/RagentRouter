import { useEffect, useState } from "react";
import TitleBar from "./components/TitleBar";
import Sidebar from "./components/Sidebar";
import StatusBar from "./components/StatusBar";
import Dashboard from "./pages/Dashboard";
import TrafficMonitor from "./pages/TrafficMonitor";
import RuleManager from "./components/RuleManager";
import TestConsole from "./components/TestConsole";
import Providers from "./components/Providers";
import Settings from "./components/Settings";
import { useDashboardStore } from "./stores/dashboard";

type Page = "providers" | "traffic" | "dashboard" | "rules" | "test" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("providers");
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
        background: "#ffffff",
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
            overflowX: "hidden",
            overflowY: "auto",
            background: "#f8f9fa",
            minWidth: 0,
          }}
        >
          {page === "providers" && <Providers />}
          {page === "traffic" && <TrafficMonitor />}
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
