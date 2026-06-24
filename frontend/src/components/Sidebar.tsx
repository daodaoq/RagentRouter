import { Tooltip } from "antd";
import {
  DashboardOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from "@ant-design/icons";

type Page = "dashboard" | "rules" | "test" | "settings";

interface NavItem {
  key: Page;
  icon: React.ReactNode;
  label: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "rules", icon: <NodeIndexOutlined />, label: "Route Rules" },
  { key: "test", icon: <ThunderboltOutlined />, label: "Test Console" },
  { key: "settings", icon: <SettingOutlined />, label: "Settings" },
];

interface Props {
  active: Page;
  onChange: (page: Page) => void;
}

export default function Sidebar({ active, onChange }: Props) {
  return (
    <div
      style={{
        width: 64,
        background: "linear-gradient(180deg, #0e0e24 0%, #0a0a1e 100%)",
        borderRight: "1px solid #1a1a40",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: 12,
        flexShrink: 0,
        gap: 4,
      }}
    >
      {navItems.map((item) => {
        const isActive = active === item.key;
        return (
          <Tooltip key={item.key} title={item.label} placement="right" mouseEnterDelay={0.5}>
            <button
              onClick={() => onChange(item.key)}
              style={{
                width: 42,
                height: 42,
                borderRadius: 10,
                border: "none",
                background: isActive ? "rgba(108, 92, 231, 0.2)" : "transparent",
                color: isActive ? "#a29bfe" : "#555",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 20,
                transition: "all 0.2s",
                position: "relative",
                outline: "none",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = "#888";
                  e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = "#555";
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {item.icon}
              {/* Active indicator bar */}
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    left: -4,
                    top: "30%",
                    height: "40%",
                    width: 3,
                    borderRadius: "0 2px 2px 0",
                    background: "linear-gradient(180deg, #6c5ce7, #a29bfe)",
                  }}
                />
              )}
            </button>
          </Tooltip>
        );
      })}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Bottom: version tag */}
      <div
        style={{
          paddingBottom: 14,
          fontSize: 9,
          color: "#444",
          fontWeight: 600,
          letterSpacing: 1,
        }}
      >
        v0.1
      </div>
    </div>
  );
}
