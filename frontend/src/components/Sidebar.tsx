import { Tooltip } from "antd";
import { useTranslation } from "react-i18next";
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
  labelKey: string;
}

export default function Sidebar({ active, onChange }: { active: Page; onChange: (p: Page) => void }) {
  const { t } = useTranslation();

  const navItems: NavItem[] = [
    { key: "dashboard", icon: <DashboardOutlined />, labelKey: "nav.dashboard" },
    { key: "rules", icon: <NodeIndexOutlined />, labelKey: "nav.rules" },
    { key: "test", icon: <ThunderboltOutlined />, labelKey: "nav.test" },
    { key: "settings", icon: <SettingOutlined />, labelKey: "nav.settings" },
  ];

  return (
    <div
      style={{
        width: 64,
        background: "#fafbfc",
        borderRight: "1px solid #e5e7eb",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: 12,
        flexShrink: 0,
        gap: 2,
      }}
    >
      {navItems.map((item) => {
        const isActive = active === item.key;
        return (
          <Tooltip key={item.key} title={t(item.labelKey)} placement="right" mouseEnterDelay={0.5}>
            <button
              onClick={() => onChange(item.key)}
              style={{
                width: 42,
                height: 42,
                borderRadius: 10,
                border: "none",
                background: isActive ? "#eef2ff" : "transparent",
                color: isActive ? "#6366f1" : "#9ca3af",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 19,
                transition: "all 0.15s",
                position: "relative",
                outline: "none",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = "#6b7280";
                  e.currentTarget.style.background = "#f3f4f6";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = "#9ca3af";
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {item.icon}
              {isActive && (
                <div
                  style={{
                    position: "absolute",
                    left: -4,
                    top: "30%",
                    height: "40%",
                    width: 3,
                    borderRadius: "0 2px 2px 0",
                    background: "#6366f1",
                  }}
                />
              )}
            </button>
          </Tooltip>
        );
      })}
      <div style={{ flex: 1 }} />
      <div style={{ paddingBottom: 14, fontSize: 9, color: "#d1d5db", fontWeight: 600, letterSpacing: 1 }}>
        {t("app.version")}
      </div>
    </div>
  );
}
